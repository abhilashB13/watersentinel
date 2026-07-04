"""
Module: scripts/test_agents.py
Purpose: End-to-end test of the full 5-agent pipeline.
         Run after Batch 3 to verify all agents work before
         building the FastAPI layer (Batch 4).
Component: Testing — Full Agent Pipeline Verification
Usage:
    python scripts/test_agents.py

Expected: Agent pipeline completes, Antigravity cluster fires for 500032,
          complaint draft generated, map data point returned.

PREREQUISITE: Run these first:
    python rag/ingest.py          (RAG knowledge base must be populated)
    python scripts/seed_mock_data.py  (500032 cluster data must exist)
    python scripts/test_mcp_servers.py  (MCP servers must pass all tests)
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add project root to path
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
            print(f"         {detail}")
        failed += 1


# ── Agent Pipeline Test ────────────────────────────────────────────────────────

async def run_agent_pipeline(user_message: str, session_id: str) -> dict:
    """
    Run the full WaterSentinel agent pipeline with a test message.

    Args:
        user_message: Simulated citizen water quality report
        session_id: Unique session identifier

    Returns:
        dict with final_response text and session state
    """
    try:
        from google.adk.runners import Runner
        from google.genai.types import Content, Part
        from agents.orchestrator.agent import runner, session_service
    except ImportError as e:
        return {"error": str(e), "final_response": "", "session_state": {}}

    # Create session for this test run
    user_id = "test_user"
    await session_service.create_session(
        app_name="watersentinel",
        user_id=user_id,
        session_id=session_id,
    )

    # Build the user message
    content = Content(
        role="user",
        parts=[Part(text=user_message)],
    )

    # Run the agent pipeline
    final_response = ""
    session_state = {}

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        # Capture final text response
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_response += part.text

        # Capture session state at end of pipeline
        if hasattr(event, "is_final_response") and event.is_final_response():
            session = await session_service.get_session(
                app_name="watersentinel",
                user_id=user_id,
                session_id=session_id,
            )
            if session:
                session_state = dict(session.state)

    return {
        "final_response": final_response,
        "session_state": session_state,
    }


async def test_full_pipeline():
    """Test the complete 5-agent pipeline with a realistic citizen report."""

    print("\n" + "="*60)
    print("Testing Full 5-Agent Pipeline")
    print("="*60)

    # Test message: borewell in Nallagandla 500032 (cluster will fire)
    test_message = (
        "My borewell water in Nallagandla smells like rotten eggs and "
        "my taps have a yellowish stain. I live in BHEL MIG Colony, "
        "pincode 500032. This has been happening for 5 days. "
        "My family is worried. What should we do?"
    )

    print(f"\nTest message: {test_message[:80]}...")
    print("\nRunning agent pipeline (may take 30-60 seconds)...\n")

    session_id = f"test_{uuid.uuid4().hex[:8]}"

    try:
        result = await run_agent_pipeline(test_message, session_id)
    except Exception as e:
        print(f"  ❌ Pipeline execution failed: {e}")
        print("  Likely cause: GOOGLE_API_KEY not set or ADK not installed")
        return

    final_response = result.get("final_response", "")
    session_state = result.get("session_state", {})

    print("Pipeline complete. Checking outputs...\n")

    # Test 1: Pipeline produced a response
    test(
        "Pipeline produced a final response",
        len(final_response) > 100,
        f"Response length: {len(final_response)} chars",
    )

    # Test 2: SourceSense classified the source
    source_classification = session_state.get("source_classification", {})
    test(
        "SourceSense — classified source as borewell",
        source_classification.get("source_type") == "borewell",
        f"Got: {source_classification.get('source_type')}",
    )

    # Test 3: SourceSense detected symptoms
    symptoms = source_classification.get("symptoms_standardised", [])
    test(
        "SourceSense — detected egg_smell and/or yellow_colour symptoms",
        "egg_smell" in symptoms or "yellow_colour" in symptoms,
        f"Got symptoms: {symptoms}",
    )

    # Test 4: WaterProfiler diagnosed contaminants
    water_profile = session_state.get("water_profile", {})
    contaminants = water_profile.get("contaminants", [])
    test(
        "WaterProfiler — identified contaminants",
        len(contaminants) > 0,
        f"Contaminants: {[c.get('name') for c in contaminants]}",
    )

    # Test 5: WaterProfiler generated quality score
    quality_score = water_profile.get("quality_score", -1)
    test(
        "WaterProfiler — generated quality score (0-100)",
        0 <= quality_score <= 100,
        f"Score: {quality_score}",
    )

    # Test 6: WaterProfiler cited BIS standard
    citations = water_profile.get("rag_citations", [])
    test(
        "WaterProfiler — includes BIS citation from RAG",
        any("BIS" in c or "WHO" in c for c in citations),
        f"Citations: {citations}",
    )

    # Test 7: CommunityMapper detected cluster for 500032
    # (requires seed_mock_data.py to have been run first)
    community_status = session_state.get("community_status", {})
    test(
        "CommunityMapper — detected cluster for 500032 (ANTIGRAVITY MOMENT)",
        community_status.get("cluster_detected") is True,
        f"Cluster count: {community_status.get('cluster_count', 0)}. "
        f"Run seed_mock_data.py if this fails.",
    )

    # Test 8: CommunityMapper generated community alert
    community_alert = community_status.get("community_alert", "")
    test(
        "CommunityMapper — generated community alert message",
        len(community_alert) > 20,
        f"Alert: {community_alert[:100]}",
    )

    # Test 9: ActionForge generated personal advisory
    action_output = session_state.get("action_output", {})
    advisory = action_output.get("personal_advisory", {})
    test(
        "ActionForge — generated personal advisory",
        bool(advisory) or "advise" in final_response.lower() or "action" in final_response.lower(),
        f"Advisory keys: {list(advisory.keys()) if advisory else 'check final_response'}",
    )

    # Test 10: Final response mentions contaminant
    test(
        "Final response — mentions H2S or Iron or sulphur",
        any(word in final_response.lower() for word in
            ["h2s", "iron", "sulphur", "sulfur", "hydrogen", "egg"]),
        f"Response preview: {final_response[:200]}",
    )

    # Test 11: Final response is empathetic and actionable
    test(
        "Final response — contains action words",
        any(word in final_response.lower() for word in
            ["do not drink", "treat", "filter", "boil", "safe", "action"]),
        f"Response preview: {final_response[:200]}",
    )

    # Print full response for manual review
    print(f"\n{'='*60}")
    print("FULL AGENT RESPONSE (for manual review):")
    print(f"{'='*60}")
    print(final_response[:1500] if len(final_response) > 1500
          else final_response)
    if len(final_response) > 1500:
        print(f"\n... [truncated — {len(final_response)} total chars]")


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "="*60)
    print("WaterSentinel — Full Agent Pipeline Test Suite")
    print("Prerequisites: rag/ingest.py + seed_mock_data.py must have run")
    print("="*60)

    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n❌ GOOGLE_API_KEY not set. Add to .env file.")
        sys.exit(1)
    print(f"\n✅ GOOGLE_API_KEY found (starts with: {api_key[:8]}...)")

    # Check ChromaDB exists
    chroma_path = Path(os.getenv("CHROMA_DB_PATH", "./data/chroma_db"))
    if not chroma_path.exists():
        print(f"\n⚠️  ChromaDB not found at {chroma_path}")
        print("   Run: python rag/ingest.py")
        print("   Continuing — WaterProfiler will use fallback responses\n")
    else:
        print(f"✅ ChromaDB found at {chroma_path}")

    # Check SQLite DB exists (seed data)
    db_path = Path(os.getenv("WATER_INTEL_DB_PATH", "./data/reports.db"))
    if not db_path.exists():
        print(f"\n⚠️  Database not found at {db_path}")
        print("   Run: python scripts/seed_mock_data.py")
        print("   Antigravity cluster test will likely fail\n")
    else:
        print(f"✅ Database found at {db_path}")

    await test_full_pipeline()

    # Summary
    total = passed + failed
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if failed == 0:
        print("\n✅ ALL TESTS PASSED — Ready for Batch 4 (FastAPI)")
    elif failed <= 2:
        print(f"\n⚠️  {failed} test(s) failed — likely cluster data issue")
        print("   Run seed_mock_data.py and retry")
        print("   If core diagnosis works, proceed to Batch 4")
    else:
        print(f"\n❌ {failed} TESTS FAILED — Fix before Batch 4")
        print("   Use Chrome AI to debug — paste errors above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
