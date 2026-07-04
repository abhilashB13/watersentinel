"""
Module: agents/water_profiler/tools.py
Purpose: RAG query + deterministic scoring for WaterProfiler agent.

SCORING LOGIC (per product specification):
  Sewage smell     → score = 0  (worst possible, unsafe for ALL use)
  Black water      → score = 10
  Iron in water    → score = 25
  High TDS > 800   → score = 20
  High TDS > 500   → score = 30
  High TDS > 200   → score = 40
  H2S (egg smell)  → score = 45 (safe to bathe, not drink)
  No contaminant   → score = 100

When multiple contaminants present: take the LOWEST individual score.
safe_for_bathing = False when sewage, black water, or diagnosed disease.
safe_for_drinking = False when score < 80.
"""

import sys
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
    """
    Retrieve relevant water quality knowledge from BIS/WHO/CGWB RAG knowledge base.
    Returns top-3 most relevant chunks with citations.
    All 7 knowledge base documents are valid sources.
    """
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
                "Black water = possible sewage, score 10. "
                "Iron = yellow water, score 25, safe to bathe. "
                "High TDS = kidney risk, RO recommended. "
                "H2S egg smell = borewell anaerobic, safe to bathe only."
            ),
            "citations": ["WaterSentinel General Guidelines (Fallback)"],
            "chunk_count": 0,
        }


# ── Scoring constants ────────────────────────────────────────────────────────

CONTAMINANT_SCORES = {
    # Key: symptom/contaminant identifier → (score, safe_for_bathing, label)
    "sewage_smell":         (0,  False, "Sewage contamination (Critical — Score 0)"),
    "sewage_contamination": (0,  False, "Sewage contamination (Critical — Score 0)"),
    "coliform":             (0,  False, "Faecal/coliform contamination (Critical — Score 0)"),
    "e_coli":               (0,  False, "E.coli detected (Critical — Score 0)"),
    "cholera":              (0,  False, "Cholera-linked contamination (Critical — Score 0)"),
    "typhoid":              (0,  False, "Typhoid-linked contamination (Critical — Score 0)"),
    "black_colour":         (10, False, "Black water — possible sewage intrusion (Score 10)"),
    "dark_water":           (10, False, "Dark water — sewage/manganese risk (Score 10)"),
    "manganese":            (10, False, "Manganese — dark water (Score 10)"),
    "iron":                 (25, True,  "Iron contamination — yellow water (Score 25, safe to bathe)"),
    "yellow_colour":        (25, True,  "Iron indicators — yellow/brown water (Score 25)"),
    "fe":                   (25, True,  "Iron (Fe) contamination (Score 25)"),
    "h2s":                  (45, True,  "H2S — egg smell from borewell (Score 45, safe to bathe)"),
    "egg_smell":            (45, True,  "H2S / egg smell detected (Score 45, safe to bathe)"),
    "hydrogen_sulphide":    (45, True,  "Hydrogen Sulphide (Score 45, safe to bathe)"),
    "white_deposits":       (50, True,  "High TDS indicators — white scale deposits"),
    "fluoride":             (35, True,  "Fluoride above BIS limit (Score 35)"),
    "nitrate":              (30, True,  "Nitrate contamination (Score 30)"),
    "arsenic":              (5,  False, "Arsenic detected (Score 5, critical)"),
}

# TDS score by value range
TDS_SCORE_MAP = [
    (800, 20,  "TDS > 800 ppm — Very High (Score 20) — RO mandatory"),
    (500, 30,  "TDS > 500 ppm — High (Score 30) — RO strongly recommended"),
    (200, 40,  "TDS > 200 ppm — Elevated (Score 40) — RO recommended"),
    (0,   80,  "TDS ≤ 200 ppm — Acceptable"),
]

# Immediate action templates per contaminant
IMMEDIATE_ACTIONS = {
    "sewage":   [
        "🚨 STOP using this water immediately for any purpose",
        "🚰 Arrange water from water tankers urgently (call Tara Water: 98490-XXXXX)",
        "🏘️ Ask neighbours or nearby RWA for temporary water supply",
        "📞 Call HMWSSB emergency: 040-23290101 to report sewage mixing",
        "🏥 If anyone has stomach symptoms, see a doctor immediately",
    ],
    "black":    [
        "🚨 Do NOT use this water for drinking or bathing",
        "⚠️ This indicates sewage or manganese — potential health emergency",
        "🚰 Use bottled or tanker water until resolved",
        "📞 Call HMWSSB helpline: 155313 immediately",
    ],
    "iron":     [
        "✅ Water is SAFE FOR BATHING — continue bathing normally",
        "❌ Do NOT drink without treatment — iron exceeds BIS limit of 0.3 mg/L",
        "🔧 Install an Iron Removal Filter (greensand/birm media, ₹5,000–15,000)",
        "⚠️ Do NOT buy a UV purifier for iron — UV does not remove iron",
        "💧 Get water tested at GHMC lab (free) to confirm iron level",
    ],
    "h2s":      [
        "✅ Water is SAFE FOR BATHING — H2S is safe for skin at borewell concentrations",
        "❌ Do NOT drink without treatment",
        "💨 Aerate water before drinking: pour between two buckets 10 times",
        "🔧 Install activated carbon filter (₹3,000–8,000) for long-term fix",
    ],
    "high_tds": [
        "✅ Water is safe for bathing",
        "💧 Use RO-filtered water for drinking — TDS above 500 ppm linked to kidney stones",
        "💇 High TDS causes hairfall and dry skin — use RO water for hair washing too",
        "🚿 Consider water softener for TDS > 500 ppm to reduce scale on taps",
        "⚠️ Boiling does NOT reduce TDS — it actually concentrates it",
    ],
    "default":  [
        "🧪 Boil water before drinking as a precaution",
        "✅ Safe to use for bathing",
        "🔬 Get water tested at GHMC water testing lab (free for municipal complaints)",
    ],
}

