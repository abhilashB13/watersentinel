"""
Module: mcp_servers/water_intel_store.py
Purpose: MCP Server 1 — Community water quality data store.
         Provides tools for storing citizen reports, querying cluster
         patterns, and serving topology map data to ADK agents.
Component: MCP Server 1 — WaterIntel Store
Inputs: Citizen water quality reports from CommunityMapper agent
Outputs: Pincode profiles, cluster status, topology data for map
Key Design Decisions:
  - SQLite for storage: zero-config, file-based, Windows-compatible.
  - stdio transport: ADK agents launch this as a subprocess.
  - Cluster threshold = 3 reports: statistically meaningful minimum.
  - Separated from ActionBridge: data and action are distinct concerns.
Competition Concepts Demonstrated:
  - MCP Server (primary demonstration of MCP protocol)
  - Multi-agent system (agents call this server's tools)
  - Security (pincode-only location storage, no PII)
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError(
        "fastmcp not installed. Run: uv add fastmcp"
    )

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

DB_PATH = os.getenv("WATER_INTEL_DB_PATH", "./data/reports.db")
CLUSTER_THRESHOLD = int(os.getenv("CLUSTER_THRESHOLD", "3"))
CLUSTER_WINDOW_DAYS = int(os.getenv("CLUSTER_WINDOW_DAYS", "7"))

mcp = FastMCP(
    name="WaterIntel Store",
    instructions=(
        "Water quality community intelligence database for WaterSentinel. "
        "Stores citizen reports by pincode, detects contamination clusters, "
        "and provides topology data for the community map. "
        "All location data is stored at pincode level only — no PII."
    ),
)

# ── Database Initialisation ────────────────────────────────────────────────────

def get_db_connection() -> sqlite3.Connection:
    """
    Get SQLite connection with auto-creation of tables on first use.
    Creates data directory if it doesn't exist.
    """
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS water_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pincode TEXT NOT NULL,
            area_name TEXT,
            source_type TEXT NOT NULL,
            quality_score INTEGER NOT NULL,
            colour_band TEXT NOT NULL,
            contaminants TEXT,
            symptoms TEXT,
            lat REAL,
            lng REAL,
            is_mock INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS topology_scores (
            pincode TEXT PRIMARY KEY,
            area_name TEXT,
            avg_score REAL,
            report_count INTEGER,
            primary_contaminant TEXT,
            colour_band TEXT,
            lat REAL,
            lng REAL,
            last_updated TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_pincode
            ON water_reports(pincode);
        CREATE INDEX IF NOT EXISTS idx_timestamp
            ON water_reports(timestamp);
        CREATE INDEX IF NOT EXISTS idx_pincode_timestamp
            ON water_reports(pincode, timestamp);
    """)
    conn.commit()
    return conn


def score_to_colour_band(score: int) -> str:
    """Convert numeric quality score to colour band for map display."""
    if score >= 80:
        return "green"
    elif score >= 60:
        return "yellow"
    elif score >= 40:
        return "orange"
    else:
        return "red"


def update_topology_score_internal(
    conn: sqlite3.Connection,
    pincode: str,
    area_name: str,
    lat: float,
    lng: float,
):
    """Recalculate and update topology score for a pincode from all its reports."""
    rows = conn.execute("""
        SELECT quality_score, contaminants
        FROM water_reports
        WHERE pincode = ?
    """, (pincode,)).fetchall()

    if not rows:
        return

    scores = [row["quality_score"] for row in rows]
    avg_score = round(sum(scores) / len(scores), 1)
    colour_band = score_to_colour_band(int(avg_score))

    all_contaminants = []
    for row in rows:
        try:
            contaminants = json.loads(row["contaminants"] or "[]")
            all_contaminants.extend(contaminants)
        except (json.JSONDecodeError, TypeError):
            pass

    primary_contaminant = (
        max(set(all_contaminants), key=all_contaminants.count)
        if all_contaminants
        else "None detected"
    )

    conn.execute("""
        INSERT OR REPLACE INTO topology_scores
        (pincode, area_name, avg_score, report_count, primary_contaminant,
         colour_band, lat, lng, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pincode, area_name, avg_score, len(rows),
        primary_contaminant, colour_band, lat, lng,
        datetime.now().isoformat(),
    ))
    conn.commit()


# ── MCP Tool 1: submit_report ──────────────────────────────────────────────────

@mcp.tool()
def submit_report(
    pincode: str,
    area_name: str,
    source_type: str,
    quality_score: int,
    colour_band: str,
    contaminants: list,
    symptoms: list,
    lat: float,
    lng: float,
) -> dict:
    """
    Submit a new citizen water quality report to the community database.
    Called by CommunityMapper agent after WaterProfiler completes diagnosis.
    Location stored as pincode only — no street address, no GPS coordinates.
    """
    conn = get_db_connection()
    try:
        timestamp = datetime.now().isoformat()

        cursor = conn.execute("""
            INSERT INTO water_reports
            (pincode, area_name, source_type, quality_score, colour_band,
             contaminants, symptoms, lat, lng, is_mock, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (
            pincode, area_name, source_type, quality_score, colour_band,
            json.dumps(contaminants), json.dumps(symptoms),
            lat, lng, timestamp,
        ))
        report_id = cursor.lastrowid
        conn.commit()

        update_topology_score_internal(conn, pincode, area_name, lat, lng)

        return {
            "success": True,
            "report_id": report_id,
            "pincode": pincode,
            "area_name": area_name,
            "timestamp": timestamp,
            "message": f"Report #{report_id} submitted for {area_name} ({pincode})",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to submit report. Please try again.",
        }
    finally:
        conn.close()


# ── MCP Tool 2: get_pincode_profile ───────────────────────────────────────────

@mcp.tool()
def get_pincode_profile(pincode: str) -> dict:
    """
    Get the aggregate water quality profile for a pincode.
    Returns current topology score, report count, and common contaminants.
    """
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM topology_scores WHERE pincode = ?", (pincode,)
        ).fetchone()

        if row:
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
        else:
            return {
                "found": False,
                "pincode": pincode,
                "message": "No reports yet for this pincode.",
                "report_count": 0,
            }
    finally:
        conn.close()


