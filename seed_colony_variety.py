"""
Run this with: python seed_colony_variety.py
(Run AFTER migrate_colony_name.py has been applied)

Adds seed reports demonstrating the exact scenario described: same pincode,
same area (Nallagandla), but DIFFERENT colonies (MIG/LIG/HIG) showing
different water quality — this is the real-world granularity the colony
field is meant to capture.

Run migrate_colony_name.py again afterward is NOT needed — this script
inserts directly into water_reports and then rebuilds topology_scores itself.
"""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'data/reports.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# (pincode, area_name, colony_name, source_type, score, band, contaminant, symptoms, lat, lng)
COLONY_SEED_DATA = [
    # Nallagandla — MIG Colony Phase 1: borewell H2S issue (your example scenario)
    ('500032', 'Nallagandla', 'MIG Colony Phase 1', 'borewell', 42, 'orange', 'H2S', '["egg_smell"]', 17.4620, 78.3150),
    ('500032', 'Nallagandla', 'MIG Colony Phase 1', 'borewell', 38, 'orange', 'H2S', '["egg_smell"]', 17.4621, 78.3151),
    ('500032', 'Nallagandla', 'MIG Colony Phase 1', 'borewell', 45, 'orange', 'H2S', '["egg_smell"]', 17.4622, 78.3149),

    # Nallagandla — LIG Colony: different issue entirely, iron not H2S
    ('500032', 'Nallagandla', 'LIG Colony', 'borewell', 25, 'red', 'Iron', '["yellow_colour"]', 17.4635, 78.3165),
    ('500032', 'Nallagandla', 'LIG Colony', 'borewell', 28, 'red', 'Iron', '["yellow_colour"]', 17.4636, 78.3166),

    # Nallagandla — HIG Colony: municipal pipe here is fine
    ('500032', 'Nallagandla', 'HIG Colony', 'municipal_pipeline', 84, 'green', 'None', '[]', 17.4610, 78.3140),

    # Nallagandla — HIG Colony borewell also fine (newer, shallower)
    ('500032', 'Nallagandla', 'HIG Colony', 'borewell', 70, 'yellow', 'None', '[]', 17.4611, 78.3141),
]

now = datetime.now()
inserted = 0

for pincode, area, colony, source, score, band, contaminant, symptoms, lat, lng in COLONY_SEED_DATA:
    timestamp = (now - timedelta(days=random.randint(0, 4))).isoformat()
    cursor.execute("""
        INSERT INTO water_reports
        (pincode, area_name, colony_name, source_type, quality_score, colour_band,
         contaminants, symptoms, lat, lng, is_mock, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (pincode, area, colony, source, score, band, contaminant, symptoms, lat, lng, timestamp))
    inserted += 1

conn.commit()
print(f"Inserted {inserted} colony-level seed reports.")
print("\nScenario summary — same area (Nallagandla), different colonies:")
print("  MIG Colony Phase 1 (borewell): H2S issue, 3 reports, cluster-triggering")
print("  LIG Colony (borewell):         Iron issue, 2 reports")
print("  HIG Colony (municipal + borewell): both fine")

# ── Rebuild topology_scores to include this new data ────────────────────────────
print("\nRebuilding topology_scores...")
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
for row in rows:
    pincode, area_name, colony_name, source_type, avg_score, report_count, lat, lng, last_updated = row
    avg_score = round(avg_score)
    if avg_score >= 80:
        colour_band = 'green'
    elif avg_score >= 60:
        colour_band = 'yellow'
    elif avg_score >= 40:
        colour_band = 'orange'
    else:
        colour_band = 'red'

    cursor.execute("""
        SELECT contaminants FROM water_reports
        WHERE pincode = ? AND area_name = ? AND source_type = ?
          AND COALESCE(NULLIF(colony_name, ''), 'Unspecified') = ?
        ORDER BY quality_score ASC LIMIT 1
    """, (pincode, area_name, source_type, colony_name))
    contaminant_row = cursor.fetchone()
    primary_contaminant = contaminant_row[0] if contaminant_row and contaminant_row[0] else 'None'

    cursor.execute("""
        INSERT INTO topology_scores
        (pincode, area_name, colony_name, source_type, avg_score, report_count,
         primary_contaminant, colour_band, lat, lng, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pincode, area_name, colony_name, source_type or 'unknown', avg_score, report_count,
          primary_contaminant, colour_band, lat or 0.0, lng or 0.0, last_updated))

conn.commit()
print(f"Rebuilt {len(rows)} topology_scores rows.")

conn.close()
print("\nDone. Restart uvicorn and refresh the Map tab.")