LONG_TERM_ACTIONS = {
    "sewage":   [
        "File official complaint with HMWSSB immediately (see complaint section below)",
        "If unresolved in 30 days, file RTI application",
        "RWA should request pipeline inspection from HMWSSB",
    ],
    "black":    [
        "HMWSSB complaint with urgency flag for sewage/manganese",
        "Request GHMC to inspect area pipelines",
    ],
    "iron":     [
        "Install iron removal filter — Kent, Aquaguard or local NABL-tested units",
        "Get borewell water tested annually for iron and H2S",
        "Consider whole-house iron filter if entire building affected",
    ],
    "h2s":      [
        "Install aeration system or activated carbon filter on borewell outlet",
        "Service borewell annually — H2S increases with depth and stagnation",
    ],
    "high_tds": [
        "Install RO system — recommended brands: Kent Grand Plus, Aquaguard Enhance",
        "RO water recommended for drinking AND cooking when TDS > 500 ppm",
        "TDS > 500 also causes hairfall — use RO or filtered water for hair washing",
        "Consider water softener if TDS > 800 ppm for pipe scale prevention",
    ],
    "default":  [
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
) -> dict:
    """
    Deterministic Water Quality Score.
    When multiple contaminants present: uses the LOWEST individual score.
    Sewage = 0 always. Safe_for_bathing follows contamination type.
    """
    if symptoms is None:
        symptoms = []

    all_indicators = (
        [c.lower().replace(" ", "_").replace("-", "_") for c in contaminants]
        + [s.lower() for s in symptoms]
    )

    # Diagnosed disease = sewage-level risk
    if diagnosed_disease:
        all_indicators.append("coliform")

    candidate_scores = []
    deductions = []
    safe_for_bathing = True
    primary_category = "default"

    # ── Match each indicator to a score ─────────────────────────────────────
    for indicator in all_indicators:
        # Direct match
        if indicator in CONTAMINANT_SCORES:
            score_val, bathing_safe, label = CONTAMINANT_SCORES[indicator]
            candidate_scores.append(score_val)
            deductions.append(f"• {label}")
            if not bathing_safe:
                safe_for_bathing = False

        # Partial match (e.g. "sewage" in "sewage_contamination_detected")
        else:
            for key, (score_val, bathing_safe, label) in CONTAMINANT_SCORES.items():
                if key in indicator or indicator in key:
                    candidate_scores.append(score_val)
                    deductions.append(f"• {label}")
                    if not bathing_safe:
                        safe_for_bathing = False
                    break

    # ── TDS scoring ─────────────────────────────────────────────────────────
    if tds_value is not None:
        for threshold, tds_score, tds_label in TDS_SCORE_MAP:
            if tds_value > threshold:
                candidate_scores.append(tds_score)
                deductions.append(f"• {tds_label}")
                break

    # ── Additional biological indicators ────────────────────────────────────
    if frequent_sickness or "stomach_issues" in all_indicators:
        candidate_scores.append(20)
        deductions.append("• Frequent sickness/stomach pains in household: high biological risk")

    if algae_in_filters or tank_sludge:
        candidate_scores.append(30)
        deductions.append("• Tank sludge/algae in filters: bacterial growth indicators")

    # ── Final score: lowest candidate wins ───────────────────────────────────
    if candidate_scores:
        final_score = min(candidate_scores)
    else:
        final_score = 100

    # Clamp
    final_score = max(0, min(100, final_score))

    # ── Determine primary category for action templates ──────────────────────
    lowest = final_score
    if lowest <= 0:
        primary_category = "sewage"
    elif lowest <= 10:
        primary_category = "black"
    elif lowest <= 25:
        primary_category = "iron"
    elif lowest <= 45:
        primary_category = "h2s"
    elif tds_value and tds_value > 200:
        primary_category = "high_tds"
    else:
        primary_category = "default"

    # Colour band
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

    safe_for_drinking = final_score >= 80

    return {
        "quality_score": final_score,
        "colour_band": colour_band,
        "band_label": band_label,
        "safe_for_drinking": safe_for_drinking,
        "safe_for_bathing": safe_for_bathing,
        "primary_category": primary_category,
        "immediate_actions": IMMEDIATE_ACTIONS.get(
            primary_category, IMMEDIATE_ACTIONS["default"]
        ),
        "long_term_actions": LONG_TERM_ACTIONS.get(
            primary_category, LONG_TERM_ACTIONS["default"]
        ),
        "score_breakdown": {
            "baseline": 100,
            "deductions": deductions if deductions else ["No contaminants identified"],
            "final_score": final_score,
            "scoring_rule": "Lowest individual contaminant score is used when multiple issues present",
            "scoring_groups": {
                "sewage_smell": "Score = 0 (Stop all use)",
                "black_water": "Score = 10",
                "iron": "Score = 25 (Safe to bathe)",
                "h2s_egg_smell": "Score = 45 (Safe to bathe)",
                "tds_800plus": "Score = 20",
                "tds_500plus": "Score = 30",
                "tds_200plus": "Score = 40",
            },
        },
    }
