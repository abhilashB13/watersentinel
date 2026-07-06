"""
Module: mcp_servers/location_canonicalizer.py
Purpose: Same principle as contaminant_classifier.py, applied to area/colony
NAMES instead of contaminant types. Autocomplete (<datalist>) only
SUGGESTS existing values — it cannot stop a citizen from typing a near-
duplicate anyway (e.g. "lingampally" lowercase, or "Lingampalli" misspelled).
This module catches that at write time: before inserting a new area/colony
name, check if it's a close fuzzy match to an EXISTING name already in the
database, and if so, auto-correct to the existing canonical spelling
instead of creating a second fragmented entry.

Uses Python's built-in difflib — no new dependency required.
"""

import sqlite3
import difflib

DB_PATH = "data/reports.db"

# How similar two strings must be (0.0-1.0) to be treated as the same real
# place. 0.82 is deliberately conservative — high enough that genuinely
# different places (e.g. "Kondapur" vs "Kukatpally") never falsely merge,
# but catches near-identical typos/casing (e.g. "lingampally" vs "Lingampally").
SIMILARITY_THRESHOLD = 0.82


def canonicalize_area_name(pincode: str, raw_area_name: str) -> str:
    """
    Checks raw_area_name against EXISTING area names for this pincode,
    drawn from BOTH the government-sourced pincode_master table AND any
    additional areas citizens have already reported. Matching against
    pincode_master means even a citizen typing the FIRST-EVER report for
    a real official area (e.g. "Ashok Nagar" — a genuine India Post
    office name that no citizen has reported yet) still gets correctly
    matched to its official spelling, not just typo-matched against prior
    citizen input.
    """
    if not raw_area_name or not raw_area_name.strip():
        return raw_area_name

    cleaned = raw_area_name.strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    existing_areas = []
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pincode_master'")
    if cursor.fetchone():
        cursor.execute("SELECT DISTINCT area_name FROM pincode_master WHERE pincode = ?", (pincode,))
        existing_areas.extend(row[0] for row in cursor.fetchall())

    cursor.execute(
        "SELECT DISTINCT area_name FROM water_reports WHERE pincode = ? AND area_name IS NOT NULL AND area_name != ''",
        (pincode,)
    )
    for row in cursor.fetchall():
        if row[0] not in existing_areas:
            existing_areas.append(row[0])
    conn.close()

    if not existing_areas:
        return cleaned.title()

    matches = difflib.get_close_matches(cleaned, existing_areas, n=1, cutoff=SIMILARITY_THRESHOLD)
    if matches:
        return matches[0]  # use the EXISTING canonical spelling, not the new near-duplicate

    return cleaned.title()


def canonicalize_colony_name(pincode: str, area_name: str, raw_colony_name: str) -> str:
    """
    Same logic as canonicalize_area_name, scoped to colonies within a
    specific pincode+area — since the same colony name might legitimately
    exist in different areas (e.g. two different "Gandhi Nagar" colonies
    in two different parts of the city), matching must stay scoped.
    """
    if not raw_colony_name or not raw_colony_name.strip():
        return raw_colony_name

    cleaned = raw_colony_name.strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT colony_name FROM water_reports
        WHERE pincode = ? AND area_name = ?
          AND colony_name IS NOT NULL AND colony_name != '' AND colony_name != 'Unspecified'
    """, (pincode, area_name))
    existing_colonies = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not existing_colonies:
        return cleaned.title()

    matches = difflib.get_close_matches(cleaned, existing_colonies, n=1, cutoff=SIMILARITY_THRESHOLD)
    if matches:
        return matches[0]

    return cleaned.title()
