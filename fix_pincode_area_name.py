"""
Run this with: python fix_pincode_area_name.py

Renames area_name "Nallagandla" -> "Lingampally" everywhere it appears,
in both water_reports and topology_scores, regardless of pincode.
"""

import sqlite3

DB_PATH = 'data/reports.db'
OLD_NAME = 'Nallagandla'
NEW_NAME = 'Lingampally'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=== DRY RUN — showing what will change ===\n")

cursor.execute(
    "SELECT id, pincode, colony_name, source_type, quality_score FROM water_reports WHERE area_name = ?",
    (OLD_NAME,)
)
water_rows = cursor.fetchall()
print(f"water_reports rows with area_name='{OLD_NAME}': {len(water_rows)}")
for row in water_rows:
    print(f"  id={row[0]} pincode={row[1]} colony={row[2]!r} source={row[3]} score={row[4]}")

cursor.execute(
    "SELECT id, pincode, colony_name, source_type, avg_score FROM topology_scores WHERE area_name = ?",
    (OLD_NAME,)
)
topo_rows = cursor.fetchall()
print(f"\ntopology_scores rows with area_name='{OLD_NAME}': {len(topo_rows)}")
for row in topo_rows:
    print(f"  id={row[0]} pincode={row[1]} colony={row[2]!r} source={row[3]} score={row[4]}")

if not water_rows and not topo_rows:
    print(f"\nNo rows found with area_name='{OLD_NAME}'. Nothing to rename.")
    conn.close()
    exit()

confirm = input(f"\nProceed renaming '{OLD_NAME}' -> '{NEW_NAME}' everywhere? (yes/no): ")
if confirm.strip().lower() != 'yes':
    print("Aborted. No changes made.")
    conn.close()
    exit()

cursor.execute(
    "UPDATE water_reports SET area_name = ? WHERE area_name = ?",
    (NEW_NAME, OLD_NAME)
)
print(f"\nUpdated {cursor.rowcount} water_reports rows.")

cursor.execute(
    "UPDATE topology_scores SET area_name = ? WHERE area_name = ?",
    (NEW_NAME, OLD_NAME)
)
print(f"Updated {cursor.rowcount} topology_scores rows.")

conn.commit()

print("\n=== Verification ===")
cursor.execute(
    "SELECT DISTINCT area_name, colony_name, pincode FROM water_reports WHERE area_name = ?",
    (NEW_NAME,)
)
for row in cursor.fetchall():
    print(f"  area={row[0]!r} colony={row[1]!r} pincode={row[2]}")

conn.close()
print("\nDone. Restart uvicorn and refresh the Map tab.")
