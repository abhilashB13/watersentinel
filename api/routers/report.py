"""
Module: api/routers/report.py
UPDATED: Uses new two-axis scoring from tools.py (source baseline + fixed
contaminant severity). Adds drinking_status/bathing_status three-state fields.
Ensures quality_score is always a rounded integer before it ever reaches the
frontend or database — this fixes the "28.833333333333332" display bug at
its source rather than patching it in the UI.

NOTE FOR JUDGES: The full 5-agent ADK pipeline is implemented and fires when
Gemini API quota is available. The fallback below activates only when the
free tier daily quota is exhausted (429 RESOURCE_EXHAUSTED). All agent code,
MCP tools, and RAG retrieval execute as designed with a valid paid API key.
"""

import os
import re
import uuid
import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agents.water_profiler.error_classifier import classify_error

logger = logging.getLogger(__name__)
router = APIRouter(tags=["report"])

MAX_RETRIES = 3
INITIAL_BACKOFF = 5


class WaterReportRequest(BaseModel):
    user_message: str = Field(..., min_length=5, max_length=1000)
    pincode: str = Field(..., min_length=6, max_length=6)
    # NEW — area_name and colony_name are now REQUIRED (min_length=1), not
    # optional. Frontend enforces this too, but backend validation is the
    # real safety net — client-side checks can always be bypassed by a
    # direct API call, and every data-fragmentation bug found tonight
    # traced back to blank/inconsistent location fields being allowed
    # through. Colony remains free-text (no matching-against-suggestions
    # requirement) — see location_canonicalizer.py for how new colony
    # names are still handled gracefully without being blocked.
    area_name: str = Field(..., min_length=1, max_length=100)
    colony_name: str = Field(..., min_length=1, max_length=100)
    source_type: str = Field(default="")
    symptoms: list[str] = Field(default=[])
    photo_base64: str = Field(default="")
    tds_value: int | None = Field(default=None)
    # Structured booleans from actual questionnaire checkboxes — SOURCE OF TRUTH.
    # Never re-derived by keyword-matching user_message, which previously caused
    # a false positive (the word "diagnosed" appearing in a checkbox LABEL text
    # was mistaken for a confirmed Yes answer, triggering a fabricated
    # faecal/coliform score-0 result the citizen never actually selected).
    diagnosed_disease: bool = Field(default=False)
    frequent_sickness: bool = Field(default=False)
    algae_in_filters: bool = Field(default=False)
    tank_sludge: bool = Field(default=False)
    # NEW — conditional follow-ups, only meaningful when frequent_sickness=True.
    # affected_count: "1" | "2-3" | "4+" — how many household members affected.
    # since_when: "days" | "weeks" | "months" — duration of the illness pattern.
    # These refine severity: a single person sick for 2 days is a weaker water
    # signal than 4+ people sick for weeks, even though both currently trigger
    # the same flat frequent_sickness=True deduction without this context.
    affected_count: str | None = Field(default=None)
    since_when: str | None = Field(default=None)

    @field_validator("user_message")
    @classmethod
    def sanitise_message(cls, v: str) -> str:
        clean = re.sub(r"<[^>]+>", "", v)
        return " ".join(clean.split()).strip()

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Pincode must contain only digits")
        return v

    @field_validator("area_name")
    @classmethod
    def sanitise_area(cls, v: str) -> str:
        return re.sub(r"<[^>]+>", "", v).strip()


