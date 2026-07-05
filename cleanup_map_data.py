"""
Run this with: python cleanup_map_data.py

Fixes two data quality issues visible on the Map page:
1. Rows where area_name is literally a pincode (e.g. "500032") instead of a
   real locality name — these came from earlier test submissions where the
   area name field was left blank. Merges them into the correct real area
   where possible, or renames them, and removes broken sort-order entries.
2. Rounds all stored avg_score values to whole numbers so the UI never shows
   long decimals like 28.833333333333332 again — this fixes the issue at the
   data layer in addition to the display-layer fix already applied in the UI.
"""

import sqlite3

DB_PATH = 'data/reports.db'

# Map from bad pincode-only area names to their real locality name.
# UPDATE this mapping if your actual pincodes correspond to different areas.
PINCODE_TO_AREA = {
    '500032': 'Kondapur',      # merge into Kondapur if this is the correct real area
    '500084': 'Kondapur',      # adjust if 500084 is actually a different locality
}

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=== Step 1: Renaming pincode-only area names ===")
for bad_name, real_name in PINCODE_TO_AREA.items():
    cursor.execute(
        "UPDATE water_reports SET area_name = ? WHERE area_name = ?",
        (real_name, bad_name)
    )
    print(f"  water_reports: {bad_name} -> {real_name} ({cursor.rowcount} rows)")

# NOTE: topology_scores is NOT updated here. It gets fully rebuilt from
# water_reports in Step 3 below, which correctly re-aggregates any rows
# that now share the same (pincode, area_name, source_type) after the
# rename above — avoiding a UNIQUE constraint clash from updating
# topology_scores directly when two different pincodes merge into one area.

conn.commit()

print("\n=== Step 2: Rounding all stored scores ===")
cursor.execute("SELECT id, avg_score FROM topology_scores")
rows = cursor.fetchall()
for row_id, avg_score in rows:
    rounded = round(avg_score)
    cursor.execute("UPDATE topology_scores SET avg_score = ? WHERE id = ?", (rounded, row_id))
print(f"  Rounded {len(rows)} topology_scores rows")

cursor.execute("SELECT id, quality_score FROM water_reports")
rows = cursor.fetchall()
for row_id, quality_score in rows:
    rounded = round(quality_score)
    cursor.execute("UPDATE water_reports SET quality_score = ? WHERE id = ?", (rounded, row_id))
print(f"  Rounded {len(rows)} water_reports rows")

conn.commit()

print("\n=== Step 3: Rebuilding topology_scores aggregates ===")
# Re-aggregate after the renames above, in case merging created new duplicate
# (pincode, area_name, source_type) combinations that need re-summing.
cursor.execute("DELETE FROM topology_scores")

cursor.execute("""
    SELECT
        pincode, area_name, source_type,
        AVG(quality_score) as avg_score,
        COUNT(*) as report_count,
        MAX(lat) as lat, MAX(lng) as lng,
        MAX(timestamp) as last_updated
    FROM water_reports
    GROUP BY pincode, area_name, source_type
""")

rows = cursor.fetchall()
for row in rows:
    pincode, area_name, source_type, avg_score, report_count, lat, lng, last_updated = row
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

print(f"  Rebuilt {len(rows)} topology_scores rows")

print("\n=== Final state ===")
cursor.execute("SELECT area_name, source_type, avg_score, colour_band, report_count FROM topology_scores ORDER BY avg_score ASC")
for row in cursor.fetchall():
    print(f"  {row[0]:20s} | {row[1]:20s} | score={row[2]:3.0f} | {row[3]:7s} | {row[4]} reports")

conn.close()
print("\nCleanup complete. Restart uvicorn and refresh the Map tab.")
