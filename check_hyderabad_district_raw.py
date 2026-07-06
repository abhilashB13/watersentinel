"""
Run this with: python check_hyderabad_district_raw.py

Prints the EXACT raw district/state text stored for pincodes we KNOW are
in Hyderabad (500032, 500084, 500001) — so we can see precisely why
DISTRICT_TO_CITY's lookup failed to match anything, instead of guessing
again. Likely causes: extra whitespace, different capitalization our
.strip().upper() didn't fully normalize, or the actual district name in
the source CSV being something we didn't anticipate (e.g. "Hyderabad
Urban" instead of just "Hyderabad").
"""

import sqlite3

DB_PATH = 'data/reports.db'
KNOWN_HYDERABAD_PINCODES = ['500032', '500084', '500001', '500072', '500081']

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Raw district/state/city values for KNOWN Hyderabad pincodes:\n")
for pin in KNOWN_HYDERABAD_PINCODES:
    cursor.execute("SELECT pincode, area_name, district, city, state FROM pincode_master WHERE pincode = ?", (pin,))
    rows = cursor.fetchall()
    if not rows:
        print(f"  {pin}: NOT FOUND in pincode_master at all")
        continue
    for row in rows:
        print(f"  {row[0]} | area={row[1]!r:25s} | district={row[2]!r:25s} | city={row[3]!r:15s} | state={row[4]!r}")

print("\n" + "=" * 70)
print("Checking for ANY district containing 'HYDERABAD' (case-insensitive)")
print("=" * 70)
cursor.execute("SELECT DISTINCT district, state, COUNT(*) FROM pincode_master WHERE district LIKE '%HYDERABAD%' OR district LIKE '%hyderabad%' GROUP BY district, state")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  district={row[0]!r} state={row[1]!r} count={row[2]}")
else:
    print("  NONE FOUND — no district value contains 'Hyderabad' at all in this table.")
    print("  This suggests the source CSV's district column may be empty/blank")
    print("  for these rows, or uses a completely different naming scheme.")

print("\n" + "=" * 70)
print("Checking for ANY row where state = 'Andhra Pradesh' or 'Telangana'")
print("and area_name suggests Hyderabad (sample of 10)")
print("=" * 70)
cursor.execute("""
    SELECT pincode, area_name, district, state FROM pincode_master
    WHERE (area_name LIKE '%hyderabad%' OR pincode LIKE '500%')
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  {row[0]} | area={row[1]!r:25s} | district={row[2]!r:20s} | state={row[3]!r}")

conn.close()