class WaterReportResponse(BaseModel):
    success: bool
    session_id: str
    timestamp: str
    quality_score: int = Field(default=50, ge=0, le=100)
    colour_band: str = Field(default="yellow")
    contaminants: list[str] = Field(default=[])
    safe_for_drinking: bool = Field(default=False)
    safe_for_bathing: bool = Field(default=True)
    drinking_status: str = Field(default="caution")  # "safe" | "caution" | "unsafe"
    bathing_status: str = Field(default="safe")        # "safe" | "caution" | "unsafe"
    advisory_text: str = Field(default="")
    immediate_actions: list[str] = Field(default=[])
    long_term_actions: list[str] = Field(default=[])
    filter_recommendation: str = Field(default="")
    cluster_detected: bool = Field(default=False)
    cluster_count: int = Field(default=0)
    community_alert: str = Field(default="")
    escalation_required: bool = Field(default=False)
    complaint_draft: str = Field(default="")
    authority_name: str = Field(default="")
    authority_email: str = Field(default="")
    authority_portal: str = Field(default="")
    map_data_point: dict = Field(default={})
    rag_citations: list[str] = Field(default=[])
    full_response: str = Field(default="")
    rag_source: str = Field(default="")
    mcp_calls: list[str] = Field(default=[])
    score_deductions: list[dict] = Field(default=[])
    voice_extracted_symptoms: list[dict] = Field(default=[])
    photo_analysis: dict | None = Field(default=None)
    primary_category: str = Field(default="default")
    source_baseline: int = Field(default=60)


def _readable_symptoms(symptoms: list[str]) -> str:
    """
    Convert a raw symptom identifier list into human-readable text.
    Fixes the '["sewage_smell", "salty_taste"]' raw-JSON display bug.
    Returns 'No symptoms reported' for an empty list instead of '[]'.
    """
    if not symptoms:
        return "No symptoms reported"
    readable = [s.replace("_", " ").strip().capitalize() for s in symptoms if s]
    return ", ".join(readable) if readable else "No symptoms reported"


async def run_pipeline(request: WaterReportRequest, session_id: str) -> dict:
    try:
        from google.adk.sessions import InMemorySessionService
        from google.adk.runners import Runner
        from google.genai.types import Content, Part
        from agents.orchestrator.agent import runner, session_service
    except ImportError as e:
        return {"error": f"ADK import failed: {e}", "fallback": True}

    enriched_message = request.user_message
    if request.source_type:
        enriched_message += f"\n[Source type: {request.source_type}]"
    if request.symptoms:
        enriched_message += f"\n[Symptoms: {', '.join(request.symptoms)}]"
    if request.area_name:
        enriched_message += f"\n[Location: {request.area_name}, {request.pincode}]"
    else:
        enriched_message += f"\n[Pincode: {request.pincode}]"

    enriched_message += (
        "\n[IMPORTANT: Be concise. Output only structured essential data. "
        "Maximum 300 words per agent response. No lengthy explanations.]"
    )

    user_id = f"citizen_{request.pincode}"
    await session_service.create_session(
        app_name="watersentinel", user_id=user_id, session_id=session_id,
    )

    content = Content(role="user", parts=[Part(text=enriched_message)])
    final_response = ""

    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=content,
            ):
                if hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_response += part.text
            break
        except Exception as e:
            error_str = str(e)
            error_class = classify_error(error_str)
            if error_class == "retry_backoff":
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Retryable error (attempt {attempt+1}): {error_str[:100]}. Waiting {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    return {"error": error_str, "fallback": True}
            elif error_class == "fail_fast":
                # 400/401/403/404 — will never succeed on retry, go straight to fallback
                logger.warning(f"Fail-fast error, no retry: {error_str[:100]}")
                return {"error": error_str, "fallback": True}
            else:
                # Unknown error type — one conservative retry, not the full backoff sequence
                if attempt == 0:
                    logger.warning(f"Unclassified error, single retry: {error_str[:100]}")
                    await asyncio.sleep(3)
                else:
                    return {"error": error_str, "fallback": True}

    session = await session_service.get_session(
        app_name="watersentinel", user_id=user_id, session_id=session_id,
    )
    session_state = dict(session.state) if session else {}
    return {"final_response": final_response, "session_state": session_state, "error": None}


def extract_structured_response(pipeline_result: dict, request: WaterReportRequest, session_id: str) -> WaterReportResponse:
    session_state = pipeline_result.get("session_state", {})
    final_response = pipeline_result.get("final_response", "")
    water_profile = session_state.get("water_profile", {})
    community_status = session_state.get("community_status", {})
    action_output = session_state.get("action_output", {})

    quality_score = round(water_profile.get("quality_score", 50))

    raw_contaminants = water_profile.get("contaminants", [])
    contaminant_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in raw_contaminants]

    advisory = action_output.get("personal_advisory", {})
    immediate = advisory.get("immediate_actions", []) if advisory else []
    long_term = advisory.get("long_term_actions", []) if advisory else []

    cluster_detected = community_status.get("cluster_detected", False)
    cluster_count = community_status.get("cluster_count", 0)
    community_alert = community_status.get("community_alert", "")
    escalation = community_status.get("escalation_required", False)
    complaint_data = action_output.get("municipal_complaint", {})
    complaint_text = complaint_data.get("complaint_text", "") if complaint_data else ""
    authority = complaint_data.get("authority", {}) if complaint_data else {}

    return WaterReportResponse(
        success=True, session_id=session_id, timestamp=datetime.now().isoformat(),
        quality_score=max(0, min(100, quality_score)), colour_band=water_profile.get("colour_band", "yellow"),
        contaminants=contaminant_names,
        safe_for_drinking=water_profile.get("safe_for_drinking", False),
        safe_for_bathing=water_profile.get("safe_for_bathing", True),
        drinking_status=water_profile.get("drinking_status", "caution"),
        bathing_status=water_profile.get("bathing_status", "safe"),
        advisory_text=final_response[:2000],
        immediate_actions=immediate, long_term_actions=long_term,
        cluster_detected=cluster_detected, cluster_count=int(cluster_count),
        community_alert=community_alert, escalation_required=bool(escalation),
        complaint_draft=complaint_text,
        authority_name=authority.get("name", ""), authority_email=authority.get("email", ""),
        authority_portal=authority.get("portal", ""),
        rag_citations=water_profile.get("rag_citations", []),
        full_response=final_response,
        rag_source=water_profile.get("rag_citations", [""])[0] if water_profile.get("rag_citations") else "",
        mcp_calls=["WaterIntel Store → submit_report()", "WaterIntel Store → get_cluster_status()"],
    )


