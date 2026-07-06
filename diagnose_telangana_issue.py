"""
Run this with: python diagnose_telangana_issue.py
(Run with backend uvicorn ALSO running, in a separate terminal)

Isolates exactly WHERE the Telangana fix is failing:
  1. Is pincode_master actually updated at the raw database level?
  2. Does map_data.py on disk actually contain the /map/available-locations
     endpoint code (in case an older version is still in place)?
  3. Does the LIVE running API actually return Telangana when called directly?

This tells us whether the problem is the database, the code file, or
something in between (e.g. server not actually restarted, wrong file
replaced, frontend caching) — rather than guessing and re-applying the
same fix blindly.
"""

import sqlite3
import os
import requests

DB_PATH = 'data/reports.db'
API_BASE = 'http://localhost:8000'

print("=" * 75)
print("STEP 1 — Raw database check (bypassing the API entirely)")
print("=" * 75)

if not os.path.exists(DB_PATH):
    print(f"❌ Database file not found at {os.path.abspath(DB_PATH)}")
    print("   Are you running this from the correct project root folder?")
else:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pincode_master'")
    if not cursor.fetchone():
        print("❌ pincode_master table does NOT exist. Run seed_pincode_master.py first.")
    else:
        cursor.execute("SELECT COUNT(*) FROM pincode_master")
        total = cursor.fetchone()[0]
        print(f"pincode_master exists, {total} total rows.")

        cursor.execute("SELECT DISTINCT state FROM pincode_master WHERE city = 'Hyderabad'")
        hyd_states = [r[0] for r in cursor.fetchall()]
        print(f"\nStates currently associated with city='Hyderabad': {hyd_states}")

        if "Telangana" in hyd_states:
            print("✅ Database IS correctly updated — Hyderabad rows show state='Telangana'")
        else:
            print("❌ Database is NOT updated — Hyderabad rows still show old state value")
            print("   This means fix_telangana_state.py either wasn't run, or didn't match")
            print("   any rows. Checking district values actually stored...")
            cursor.execute("SELECT DISTINCT district, state FROM pincode_master WHERE city = 'Hyderabad'")
            for row in cursor.fetchall():
                print(f"     district={row[0]!r} state={row[1]!r}")

        cursor.execute("SELECT DISTINCT state FROM pincode_master ORDER BY state")
        all_states = [r[0] for r in cursor.fetchall()]
        print(f"\nALL distinct states in pincode_master right now: {all_states}")
        print(f"Telangana present anywhere in the table: {'Telangana' in all_states}")

    conn.close()

print("\n" + "=" * 75)
print("STEP 2 — Does map_data.py on disk have the /map/available-locations")
print("endpoint at all? (checks for an outdated file being served)")
print("=" * 75)

map_data_path = "api/routers/map_data.py"
if os.path.exists(map_data_path):
    with open(map_data_path, 'r', encoding='utf-8') as f:
        content = f.read()
    has_endpoint = "available-locations" in content or "available_locations" in content
    print(f"map_data.py exists at {os.path.abspath(map_data_path)}")
    print(f"Contains /map/available-locations endpoint code: {has_endpoint}")
    if not has_endpoint:
        print("❌ This file does NOT have the endpoint — an older version of")
        print("   map_data.py may still be in place. Re-apply the correct file.")
else:
    print(f"❌ Could not find {map_data_path} — check you're running this from project root")

print("\n" + "=" * 75)
print("STEP 3 — Calling the LIVE running API directly")
print("=" * 75)

try:
    r = requests.get(f"{API_BASE}/map/available-locations", timeout=5)
    print(f"HTTP status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Live API response: {data}")
        if "Telangana" in data.get("states", []):
            print("✅ LIVE API correctly returns Telangana")
        else:
            print("❌ LIVE API does NOT return Telangana — even though we may have")
            print("   confirmed the DB is correct above. This points to the running")
            print("   uvicorn process not having picked up the change (needs a FULL")
            print("   stop + restart, not just --reload triggering) OR a stale")
            print("   in-memory connection.")
    elif r.status_code == 404:
        print("❌ Got 404 — the /map/available-locations endpoint doesn't exist on")
        print("   the currently running server. The running process is serving an")
        print("   OLDER map_data.py than what's on disk now — needs a full restart.")
    else:
        print(f"Unexpected response: {r.text[:300]}")
except requests.exceptions.ConnectionError:
    print("❌ Could not connect to localhost:8000 — is uvicorn actually running?")
except Exception as e:
    print(f"❌ Request failed: {e}")

print("\n" + "=" * 75)
print("DIAGNOSIS COMPLETE — compare the three steps above:")
print("  Step 1 fails  -> re-run fix_telangana_state.py, check district names")
print("  Step 2 fails  -> the wrong/old map_data.py file is on disk, replace it")
print("  Step 3 fails but 1&2 pass -> STOP uvicorn fully (Ctrl+C) and restart,")
print("                                don't rely on --reload picking it up")
print("=" * 75)
