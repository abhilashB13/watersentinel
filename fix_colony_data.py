"""
Run this with: python fix_colony_data_final.py

Fixes ALL issues identified by diagnose_colony_data.py:

1. Merges legacy 'BHEL MIG/LIG/HIG Colony' rows (old area-name-style data)
   into area_name='Nallagandla' with correct colony_name — these were the
   same real place as the new Nallagandla colony rows, just entered before
   colony_name existed as a field.

2. Fixes Gachibowli and Kondapur, which each have TWO different pincodes
   both showing as empty-colony 'General area report' rows — these get
   assigned real colony names instead of being fake pincode-based splits.

3. Adds at least 2 real named colonies to EVERY other area that currently
   has zero colony breakdown (Chanda Nagar, Kukatpally, LB Nagar, Madhapur,
   Manikonda, Miyapur, Narsingi, Osman Nagar, Patancheru, Puppalaguda,
   Ramachandrapuram, Sangareddy, Tellapur, Uppal) — by splitting their
   existing single report across 2 newly-named colonies plus adding one
   extra seed report so each area has genuine multi-colony data, not just
   one report awkwardly split.

4. Normalizes ALL empty colony_name values to the single canonical string
   'Unspecified' (not '', not NULL) so GROUP BY never creates accidental
   duplicate 'General area report' rows again.

Safe to run once. Rebuilds topology_scores from scratch at the end.
"""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'data/reports.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

now = datetime.now()

print("=" * 70)
print("STEP 1: Merge legacy BHEL area-name rows into Nallagandla")
print("=" * 70)

BHEL_MERGE_MAP = {
    'BHEL MIG Colony': 'MIG Colony Phase 1',
    'BHEL LIG Colony': 'LIG Colony',
    'BHEL HIG Colony': 'HIG Colony',
}

for old_area, target_colony in BHEL_MERGE_MAP.items():
    cursor.execute("""
        UPDATE water_reports
        SET area_name = 'Nallagandla', colony_name = ?
        WHERE area_name = ?
    """, (target_colony, old_area))
    print(f"  {old_area} -> Nallagandla / {target_colony} ({cursor.rowcount} rows)")

conn.commit()

print("\n" + "=" * 70)
print("STEP 2: Normalize ALL empty/null colony_name to 'Unspecified'")
print("=" * 70)
cursor.execute("""
    UPDATE water_reports
    SET colony_name = 'Unspecified'
    WHERE colony_name IS NULL OR colony_name = ''
""")
print(f"  Normalized {cursor.rowcount} rows to colony_name='Unspecified'")
conn.commit()

print("\n" + "=" * 70)
print("STEP 3: Fix Gachibowli's two pincodes -> real colony names")
print("=" * 70)
# 500032 keeps as main Gachibowli colony, 500099 becomes a distinct named colony
cursor.execute("""
    UPDATE water_reports
    SET colony_name = 'Software Units Layout'
    WHERE area_name = 'Gachibowli' AND pincode = '500032' AND colony_name = 'Unspecified'
""")
print(f"  Gachibowli/500032 -> Software Units Layout ({cursor.rowcount} rows)")

cursor.execute("""
    UPDATE water_reports
    SET colony_name = 'DLF Cyber City Colony'
    WHERE area_name = 'Gachibowli' AND pincode = '500099' AND colony_name = 'Unspecified'
""")
print(f"  Gachibowli/500099 -> DLF Cyber City Colony ({cursor.rowcount} rows)")

print("\n" + "=" * 70)
print("STEP 4: Fix Kondapur's two pincodes -> real colony names")
print("=" * 70)
cursor.execute("""
    UPDATE water_reports
    SET colony_name = 'Botanical Garden Colony'
    WHERE area_name = 'Kondapur' AND pincode = '500084' AND colony_name = 'Unspecified'
""")
print(f"  Kondapur/500084 -> Botanical Garden Colony ({cursor.rowcount} rows)")

cursor.execute("""
    UPDATE water_reports
    SET colony_name = 'Laxmi Cyber City Colony'
    WHERE area_name = 'Kondapur' AND pincode = '500032' AND colony_name = 'Unspecified'
""")
print(f"  Kondapur/500032 -> Laxmi Cyber City Colony ({cursor.rowcount} rows)")
# Raghavendra Colony already exists correctly for Kondapur/500084 — left untouched

conn.commit()

print("\n" + "=" * 70)
print("STEP 5: Add a 2nd real colony to every area that currently has ZERO")
print("=" * 70)

