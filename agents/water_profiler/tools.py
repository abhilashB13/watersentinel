"""
Module: agents/water_profiler/tools.py
Purpose: RAG query tool and deterministic scoring tool for WaterProfiler agent.

SCORING MODEL — TWO SEPARATE AXES (do not collapse into one table):

AXIS 1 — Baseline (source-type only, applies when NO symptoms are reported):
  Municipal Pipeline = 85 | Borewell = 65 | Hand Pump = 55 | Open Well = 45
  Reflects real-world prior probability of contamination by infrastructure type.

AXIS 2 — Contaminant severity (near-fixed, health-driven, source-independent):
  Sewage/faecal smell → 0  | Black water → 10 | Iron → 20-25 | H2S → 40-45
  These do NOT get diluted by source type. A serious contaminant is serious
  regardless of whether it came from a treated pipe or a borewell — softening
  severity by source would make the score meaningless as a safety signal.

Baseline only matters when nothing serious is reported. The moment a real
contaminant is named, its fixed severity overrides the baseline (worst signal wins).

BATHING STATUS — three states, not a boolean:
  safe    — no bathing concern
  caution — not acutely dangerous, but chronic use causes real harm (TDS: dry
            skin, hair breakage, scalp irritation) — documented, not cosmetic-only
  unsafe  — acute health/infection risk (sewage, black water, diagnosed disease)
"""

import sys
import re
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# NOTE: query_knowledge_base is imported LAZILY inside
# retrieve_water_quality_knowledge() below, not at module level here —
# calculate_quality_score() has zero dependency on RAG/ChromaDB.


def retrieve_water_quality_knowledge(
    symptoms: list[str],
    source_type: str,
    location_context: str = "",
) -> dict:
    """Retrieve relevant water quality knowledge from BIS/WHO/CGWB RAG knowledge base."""
    try:
        from rag.query import query_knowledge_base  # lazy — only this function needs ChromaDB
        chunks = query_knowledge_base(
            symptoms=symptoms,
            source_type=source_type,
            location_context=location_context,
            top_k=3,
        )
        combined_knowledge = "\n\n---\n\n".join([
            f"SOURCE: {chunk['citation']}\n{chunk['content']}"
            for chunk in chunks
        ])
        citations = list(set([chunk["citation"] for chunk in chunks]))
        return {
            "success": True,
            "retrieved_chunks": chunks,
            "combined_knowledge": combined_knowledge,
            "citations": citations,
            "chunk_count": len(chunks),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "combined_knowledge": (
                "Sewage smell = critical contamination, score 0, unsafe for all use. "
                "Black water = possible sewage/manganese, score 10. "
                "Iron = yellow water, score 20-25, safe to bathe. "
                "High TDS = graded by BIS/WHO tiers, caution for bathing above 500ppm. "
                "H2S egg smell = borewell anaerobic, score 40-45, safe to bathe."
            ),
            "citations": ["WaterSentinel General Guidelines (Fallback)"],
            "chunk_count": 0,
        }


# ── AXIS 1 — Source-type baselines (used only when no symptoms reported) ───────

SOURCE_BASELINES = {
    "municipal_pipeline": 85,
    "borewell": 65,
    "hand_pump": 55,
    "open_well": 45,
}

DEFAULT_BASELINE = 60  # unknown/unspecified source


# ── AXIS 2 — Fixed contaminant severity (near source-independent) ──────────────
# Each entry: (score, drinking_status, bathing_status, label)
# drinking_status / bathing_status: "safe" | "caution" | "unsafe"

