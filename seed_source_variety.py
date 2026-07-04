"""
Run this with: python seed_source_variety.py
Adds EXTRA seed reports so the same area has BOTH municipal pipe
(good score) AND borewell (bad score) — demonstrating the exact
scenario described: Kondapur municipal water is fine, but borewells
in the same area have high TDS / H2S issues.

This does NOT touch existing reports — it only ADDS new ones.
Run migrate_source_type.py AFTER this to rebuild the aggregates.
"""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'data/reports.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Scenario data: (pincode, area_name, source_type, score, colour_band, contaminant, symptoms, lat, lng)
EXTRA_SEED_DATA = [
    # Kondapur — Municipal pipe is GOOD (treated water)
    ('500084', 'Kondapur', 'municipal_pipeline', 88, 'green', 'None', '[]', 17.4590, 78.3670),
    ('500084', 'Kondapur', 'municipal_pipeline', 85, 'green', 'None', '[]', 17.4595, 78.3675),

    # Kondapur — Borewell is BAD (high TDS, geology-driven)
    ('500084', 'Kondapur', 'borewell', 32, 'red', 'High_TDS', '["white_deposits"]', 17.4592, 78.3672),
    ('500084', 'Kondapur', 'borewell', 28, 'red', 'High_TDS', '["white_deposits", "salty_taste"]', 17.4588, 78.3668),
    ('500084', 'Kondapur', 'borewell', 35, 'red', 'Iron', '["yellow_colour"]', 17.4593, 78.3671),

    # Gachibowli — Municipal pipe GOOD
    ('500032', 'Gachibowli', 'municipal_pipeline', 82, 'green', 'None', '[]', 17.4400, 78.3489),

    # Gachibowli — Borewell has H2S (deep aquifer smell issue)
    ('500032', 'Gachibowli', 'borewell', 45, 'orange', 'H2S', '["egg_smell"]', 17.4402, 78.3491),
    ('500032', 'Gachibowli', 'borewell', 42, 'orange', 'H2S', '["egg_smell"]', 17.4398, 78.3487),

    # Madhapur — Municipal pipe MODERATE
    ('500081', 'Madhapur', 'municipal_pipeline', 68, 'yellow', 'None', '[]', 17.4483, 78.3915),

    # Madhapur — Hand pump BAD (shared community source, contaminated)
    ('500081', 'Madhapur', 'hand_pump', 25, 'red', 'Sewage_Contamination', '["sewage_smell", "black_colour"]', 17.4485, 78.3917),

    # Kukatpally — Municipal pipe GOOD
    ('500072', 'Kukatpally', 'municipal_pipeline', 79, 'yellow', 'None', '[]', 17.4849, 78.3994),

    # Kukatpally — Open well VERY BAD (surface contamination exposure)
    ('500072', 'Kukatpally', 'open_well', 18, 'red', 'Fecal_Coliform', '["black_colour", "stomach_issues"]', 17.4851, 78.3996),
]

now = datetime.now()
inserted = 0

for pincode, area, source, score, band, contaminant, symptoms, lat, lng in EXTRA_SEED_DATA:
    timestamp = (now - timedelta(days=random.randint(0, 5))).isoformat()
    cursor.execute("""
        INSERT INTO water_reports
        (pincode, area_name, source_type, quality_score, colour_band, contaminants, symptoms, lat, lng, is_mock, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (pincode, area, source, score, band, contaminant, symptoms, lat, lng, timestamp))
    inserted += 1

conn.commit()
print(f"Inserted {inserted} new seed reports showing source-type variety.")
print("\nScenario summary:")
print("  Kondapur: Municipal=Good(85-88) vs Borewell=Bad(28-35)")
print("  Gachibowli: Municipal=Good(82) vs Borewell=H2S issue(42-45)")
print("  Madhapur: Municipal=Moderate(68) vs Hand Pump=Bad(25)")
print("  Kukatpally: Municipal=Moderate(79) vs Open Well=Critical(18)")
print("\nNow run: python migrate_source_type.py to rebuild topology aggregates.")

conn.close()
