"""
Run this with: python check_db_path.py

Prints the ABSOLUTE resolved path of the database file this script sees,
plus a live count of bracketed vs clean contaminant values in it RIGHT NOW.
Run this immediately after fix_contaminant_format.py, with NO uvicorn
restart in between, to isolate whether the issue is a path mismatch
(different processes reading different physical files) or something else
actively re-writing old data between your fix and your audit.
"""

import sqlite3
import os

DB_PATH = 'data/reports.db'

print(f"Relative DB_PATH used: {DB_PATH!r}")
print(f"Absolute resolved path: {os.path.abspath(DB_PATH)}")
print(f"File exists at that path: {os.path.exists(DB_PATH)}")
print(f"File last modified: {os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else 'N/A'}")
print(f"Current working directory: {os.getcwd()}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM topology_scores WHERE primary_contaminant LIKE '%[%'")
bracketed_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM topology_scores")
total_count = cursor.fetchone()[0]

print(f"\nTotal topology_scores rows: {total_count}")
print(f"Rows with bracketed (old-format) contaminant values: {bracketed_count}")

if bracketed_count > 0:
    print("\nSample bracketed rows:")
    cursor.execute("SELECT id, area_name, colony_name, source_type, primary_contaminant FROM topology_scores WHERE primary_contaminant LIKE '%[%' LIMIT 5")
    for row in cursor.fetchall():
        print(f"  id={row[0]} area={row[1]!r} colony={row[2]!r} source={row[3]!r} contaminant={row[4]!r}")

conn.close()
