"""
Run this with: python migrate_source_type.py
FIXED VERSION: The old topology_scores table has UNIQUE constraint on
pincode alone, which blocks multiple source_types per pincode.
This script drops and recreates the table with the correct constraint:
UNIQUE(pincode, area_name, source_type) instead of UNIQUE(pincode).

Safe to run multiple times.
"""

import sqlite3

DB_PATH = 'data/reports.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Dropping old topology_scores table (had wrong UNIQUE constraint)...")
cursor.execute("DROP TABLE IF EXISTS topology_scores")

print("Creating new topology_scores table with correct schema...")
cursor.execute("""
    CREATE TABLE topology_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pincode TEXT NOT NULL,
        area_name TEXT NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'unknown',
        avg_score REAL,
        report_count INTEGER,
        primary_contaminant TEXT,
        colour_band TEXT,
        lat REAL,
        lng REAL,
        last_updated TEXT,
        UNIQUE(pincode, area_name, source_type)
    )
""")
conn.commit()
print("Table recreated.")

print("\nRebuilding topology_scores from water_reports, grouped by source_type...")

cursor.execute("""
    SELECT
        pincode,
        area_name,
        source_type,
        AVG(quality_score) as avg_score,
        COUNT(*) as report_count,
        MAX(lat) as lat,
        MAX(lng) as lng,
        MAX(timestamp) as last_updated
    FROM water_reports
    GROUP BY pincode, area_name, source_type
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} unique (pincode, area, source_type) combinations.")

for row in rows:
    pincode, area_name, source_type, avg_score, report_count, lat, lng, last_updated = row

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
        ORDER BY quality_score ASC LIMIT 1
    """, (pincode, area_name, source_type))
    contaminant_row = cursor.fetchone()
    primary_contaminant = contaminant_row[0] if contaminant_row and contaminant_row[0] else 'None'

    cursor.execute("""
        INSERT INTO topology_scores
        (pincode, area_name, source_type, avg_score, report_count, primary_contaminant, colour_band, lat, lng, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pincode, area_name, source_type or 'unknown', avg_score, report_count,
          primary_contaminant, colour_band, lat or 0.0, lng or 0.0, last_updated))

conn.commit()

print("\nRebuilt topology_scores. Sample rows:")
cursor.execute("SELECT area_name, source_type, avg_score, colour_band FROM topology_scores ORDER BY area_name, source_type LIMIT 30")
for row in cursor.fetchall():
    print(f"  {row[0]:20s} | {row[1]:20s} | score={row[2]:.0f} | {row[3]}")

conn.close()
print("\nMigration complete. Restart uvicorn and refresh the Map tab.")