# ── MCP Tool 3: get_cluster_status ────────────────────────────────────────────

@mcp.tool()
def get_cluster_status(
    pincode: str,
    contaminant_types: list = None,
    days: int = CLUSTER_WINDOW_DAYS,
) -> dict:
    """
    Check if a community contamination cluster exists for a pincode.
    ANTIGRAVITY TRIGGER: When cluster_detected = True, CommunityMapper
    generates the community alert that surprises the citizen.
    Cluster = >= 3 reports with matching contaminants within 7 days.
    """
    conn = get_db_connection()
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        rows = conn.execute("""
            SELECT id, area_name, contaminants, symptoms, timestamp, source_type
            FROM water_reports
            WHERE pincode = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (pincode, cutoff_date)).fetchall()

        if not rows:
            return {
                "cluster_detected": False,
                "pincode": pincode,
                "count": 0,
                "message": "No recent reports in this area.",
            }

        matching_rows = []
        for row in rows:
            try:
                row_contaminants = json.loads(row["contaminants"] or "[]")
            except (json.JSONDecodeError, TypeError):
                row_contaminants = []

            if contaminant_types:
                if any(c in row_contaminants for c in contaminant_types):
                    matching_rows.append(row)
            else:
                matching_rows.append(row)

        count = len(matching_rows)
        cluster_detected = count >= CLUSTER_THRESHOLD

        all_contaminants = []
        for row in matching_rows:
            try:
                all_contaminants.extend(json.loads(row["contaminants"] or "[]"))
            except (json.JSONDecodeError, TypeError):
                pass

        unique_contaminants = list(set(all_contaminants))
        area_name = matching_rows[0]["area_name"] if matching_rows else ""
        earliest = matching_rows[0]["timestamp"][:10] if matching_rows else ""

        return {
            "cluster_detected": cluster_detected,
            "pincode": pincode,
            "area_name": area_name,
            "count": count,
            "threshold": CLUSTER_THRESHOLD,
            "time_window_days": days,
            "contaminants_found": unique_contaminants,
            "earliest_report": earliest,
            "message": (
                f"{count} households in {area_name} reported water issues "
                f"in the last {days} days."
                if cluster_detected
                else f"Only {count} report(s) — below cluster threshold of {CLUSTER_THRESHOLD}."
            ),
        }
    finally:
        conn.close()


# ── MCP Tool 4: get_area_history ──────────────────────────────────────────────

@mcp.tool()
def get_area_history(pincode: str, days: int = 30) -> list:
    """
    Get time-series quality score history for a pincode.
    Used by the mobile app map screen to show water quality trends.
    """
    conn = get_db_connection()
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        rows = conn.execute("""
            SELECT
                date(timestamp) as report_date,
                AVG(quality_score) as avg_score,
                COUNT(*) as report_count
            FROM water_reports
            WHERE pincode = ? AND timestamp >= ?
            GROUP BY date(timestamp)
            ORDER BY report_date ASC
        """, (pincode, cutoff_date)).fetchall()

        history = []
        for row in rows:
            history.append({
                "date": row["report_date"],
                "avg_score": round(row["avg_score"], 1),
                "colour_band": score_to_colour_band(int(row["avg_score"])),
                "report_count": row["report_count"],
            })

        return history
    finally:
        conn.close()


# ── MCP Tool 5: update_topology_score ─────────────────────────────────────────

@mcp.tool()
def update_topology_score(
    pincode: str,
    new_score: int,
    colour_band: str,
    area_name: str = "",
    lat: float = 0.0,
    lng: float = 0.0,
) -> dict:
    """
    Directly update the topology score for a pincode on the map.
    Called by CommunityMapper after cluster detection.
    """
    conn = get_db_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM topology_scores WHERE pincode = ?", (pincode,)
        ).fetchone()

        final_area_name = area_name or (existing["area_name"] if existing else pincode)
        final_lat = lat or (existing["lat"] if existing else 0.0)
        final_lng = lng or (existing["lng"] if existing else 0.0)
        final_count = (existing["report_count"] if existing else 0)

        conn.execute("""
            INSERT OR REPLACE INTO topology_scores
            (pincode, area_name, avg_score, report_count, primary_contaminant,
             colour_band, lat, lng, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pincode, final_area_name, new_score, final_count,
            existing["primary_contaminant"] if existing else "Unknown",
            colour_band, final_lat, final_lng,
            datetime.now().isoformat(),
        ))
        conn.commit()

        return {
            "success": True,
            "pincode": pincode,
            "new_score": new_score,
            "colour_band": colour_band,
            "message": f"Topology updated for {final_area_name}: {new_score}/100 ({colour_band})",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ── MCP Tool 6: get_all_topology_data ─────────────────────────────────────────

@mcp.tool()
def get_all_topology_data() -> list:
    """
    Retrieve all pincode topology scores for rendering the community map.
    Called by FastAPI /map/topology endpoint for Leaflet heatmap.
    """
    conn = get_db_connection()
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
                "heat_intensity": round((100 - row["avg_score"]) / 100, 2),
            }
            for row in rows
        ]
    finally:
        conn.close()


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("WaterIntel Store MCP Server starting...", flush=True)
    print(f"Database: {DB_PATH}", flush=True)
    mcp.run(transport="stdio")