CONTAMINANT_SEVERITY = {
    "sewage_smell":         (0,  "unsafe", "unsafe", "Sewage contamination — critical, stop all use"),
    "sewage_contamination": (0,  "unsafe", "unsafe", "Sewage contamination — critical, stop all use"),
    "coliform":             (0,  "unsafe", "unsafe", "Faecal/coliform contamination — critical"),
    "e_coli":               (0,  "unsafe", "unsafe", "E.coli detected — critical"),
    "cholera":              (0,  "unsafe", "unsafe", "Cholera-linked contamination — critical"),
    "typhoid":              (0,  "unsafe", "unsafe", "Typhoid-linked contamination — critical"),

    "black_colour":         (10, "unsafe", "unsafe", "Black water — possible sewage/manganese intrusion"),
    "dark_water":           (10, "unsafe", "unsafe", "Dark water — sewage/manganese risk"),
    "manganese":            (10, "unsafe", "unsafe", "Manganese contamination — dark water"),

    "iron":                 (22, "unsafe", "safe",   "Iron contamination — yellow water, safe to bathe"),
    "yellow_colour":        (22, "unsafe", "safe",   "Iron indicators — yellow/brown water"),
    "fe":                   (22, "unsafe", "safe",   "Iron (Fe) contamination"),

    "h2s":                  (42, "unsafe", "safe",   "H2S — egg smell, safe to bathe"),
    "egg_smell":            (42, "unsafe", "safe",   "H2S / egg smell detected, safe to bathe"),
    "hydrogen_sulphide":    (42, "unsafe", "safe",   "Hydrogen Sulphide, safe to bathe"),

    "fluoride":             (35, "unsafe", "safe",   "Fluoride above BIS limit"),
    "nitrate":              (30, "unsafe", "safe",   "Nitrate contamination"),
    "arsenic":              (5,  "unsafe", "unsafe", "Arsenic detected — critical"),

    "white_deposits":       (None, None, None, "White deposits — deferred to TDS table"),  # handled via TDS
    "salty_taste":          (None, None, None, "Salty taste — deferred to TDS table"),
    "metallic_taste":       (None, None, None, "Metallic taste — often iron-linked, minor deduction"),
    "milky_appearance":     (40, "unsafe", "safe",   "Milky/cloudy water — possible air or mineral suspension"),
    "blue_green_stain":     (30, "unsafe", "safe",   "Blue-green staining — copper corrosion indicator"),

    # ── NEW — research-backed additions (BIS sensory-check protocol) ────────
    "chlorine_smell":       (65, "caution", "safe",  "Strong chlorine smell — possible over-chlorination, monitor"),
    "colour_after_standing": (35, "unsafe", "safe",  "Water discolours on standing — iron oxidising on air exposure"),
    "gritty_texture":       (45, "unsafe", "safe",   "Gritty/sandy texture — sediment contamination"),
    "foamy_water":          (40, "unsafe", "safe",   "Foamy/bubbly water — detergent contamination or high alkalinity"),
    "oily_sheen":           (10, "unsafe", "unsafe", "Oily sheen on surface — possible petroleum/industrial contamination, critical"),
    "insects_visible":      (15, "unsafe", "unsafe", "Insects or larvae visible — stagnant water, poor storage hygiene"),
    "skin_irritation":      (30, "unsafe", "unsafe", "Skin irritation after bathing — bathing-specific health signal"),
    "vessel_staining":      (28, "unsafe", "safe",   "Vessel staining over time — hardness/iron indicator, delayed onset"),
}

# Vague/mild symptoms that don't map to a fixed contaminant — small baseline nudge only
VAGUE_SYMPTOM_DEDUCTION = 12


# ── TDS — 6-tier table, graded per BIS/WHO/ICMR research ────────────────────────
# (threshold_ppm, deduction, drinking_status, bathing_status, label)

TDS_TIERS = [
    (2000, 60, "unsafe", "caution", "TDS > 2000 ppm — exceeds BIS permissible limit, reject source"),
    (1200, 45, "unsafe", "caution", "TDS 1201-2000 ppm — above WHO unacceptable threshold, RO mandatory"),
    (900,  30, "unsafe", "caution", "TDS 901-1200 ppm — not recommended long-term, hair/scalp risk"),
    (500,  15, "caution", "caution", "TDS 501-900 ppm — above BIS acceptable limit, monitor; kidney stone risk research starts here"),
    (300,  0,  "safe",    "safe",    "TDS 301-500 ppm — within BIS acceptable limit"),
    (0,    0,  "safe",    "safe",    "TDS ≤ 300 ppm — ICMR/WHO optimal range"),
]


def _score_tds(tds_value: int) -> dict:
    """Return the matching tier for a given TDS value."""
    for threshold, deduction, drink_status, bath_status, label in TDS_TIERS:
        if tds_value > threshold:
            return {
                "deduction": deduction,
                "drinking_status": drink_status,
                "bathing_status": bath_status,
                "label": label,
            }
    # tds_value is 0 or negative — treat as optimal
    return {
        "deduction": 0,
        "drinking_status": "safe",
        "bathing_status": "safe",
        "label": "TDS ≤ 300 ppm — ICMR/WHO optimal range",
    }


