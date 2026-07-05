"""
Module: api/routers/map_data.py
UPDATED: TopologyPoint now includes colony_name. When multiple colonies exist
within the same area (grouped by source_type too), each colony returns as a
SEPARATE point — this is what allows the map to show granular per-colony
markers instead of one blended area-level dot.
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
    colony_name: str = "Unspecified"
    source_type: str = "unknown"
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
    Returns topology data for the community map, now at colony granularity.
    Each row is a distinct (pincode, area_name, colony_name, source_type)
    combination — meaning MIG Colony and LIG Colony within the same
    Nallagandla/pincode/source will appear as separate map points with
    potentially very different scores, instead of being blended into one.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if source_type and source_type != "all":
        cursor.execute("""
            SELECT pincode, area_name, colony_name, source_type, avg_score, report_count,
                   primary_contaminant, colour_band, lat, lng, last_updated
            FROM topology_scores
            WHERE source_type = ?
            ORDER BY avg_score ASC
        """, (source_type,))
    else:
        # No source filter — aggregate across sources but KEEP colony granularity
        cursor.execute("""
            SELECT
                pincode, area_name, colony_name,
                'all' as source_type,
                AVG(avg_score) as avg_score,
                SUM(report_count) as report_count,
                primary_contaminant,
                colour_band,
                lat, lng, last_updated
            FROM topology_scores
            GROUP BY pincode, area_name, colony_name
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
            colony_name=row["colony_name"] or "Unspecified",
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
