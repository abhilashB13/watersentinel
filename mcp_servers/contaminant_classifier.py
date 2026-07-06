"""
Module: mcp_servers/contaminant_classifier.py
Purpose: ONE canonical function for converting raw contaminant/symptom data
(in whatever format it arrives — snake_case symptom IDs, capitalized words,
JSON arrays, plain strings) into a single consistent display format that
matches the Map page's filter chip vocabulary exactly.

WHY THIS EXISTS: audit_all_filters.py found primary_contaminant stored in
at least 4 different formats simultaneously (plain 'Iron', underscored
'Fecal_Coliform', JSON arrays of capitalized words '["H2S", "Iron"]', and
JSON arrays of snake_case symptom IDs '["yellow_colour", "salty_taste"]')
— causing the 'Fecal Coliform' filter chip to silently match zero rows
despite real matching data existing, AND causing the same real-world
condition to fragment into multiple separate topology_scores rows purely
due to storage-format inconsistency (confirmed for Lingampally/MIG Colony
Phase 1, which had 'H2S' and '["H2S"]' as two separate rows for the same
colony/source).

Every code path that writes primary_contaminant — submit_report,
update_topology_score, and any migration/seed script — must route through
this function, so the format can never fragment again.
"""

import json

# Maps ANY raw symptom identifier or legacy contaminant string to exactly
# ONE canonical display label. These labels are the single source of truth
# and MUST match the Map page's CONTAMINANT_FILTERS chip labels exactly
# (High TDS, Iron, H2S, Fecal Coliform) for the filter to ever work.
CANONICAL_CONTAMINANT_MAP = {
    # Sewage / faecal — all variants collapse to one canonical label
    "sewage_smell": "Fecal Coliform",
    "sewage_contamination": "Fecal Coliform",
    "fecal_coliform": "Fecal Coliform",
    "coliform": "Fecal Coliform",
    "e_coli": "Fecal Coliform",
    "cholera": "Fecal Coliform",
    "typhoid": "Fecal Coliform",

    # Black water / manganese
    "black_colour": "Black Water",
    "dark_water": "Black Water",
    "manganese": "Black Water",

    # Iron
    "iron": "Iron",
    "yellow_colour": "Iron",
    "fe": "Iron",

    # H2S
    "h2s": "H2S",
    "egg_smell": "H2S",
    "hydrogen_sulphide": "H2S",

    # High TDS
    "high_tds": "High TDS",
    "white_deposits": "High TDS",
    "salty_taste": "High TDS",
    "metallic_taste": "High TDS",

    # Other known contaminants (not currently filter chips, but kept canonical)
    "fluoride": "Fluoride",
    "nitrate": "Nitrate",
    "arsenic": "Arsenic",

    # Symptoms that are real but don't map to a specific filter-chip contaminant
    "stomach_issues": None,
    "gritty_texture": None,
    "foamy_water": None,
    "oily_sheen": None,
    "insects_visible": None,
    "skin_irritation": None,
    "vessel_staining": None,
    "colour_after_standing": "Iron",  # delayed iron oxidation — same underlying cause
    "chlorine_smell": None,
    "milky_appearance": None,
    "blue_green_stain": None,
    "no_visible_symptom": None,

    # Legacy stored values from earlier seed scripts (capitalized, no underscore
    # conversion needed but still normalized through this same map for consistency)
    "none": None,
}


def normalize_contaminant(raw_value) -> str:
    """
    Converts ANY raw contaminant/symptom value — string, JSON-array string,
    list, or None — into ONE canonical display string, e.g. "Iron, H2S" or
    "None". This is the ONLY function that should ever produce a
    primary_contaminant value anywhere in the codebase.
    """
    if raw_value is None or raw_value == "" or raw_value == "[]":
        return "None"

    # Parse JSON array strings into a real list first
    items = raw_value
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                items = json.loads(stripped)
            except (json.JSONDecodeError, ValueError):
                items = [stripped]
        else:
            items = [stripped]
    elif not isinstance(raw_value, list):
        items = [str(raw_value)]

    canonical_labels = []
    for item in items:
        key = str(item).strip().lower().replace(" ", "_").replace("-", "_")
        label = CANONICAL_CONTAMINANT_MAP.get(key)
        if label and label not in canonical_labels:
            canonical_labels.append(label)

    if not canonical_labels:
        return "None"
    return ", ".join(canonical_labels)
