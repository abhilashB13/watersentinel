"""
Run this with: python fix_city_state_by_pincode_prefix.py

ROOT CAUSE CONFIRMED: the source pincode CSV's district column is EMPTY
for these rows entirely — not differently formatted, genuinely blank.
This means DISTRICT_TO_CITY matching could never work, for any city,
regardless of wording. Pincode PREFIX is a more reliable signal here,
since it's an official structural property of the pincode itself, not
dependent on an unreliable text column.

Fixes city AND state together, using well-known official pincode prefix
ranges for the three priority test cities. Extend PINCODE_PREFIX_RULES
for additional cities as needed later — same pattern.
"""

import sqlite3

DB_PATH = 'data/reports.db'

# (pincode_prefix, city, correct_state) — prefix matched via pincode.startswith()
# State is set explicitly here too, since we now know the source's state
# column also carries the pre-2014 "Andhra Pradesh" label for Hyderabad's
# pincodes, and needs correcting to "Telangana" regardless of district data.
PINCODE_PREFIX_RULES = [
    ("500", "Hyderabad", "Telangana"),     # Hyderabad core + most of GHMC area
    ("501", "Hyderabad", "Telangana"),     # Rangareddy/outer Hyderabad extension
    ("502", "Hyderabad", "Telangana"),     # Medchal-Malkajgiri extension (Sangareddy area)
    ("208", "Kanpur", "Uttar Pradesh"),    # Kanpur Nagar
    ("520", "Vijayawada", "Andhra Pradesh"),  # Vijayawada (NTR district)
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 70)
print("BEFORE FIX")
print("=" * 70)
cursor.execute("SELECT COUNT(*) FROM pincode_master WHERE city = '' OR city IS NULL")
print(f"Rows with blank city: {cursor.fetchone()[0]} out of total")
cursor.execute("SELECT COUNT(*) FROM pincode_master")
print(f"Total rows: {cursor.fetchone()[0]}")

total_updated = 0
for prefix, city, state in PINCODE_PREFIX_RULES:
    cursor.execute("""
        UPDATE pincode_master
        SET city = ?, state = ?
        WHERE pincode LIKE ?
    """, (city, state, f"{prefix}%"))
    print(f"\nPrefix '{prefix}%' -> city='{city}', state='{state}': {cursor.rowcount} rows updated")
    total_updated += cursor.rowcount

conn.commit()

print(f"\nTotal rows updated: {total_updated}")

print("\n" + "=" * 70)
print("AFTER FIX — verification")
print("=" * 70)
cursor.execute("SELECT DISTINCT city, state, COUNT(*) FROM pincode_master WHERE city != '' GROUP BY city, state ORDER BY city")
for row in cursor.fetchall():
    print(f"  city={row[0]:15s} state={row[1]:20s} count={row[2]}")

print("\n" + "=" * 70)
print("Sample Hyderabad rows now (should show real area names + correct city/state):")
print("=" * 70)
cursor.execute("SELECT pincode, area_name, city, state FROM pincode_master WHERE city = 'Hyderabad' LIMIT 15")
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]:30s} | city={row[2]:12s} | state={row[3]}")

conn.close()
print("\nDone. Restart uvicorn fully (Ctrl+C then restart, not just --reload)")
print("and refresh the Map tab — Hyderabad and Telangana should now appear correctly.")
