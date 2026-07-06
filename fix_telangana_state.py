"""
Run this with: python fix_telangana_state.py
(Run AFTER seed_pincode_master.py)

FIXES: Telangana missing from the State filter dropdown, even though
Hyderabad clearly has data. Root cause: the source pincode dataset
(kishorek/India-Codes) appears to predate Telangana's 2014 bifurcation
from Andhra Pradesh — Hyderabad's pincode rows are still labeled
state="Andhra Pradesh" in the raw source data. Our city-mapping already
correctly identifies which districts belong to Hyderabad (via
DISTRICT_TO_CITY), so this script relabels those SAME districts' state
field to "Telangana" as a post-processing correction.
"""

import sqlite3

DB_PATH = 'data/reports.db'

# Same district list used for Hyderabad city mapping in seed_pincode_master.py —
# these districts are genuinely in Telangana, regardless of what the
# legacy source data's state column says.
HYDERABAD_TELANGANA_DISTRICTS = [
    "HYDERABAD", "RANGAREDDY", "RANGA REDDY",
    "MEDCHAL MALKAJGIRI", "MEDCHAL-MALKAJGIRI",
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=== Before fix ===")
cursor.execute("SELECT DISTINCT state FROM pincode_master WHERE city = 'Hyderabad'")
print("States currently associated with Hyderabad city:", [r[0] for r in cursor.fetchall()])

total_updated = 0
for district in HYDERABAD_TELANGANA_DISTRICTS:
    cursor.execute("""
        UPDATE pincode_master SET state = 'Telangana'
        WHERE UPPER(district) = ? AND state != 'Telangana'
    """, (district,))
    total_updated += cursor.rowcount

conn.commit()

print(f"\nUpdated {total_updated} rows to state='Telangana'.")

print("\n=== After fix ===")
cursor.execute("SELECT DISTINCT state FROM pincode_master WHERE city = 'Hyderabad'")
print("States now associated with Hyderabad city:", [r[0] for r in cursor.fetchall()])

cursor.execute("SELECT DISTINCT state FROM pincode_master ORDER BY state")
print("\nAll distinct states now in pincode_master:")
for row in cursor.fetchall():
    print(f"  {row[0]}")

conn.close()
print("\nDone. Restart uvicorn and refresh the Map tab — Telangana should now appear in the State filter.")
