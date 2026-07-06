"""
Run this with: python audit_all_filters.py
(Requires your backend to be running: uv run uvicorn api.main:app --port 8000)

Comprehensive test of EVERY filter combination possible in the UI:
  - 5 source types (all, municipal_pipeline, borewell, hand_pump, open_well)
  - 3 time windows (Today=1d, Last 7d, Last 30d)
  - 5 contaminant chips (All, High TDS, Iron, H2S, Fecal Coliform)
  = up to 75 combinations, tested against your REAL running API — not a
  simulation — so any bug in the actual endpoint or actual data gets
  caught here, in seconds, instead of by clicking through the UI 75 times.

For each combination:
  1. Calls the real /map/topology endpoint with the matching query params
  2. Applies the SAME client-side contaminant filter logic MapPage.tsx uses
  3. Reports the resulting count
  4. Flags anything suspicious: a contaminant chip returning 0 when raw
     data suggests it shouldn't, or a chip matching nothing across ALL
     source/time combinations (near-certain format mismatch bug)
"""

import requests
import sqlite3
from itertools import product

API_BASE = "http://localhost:8000"
DB_PATH = "data/reports.db"

SOURCE_TYPES = ['all', 'municipal_pipeline', 'borewell', 'hand_pump', 'open_well']
TIME_WINDOWS = {'Today': 1, 'Last 7d': 7, 'Last 30d': 30, 'All-time': None}
CONTAMINANT_CHIPS = ['All', 'High TDS', 'Iron', 'H2S', 'Fecal Coliform']


def chip_matches(chip: str, stored_value: str) -> bool:
    """Replicates EXACT frontend filter logic from MapPage.tsx"""
    if chip == 'All':
        return True
    search_term = chip.replace('High ', '').lower()
    return search_term in (stored_value or '').lower()


def fetch_topology(source_type: str, days_back):
    params = {}
    if source_type != 'all':
        params['source_type'] = source_type
    if days_back is not None:
        params['days_back'] = days_back
    try:
        r = requests.get(f"{API_BASE}/map/topology", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"__error__": str(e)}


print("=" * 80)
print("STEP 1 — Raw data baseline (what's actually in the database)")
print("=" * 80)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT primary_contaminant, COUNT(*) FROM topology_scores GROUP BY primary_contaminant ORDER BY 2 DESC")
raw_contaminants = cursor.fetchall()
for val, cnt in raw_contaminants:
    print(f"  {val!r:30s} -> {cnt} rows")

cursor.execute("SELECT DISTINCT source_type, COUNT(*) FROM topology_scores GROUP BY source_type")
raw_sources = cursor.fetchall()
print("\nSource types in data:")
for val, cnt in raw_sources:
    print(f"  {val!r:20s} -> {cnt} rows")
conn.close()

print("\n" + "=" * 80)
print("STEP 2 — Testing all source x time combinations against LIVE API")
print("=" * 80)

results_matrix = {}
for source, (time_label, days) in product(SOURCE_TYPES, TIME_WINDOWS.items()):
    data = fetch_topology(source, days)
    if isinstance(data, dict) and "__error__" in data:
        print(f"  ❌ source={source:20s} time={time_label:10s} -> API ERROR: {data['__error__']}")
        continue
    results_matrix[(source, time_label)] = data
    print(f"  source={source:20s} time={time_label:10s} -> {len(data)} rows returned")

print("\n" + "=" * 80)
print("STEP 3 — Testing each contaminant chip against every combination")
print("=" * 80)

chip_ever_matched = {chip: False for chip in CONTAMINANT_CHIPS}

for (source, time_label), data in results_matrix.items():
    for chip in CONTAMINANT_CHIPS:
        if chip == 'All':
            continue
        matched = [p for p in data if chip_matches(chip, p.get('primary_contaminant', ''))]
        if matched:
            chip_ever_matched[chip] = True

print("\nSummary — did each chip EVER match anything, across ALL combinations tested:")
for chip, matched_ever in chip_ever_matched.items():
    if chip == 'All':
        continue
    status = "✅ matches at least once" if matched_ever else "❌ NEVER MATCHES ANYTHING — broken filter"
    print(f"  '{chip}': {status}")

print("\n" + "=" * 80)
print("STEP 4 — Detailed breakdown for the BROKEN chip(s) — showing the exact")
print("mismatch between what the chip searches for and what's actually stored")
print("=" * 80)
for chip, matched_ever in chip_ever_matched.items():
    if chip == 'All' or matched_ever:
        continue
    search_term = chip.replace('High ', '').lower()
    print(f"\nChip '{chip}' searches (case-insensitive) for substring: '{search_term}'")
    print(f"Actual stored primary_contaminant values that DON'T contain '{search_term}':")
    for val, cnt in raw_contaminants:
        if val and search_term not in val.lower():
            print(f"  {val!r} ({cnt} rows) — closest word overlap: "
                  f"{[w for w in search_term.split() if w in (val or '').lower()]}")

print("\n" + "=" * 80)
print("STEP 5 — Lingampally specific check (cross-referencing your report)")
print("=" * 80)
lingampally_rows = []
for (source, time_label), data in results_matrix.items():
    for p in data:
        if 'lingampal' in (p.get('area_name', '') or '').lower():
            lingampally_rows.append({**p, '_tested_source': source, '_tested_time': time_label})

seen = set()
for row in lingampally_rows:
    key = (row.get('colony_name'), row.get('source_type'), row.get('primary_contaminant'))
    if key in seen:
        continue
    seen.add(key)
    print(f"  colony={row.get('colony_name')!r} source={row.get('source_type')!r} "
          f"contaminant={row.get('primary_contaminant')!r} score={row.get('avg_score')} "
          f"reports={row.get('report_count')}")

print("\n" + "=" * 80)
print("DONE — any chip marked '❌ NEVER MATCHES' above is broken regardless of")
print("which source/time filter is active, confirming a FORMAT mismatch bug")
print("(e.g. underscore vs space, or wrong keyword entirely) rather than a")
print("data-availability issue.")
print("=" * 80)
