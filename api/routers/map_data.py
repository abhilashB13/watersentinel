"""
Module: api/routers/map_data.py
Purpose: Map data endpoints. Serves topology heatmap data directly
         from SQLite (bypasses agent pipeline for speed).
         Also serves pincode-level history for trend charts.
Component: API — Map Data Endpoints
Inputs: HTTP GET requests from mobile app map screen
Outputs: JSON arrays of pincode topology scores and history
Key Design Decisions:
  - Direct SQLite read (no agent pipeline): map data must load fast.
    Running 5 agents per map refresh would be too slow for smooth UX.
    The topology_scores table is always up-to-date (updated after each report).
  - Heatmap intensity field: pre-calculated (100-score)/100 so the
    Leaflet.heat plugin can use it directly without client-side math.
  - /map/pincode/{pincode}/history: enables the mobile app to show a
    trend line for a selected pincode — quality improving or worsening.
Competition Concepts Demonstrated:
  - Deployability (REST API serving mobile app map in real time)
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/map", tags=["map"])

DB_PATH = os.getenv("WATER_INTEL_DB_PATH", "./data/reports.db")


def get_db():
    """Get SQLite connection. Raises 503 if database not initialised."""
    if not Path(DB_PATH).exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Database not initialised. "
                "Run: python scripts/seed_mock_data.py"
            ),
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/topology")
async def get_topology():
    """
    Get all pincode water quality scores for the Leaflet heatmap.
    Called by the mobile app map screen on load and after each report.

    Returns list of pincode records with lat, lng, score, colour_band,
    heat_intensity (for Leaflet.heat plugin), and report metadata.
    """
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT
                pincode, area_name, avg_score, report_count,
                primary_contaminant, colour_band, lat, lng, last_updated
            FROM topology_scores
            WHERE lat IS NOT NULL AND lat != 0
            ORDER BY avg_score ASC
        """).fetchall()

        return [
            {
                "pincode": row["pincode"],
                "area_name": row["area_name"],
                "avg_score": row["avg_score"],
                "report_count": row["report_count"],
                "primary_contaminant": row["primary_contaminant"],
                "colour_band": row["colour_band"],
                "lat": row["lat"],
                "lng": row["lng"],
                "last_updated": row["last_updated"],
                # Heat intensity: invert score so red areas = highest intensity
                # Range: 0.0 (perfect water) to 1.0 (severely contaminated)
                "heat_intensity": round((100 - (row["avg_score"] or 50)) / 100, 2),
            }
            for row in rows
        ]
    finally:
        conn.close()


@router.get("/pincode/{pincode}/history")
async def get_pincode_history(pincode: str, days: int = 30):
    """
    Get water quality score history for a specific pincode.
    Used by mobile app to show trend chart when user taps a map marker.

    Args:
        pincode: 6-digit Indian pincode
        days: Number of days of history (default 30, max 90)

    Returns:
        List of daily average scores with colour band and report count
    """
    # Validate pincode
    if not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(status_code=400, detail="Invalid pincode format")

    # Cap days at 90 to prevent large queries
    days = min(days, 90)

    conn = get_db()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        rows = conn.execute("""
            SELECT
                date(timestamp) as report_date,
                AVG(quality_score) as avg_score,
                COUNT(*) as report_count
            FROM water_reports
            WHERE pincode = ? AND timestamp >= ?
            GROUP BY date(timestamp)
            ORDER BY report_date ASC
        """, (pincode, cutoff)).fetchall()

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for pincode {pincode} in last {days} days",
            )

        def score_to_band(score: float) -> str:
            if score >= 80: return "green"
            elif score >= 60: return "yellow"
            elif score >= 40: return "orange"
            return "red"

        return {
            "pincode": pincode,
            "days_requested": days,
            "data_points": len(rows),
            "history": [
                {
                    "date": row["report_date"],
                    "avg_score": round(row["avg_score"], 1),
                    "colour_band": score_to_band(row["avg_score"]),
                    "report_count": row["report_count"],
                }
                for row in rows
            ],
        }
    finally:
        conn.close()


@router.get("/pincode/{pincode}/profile")
async def get_pincode_profile(pincode: str):
    """
    Get the current aggregate water quality profile for a pincode.
    Returns overall score, most common contaminant, and report count.
    """
    if not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(status_code=400, detail="Invalid pincode format")

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM topology_scores WHERE pincode = ?", (pincode,)
        ).fetchone()

        if not row:
            return {
                "found": False,
                "pincode": pincode,
                "message": "No reports yet for this pincode",
            }

        return {
            "found": True,
            "pincode": pincode,
            "area_name": row["area_name"],
            "avg_score": row["avg_score"],
            "colour_band": row["colour_band"],
            "report_count": row["report_count"],
            "primary_contaminant": row["primary_contaminant"],
            "lat": row["lat"],
            "lng": row["lng"],
            "last_updated": row["last_updated"],
        }
    finally:
        conn.close()
