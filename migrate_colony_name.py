"""
Run this with: python migrate_colony_name.py

Adds colony_name column to water_reports and topology_scores.
Rebuilds topology_scores grouped by (pincode, area_name, source_type, colony_name)
so colony-level scores can be shown distinctly from area-level scores.

Existing reports without a colony_name get 'Unspecified' as a placeholder —
they still aggregate correctly at the area level, just without colony detail.
"""

import sqlite3

DB_PATH = 'data/reports.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Step 1: Add colony_name to water_reports if missing ────────────────────────
cursor.execute("PRAGMA table_info(water_reports)")
existing_cols = [row[1] for row in cursor.fetchall()]

if 'colony_name' not in existing_cols:
    print("Adding colony_name to water_reports...")
    cursor.execute("ALTER TABLE water_reports ADD COLUMN colony_name TEXT DEFAULT ''")
    conn.commit()
else:
    print("colony_name already exists on water_reports.")

# ── Step 2: Recreate topology_scores with colony_name in the unique constraint ──
print("\nRecreating topology_scores with colony_name support...")
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
conn.commit()

# ── Step 3: Rebuild aggregates from water_reports ───────────────────────────────
print("Rebuilding topology_scores grouped by colony...")

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
print(f"Found {len(rows)} unique (pincode, area, colony, source_type) combinations.")

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

print(f"\nRebuilt {len(rows)} topology_scores rows.")
print("\nSample (area / colony breakdown):")
cursor.execute("""
    SELECT area_name, colony_name, source_type, avg_score, report_count
    FROM topology_scores ORDER BY area_name, avg_score ASC LIMIT 30
""")
for row in cursor.fetchall():
    print(f"  {row[0]:18s} | {row[1]:20s} | {row[2]:18s} | score={row[3]:3.0f} | {row[4]} reports")

conn.close()
print("\nMigration complete. Restart uvicorn and refresh the Map tab.")
