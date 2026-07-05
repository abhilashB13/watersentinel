"""
Run this with: python diagnose_colony_data.py
Dumps the EXACT current state of water_reports so we can see precisely
what needs fixing before writing a blind cleanup script.
"""

import sqlite3

conn = sqlite3.connect('data/reports.db')
cursor = conn.cursor()

print("=" * 70)
print("ALL DISTINCT (area_name, colony_name) COMBINATIONS")
print("=" * 70)
cursor.execute("""
    SELECT area_name,
           colony_name,
           typeof(colony_name) as colony_type,
           COUNT(*) as report_count,
           pincode
    FROM water_reports
    GROUP BY area_name, colony_name, pincode
    ORDER BY area_name, colony_name
""")
for row in cursor.fetchall():
    area, colony, ctype, count, pincode = row
    colony_display = repr(colony)  # shows '' vs None vs 'Unspecified' clearly
    print(f"  area={area!r:30s} colony={colony_display:20s} type={ctype:8s} pincode={pincode} count={count}")

print("\n" + "=" * 70)
print("DISTINCT PINCODES PER AREA (checking for area/pincode mismatches)")
print("=" * 70)
cursor.execute("""
    SELECT area_name, GROUP_CONCAT(DISTINCT pincode) as pincodes
    FROM water_reports
    GROUP BY area_name
    ORDER BY area_name
""")
for row in cursor.fetchall():
    print(f"  {row[0]!r:30s} -> pincodes: {row[1]}")

print("\n" + "=" * 70)
print("ROWS THAT LOOK LIKE OLD-STYLE 'COLONY AS AREA NAME' DATA")
print("(area names containing 'Colony' or 'BHEL' — these are suspects)")
print("=" * 70)
cursor.execute("""
    SELECT DISTINCT area_name, pincode, colony_name
    FROM water_reports
    WHERE area_name LIKE '%Colony%' OR area_name LIKE '%BHEL%'
    ORDER BY area_name
""")
for row in cursor.fetchall():
    print(f"  area={row[0]!r:30s} pincode={row[1]} colony={row[2]!r}")

conn.close()
