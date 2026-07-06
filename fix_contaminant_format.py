"""
Run this with: python fix_contaminant_format.py
(Run AFTER placing contaminant_classifier.py in mcp_servers/)

One-time cleanup: rebuilds topology_scores from water_reports using the new
canonical contaminant format — this both fixes the "Fecal Coliform never
matches" bug AND merges rows that were fragmented purely due to storage
format differences (confirmed case: MIG Colony Phase 1 borewell had 'H2S'
and '["H2S"]' as two separate rows for the same real-world colony/source,
splitting its true report count and diluting its average score).
"""

import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp_servers.contaminant_classifier import normalize_contaminant

DB_PATH = 'data/reports.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 70)
print("STEP 1: Rebuilding topology_scores with canonical contaminant format")
print("=" * 70)

cursor.execute("DROP TABLE IF EXISTS topology_scores")
cursor.execute("""
    CREATE TABLE topology_scores (
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
    )
""")

cursor.execute("""
    SELECT
        pincode, area_name,
        COALESCE(NULLIF(colony_name, ''), 'Unspecified') as colony_name,
        source_type,
        AVG(quality_score) as avg_score,
        COUNT(*) as report_count,
        MAX(lat) as lat, MAX(lng) as lng,
        MAX(timestamp) as last_updated
    FROM water_reports
    GROUP BY pincode, area_name, colony_name, source_type
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} unique (pincode, area, colony, source_type) groupings.\n")

for row in rows:
    pincode, area_name, colony_name, source_type, avg_score, report_count, lat, lng, last_updated = (
        row["pincode"], row["area_name"], row["colony_name"], row["source_type"],
        row["avg_score"], row["report_count"], row["lat"], row["lng"], row["last_updated"],
    )
    avg_score = round(avg_score)

    if avg_score >= 80:
        colour_band = 'green'
    elif avg_score >= 60:
        colour_band = 'yellow'
    elif avg_score >= 40:
        colour_band = 'orange'
    else:
        colour_band = 'red'

    # Collect ALL contaminants across every report in this grouping,
    # then normalize the whole set through the ONE canonical classifier —
    # this is what merges 'H2S' and '["H2S"]' into a single consistent value.
    cursor.execute("""
        SELECT contaminants FROM water_reports
        WHERE pincode = ? AND area_name = ? AND source_type = ?
          AND COALESCE(NULLIF(colony_name, ''), 'Unspecified') = ?
    """, (pincode, area_name, source_type, colony_name))

    all_raw_contaminants = []
    for contam_row in cursor.fetchall():
        raw = contam_row[0]
        if not raw:
            continue
        import json
        try:
            parsed = json.loads(raw) if raw.strip().startswith("[") else raw
            if isinstance(parsed, list):
                all_raw_contaminants.extend(parsed)
            else:
                all_raw_contaminants.append(parsed)
        except (json.JSONDecodeError, ValueError):
            all_raw_contaminants.append(raw)

    primary_contaminant = normalize_contaminant(all_raw_contaminants)

    cursor.execute("""
        INSERT INTO topology_scores
        (pincode, area_name, colony_name, source_type, avg_score, report_count,
         primary_contaminant, colour_band, lat, lng, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pincode, area_name, colony_name, source_type or 'unknown', avg_score, report_count,
          primary_contaminant, colour_band, lat or 0.0, lng or 0.0, last_updated))

conn.commit()

print(f"Rebuilt {len(rows)} topology_scores rows with canonical contaminant format.\n")

print("=" * 70)
print("STEP 2: Verification — final canonical contaminant values now in use")
print("=" * 70)
cursor.execute("SELECT DISTINCT primary_contaminant, COUNT(*) FROM topology_scores GROUP BY primary_contaminant ORDER BY 2 DESC")
for val, cnt in cursor.fetchall():
    print(f"  {val!r:30s} -> {cnt} rows")

print("\n" + "=" * 70)
print("STEP 3: Lingampally / MIG Colony Phase 1 check — should now be ONE row")
print("per (colony, source_type), not fragmented across format variants")
print("=" * 70)
cursor.execute("""
    SELECT area_name, colony_name, source_type, primary_contaminant, report_count, avg_score
    FROM topology_scores
    WHERE area_name LIKE '%Lingampal%'
    ORDER BY colony_name, source_type
""")
for row in cursor.fetchall():
    print(f"  colony={row[1]!r:25s} source={row[2]!r:20s} contaminant={row[3]!r:20s} "
          f"reports={row[4]} score={row[5]}")

conn.close()
print("\nDone. Restart uvicorn and refresh the Map tab.")
print("Re-run audit_all_filters.py to confirm 'Fecal Coliform' now matches real data.")