# ── Immediate / Long-term action templates (unchanged structure, by category) ──

IMMEDIATE_ACTIONS = {
    "medical_emergency": [
        "🚨 SEEK MEDICAL CARE IMMEDIATELY — this is a health emergency, not just a water quality issue",
        "🏥 Go to the nearest hospital or call an ambulance if symptoms are severe (fever, dehydration, blood in stool)",
        "💧 Give oral rehydration solution (ORS) while arranging medical transport",
        "🚫 STOP using this water source immediately — do not drink, do not cook with it",
        "📞 Report to HMWSSB emergency (040-23290101) AFTER medical care is arranged, not before",
    ],
    "sewage": [
        "🚨 STOP using this water immediately for any purpose",
        "🚰 Arrange water from water tankers urgently (call Tara Water: 98490-XXXXX)",
        "🏘️ Ask neighbours or nearby RWA for temporary water supply",
        "📞 Call HMWSSB emergency: 040-23290101 to report sewage mixing",
        "🏥 If anyone has stomach symptoms, see a doctor immediately",
    ],
    "black": [
        "🚨 Do NOT use this water for drinking or bathing",
        "⚠️ This indicates sewage or manganese — potential health emergency",
        "🚰 Use bottled or tanker water until resolved",
        "📞 Call HMWSSB helpline: 155313 immediately",
    ],
    "iron": [
        "✅ Water is SAFE FOR BATHING — continue bathing normally",
        "❌ Do NOT drink without treatment — iron exceeds BIS limit of 0.3 mg/L",
        "🔧 Install an Iron Removal Filter (greensand/birm media, ₹5,000–15,000)",
        "⚠️ Do NOT buy a UV purifier for iron — UV does not remove iron",
        "💧 Get water tested at GHMC lab (free) to confirm iron level",
    ],
    "h2s": [
        "✅ Water is SAFE FOR BATHING — H2S is safe for skin at borewell concentrations",
        "❌ Do NOT drink without treatment",
        "💨 Aerate water before drinking: pour between two buckets 10 times",
        "🔧 Install activated carbon filter (₹3,000–8,000) for long-term fix",
    ],
    "high_tds": [
        "⚠️ Bathing not acutely dangerous, but prolonged use may cause dry skin, scalp irritation, and hair breakage",
        "💧 Use RO-filtered water for drinking — TDS above 500 ppm linked to elevated kidney stone risk",
        "💇 Consider a shower filter or water softener if bathing daily in this water",
        "🚿 Soap will not lather well — this is expected with high TDS, not a product issue",
        "⚠️ Boiling does NOT reduce TDS — it actually concentrates it",
    ],
    "default": [
        "🧪 Boil water before drinking as a precaution",
        "✅ Safe to use for bathing",
        "🔬 Get water tested at GHMC water testing lab (free for municipal complaints)",
    ],
}

LONG_TERM_ACTIONS = {
    "medical_emergency": [
        "Complete the full course of any medical treatment prescribed — do not stop early even if symptoms improve",
        "Get the water source tested at a NABL-certified lab before resuming use, even after switching to tanker water temporarily",
        "File an HMWSSB complaint citing the medical diagnosis as supporting evidence — this carries more weight than a symptom report alone",
        "Inform your RWA — a confirmed water-borne disease case is a serious signal for the whole building/colony, not just your household",
    ],
    "sewage": [
        "File official complaint with HMWSSB immediately (see complaint section below)",
        "If unresolved in 30 days, file RTI application",
        "RWA should request pipeline inspection from HMWSSB",
    ],
    "black": [
        "HMWSSB complaint with urgency flag for sewage/manganese",
        "Request GHMC to inspect area pipelines",
    ],
    "iron": [
        "Install iron removal filter — Kent, Aquaguard or local NABL-tested units",
        "Get borewell water tested annually for iron and H2S",
        "Consider whole-house iron filter if entire building affected",
    ],
    "h2s": [
        "Install aeration system or activated carbon filter on borewell outlet",
        "Service borewell annually — H2S increases with depth and stagnation",
    ],
    "high_tds": [
        "Install RO system — recommended brands: Kent Grand Plus, Aquaguard Enhance",
        "RO water recommended for drinking AND cooking when TDS > 500 ppm",
        "Consider a water softener for bathing/hair-washing if TDS > 900 ppm — reduces scale and hair damage",
        "Retest TDS every 6 months, especially for borewell sources where levels drift with season",
    ],
    "default": [
        "Call HMWSSB helpline: 155313 (Hyderabad)",
        "Visit hmwssb.telangana.gov.in for online complaint",
    ],
}


