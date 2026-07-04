"""
Module: scripts/test_mcp_servers.py
Purpose: Standalone test for both MCP servers WITHOUT needing ADK agents.
         Run this immediately after Batch 2 to verify MCP servers work
         before spending time building agents.
Component: Testing — MCP Server Verification
Usage:
    python scripts/test_mcp_servers.py

Expected output: All 11 tests PASSED
If any test fails: Read the error, fix with Chrome AI, re-run.
Do NOT proceed to Batch 3 (agents) until all tests pass here.
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# ── Test Runner ────────────────────────────────────────────────────────────────

passed = 0
failed = 0


def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        print(f"  ✅ PASS: {name}")
        passed += 1
    else:
        print(f"  ❌ FAIL: {name}")
        if detail:
            print(f"         Detail: {detail}")
        failed += 1


# ── Test WaterIntel Store ──────────────────────────────────────────────────────

def test_water_intel_store():
    print("\n" + "="*60)
    print("Testing MCP Server 1 — WaterIntel Store")
    print("="*60)

    try:
        from mcp_servers.water_intel_store import (
            submit_report,
            get_pincode_profile,
            get_cluster_status,
            get_area_history,
            update_topology_score,
            get_all_topology_data,
            get_db_connection,
        )
        print("  ✅ Import successful")
    except ImportError as e:
        print(f"  ❌ IMPORT FAILED: {e}")
        print("  Fix: uv add fastmcp")
        return

    # Test 1: Database connection
    try:
        conn = get_db_connection()
        conn.close()
        test("Database connection and table creation", True)
    except Exception as e:
        test("Database connection and table creation", False, str(e))
        return

    # Test 2: submit_report
    result = submit_report(
        pincode="500032",
        area_name="Test Nallagandla",
        source_type="borewell",
        quality_score=35,
        colour_band="red",
        contaminants=["H2S", "Iron"],
        symptoms=["egg_smell", "yellow_colour"],
        lat=17.4532,
        lng=78.3241,
    )
    test(
        "submit_report — returns success and report_id",
        result.get("success") is True and "report_id" in result,
        str(result),
    )

    # Test 3: get_pincode_profile
    profile = get_pincode_profile("500032")
    test(
        "get_pincode_profile — returns data for submitted pincode",
        profile.get("found") is True and profile.get("report_count", 0) >= 1,
        str(profile),
    )

    # Test 4: get_cluster_status — add 2 more reports to reach threshold
    for i in range(2):
        submit_report(
            pincode="500099",
            area_name="Test Cluster Area",
            source_type="borewell",
            quality_score=30,
            colour_band="red",
            contaminants=["H2S"],
            symptoms=["egg_smell"],
            lat=17.4532,
            lng=78.3241,
        )
    submit_report(
        pincode="500099",
        area_name="Test Cluster Area",
        source_type="borewell",
        quality_score=28,
        colour_band="red",
        contaminants=["H2S"],
        symptoms=["egg_smell"],
        lat=17.4532,
        lng=78.3241,
    )

    cluster = get_cluster_status("500099", days=7)
    test(
        "get_cluster_status — detects cluster when >= 3 reports",
        cluster.get("cluster_detected") is True and cluster.get("count", 0) >= 3,
        str(cluster),
    )

    # Test 5: get_area_history
    history = get_area_history("500032", days=30)
    test(
        "get_area_history — returns list",
        isinstance(history, list),
        str(history[:1]),
    )

    # Test 6: update_topology_score
    update_result = update_topology_score(
        pincode="500032",
        new_score=30,
        colour_band="red",
        area_name="Nallagandla",
        lat=17.4532,
        lng=78.3241,
    )
    test(
        "update_topology_score — returns success",
        update_result.get("success") is True,
        str(update_result),
    )

    # Test 7: get_all_topology_data
    topology = get_all_topology_data()
    test(
        "get_all_topology_data — returns list with entries",
        isinstance(topology, list) and len(topology) >= 1,
        f"Returned {len(topology)} entries",
    )


# ── Test ActionBridge ──────────────────────────────────────────────────────────

def test_action_bridge():
    print("\n" + "="*60)
    print("Testing MCP Server 2 — ActionBridge")
    print("="*60)

    try:
        from mcp_servers.action_bridge import (
            generate_municipal_complaint,
            get_authority_contact,
            generate_rti_draft,
            log_escalation,
        )
        print("  ✅ Import successful")
    except ImportError as e:
        print(f"  ❌ IMPORT FAILED: {e}")
        print("  Fix: uv add fastmcp")
        return

    # Test 8: get_authority_contact
    contact = get_authority_contact("500032", "municipal_pipeline")
    test(
        "get_authority_contact — returns HMWSSB for 500032",
        "HMWSSB" in contact.get("authority", {}).get("name", ""),
        str(contact.get("authority", {}).get("name")),
    )

    # Test 9: generate_municipal_complaint
    complaint = generate_municipal_complaint(
        area="Nallagandla",
        pincode="500032",
        contaminants=["H2S", "Iron"],
        affected_count=4,
        source_type="municipal_pipeline",
        bis_references=["BIS IS 10500:2012"],
        symptoms=["egg_smell", "yellow_colour"],
    )
    test(
        "generate_municipal_complaint — returns complaint_text",
        "complaint_text" in complaint and len(complaint.get("complaint_text", "")) > 100,
        f"Complaint length: {len(complaint.get('complaint_text', ''))} chars",
    )
    complaint_ref = complaint.get("complaint_ref", "WS-TEST-001")

    # Test 10: log_escalation
    log_result = log_escalation(
        pincode="500032",
        area_name="Nallagandla",
        severity="high",
        contaminants=["H2S", "Iron"],
        affected_count=4,
        complaint_ref=complaint_ref,
        source_type="municipal_pipeline",
    )
    test(
        "log_escalation — returns success and escalation_id",
        log_result.get("success") is True and "escalation_id" in log_result,
        str(log_result),
    )

    # Test 11: generate_rti_draft
    rti = generate_rti_draft(
        complaint_ref=complaint_ref,
        complaint_date="2026-06-27",
        area="Nallagandla",
        pincode="500032",
        authority_name="HMWSSB Hyderabad",
        days_elapsed=31,
    )
    test(
        "generate_rti_draft — returns RTI text",
        "rti_text" in rti and len(rti.get("rti_text", "")) > 100,
        f"RTI text length: {len(rti.get('rti_text', ''))} chars",
    )


# ── Run All Tests ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("WaterSentinel — MCP Server Test Suite")
    print("Run this BEFORE building agents (Batch 3)")
    print("="*60)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n⚠️  WARNING: GOOGLE_API_KEY not set.")
        print("   ActionBridge will use fallback template for complaints.\n")
    else:
        print(f"\n✅ GOOGLE_API_KEY found ({api_key[:8]}...)\n")

    test_water_intel_store()
    test_action_bridge()

    total = passed + failed
    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if failed == 0:
        print("\n✅ ALL TESTS PASSED — Ready for Batch 3 (ADK Agents)")
        print("   Next: run seed_mock_data.py then say Start Batch 3")
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
        print("   Fix failures before proceeding to Batch 3.")
        print("   Paste the error into Chrome AI to debug.")
        sys.exit(1)
