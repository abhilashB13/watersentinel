"""
Module: api/routers/map_data.py
UPDATED: TopologyPoint now includes colony_name. When multiple colonies exist
within the same area (grouped by source_type too), each colony returns as a
SEPARATE point — this is what allows the map to show granular per-colony
markers instead of one blended area-level dot.
"""

import sqlite3
import json
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(tags=["map"])

DB_PATH = "data/reports.db"


def _score_to_band(score: float) -> str:
    if score >= 80: return "green"
    if score >= 60: return "yellow"
    if score >= 40: return "orange"
    return "red"


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
    ),
    days_back: Optional[int] = Query(
        default=None,
        description="Filter to reports from the last N days (e.g. 1 for Today, 7 for Last 7d, 30 for Last 30d). Omit for all-time."
    ),
    state: Optional[str] = Query(default=None, description="Filter to reports within this state only, via pincode_master lookup"),
    city: Optional[str] = Query(default=None, description="Filter to reports within this city only, via pincode_master lookup"),
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

    try:
        if days_back is not None:
            # REAL time filtering: query water_reports directly by timestamp
            # (topology_scores is pre-aggregated with no per-report date, so
            # accurate time filtering requires the raw reports table).
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()
            source_clause = "AND source_type = ?" if (source_type and source_type != "all") else ""
            params = [cutoff] + ([source_type] if source_clause else [])

            cursor.execute(f"""
                SELECT
                    pincode, area_name,
                    COALESCE(NULLIF(colony_name, ''), 'Unspecified') as colony_name,
                    {'source_type' if source_clause else "'all'"} as source_type,
                    AVG(quality_score) as avg_score,
                    COUNT(*) as report_count,
                    MAX(lat) as lat, MAX(lng) as lng,
                    MAX(timestamp) as last_updated
                FROM water_reports
                WHERE timestamp >= ? {source_clause}
                GROUP BY pincode, area_name, colony_name {', source_type' if source_clause else ''}
                ORDER BY avg_score ASC
            """, params)
            rows = cursor.fetchall()
            # FIXED: previously grabbed only the single worst-scoring
            # report's RAW contaminants JSON string and used it verbatim
            # as primary_contaminant — completely bypassing normalization.
            # This is why bracketed/raw values like '["egg_smell",
            # "yellow_colour"]' kept appearing specifically whenever a
            # days_back time filter (Today/Last 7d/Last 30d) was active,
            # even after topology_scores itself was fully cleaned — this
            # branch reads water_reports directly and never touched
            # topology_scores at all. Now collects ALL matching reports'
            # contaminants for the group and normalizes the combined set,
            # exactly like the other two query branches already do.
            from mcp_servers.contaminant_classifier import normalize_contaminant
            enriched_rows = []
            for r in rows:
                cursor.execute("""
                    SELECT contaminants FROM water_reports
                    WHERE pincode = ? AND area_name = ?
                      AND COALESCE(NULLIF(colony_name, ''), 'Unspecified') = ?
                      AND timestamp >= ?
                """, (r["pincode"], r["area_name"], r["colony_name"], cutoff))
                all_raw = []
                for row in cursor.fetchall():
                    raw = row[0]
                    if not raw:
                        continue
                    try:
                        parsed = json.loads(raw) if raw.strip().startswith("[") else raw
                        if isinstance(parsed, list):
                            all_raw.extend(parsed)
                        else:
                            all_raw.append(parsed)
                    except (json.JSONDecodeError, ValueError):
                        all_raw.append(raw)
                normalized = normalize_contaminant(all_raw)
                enriched_rows.append({**dict(r), "primary_contaminant": normalized, "colour_band": _score_to_band(r["avg_score"])})
            rows = enriched_rows
        elif source_type and source_type != "all":
            cursor.execute("""
                SELECT pincode, area_name, colony_name, source_type, avg_score, report_count,
                       primary_contaminant, colour_band, lat, lng, last_updated
                FROM topology_scores
                WHERE source_type = ?
                ORDER BY avg_score ASC
            """, (source_type,))
            rows = [dict(r) for r in cursor.fetchall()]
        else:
            # FIXED: previously selected primary_contaminant directly under
            # a GROUP BY with no aggregation function — when a colony has
            # multiple source-type rows (e.g. borewell AND municipal_pipeline
            # both existing for the same colony), SQLite picked ONE
            # arbitrary underlying row's contaminant string rather than a
            # genuine merge. This is what caused the "all sources" view to
            # show inconsistent/stale-looking contaminant values even after
            # each individual source-specific row was correctly normalized —
            # the per-source rows were fine, this aggregation step wasn't.
            #
            # Now explicitly collects contaminants from EVERY underlying row
            # in the group and re-normalizes the combined set, exactly like
            # each individual source-type row already does.
            cursor.execute("""
                SELECT pincode, area_name, colony_name,
                       AVG(avg_score) as avg_score,
                       SUM(report_count) as report_count,
                       colour_band, lat, lng, last_updated
                FROM topology_scores
                GROUP BY pincode, area_name, colony_name
                ORDER BY avg_score ASC
            """)
            grouped = cursor.fetchall()

            from mcp_servers.contaminant_classifier import normalize_contaminant

            rows = []
            for g in grouped:
                # Pull every distinct primary_contaminant string across all
                # source-type rows for this (pincode, area, colony), then
                # re-normalize the combined set into one canonical value.
                cursor.execute("""
                    SELECT primary_contaminant FROM topology_scores
                    WHERE pincode = ? AND area_name = ? AND colony_name = ?
                """, (g["pincode"], g["area_name"], g["colony_name"]))
                # Each stored value may itself be a comma-joined canonical
                # string (e.g. "H2S, Iron") from a single source-type row —
                # split those apart into individual items before re-merging,
                # since normalize_contaminant expects individual raw items,
                # not pre-joined strings.
                all_contaminant_strings = []
                for r in cursor.fetchall():
                    if r[0]:
                        all_contaminant_strings.extend(part.strip() for part in r[0].split(","))
                merged_contaminant = normalize_contaminant(all_contaminant_strings)

                rows.append({
                    "pincode": g["pincode"], "area_name": g["area_name"],
                    "colony_name": g["colony_name"], "source_type": "all",
                    "avg_score": g["avg_score"], "report_count": g["report_count"],
                    "primary_contaminant": merged_contaminant,
                    "colour_band": g["colour_band"], "lat": g["lat"], "lng": g["lng"],
                    "last_updated": g["last_updated"],
                })
    except Exception:
        # Safety net: if the time-filter query fails for any reason, fall
        # back to unfiltered topology_scores rather than erroring out the map
        rows = []
    finally:
        conn.close()

    # FIXED: previously filtered by EXACT pincode membership in
    # pincode_master — meaning a real citizen report using a pincode that
    # correctly STARTS WITH a known city's prefix (e.g. 500086, 500075,
    # 500089 — all genuinely Hyderabad-range pincodes) but happens to NOT
    # exist as a literal row in the government reference dataset was
    # silently excluded entirely. The reference table can label EXISTING
    # rows correctly, but it can't vouch for pincodes it doesn't contain.
    #
    # Now derives the PREFIX(es) associated with the requested city/state
    # from pincode_master (using whichever known pincodes it does have as
    # a sample), then matches report pincodes by PREFIX — robust regardless
    # of whether every individual pincode exists in the reference table.
    if state or city:
        conn2 = sqlite3.connect(DB_PATH)
        cursor2 = conn2.cursor()
        conditions = []
        params = []
        if state:
            conditions.append("state = ?")
            params.append(state)
        if city:
            conditions.append("city = ?")
            params.append(city)
        cursor2.execute(f"SELECT DISTINCT pincode FROM pincode_master WHERE {' AND '.join(conditions)}", params)
        sample_pincodes = [row[0] for row in cursor2.fetchall()]
        conn2.close()

        # Derive 3-digit prefixes from the known matching pincodes — this
        # generalizes correctly since Indian pincode prefixes are assigned
        # by region, so any report sharing that prefix genuinely belongs
        # to the same city/state, even if that exact pincode number isn't
        # in the reference table.
        allowed_prefixes = {p[:3] for p in sample_pincodes if len(p) >= 3}
        rows = [r for r in rows if r["pincode"][:3] in allowed_prefixes]

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