# For each area below, we RENAME the existing single 'Unspecified' report to
# a real colony name, then INSERT one new seed report as the 2nd colony —
# giving every area genuine 2-colony breakdown instead of a lone flat row.
SINGLE_COLONY_AREAS = [
    # (area_name, pincode, existing_report_new_colony, new_colony_2, new_colony_2_score, new_colony_2_band, new_colony_2_contaminant, new_colony_2_symptoms, lat, lng, source_type)
    ('Chanda Nagar',      '500050', 'Chanda Nagar Main Colony',   'RTC Colony',           55, 'yellow', 'None',      '[]',                17.5010, 78.3020, 'municipal_pipeline'),
    ('Kukatpally',        '500072', 'JNTU Colony',                'Vivekananda Nagar Colony', 40, 'orange', 'Iron', '["yellow_colour"]', 17.4870, 78.4010, 'borewell'),
    ('LB Nagar',          '500074', 'Vanasthalipuram Colony',     'Kothapet Colony',      45, 'orange', 'Iron',      '["yellow_colour"]', 17.3570, 78.5550, 'borewell'),
    ('Madhapur',          '500081', 'Ayyappa Society Colony',     'HITEC City Colony',    48, 'orange', 'High_TDS',  '["salty_taste"]',    17.4472, 78.3802, 'borewell'),
    ('Manikonda',         '500089', 'Manikonda Main Colony',      'TSPA Colony',          38, 'red',    'Iron',      '["yellow_colour"]', 17.4020, 78.3780, 'borewell'),
    ('Miyapur',           '500049', 'Miyapur Main Colony',        'Prashanth Nagar Colony', 50, 'orange', 'High_TDS', '["salty_taste"]',  17.4960, 78.3600, 'borewell'),
    ('Narsingi',          '500075', 'Narsingi Main Colony',       'TSR Nagar Colony',     36, 'red',    'H2S',       '["egg_smell"]',      17.3900, 78.3500, 'borewell'),
    ('Osman Nagar',       '500019', 'Osman Nagar Main Colony',    'Bandlaguda Colony',    52, 'orange', 'High_TDS',  '["salty_taste"]',    17.4680, 78.2780, 'borewell'),
    ('Patancheru',        '500086', 'IDA Colony',                 'Ramachandrapuram Colony', 30, 'red', 'High_TDS', '["salty_taste"]',   17.5300, 78.2670, 'borewell'),
    ('Puppalaguda',       '500089', 'Puppalaguda Main Colony',    'NAD Colony',           41, 'orange', 'Iron',      '["yellow_colour"]', 17.4100, 78.3650, 'borewell'),
    ('Ramachandrapuram',  '500055', 'Ramachandrapuram Main Colony', 'IDPL Colony',        58, 'yellow', 'None',      '[]',                17.4900, 78.2900, 'municipal_pipeline'),
    ('Sangareddy',        '502001', 'Fatima Nagar Colony',        'Kalyan Nagar Colony',  35, 'red',    'Iron',      '["yellow_colour"]', 17.6220, 78.0920, 'borewell'),
    ('Tellapur',          '500019', 'Aparna Colony',              'Osman Nagar Colony',   50, 'orange', 'High_TDS',  '["salty_taste"]',    17.4680, 78.2780, 'borewell'),
    ('Uppal',             '500039', 'Uppal Main Colony',          'Nagole Colony',        47, 'orange', 'Iron',      '["yellow_colour"]', 17.4020, 78.5580, 'borewell'),
]

for area, pincode, colony1_name, colony2_name, score2, band2, contaminant2, symptoms2, lat, lng, source in SINGLE_COLONY_AREAS:
    # Rename the existing lone report to a real colony name
    cursor.execute("""
        UPDATE water_reports
        SET colony_name = ?
        WHERE area_name = ? AND pincode = ? AND colony_name = 'Unspecified'
    """, (colony1_name, area, pincode))
    print(f"  {area}: existing report -> {colony1_name} ({cursor.rowcount} rows)")

    # Insert a new seed report as the 2nd colony
    timestamp = (now - timedelta(days=random.randint(0, 5))).isoformat()
    cursor.execute("""
        INSERT INTO water_reports
        (pincode, area_name, colony_name, source_type, quality_score, colour_band,
         contaminants, symptoms, lat, lng, is_mock, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (pincode, area, colony2_name, source, score2, band2, contaminant2, symptoms2, lat, lng, timestamp))
    print(f"  {area}: inserted new colony -> {colony2_name} (score {score2})")

conn.commit()

print("\n" + "=" * 70)
print("STEP 6: Rebuild topology_scores from scratch")
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
        pincode, area_name, colony_name, source_type,
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
        WHERE pincode = ? AND area_name = ? AND source_type = ? AND colony_name = ?
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

print("\n" + "=" * 70)
print("FINAL STATE — every area and its colonies")
print("=" * 70)
cursor.execute("""
    SELECT area_name, colony_name, source_type, avg_score, report_count
    FROM topology_scores ORDER BY area_name, colony_name
""")
for row in cursor.fetchall():
    print(f"  {row[0]:20s} | {row[1]:26s} | {row[2]:18s} | score={row[3]:3.0f} | {row[4]} reports")

conn.close()
print("\nDone. Restart uvicorn and refresh the Map tab.")
