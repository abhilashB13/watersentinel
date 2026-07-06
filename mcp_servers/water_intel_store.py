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
  - COLONY-LEVEL GRANULARITY (v2): pincode and even area_name are too
    coarse — the same pincode/area can contain multiple colonies (e.g.
    MIG/LIG/HIG Colony within Nallagandla, pincode 500032) with very
    different water quality depending on local infrastructure age,
    borewell depth, and maintenance. Reports now optionally carry a
    colony_name, and cluster detection checks colony-level matches FIRST
    (most personal, most actionable alert — "your actual neighbours"),
    falling back to area-level matching if colony data isn't available.
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
        "Stores citizen reports by pincode, area, and colony, detects "
        "contamination clusters at colony or area level, and provides "
        "topology data for the community map. "
        "All location data is stored at pincode/area/colony level only — "
        "no street address, no GPS, no PII."
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
            colony_name TEXT DEFAULT '',
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pincode TEXT NOT NULL,
            area_name TEXT NOT NULL,
            colony_name TEXT NOT NULL DEFAULT 'Unspecified',
            source_type TEXT NOT NULL DEFAULT 'unknown',
            avg_score REAL,
            report_count INTEGER,
            primary_contaminant TEXT,
            colour_band TEXT,
            lat REAL,
            lng REAL,
            last_updated TEXT,
            UNIQUE(pincode, area_name, colony_name, source_type)
        );

        CREATE INDEX IF NOT EXISTS idx_pincode
            ON water_reports(pincode);
        CREATE INDEX IF NOT EXISTS idx_timestamp
            ON water_reports(timestamp);
        CREATE INDEX IF NOT EXISTS idx_pincode_timestamp
            ON water_reports(pincode, timestamp);
        CREATE INDEX IF NOT EXISTS idx_colony
            ON water_reports(pincode, colony_name);
    """)
    conn.commit()

    # Backfill colony_name column if this DB was created before this version
    # (safe no-op if the column already exists)
    try:
        conn.execute("ALTER TABLE water_reports ADD COLUMN colony_name TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

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
    colony_name: str,
    source_type: str,
    lat: float,
    lng: float,
):
    """
    Recalculate and update topology score for a specific
    (pincode, area_name, colony_name, source_type) combination.
    Each combination gets its own row — this is what allows MIG Colony
    and LIG Colony within the same area/pincode to show different scores,
    and what allows the same colony's municipal supply vs borewell to
    also differ.
    """
    colony_key = colony_name or "Unspecified"

    rows = conn.execute("""
        SELECT quality_score, contaminants
        FROM water_reports
        WHERE pincode = ? AND area_name = ?
          AND COALESCE(NULLIF(colony_name, ''), 'Unspecified') = ?
          AND source_type = ?
    """, (pincode, area_name, colony_key, source_type)).fetchall()

    if not rows:
        return

    scores = [row["quality_score"] for row in rows]
    avg_score = round(sum(scores) / len(scores))
    colour_band = score_to_colour_band(avg_score)

    all_contaminants = []
    for row in rows:
        try:
            contaminants = json.loads(row["contaminants"] or "[]")
            if isinstance(contaminants, list):
                all_contaminants.extend(contaminants)
            elif contaminants:
                all_contaminants.append(contaminants)
        except (json.JSONDecodeError, TypeError):
            # Raw value wasn't valid JSON — treat as a single plain string
            if row["contaminants"]:
                all_contaminants.append(row["contaminants"])

    # FIXED: previously used max(set(...), key=count) directly on raw,
    # inconsistently-formatted strings (mix of 'Iron', 'iron_colour',
    # '["H2S"]' etc.) — this is what caused the same real-world condition
    # to fragment into multiple topology_scores rows purely due to string
    # format differences, and caused filter chips like "Fecal Coliform" to
    # never match anything since the stored format didn't match the chip's
    # search text. Now routes through normalize_contaminant(), the ONE
    # canonical classifier used everywhere in the codebase.
    from mcp_servers.contaminant_classifier import normalize_contaminant
    primary_contaminant = normalize_contaminant(all_contaminants)

    conn.execute("""
        INSERT OR REPLACE INTO topology_scores
        (pincode, area_name, colony_name, source_type, avg_score, report_count,
         primary_contaminant, colour_band, lat, lng, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pincode, area_name, colony_key, source_type, avg_score, len(rows),
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
    colony_name: str = "",
) -> dict:
    """
    Submit a new citizen water quality report to the community database.
    Called by CommunityMapper agent after WaterProfiler completes diagnosis.
    Location stored as pincode + area + optional colony — no street
    address, no GPS coordinates beyond the general area marker.

    colony_name is optional. When provided, it enables much more precise
    community alerts (e.g. "your literal neighbours in MIG Colony Phase 1
    reported this" rather than the more diffuse "somewhere in Nallagandla").
    """
    conn = get_db_connection()
    try:
        timestamp = datetime.now().isoformat()

        cursor = conn.execute("""
            INSERT INTO water_reports
            (pincode, area_name, colony_name, source_type, quality_score, colour_band,
             contaminants, symptoms, lat, lng, is_mock, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (
            pincode, area_name, colony_name or "", source_type, quality_score, colour_band,
            json.dumps(contaminants), json.dumps(symptoms),
            lat, lng, timestamp,
        ))
        report_id = cursor.lastrowid
        conn.commit()

        update_topology_score_internal(
            conn, pincode, area_name, colony_name or "", source_type, lat, lng
        )

        return {
            "success": True,
            "report_id": report_id,
            "pincode": pincode,
            "area_name": area_name,
            "colony_name": colony_name or "",
            "timestamp": timestamp,
            "message": f"Report #{report_id} submitted for {colony_name or area_name} ({pincode})",
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
    Returns ALL (area/colony/source) combinations under this pincode,
    since a single pincode can contain multiple distinct water quality
    situations depending on colony and source type.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM topology_scores WHERE pincode = ? ORDER BY avg_score ASC",
            (pincode,)
        ).fetchall()

        if rows:
            return {
                "found": True,
                "pincode": pincode,
                "combinations": [
                    {
                        "area_name": row["area_name"],
                        "colony_name": row["colony_name"],
                        "source_type": row["source_type"],
                        "avg_score": row["avg_score"],
                        "colour_band": row["colour_band"],
                        "report_count": row["report_count"],
                        "primary_contaminant": row["primary_contaminant"],
                        "lat": row["lat"],
                        "lng": row["lng"],
                        "last_updated": row["last_updated"],
                    }
                    for row in rows
                ],
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

def _extract_contaminants(rows) -> list:
    """
    Parses contaminant JSON from a list of DB rows into a flat, unique,
    readable list. FIXED: previously this function received a single
    comma-joined string and did a naive .split(",") before parsing —
    which corrupts any row whose own JSON array contains more than one
    item (e.g. '["no_visible_symptom", "stomach_issues"]' gets split
    mid-array into malformed fragments, producing garbled text like
    the ']" leaking into a citizen-facing community alert message).

    Now takes the raw row objects directly and parses each row's
    contaminants field independently, BEFORE any joining — no string
    splitting on commas ever happens, so multi-item arrays stay intact.
    """
    found = set()
    for row in rows:
        raw = row["contaminants"] if row["contaminants"] else None
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for item in parsed:
                    if item and str(item).strip():
                        found.add(str(item).strip())
            elif isinstance(parsed, str) and parsed.strip():
                found.add(parsed.strip())
        except (json.JSONDecodeError, ValueError, TypeError):
            # Raw string wasn't valid JSON — skip rather than guess-parse it
            continue
    # Convert to readable text (underscores -> spaces, title case) here,
    # once, rather than leaving raw identifiers for the caller to clean up
    readable = [c.replace("_", " ").strip().title() for c in found if c and c.lower() != "none"]
    return readable[:5]


@mcp.tool()
def get_cluster_status(
    pincode: str,
    colony_name: str = None,
    contaminant_types: list = None,
    days: int = CLUSTER_WINDOW_DAYS,
) -> dict:
    """
    Check if a community contamination cluster exists for a citizen's report.
    ANTIGRAVITY TRIGGER: When cluster_detected = True, CommunityMapper
    generates the community alert that surprises the citizen.

    TIERED MATCHING (colony-first, area fallback):
      Tier 1 — If colony_name is provided, checks for >= CLUSTER_THRESHOLD
               reports in the SAME colony within `days`. This is the most
               personal, most actionable alert — genuinely "your neighbours."
      Tier 2 — If colony_name wasn't provided, or the colony has fewer
               than threshold matching reports, falls back to the original
               area_name-level matching.

    Returns matched_level: "colony" | "area" | "none" so the caller can
    phrase the alert appropriately.
    """
    conn = get_db_connection()
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Find this pincode's most recent area_name for fallback/context
        area_row = conn.execute("""
            SELECT area_name FROM water_reports
            WHERE pincode = ? ORDER BY timestamp DESC LIMIT 1
        """, (pincode,)).fetchone()
        area_name = area_row["area_name"] if area_row else pincode

        def _filter_by_contaminant(rows):
            if not contaminant_types:
                return rows
            matched = []
            for row in rows:
                try:
                    row_contaminants = json.loads(row["contaminants"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    row_contaminants = []
                if any(c in row_contaminants for c in contaminant_types):
                    matched.append(row)
            return matched

        # ── Tier 1 — Colony-level ────────────────────────────────────────────
        if colony_name:
            colony_rows = conn.execute("""
                SELECT id, area_name, colony_name, contaminants, symptoms, timestamp, source_type
                FROM water_reports
                WHERE pincode = ? AND colony_name = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (pincode, colony_name, cutoff_date)).fetchall()

            colony_matches = _filter_by_contaminant(colony_rows)
            colony_count = len(colony_matches)

            if colony_count >= CLUSTER_THRESHOLD:
                return {
                    "cluster_detected": True,
                    "pincode": pincode,
                    "area_name": area_name,
                    "colony_name": colony_name,
                    "matched_level": "colony",
                    "count": colony_count,
                    "threshold": CLUSTER_THRESHOLD,
                    "time_window_days": days,
                    "contaminants_found": _extract_contaminants(colony_matches),
                    "earliest_report": colony_matches[0]["timestamp"][:10] if colony_matches else "",
                    "message": (
                        f"{colony_count} households in your colony ({colony_name}, {area_name}) "
                        f"reported water issues in the last {days} days."
                    ),
                }

        # ── Tier 2 — Area-level fallback ──────────────────────────────────────
        area_rows = conn.execute("""
            SELECT id, area_name, colony_name, contaminants, symptoms, timestamp, source_type
            FROM water_reports
            WHERE pincode = ? AND area_name = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (pincode, area_name, cutoff_date)).fetchall()

        area_matches = _filter_by_contaminant(area_rows)
        area_count = len(area_matches)
        cluster_detected = area_count >= CLUSTER_THRESHOLD

        return {
            "cluster_detected": cluster_detected,
            "pincode": pincode,
            "area_name": area_name,
            "colony_name": colony_name or "",
            "matched_level": "area" if cluster_detected else "none",
            "count": area_count,
            "threshold": CLUSTER_THRESHOLD,
            "time_window_days": days,
            "contaminants_found": _extract_contaminants(area_matches),
            "earliest_report": area_matches[0]["timestamp"][:10] if area_matches else "",
            "message": (
                f"{area_count} households in {area_name} reported water issues "
                f"in the last {days} days."
                if cluster_detected
                else f"Only {area_count} report(s) — below cluster threshold of {CLUSTER_THRESHOLD}."
            ),
        }
    finally:
        conn.close()


# ── MCP Tool 4: get_area_history ──────────────────────────────────────────────

@mcp.tool()
def get_area_history(pincode: str, days: int = 30) -> list:
    """
    Get time-series quality score history for a pincode.
    Used by the map screen to show water quality trends over time.
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
    colony_name: str = "",
    source_type: str = "unknown",
    lat: float = 0.0,
    lng: float = 0.0,
) -> dict:
    """
    Directly update the topology score for a specific
    (pincode, area_name, colony_name, source_type) combination.
    Called by CommunityMapper after cluster detection or manual correction.
    """
    conn = get_db_connection()
    try:
        colony_key = colony_name or "Unspecified"

        existing = conn.execute("""
            SELECT * FROM topology_scores
            WHERE pincode = ? AND area_name = ? AND colony_name = ? AND source_type = ?
        """, (pincode, area_name or pincode, colony_key, source_type)).fetchone()

        final_area_name = area_name or (existing["area_name"] if existing else pincode)
        final_lat = lat or (existing["lat"] if existing else 0.0)
        final_lng = lng or (existing["lng"] if existing else 0.0)
        final_count = (existing["report_count"] if existing else 0)

        conn.execute("""
            INSERT OR REPLACE INTO topology_scores
            (pincode, area_name, colony_name, source_type, avg_score, report_count,
             primary_contaminant, colour_band, lat, lng, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pincode, final_area_name, colony_key, source_type, new_score, final_count,
            existing["primary_contaminant"] if existing else "Unknown",
            colour_band, final_lat, final_lng,
            datetime.now().isoformat(),
        ))
        conn.commit()

        return {
            "success": True,
            "pincode": pincode,
            "colony_name": colony_key,
            "new_score": new_score,
            "colour_band": colour_band,
            "message": f"Topology updated for {colony_key}, {final_area_name}: {new_score}/100 ({colour_band})",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ── MCP Tool 6: get_all_topology_data ─────────────────────────────────────────

@mcp.tool()
def get_all_topology_data() -> list:
    """
    Retrieve all topology score combinations for rendering the community map.
    Each row is a distinct (pincode, area_name, colony_name, source_type)
    combination — meaning the map can render MIG Colony and LIG Colony
    within the same area as separate, independently-scored points.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT
                pincode, area_name, colony_name, source_type, avg_score, report_count,
                primary_contaminant, colour_band, lat, lng, last_updated
            FROM topology_scores
            WHERE lat IS NOT NULL AND lat != 0
            ORDER BY avg_score ASC
        """).fetchall()

        return [
            {
                "pincode": row["pincode"],
                "area_name": row["area_name"],
                "colony_name": row["colony_name"],
                "source_type": row["source_type"],
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