def _classify_contaminant_type(indicator: str, label: str) -> str | None:
    """
    Maps a matched symptom/contaminant INDICATOR ID to its underlying
    contaminant TYPE (sewage/black/iron/h2s/high_tds), independent of its
    numeric severity score. This is what allows category selection to be
    decided SEPARATELY from score selection.

    FIXED: previously matched against the full descriptive LABEL text (e.g.
    "Vessel staining over time — hardness/iron indicator, delayed onset"),
    which caused a real bug — vessel_staining's own descriptive note
    happens to mention "iron" as context, causing it to be misclassified
    as the iron contaminant type even though it's a distinct symptom. Now
    matches against the explicit indicator ID only, via a precise lookup
    table — never fuzzy-searching prose that may incidentally contain
    another contaminant's name as explanatory text.
    """
    INDICATOR_TO_TYPE = {
        "sewage_smell": "sewage", "sewage_contamination": "sewage",
        "coliform": "sewage", "e_coli": "sewage",
        "cholera": "sewage", "typhoid": "sewage",
        "black_colour": "black", "dark_water": "black", "manganese": "black",
        "iron": "iron", "yellow_colour": "iron", "fe": "iron",
        "h2s": "h2s", "egg_smell": "h2s", "hydrogen_sulphide": "h2s",
        "high_tds": "high_tds", "white_deposits": "high_tds",
        "salty_taste": "high_tds", "metallic_taste": "high_tds",
    }
    return INDICATOR_TO_TYPE.get(indicator)


