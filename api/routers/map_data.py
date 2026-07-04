"""
Module: api/routers/map_data.py
UPDATE: /map/topology now accepts optional ?source_type= query param.
When provided, filters topology data to only that source type.
When omitted or 'all', returns all source types (existing behaviour).
"""

import sqlite3
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(tags=["map"])

DB_PATH = "data/reports.db"


class TopologyPoint(BaseModel):
    pincode: str
    area_name: str
    source_type: str = "unknown"  # NEW field
    avg_score: float
    report_count: int
    primary_contaminant: str
    colour_band: str
    lat: float
    lng: float
    heat_intensity: float = 0.5
    last_updated: str


@router.get("/map/topology", response_model=list[TopologyPoint])
async def get_topology(
    source_type: Optional[str] = Query(
        default=None,
        description="Filter by water source: municipal_pipeline, borewell, hand_pump, open_well. Omit or 'all' for everything."
    )
):
    """
    Returns topology data for the community map.
    NEW: optional source_type filter — when a citizen selects
    'Borewell' in the UI dropdown, only borewell-sourced scores
    are returned, showing that specific infrastructure's water quality
    independent of municipal/hand pump/open well data in the same area.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if source_type and source_type != "all":
        cursor.execute("""
            SELECT pincode, area_name, source_type, avg_score, report_count,
                   primary_contaminant, colour_band, lat, lng, last_updated
            FROM topology_scores
            WHERE source_type = ?
            ORDER BY avg_score ASC
        """, (source_type,))
    else:
        # No filter — aggregate across ALL source types per area (existing behaviour)
        cursor.execute("""
            SELECT
                pincode, area_name,
                'all' as source_type,
                AVG(avg_score) as avg_score,
                SUM(report_count) as report_count,
                primary_contaminant,
                colour_band,
                lat, lng, last_updated
            FROM topology_scores
            GROUP BY pincode, area_name
            ORDER BY avg_score ASC
        """)

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        max_score = 100.0
        heat = 1.0 - (row["avg_score"] / max_score)
        results.append(TopologyPoint(
            pincode=row["pincode"],
            area_name=row["area_name"],
            source_type=row["source_type"],
            avg_score=row["avg_score"],
            report_count=row["report_count"],
            primary_contaminant=row["primary_contaminant"] or "None",
            colour_band=row["colour_band"],
            lat=row["lat"] or 0.0,
            lng=row["lng"] or 0.0,
            heat_intensity=max(0.1, min(1.0, heat)),
            last_updated=row["last_updated"] or "",
        ))

    return results
