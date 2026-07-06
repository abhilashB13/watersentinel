"""
Module: api/routers/location_suggestions.py
Purpose: CASCADING autocomplete, now backed by the real, government-sourced
pincode_master table for pincode + area suggestions — meaning every real
pincode/area in Hyderabad, Kanpur, and Vijayawada is suggested correctly
from day one, even before a single citizen report exists there. Colony
suggestions remain sourced ONLY from water_reports (citizen-submitted),
since no government database anywhere tracks colony-level names — that
layer is, by design, 100% crowdsourced and starts empty for any new city
until real citizens report from there.

Citizens can still freely type anything new at any level — this only
narrows SUGGESTIONS, never blocks or forces a selection.
"""

import sqlite3
from typing import Optional
from fastapi import APIRouter, Query

router = APIRouter(tags=["location_suggestions"])

DB_PATH = "data/reports.db"


@router.get("/location-suggestions")
async def get_location_suggestions(
    pincode: Optional[str] = Query(default=None, description="If provided, areas are filtered to this pincode only"),
    area_name: Optional[str] = Query(default=None, description="If provided (with pincode), colonies are filtered to this pincode+area only"),
):
    """
    Returns cascading location suggestions:
    - pincodes: from pincode_master (real, government-sourced) if it has
      data; falls back to water_reports (citizen-only) if pincode_master
      hasn't been seeded yet, so the feature degrades gracefully rather
      than breaking.
    - areas: filtered to the given pincode, from pincode_master first,
      supplemented with any additional areas citizens have reported under
      that pincode that aren't in the official dataset.
    - colonies: ALWAYS from water_reports only — colony data has no
      government source and is 100% citizen-reported by design.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pincode_master'")
    has_pincode_master = cursor.fetchone() is not None
    master_count = 0
    if has_pincode_master:
        cursor.execute("SELECT COUNT(*) FROM pincode_master")
        master_count = cursor.fetchone()[0]

    if has_pincode_master and master_count > 0:
        cursor.execute("SELECT DISTINCT pincode FROM pincode_master ORDER BY pincode")
        pincodes = [row[0] for row in cursor.fetchall()]

        if pincode:
            cursor.execute("SELECT DISTINCT area_name FROM pincode_master WHERE pincode = ? ORDER BY area_name", (pincode,))
            areas = [row[0] for row in cursor.fetchall()]
            cursor.execute("""
                SELECT DISTINCT area_name FROM water_reports
                WHERE pincode = ? AND area_name IS NOT NULL AND area_name != ''
            """, (pincode,))
            for row in cursor.fetchall():
                if row[0] not in areas:
                    areas.append(row[0])
        else:
            cursor.execute("SELECT DISTINCT area_name FROM pincode_master ORDER BY area_name")
            areas = [row[0] for row in cursor.fetchall()]
    else:
        cursor.execute("SELECT DISTINCT pincode FROM water_reports WHERE pincode IS NOT NULL AND pincode != '' ORDER BY pincode")
        pincodes = [row[0] for row in cursor.fetchall()]

        if pincode:
            cursor.execute("SELECT DISTINCT area_name FROM water_reports WHERE pincode = ? AND area_name IS NOT NULL AND area_name != '' ORDER BY area_name", (pincode,))
        else:
            cursor.execute("SELECT DISTINCT area_name FROM water_reports WHERE area_name IS NOT NULL AND area_name != '' ORDER BY area_name")
        areas = [row[0] for row in cursor.fetchall()]

    if pincode and area_name:
        cursor.execute("""
            SELECT DISTINCT colony_name FROM water_reports
            WHERE pincode = ? AND area_name = ? COLLATE NOCASE
              AND colony_name IS NOT NULL AND colony_name != '' AND colony_name != 'Unspecified'
            ORDER BY colony_name
        """, (pincode, area_name))
    else:
        cursor.execute("""
            SELECT DISTINCT colony_name FROM water_reports
            WHERE colony_name IS NOT NULL AND colony_name != '' AND colony_name != 'Unspecified'
            ORDER BY colony_name
        """)
    colonies = [row[0] for row in cursor.fetchall()]

    conn.close()

    return {"pincodes": pincodes, "areas": areas, "colonies": colonies}