def calculate_quality_score(
    contaminants: list[str],
    severity: str,
    source_type: str,
    diagnosed_disease: bool = False,
    frequent_sickness: bool = False,
    algae_in_filters: bool = False,
    tank_sludge: bool = False,
    tds_value: int = None,
    poor_lather: bool = False,
    pipe_deposits: bool = False,
    symptoms: list[str] = None,
    affected_count: str = None,   # "1" | "2-3" | "4+"
    since_when: str = None,       # "days" | "weeks" | "months"
) -> dict:
    """
    Two-axis deterministic Water Quality Score.

    Axis 1 (baseline) applies only when nothing serious is reported.
    Axis 2 (contaminant severity) is near-fixed regardless of source —
    a genuine contaminant's health risk does not get diluted by infrastructure type.
    Worst signal wins when multiple issues are present.

    Returns bathing_status as "safe" | "caution" | "unsafe" (not a boolean) so
    that chronic-but-non-acute risks (e.g. high TDS hair/skin effects) can be
    represented without conflating them with acute infection risk.
    """
    if symptoms is None:
        symptoms = []

    source_type = (source_type or "").lower().strip()
    baseline = SOURCE_BASELINES.get(source_type, DEFAULT_BASELINE)

    all_indicators = (
        [c.lower().replace(" ", "_").replace("-", "_") for c in contaminants]
        + [s.lower() for s in symptoms]
    )
    # NOTE: diagnosed_disease is intentionally NOT folded into all_indicators
    # here — it's handled as its own explicit, higher-urgency category below,
    # never inferred via keyword matching against free text.

    candidate_scores = []       # list of (score, drinking_status, bathing_status, label, contaminant_type)
    deductions_log = []         # human-readable breakdown for UI, now with provenance

    # FIXED: baseline is now ALWAYS included as a candidate in the worst-signal
    # comparison below, not just used as a fallback when zero symptoms exist.
    # Previously, the moment ANY symptom was reported, the baseline was
    # excluded entirely from consideration — meaning a real measured TDS of
    # 700ppm (fixed score 85) could score BETTER than reporting nothing at
    # all (baseline 65 for borewell), since 85 was never compared against 65.
    # Now the baseline competes on equal footing with every reported symptom,
    # so "worst signal wins" genuinely means worst signal, always including
    # "no news is better than this specific finding" as a real possibility.
    baseline_drink_status = "safe" if baseline >= 80 else ("caution" if baseline >= 60 else "unsafe")
    candidate_scores.append((baseline, baseline_drink_status, "safe", f"{source_type or 'unspecified'} source baseline", None))

    # ── Diagnosed disease — its OWN category, not folded into generic coliform ──
    # This is treated as MORE urgent than a sensory report, not less — a confirmed
    # diagnosis means active illness, potentially progressing fast without treatment.
    # Requires the frontend to send this as an explicit boolean, never inferred
    # from free-text keyword matching (which previously caused false positives).
    if diagnosed_disease:
        candidate_scores.append((0, "unsafe", "unsafe", "Doctor-confirmed water-borne disease diagnosis", "medical_emergency"))
        deductions_log.append({
            "factor": "Doctor diagnosed Cholera/Typhoid/Dysentery",
            "points": -100,
            "note": "MEDICAL EMERGENCY — confirmed diagnosis, not a symptom report. Seek care immediately.",
            "triggered_by": "Questionnaire: 'Doctor diagnosed Cholera, Typhoid, Dysentery?' = Yes",
        })

    # ── Fixed contaminant severities (Axis 2) — matched ONLY against explicit
    # symptom/contaminant identifiers, never against free-text keyword search ──
    matched_any_fixed = False
    for indicator in all_indicators:
        entry = CONTAMINANT_SEVERITY.get(indicator)
        if entry and entry[0] is not None:
            score_val, drink_status, bath_status, label = entry
            # NEW — 5th tuple element tags the ACTUAL contaminant type this
            # symptom represents, independent of whether it numerically wins
            # the score comparison. This is what lets category selection be
            # decided separately from score selection (see below).
            contaminant_type = _classify_contaminant_type(indicator, label)
            candidate_scores.append((score_val, drink_status, bath_status, label, contaminant_type))
            deductions_log.append({
                "factor": label,
                "points": score_val - 100,
                "note": f"Fixed severity — drinking: {drink_status}, bathing: {bath_status}",
                "triggered_by": f"Symptom selected: {indicator.replace('_', ' ')}",
            })
            matched_any_fixed = True

    # ── TDS — tiered lookup (Axis 2) ────────────────────────────────────────
    if tds_value is not None:
        tds_result = _score_tds(tds_value)
        if tds_result["deduction"] > 0:
            tds_score = 100 - tds_result["deduction"]
            candidate_scores.append((
                tds_score, tds_result["drinking_status"], tds_result["bathing_status"], tds_result["label"], "high_tds"
            ))
            deductions_log.append({
                "factor": tds_result["label"],
                "points": -tds_result["deduction"],
                "note": f"BIS/WHO tiered TDS — drinking: {tds_result['drinking_status']}, bathing: {tds_result['bathing_status']}",
                "triggered_by": f"TDS value entered: {tds_value} ppm",
            })
            matched_any_fixed = True
    elif "white_deposits" in all_indicators or pipe_deposits:
        # No exact TDS number given, but deposits reported — assume moderate tier
        candidate_scores.append((78, "caution", "caution", "White deposits reported — TDS likely 500-900 ppm range", "high_tds"))
        deductions_log.append({
            "factor": "White deposits on taps (TDS not measured)",
            "points": -22,
            "note": "Estimated moderate TDS — get exact reading for precise guidance",
            "triggered_by": "Symptom selected: white deposits on taps (no exact TDS given)",
        })
        matched_any_fixed = True

    # ── Vague/mild symptoms with no fixed severity (small baseline nudge) ──
    vague_symptoms_present = [
        s for s in all_indicators
        if s in ("salty_taste", "metallic_taste") and s not in [d for d in all_indicators if d in CONTAMINANT_SEVERITY and CONTAMINANT_SEVERITY[d][0] is not None]
    ]
    if vague_symptoms_present and not matched_any_fixed:
        vague_score = baseline - VAGUE_SYMPTOM_DEDUCTION
        candidate_scores.append((vague_score, "caution", "safe", "Salty/bitter/metallic taste — mild mineral indicator", "high_tds"))
        deductions_log.append({
            "factor": "Salty/bitter/metallic taste (no confirmed TDS)",
            "points": -VAGUE_SYMPTOM_DEDUCTION,
            "note": f"Minor deduction from {source_type} baseline — monitor, consider TDS test",
            "triggered_by": "Symptom selected: salty/bitter/metallic taste",
        })

    # ── Biological / hygiene indicators (stack independently) ───────────────
    if frequent_sickness or "stomach_issues" in all_indicators:
        # GRADUATED severity based on how many affected and for how long —
        # this is a real signal distinguishing "one person, one bad day"
        # from "half the household, sick for weeks" — the latter is a much
        # stronger indicator of genuine water contamination, not unrelated
        # illness or food poisoning. Falls back to the flat -35 when these
        # optional context fields aren't provided (e.g. older client version,
        # or citizen skipped the follow-up).
        base_sick_deduction = 35
        severity_note_parts = []

        if affected_count == "4+":
            base_sick_deduction += 15
            severity_note_parts.append("4+ household members affected")
        elif affected_count == "2-3":
            base_sick_deduction += 8
            severity_note_parts.append("2-3 household members affected")
        elif affected_count == "1":
            severity_note_parts.append("1 household member affected")

        if since_when == "months":
            base_sick_deduction += 15
            severity_note_parts.append("ongoing for months — chronic pattern")
        elif since_when == "weeks":
            base_sick_deduction += 8
            severity_note_parts.append("ongoing for weeks")
        elif since_when == "days":
            severity_note_parts.append("recent, few days")

        sick_score = baseline - base_sick_deduction
        severity_summary = ", ".join(severity_note_parts) if severity_note_parts else "details not specified"

        candidate_scores.append((sick_score, "unsafe", "caution", "Frequent sickness / stomach pains reported", None))
        deductions_log.append({
            "factor": "Frequent sickness / stomach pains in household",
            "points": -base_sick_deduction,
            "note": f"Biological risk indicator ({severity_summary}) — consider medical consultation",
            "triggered_by": "Questionnaire/symptom: sickness or stomach pains reported",
        })

    if algae_in_filters or tank_sludge:
        tank_score = baseline - 30
        candidate_scores.append((tank_score, "unsafe", "caution", "Tank sludge / algae in filters detected", None))
        deductions_log.append({
            "factor": "Tank sludge / algae in filters",
            "points": -30,
            "note": "Bacterial/biogrowth indicator — clean tank and retest",
            "triggered_by": "Questionnaire: algae/rust in filters or tank sludge = Yes",
        })

    # ── Determine final score: LOWEST wins (worst signal) ───────────────────
    STATUS_SEVERITY = {"safe": 0, "caution": 1, "unsafe": 2}  # for picking the WORST status

    # Baseline is now ALWAYS a candidate (added earlier), so candidate_scores
    # can never actually be empty — but the else branch is kept as a
    # defensive fallback in case this function is ever called in a way that
    # bypasses that guarantee.
    if candidate_scores:
        best_match = min(candidate_scores, key=lambda x: x[0])
        final_score, _, _, primary_label, _ = best_match

        drinking_status = max((c[1] for c in candidate_scores), key=lambda s: STATUS_SEVERITY[s])
        bathing_status = max((c[2] for c in candidate_scores), key=lambda s: STATUS_SEVERITY[s])

        # NEW (Option B): category is determined by scanning ALL candidates
        # for a real, identified contaminant TYPE — independent of which
        # candidate numerically won the score. If sickness or tank-sludge
        # (contaminant_type=None) happens to produce the worst score, but a
        # real contaminant (e.g. egg_smell -> "h2s") was ALSO reported, the
        # category correctly stays tied to that actual contaminant rather
        # than silently falling through to a generic default just because
        # the non-specific signal happened to win on numbers.
        identified_contaminant_types = [c[4] for c in candidate_scores if c[4] is not None]
        # Priority order when multiple distinct contaminant types are present:
        # most severe/urgent first
        TYPE_PRIORITY = ["medical_emergency", "sewage", "black", "iron", "h2s", "high_tds"]
        contaminant_category = next(
            (t for t in TYPE_PRIORITY if t in identified_contaminant_types), None
        )
    else:
        # Nothing reported — pure baseline holds
        final_score = baseline
        drinking_status = "safe" if baseline >= 80 else ("caution" if baseline >= 60 else "unsafe")
        bathing_status = "safe"
        primary_label = f"No contaminants reported — {source_type or 'unspecified source'} baseline"
        contaminant_category = None
        deductions_log.append({
            "factor": "No significant contaminants detected",
            "points": 0,
            "note": f"Baseline retained for {source_type or 'unspecified'} source type",
            "triggered_by": "No symptoms or diagnosis reported",
        })

    final_score = max(0, min(100, round(final_score)))

    # ── Determine primary category for action templates ─────────────────────
    # Medical emergency (confirmed diagnosis) takes priority over generic
    # sewage/contaminant categories — a confirmed disease case needs medical
    # care as the FIRST instruction, not water-source troubleshooting first.
    # FIXED: previously inferred purely from the numeric score RANGE (e.g.
    # "score <= 30 and drink=unsafe/bathe=safe -> assume iron"), which made
    # unsupported specific claims — a citizen who never reported yellow
    # water could see "iron exceeds BIS limit of 0.3 mg/L" purely because
    # their score happened to land in the same numeric range iron produces.
    # Now traces back to the ACTUAL primary_label that won the min() above,
    # so the category — and its advisory text — only ever claims what the
    # citizen actually reported.
    # NEW: category now comes directly from the independent contaminant-type
    # scan done above (Option B) — checked across ALL reported symptoms,
    # not just whichever one happened to win the score comparison. Only
    # falls to "default" if genuinely no contaminant type was identified
    # anywhere in the report (e.g. sickness/tank-sludge alone, no specific
    # contaminant symptom present at all).
    if diagnosed_disease:
        primary_category = "medical_emergency"
    elif contaminant_category:
        primary_category = contaminant_category
    else:
        primary_category = "default"

    # ── Colour band ───────────────────────────────────────────────────────
    if final_score >= 80:
        colour_band, band_label = "green", "Safe"
    elif final_score >= 60:
        colour_band, band_label = "yellow", "Acceptable — Monitor"
    elif final_score >= 40:
        colour_band, band_label = "orange", "Caution — Treatment Required"
    elif final_score > 0:
        colour_band, band_label = "red", "Critical — Do Not Drink"
    else:
        colour_band, band_label = "red", "CRITICAL — Stop All Use"

    # NEW: when landing in "default" specifically because sickness/tank
    # issues were the driving factor (no actual contaminant identified),
    # append sickness-aware guidance dynamically — rather than editing the
    # static IMMEDIATE_ACTIONS["default"] list, which would otherwise show
    # this same sickness-specific advice even to citizens who never
    # reported any sickness at all.
    immediate_actions_final = list(IMMEDIATE_ACTIONS.get(primary_category, IMMEDIATE_ACTIONS["default"]))
    long_term_actions_final = list(LONG_TERM_ACTIONS.get(primary_category, LONG_TERM_ACTIONS["default"]))
    sickness_was_driving_factor = (
        primary_category == "default"
        and (frequent_sickness or "stomach_issues" in all_indicators)
    )
    if sickness_was_driving_factor:
        immediate_actions_final.insert(0,
            "🏥 Your household reported recurring illness — while no specific "
            "contaminant was clearly identified from your description, this "
            "is a genuine health signal. Consider a medical consultation."
        )
        long_term_actions_final.append(
            "Get water tested at a NABL-certified lab even without a visible "
            "contaminant — some issues (e.g. bacterial contamination) have no smell or colour."
        )

    return {
        "quality_score": final_score,
        "colour_band": colour_band,
        "band_label": band_label,
        # Booleans kept for backward compatibility with existing frontend fields
        "safe_for_drinking": drinking_status == "safe",
        "safe_for_bathing": bathing_status == "safe",
        # New three-state fields — preferred going forward
        "drinking_status": drinking_status,   # "safe" | "caution" | "unsafe"
        "bathing_status": bathing_status,     # "safe" | "caution" | "unsafe"
        "primary_category": primary_category,
        "immediate_actions": immediate_actions_final,
        "long_term_actions": long_term_actions_final,
        "score_breakdown": {
            "baseline": baseline,
            "source_type": source_type or "unspecified",
            "deductions": deductions_log,
            "final_score": final_score,
            "primary_label": primary_label,
            "scoring_model": "Two-axis: source baseline (no symptoms) + fixed contaminant severity (worst signal wins)",
        },
    }
