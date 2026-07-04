"""
Module: scripts/seed_mock_data.py
Purpose: Seeds 20 mock water quality reports across real Hyderabad
         pincodes to populate the topology map for demo purposes.
Component: Demo Data Seeding
Inputs: None (hardcoded mock data with real Hyderabad coordinates)
Outputs: 20 records in SQLite reports.db + topology_scores table
Key Design Decisions:
  - Pincode 500032 has 4 records with H2S/Iron: guarantees the
    Antigravity cluster detection moment fires in the demo.
  - Uses real Hyderabad area names and coordinates: map looks authentic.
  - is_mock=1 flag: distinguishes seeded data from real citizen reports
    in any analytics. Can be filtered out in production.
  - Direct SQLite insert: faster than going through MCP server for seeding.
Competition Concepts Demonstrated:
  - Deployability (live demo with realistic data)
  - Antigravity moment setup (cluster detection trigger)
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("WATER_INTEL_DB_PATH", "./data/reports.db")

# ── Mock Data — 20 Real Hyderabad Locations ────────────────────────────────────
# CRITICAL: 500032 has 4 records → triggers cluster detection in demo

MOCK_REPORTS = [
    # ── Pincode 500032 — 4 records to trigger Antigravity cluster ──
    {
        "area_name": "Nallagandla",
        "pincode": "500032",
        "lat": 17.4532,
        "lng": 78.3241,
        "source_type": "borewell",
        "quality_score": 28,
        "colour_band": "red",
        "contaminants": ["H2S", "Iron"],
        "symptoms": ["egg_smell", "yellow_colour"],
        "days_ago": 5,
    },
    {
        "area_name": "BHEL MIG Colony",
        "pincode": "500032",
        "lat": 17.4620,
        "lng": 78.3150,
        "source_type": "borewell",
        "quality_score": 32,
        "colour_band": "red",
        "contaminants": ["H2S"],
        "symptoms": ["egg_smell"],
        "days_ago": 3,
    },
    {
        "area_name": "BHEL LIG Colony",
        "pincode": "500032",
        "lat": 17.4580,
        "lng": 78.3200,
        "source_type": "borewell",
        "quality_score": 35,
        "colour_band": "red",
        "contaminants": ["Iron"],
        "symptoms": ["yellow_colour", "metallic_taste"],
        "days_ago": 4,
    },
    {
        "area_name": "BHEL HIG Colony",
        "pincode": "500032",
        "lat": 17.4650,
        "lng": 78.3100,
        "source_type": "borewell",
        "quality_score": 41,
        "colour_band": "orange",
        "contaminants": ["H2S", "Iron"],
        "symptoms": ["egg_smell", "yellow_colour"],
        "days_ago": 6,
    },
    # ── Other Hyderabad areas ──────────────────────────────────────
    {
        "area_name": "Ramachandrapuram",
        "pincode": "500055",
        "lat": 17.4400,
        "lng": 78.3600,
        "source_type": "municipal_pipeline",
        "quality_score": 48,
        "colour_band": "orange",
        "contaminants": ["High_TDS"],
        "symptoms": ["white_deposits", "bitter_taste"],
        "days_ago": 8,
    },
    {
        "area_name": "Kondapur",
        "pincode": "500084",
        "lat": 17.4900,
        "lng": 78.3900,
        "source_type": "borewell",
        "quality_score": 71,
        "colour_band": "yellow",
        "contaminants": [],
        "symptoms": ["no_visible_symptom"],
        "days_ago": 10,
    },
    {
        "area_name": "Madhapur",
        "pincode": "500081",
        "lat": 17.4479,
        "lng": 78.3882,
        "source_type": "municipal_pipeline",
        "quality_score": 65,
        "colour_band": "yellow",
        "contaminants": [],
        "symptoms": ["chlorine_smell"],
        "days_ago": 12,
    },
    {
        "area_name": "Gachibowli",
        "pincode": "500032",
        "lat": 17.4401,
        "lng": 78.3489,
        "source_type": "borewell",
        "quality_score": 38,
        "colour_band": "red",
        "contaminants": ["Fluoride_trace", "Iron"],
        "symptoms": ["yellow_colour"],
        "days_ago": 7,
    },
    {
        "area_name": "Miyapur",
        "pincode": "500049",
        "lat": 17.4960,
        "lng": 78.3549,
        "source_type": "municipal_pipeline",
        "quality_score": 55,
        "colour_band": "yellow",
        "contaminants": ["Iron"],
        "symptoms": ["yellow_colour"],
        "days_ago": 9,
    },
    {
        "area_name": "Kukatpally",
        "pincode": "500072",
        "lat": 17.4849,
        "lng": 78.3994,
        "source_type": "municipal_pipeline",
        "quality_score": 52,
        "colour_band": "yellow",
        "contaminants": ["High_TDS"],
        "symptoms": ["white_deposits"],
        "days_ago": 11,
    },
    {
        "area_name": "Manikonda",
        "pincode": "500089",
        "lat": 17.4048,
        "lng": 78.3763,
        "source_type": "borewell",
        "quality_score": 61,
        "colour_band": "yellow",
        "contaminants": [],
        "symptoms": ["no_visible_symptom"],
        "days_ago": 14,
    },
    {
        "area_name": "Puppalaguda",
        "pincode": "500089",
        "lat": 17.4120,
        "lng": 78.3700,
        "source_type": "borewell",
        "quality_score": 44,
        "colour_band": "orange",
        "contaminants": ["Iron"],
        "symptoms": ["yellow_colour", "metallic_taste"],
        "days_ago": 13,
    },
    {
        "area_name": "Narsingi",
        "pincode": "500075",
        "lat": 17.3965,
        "lng": 78.3650,
        "source_type": "borewell",
        "quality_score": 39,
        "colour_band": "red",
        "contaminants": ["H2S"],
        "symptoms": ["egg_smell"],
        "days_ago": 2,
    },
    {
        "area_name": "Tellapur",
        "pincode": "500019",
        "lat": 17.4701,
        "lng": 78.2801,
        "source_type": "borewell",
        "quality_score": 33,
        "colour_band": "red",
        "contaminants": ["Iron", "H2S"],
        "symptoms": ["egg_smell", "yellow_colour"],
        "days_ago": 4,
    },
    {
        "area_name": "Osman Nagar",
        "pincode": "500019",
        "lat": 17.4780,
        "lng": 78.2900,
        "source_type": "borewell",
        "quality_score": 29,
        "colour_band": "red",
        "contaminants": ["H2S"],
        "symptoms": ["egg_smell"],
        "days_ago": 6,
    },
    {
        "area_name": "Chanda Nagar",
        "pincode": "500050",
        "lat": 17.4942,
        "lng": 78.3228,
        "source_type": "municipal_pipeline",
        "quality_score": 58,
        "colour_band": "yellow",
        "contaminants": [],
        "symptoms": ["no_visible_symptom"],
        "days_ago": 15,
    },
    {
        "area_name": "Patancheru",
        "pincode": "500086",
        "lat": 17.5280,
        "lng": 78.2648,
        "source_type": "borewell",
        "quality_score": 22,
        "colour_band": "red",
        "contaminants": ["Iron", "Nitrate"],
        "symptoms": ["yellow_colour", "stomach_issues"],
        "days_ago": 3,
    },
    {
        "area_name": "Sangareddy",
        "pincode": "502001",
        "lat": 17.6200,
        "lng": 78.0900,
        "source_type": "borewell",
        "quality_score": 19,
        "colour_band": "red",
        "contaminants": ["Fluoride", "Iron"],
        "symptoms": ["yellow_colour"],
        "days_ago": 7,
    },
    {
        "area_name": "LB Nagar",
        "pincode": "500074",
        "lat": 17.3547,
        "lng": 78.5524,
        "source_type": "municipal_pipeline",
        "quality_score": 67,
        "colour_band": "yellow",
        "contaminants": [],
        "symptoms": ["chlorine_smell"],
        "days_ago": 20,
    },
    {
        "area_name": "Uppal",
        "pincode": "500039",
        "lat": 17.4065,
        "lng": 78.5593,
        "source_type": "municipal_pipeline",
        "quality_score": 59,
        "colour_band": "yellow",
        "contaminants": ["High_TDS"],
        "symptoms": ["white_deposits"],
        "days_ago": 18,
    },
]


# ── Database Setup ─────────────────────────────────────────────────────────────

def create_tables(conn: sqlite3.Connection):
    """Create SQLite tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS water_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pincode TEXT NOT NULL,
            area_name TEXT,
            source_type TEXT NOT NULL,
            quality_score INTEGER NOT NULL,
            colour_band TEXT NOT NULL,
            contaminants TEXT,
            symptoms TEXT,
            lat REAL,
            lng REAL,
            is_mock INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS topology_scores (
            pincode TEXT PRIMARY KEY,
            area_name TEXT,
            avg_score REAL,
            report_count INTEGER,
            primary_contaminant TEXT,
            colour_band TEXT,
            lat REAL,
            lng REAL,
            last_updated TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_pincode ON water_reports(pincode);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON water_reports(timestamp);
        CREATE INDEX IF NOT EXISTS idx_contaminants ON water_reports(contaminants);
    """)
    conn.commit()


# ── Seeding Logic ──────────────────────────────────────────────────────────────

def seed_mock_data():
    """Insert mock reports and build topology scores from them."""
    print("\n" + "="*60)
    print("WaterSentinel Mock Data Seeder")
    print("="*60)

    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    # Clear existing mock data (allows re-running script cleanly)
    conn.execute("DELETE FROM water_reports WHERE is_mock = 1")
    conn.execute("DELETE FROM topology_scores")
    conn.commit()
    print(f"\nCleared existing mock data from {DB_PATH}")

    # Insert reports
    now = datetime.now()
    inserted = 0
    pincode_data = {}  # Track for topology aggregation

    print(f"\nInserting {len(MOCK_REPORTS)} mock reports...")

    for report in MOCK_REPORTS:
        timestamp = (now - timedelta(days=report["days_ago"])).isoformat()

        conn.execute("""
            INSERT INTO water_reports
            (pincode, area_name, source_type, quality_score, colour_band,
             contaminants, symptoms, lat, lng, is_mock, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            report["pincode"],
            report["area_name"],
            report["source_type"],
            report["quality_score"],
            report["colour_band"],
            json.dumps(report["contaminants"]),
            json.dumps(report["symptoms"]),
            report["lat"],
            report["lng"],
            timestamp,
        ))
        inserted += 1

        # Accumulate data for topology scoring
        pc = report["pincode"]
        if pc not in pincode_data:
            pincode_data[pc] = {
                "area_name": report["area_name"],
                "scores": [],
                "contaminants": [],
                "lat": report["lat"],
                "lng": report["lng"],
            }
        pincode_data[pc]["scores"].append(report["quality_score"])
        pincode_data[pc]["contaminants"].extend(report["contaminants"])

        print(f"  ✅ {report['area_name']} ({report['pincode']}): "
              f"score={report['quality_score']}, "
              f"contaminants={report['contaminants']}")

    conn.commit()

    # Build topology scores from aggregated data
    print(f"\nBuilding topology scores for {len(pincode_data)} pincodes...")
    for pincode, data in pincode_data.items():
        avg_score = sum(data["scores"]) / len(data["scores"])

        # Determine colour band from average score
        if avg_score >= 80:
            colour_band = "green"
        elif avg_score >= 60:
            colour_band = "yellow"
        elif avg_score >= 40:
            colour_band = "orange"
        else:
            colour_band = "red"

        # Find most common contaminant
        if data["contaminants"]:
            primary = max(set(data["contaminants"]),
                         key=data["contaminants"].count)
        else:
            primary = "None detected"

        conn.execute("""
            INSERT OR REPLACE INTO topology_scores
            (pincode, area_name, avg_score, report_count, primary_contaminant,
             colour_band, lat, lng, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pincode,
            data["area_name"],
            round(avg_score, 1),
            len(data["scores"]),
            primary,
            colour_band,
            data["lat"],
            data["lng"],
            now.isoformat(),
        ))

    conn.commit()
    conn.close()

    print(f"\n✅ Seeding complete!")
    print(f"   Reports inserted: {inserted}")
    print(f"   Topology pincodes: {len(pincode_data)}")
    print(f"   Database: {DB_PATH}")
    print(f"\n🎯 Demo ready: Pincode 500032 has 4 reports with H2S/Iron")
    print(f"   → Antigravity cluster moment will fire automatically")


if __name__ == "__main__":
    seed_mock_data()