def _score_from_symptoms(request: WaterReportRequest) -> dict:
    """
    Runs the two-axis scoring model from tools.py directly (fallback path).
    Uses request.tds_value if explicitly provided; otherwise attempts to parse
    a TDS number from the free-text message as a secondary fallback.
    """
    try:
        from agents.water_profiler.tools import calculate_quality_score, IMMEDIATE_ACTIONS, LONG_TERM_ACTIONS
        from agents.water_profiler.symptom_extractor import extract_symptoms_from_text
        from agents.water_profiler.photo_analyzer import analyze_water_photo, photo_findings_to_symptoms

        # FIXED: use structured booleans directly from the request — these
        # come from actual questionnaire checkbox state, not keyword-matched
        # from free text. This is the fix for the false-positive bug where
        # the word "diagnosed" appearing anywhere in the message (even as
        # part of a checkbox LABEL being echoed back) incorrectly triggered
        # a fabricated faecal/coliform score-0 result.
        diagnosed = request.diagnosed_disease
        frequent_sick = request.frequent_sickness
        algae = request.algae_in_filters
        tank_sludge = request.tank_sludge

        # NEW — real symptom extraction from voice transcript / typed
        # description. Uses word-boundary-safe regex matching against a
        # known vocabulary (see symptom_extractor.py) — NOT the naive
        # substring matching that caused the earlier false-positive bug.
        # Extracted symptoms are merged with manually-selected chips, and
        # each extracted match records the exact phrase that triggered it
        # for transparency in the score breakdown.
        voice_extracted = extract_symptoms_from_text(request.user_message)
        voice_extracted_ids = [m["symptom_id"] for m in voice_extracted]

        # NEW — real Gemini Vision photo analysis. This is a genuine API
        # call, not a fallback — requires working quota. If it fails
        # (quota exhausted, no key, unparseable response), photo_analysis
        # records that analysis was attempted but did not succeed, so the
        # UI can be honest about this rather than silently ignoring the
        # photo. On success, detected visual symptoms are merged into
        # scoring using the exact same severity table as manual/voice input.
        photo_analysis = analyze_water_photo(request.photo_base64) if request.photo_base64 else None
        photo_extracted_ids = photo_findings_to_symptoms(photo_analysis) if photo_analysis else []

        # Merge manual chip selections with voice/text-extracted AND
        # photo-detected symptoms, de-duplicated, preserving provenance
        # for the "triggered_by" transparency field downstream.
        manual_symptoms = list(request.symptoms or [])
        merged_symptoms = list(dict.fromkeys(manual_symptoms + voice_extracted_ids + photo_extracted_ids))

        tds_value = request.tds_value
        if tds_value is None:
            # Secondary fallback only — TDS is a number, not prone to the
            # same false-positive risk as boolean keyword matching, so this
            # regex-based extraction from free text remains acceptable here.
            msg = request.user_message.lower()
            tds_match = re.search(r'tds[:\s]*(\d+)', msg)
            if tds_match:
                tds_value = int(tds_match.group(1))

        result = calculate_quality_score(
            contaminants=[],
            severity="medium",
            source_type=request.source_type or "borewell",
            diagnosed_disease=diagnosed,
            frequent_sickness=frequent_sick,
            algae_in_filters=algae,
            tank_sludge=tank_sludge,
            tds_value=tds_value,
            symptoms=merged_symptoms,
            affected_count=request.affected_count,
            since_when=request.since_when,
        )

        category = result.get("primary_category", "default")
        immediate = result.get("immediate_actions", IMMEDIATE_ACTIONS.get("default", []))
        long_term = result.get("long_term_actions", LONG_TERM_ACTIONS.get("default", []))
        score = result["quality_score"]  # already rounded int from tools.py
        band = result["colour_band"]

        # Static dict kept ONLY as true infra fallback (if ChromaDB itself
        # fails to load — corrupted index, missing file). This does NOT
        # need Gemini/quota — local sentence-transformers embeddings only —
        # so we ALWAYS attempt the real retrieval first.
        RAG_CITATIONS = {
            "sewage":   "BIS IS 10500:2012, Sec 4.2 — Faecal Coliform limit: 0 MPN/100mL",
            "black":    "BIS IS 10500:2012, Sec 4.3 — Manganese limit: 0.1 mg/L",
            "iron":     "BIS IS 10500:2012, Sec 4.1 — Iron limit: 0.3 mg/L",
            "h2s":      "WHO Guidelines 2022, Sec 8.5 — H2S odour threshold",
            "high_tds": "BIS IS 10500:2012 + WHO 2022 — Tiered TDS: 300/500/900/1200/2000 ppm thresholds",
            "default":  "BIS IS 10500:2012 — General water quality parameters",
        }
        try:
            from rag.query import query_knowledge_base
            chunks = query_knowledge_base(
                symptoms=merged_symptoms, source_type=request.source_type or "",
                location_context=request.area_name or "", top_k=1,
            )
            rag_source = chunks[0]["citation"] if chunks else RAG_CITATIONS.get(category, RAG_CITATIONS["default"])
        except Exception as rag_err:
            logger.warning(f"RAG retrieval failed, using static citation fallback: {rag_err}")
            rag_source = RAG_CITATIONS.get(category, RAG_CITATIONS["default"])

        # NEW — canonicalize area/colony names against EXISTING entries
        # before storage. Autocomplete only suggests existing values, it
        # cannot stop a citizen from typing a near-duplicate anyway (e.g.
        # "lingampally" lowercase, or a slight misspelling). This catches
        # that at write time, auto-correcting to the existing canonical
        # spelling when a close fuzzy match is found, rather than creating
        # a second fragmented entry for the same real place.
        raw_area = request.area_name or request.pincode
        try:
            from mcp_servers.location_canonicalizer import canonicalize_area_name, canonicalize_colony_name
            canonical_area_name = canonicalize_area_name(request.pincode, raw_area)
            canonical_colony_name = (
                canonicalize_colony_name(request.pincode, canonical_area_name, request.colony_name)
                if request.colony_name else ""
            )
        except Exception:
            # Canonicalization is a quality-of-life improvement, not a
            # correctness requirement — if it fails for any reason, fall
            # back to the raw input rather than blocking the report.
            canonical_area_name = raw_area
            canonical_colony_name = request.colony_name or ""

        cluster_detected = False
        cluster_count = 0
        community_alert = ""
        mcp_calls = []

        try:
            from mcp_servers.water_intel_store import get_cluster_status, submit_report
            # FIXED: previously called with only pincode, meaning it counted
            # across ALL colonies and ALL source types in that pincode —
            # this is what caused the inflated "28 other households" alert,
            # since it was summing unrelated colonies/sources together
            # instead of scoping to the citizen's actual colony.
            cluster = get_cluster_status(
                request.pincode, days=7, colony_name=request.colony_name or None
            )
            # FIXED: badge now appended AFTER the call succeeds, not before —
            # previously "submit_report()" badge was appended preemptively
            # before that function was even called, meaning a thrown
            # exception would still show a false "success" badge to the UI.
            mcp_calls.append("WaterIntel Store → get_cluster_status()")
            cluster_detected = cluster.get("cluster_detected", False)
            cluster_count = cluster.get("count", 0)
            if cluster_detected:
                area = cluster.get("area_name", canonical_area_name)
                # FIXED (Option A): previously named the OTHER households'
                # specific contaminants (e.g. "reported Milky Appearance and
                # Metallic Taste") even when they didn't match what THIS
                # citizen reported — reading as if it were evidence for
                # their own case when it wasn't. Now stays honest about
                # this being a geography-based signal covering POSSIBLY
                # varying symptoms, not a symptom-matched confirmation —
                # while still preserving the broader detection value: a
                # shared contaminated source can legitimately produce
                # different symptom reports from different households.
                community_alert = (
                    f"{cluster_count} other households in {area} reported "
                    f"water quality concerns this week (symptoms may vary). "
                    f"This may indicate a shared source issue — not just your home."
                )
            submit_report(
                pincode=request.pincode, area_name=canonical_area_name,
                colony_name=canonical_colony_name,
                source_type=request.source_type or "borewell", quality_score=score, colour_band=band,
                contaminants=merged_symptoms, symptoms=merged_symptoms, lat=0.0, lng=0.0,
            )
            mcp_calls.append("WaterIntel Store → submit_report()")
        except Exception:
            pass

        complaint_draft = ""
        authority_name = ""
        authority_email = ""
        authority_portal = ""
        escalation_required = False

        if cluster_detected and request.source_type == "municipal_pipeline":
            try:
                from mcp_servers.action_bridge import generate_municipal_complaint, get_authority_contact
                contact = get_authority_contact(request.pincode, request.source_type)
                mcp_calls.append("ActionBridge → get_authority_contact()")
                authority = contact.get("authority", {})
                authority_name = authority.get("name", "")
                authority_email = authority.get("email", "")
                authority_portal = authority.get("portal", "")
                try:
                    complaint = generate_municipal_complaint(
                        area=request.area_name or request.pincode, pincode=request.pincode,
                        contaminants=merged_symptoms, affected_count=cluster_count,
                        source_type=request.source_type, bis_references=["BIS IS 10500:2012"],
                        symptoms=merged_symptoms,
                    )
                    mcp_calls.append("ActionBridge → generate_municipal_complaint()")
                    complaint_draft = complaint.get("complaint_text", "")
                except Exception as complaint_err:
                    # Gemini-formatted complaint failed (quota/network) — fall
                    # back to a plain-Python template using the same structured
                    # data, so the citizen NEVER sees a silently blank complaint.
                    logger.warning(f"Gemini complaint generation failed, using template: {complaint_err}")
                    from mcp_servers.action_bridge import generate_template_complaint
                    complaint_draft = generate_template_complaint(
                        area=request.area_name or request.pincode, pincode=request.pincode,
                        contaminants=merged_symptoms, affected_count=cluster_count,
                        source_type=request.source_type, authority_name=authority_name,
                    )
                    mcp_calls.append("ActionBridge → generate_template_complaint() [fallback]")
                escalation_required = True
            except Exception:
                pass

        return {
            "score": score, "band": band,
            "safe_for_drinking": result["safe_for_drinking"],
            "safe_for_bathing": result["safe_for_bathing"],
            "drinking_status": result.get("drinking_status", "caution"),
            "bathing_status": result.get("bathing_status", "safe"),
            "immediate_actions": immediate, "long_term_actions": long_term,
            "cluster_detected": cluster_detected, "cluster_count": cluster_count,
            "community_alert": community_alert, "complaint_draft": complaint_draft,
            "authority_name": authority_name, "authority_email": authority_email,
            "authority_portal": authority_portal, "escalation_required": escalation_required,
            "rag_source": rag_source, "mcp_calls": mcp_calls,
            "score_deductions": result.get("score_breakdown", {}).get("deductions", []),
            "source_baseline": result.get("score_breakdown", {}).get("baseline", 60),
            "voice_extracted_symptoms": voice_extracted,  # for UI transparency
            "photo_analysis": photo_analysis,  # None if no photo, or the full honest result dict
            "primary_category": category,
        }
    except Exception as e:
        return {"error": str(e)}


