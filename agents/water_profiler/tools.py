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

from rag.query import query_knowledge_base


def retrieve_water_quality_knowledge(
    symptoms: list[str],
    source_type: str,
    location_context: str = "",
) -> dict:
    """Retrieve relevant water quality knowledge from BIS/WHO/CGWB RAG knowledge base."""
    try:
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

    candidate_scores = []       # list of (score, drinking_status, bathing_status, label, triggered_by)
    deductions_log = []         # human-readable breakdown for UI, now with provenance

    # ── Diagnosed disease — its OWN category, not folded into generic coliform ──
    # This is treated as MORE urgent than a sensory report, not less — a confirmed
    # diagnosis means active illness, potentially progressing fast without treatment.
    # Requires the frontend to send this as an explicit boolean, never inferred
    # from free-text keyword matching (which previously caused false positives).
    if diagnosed_disease:
        candidate_scores.append((0, "unsafe", "unsafe", "Doctor-confirmed water-borne disease diagnosis"))
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
            candidate_scores.append((score_val, drink_status, bath_status, label))
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
                tds_score, tds_result["drinking_status"], tds_result["bathing_status"], tds_result["label"]
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
        candidate_scores.append((78, "caution", "caution", "White deposits reported — TDS likely 500-900 ppm range"))
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
        candidate_scores.append((vague_score, "caution", "safe", "Salty/bitter/metallic taste — mild mineral indicator"))
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

        candidate_scores.append((sick_score, "unsafe", "caution", "Frequent sickness / stomach pains reported"))
        deductions_log.append({
            "factor": "Frequent sickness / stomach pains in household",
            "points": -base_sick_deduction,
            "note": f"Biological risk indicator ({severity_summary}) — consider medical consultation",
            "triggered_by": "Questionnaire/symptom: sickness or stomach pains reported",
        })

    if algae_in_filters or tank_sludge:
        tank_score = baseline - 30
        candidate_scores.append((tank_score, "unsafe", "caution", "Tank sludge / algae in filters detected"))
        deductions_log.append({
            "factor": "Tank sludge / algae in filters",
            "points": -30,
            "note": "Bacterial/biogrowth indicator — clean tank and retest",
            "triggered_by": "Questionnaire: algae/rust in filters or tank sludge = Yes",
        })

    # ── Determine final score: LOWEST wins (worst signal) ───────────────────
    if candidate_scores:
        best_match = min(candidate_scores, key=lambda x: x[0])
        final_score, drinking_status, bathing_status, primary_label = best_match
    else:
        # Nothing reported — pure baseline holds
        final_score = baseline
        drinking_status = "safe" if baseline >= 80 else ("caution" if baseline >= 60 else "unsafe")
        bathing_status = "safe"
        primary_label = f"No contaminants reported — {source_type or 'unspecified source'} baseline"
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
    if diagnosed_disease:
        primary_category = "medical_emergency"
    elif final_score <= 0:
        primary_category = "sewage"
    elif final_score <= 12:
        primary_category = "black"
    elif final_score <= 30 and drinking_status == "unsafe" and bathing_status == "safe":
        primary_category = "iron"
    elif final_score <= 50 and drinking_status == "unsafe" and bathing_status == "safe":
        primary_category = "h2s"
    elif tds_value and tds_value > 500:
        primary_category = "high_tds"
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
        "immediate_actions": IMMEDIATE_ACTIONS.get(primary_category, IMMEDIATE_ACTIONS["default"]),
        "long_term_actions": LONG_TERM_ACTIONS.get(primary_category, LONG_TERM_ACTIONS["default"]),
        "score_breakdown": {
            "baseline": baseline,
            "source_type": source_type or "unspecified",
            "deductions": deductions_log,
            "final_score": final_score,
            "primary_label": primary_label,
            "scoring_model": "Two-axis: source baseline (no symptoms) + fixed contaminant severity (worst signal wins)",
        },
    }