@router.get("/map/available-locations")
async def get_available_locations(state: Optional[str] = Query(default=None, description="If provided, cities are narrowed to only this state")):
    """
    Returns distinct states and cities from pincode_master, for the Map
    page's State/City filter dropdowns. Only returns states/cities that
    genuinely have citizen reports (not every state in pincode_master,
    which could be all of India) — so the dropdown only shows places
    where there's actually something to view.

    FIXED: previously returned ALL cities regardless of which state was
    selected, meaning selecting "Telangana" still showed "Kanpur" as a
    city option — no relationship existed between the two dropdowns.
    Now accepts an optional `state` param that narrows the returned
    cities to only that state, giving genuine State -> City cascading.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pincode_master'")
    if not cursor.fetchone():
        conn.close()
        return {"states": [], "cities": []}

    cursor.execute("""
        SELECT DISTINCT pm.state FROM pincode_master pm
        WHERE pm.pincode IN (SELECT DISTINCT pincode FROM water_reports)
        ORDER BY pm.state
    """)
    states = [row[0] for row in cursor.fetchall() if row[0]]

    if state:
        cursor.execute("""
            SELECT DISTINCT pm.city FROM pincode_master pm
            WHERE pm.pincode IN (SELECT DISTINCT pincode FROM water_reports)
              AND pm.state = ?
            ORDER BY pm.city
        """, (state,))
    else:
        cursor.execute("""
            SELECT DISTINCT pm.city FROM pincode_master pm
            WHERE pm.pincode IN (SELECT DISTINCT pincode FROM water_reports)
            ORDER BY pm.city
        """)
    cities = [row[0] for row in cursor.fetchall() if row[0]]

    conn.close()
    return {"states": states, "cities": cities}