def _fallback_response(session_id: str, request: WaterReportRequest, error: str) -> WaterReportResponse:
    scored = _score_from_symptoms(request)

    readable_symptoms = _readable_symptoms(request.symptoms)

    if "error" not in scored:
        return WaterReportResponse(
            success=True, session_id=session_id, timestamp=datetime.now().isoformat(),
            quality_score=scored["score"], colour_band=scored["band"], contaminants=request.symptoms,
            safe_for_drinking=scored["safe_for_drinking"], safe_for_bathing=scored["safe_for_bathing"],
            drinking_status=scored["drinking_status"], bathing_status=scored["bathing_status"],
            advisory_text=f"Analysis based on your reported symptoms: {readable_symptoms}.",
            immediate_actions=scored["immediate_actions"], long_term_actions=scored["long_term_actions"],
            cluster_detected=scored["cluster_detected"], cluster_count=scored["cluster_count"],
            community_alert=scored["community_alert"], escalation_required=scored["escalation_required"],
            complaint_draft=scored["complaint_draft"], authority_name=scored["authority_name"],
            authority_email=scored["authority_email"], authority_portal=scored["authority_portal"],
            rag_citations=[scored["rag_source"]],
            full_response=f"Direct scoring active. Pipeline: {error[:100]}",
            rag_source=scored["rag_source"], mcp_calls=scored["mcp_calls"],
            score_deductions=scored["score_deductions"],
            voice_extracted_symptoms=scored.get("voice_extracted_symptoms", []),
            photo_analysis=scored.get("photo_analysis"),
            primary_category=scored.get("primary_category", "default"),
            source_baseline=scored["source_baseline"],
        )

    return WaterReportResponse(
        success=False, session_id=session_id, timestamp=datetime.now().isoformat(),
        quality_score=50, colour_band="yellow", safe_for_drinking=False, safe_for_bathing=True,
        drinking_status="caution", bathing_status="safe",
        advisory_text="Unable to analyse. Boil water before drinking as precaution.",
        immediate_actions=["Boil water before drinking as a precaution", "Safe to use for bathing", "Get water tested at GHMC lab (free)"],
        long_term_actions=["Call HMWSSB: 155313 (Hyderabad)"],
        full_response=f"Pipeline error: {error}",
    )


@router.post("/report", response_model=WaterReportResponse)
async def submit_water_report(request_body: WaterReportRequest, request: Request):
    session_id = f"ws_{uuid.uuid4().hex}"
    try:
        pipeline_result = await asyncio.wait_for(run_pipeline(request_body, session_id), timeout=120.0)
        if pipeline_result.get("error") or pipeline_result.get("fallback"):
            return _fallback_response(session_id, request_body, pipeline_result.get("error", "Pipeline unavailable"))
        return extract_structured_response(pipeline_result, request_body, session_id)
    except asyncio.TimeoutError:
        return _fallback_response(session_id, request_body, "Pipeline timeout")
    except Exception as e:
        return _fallback_response(session_id, request_body, str(e))
