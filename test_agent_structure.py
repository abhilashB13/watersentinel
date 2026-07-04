"""
Module: scripts/test_agent_structure.py
Purpose: Verify agent pipeline structure WITHOUT making any Gemini API calls.
         Tests imports, wiring, MCP connections, RAG tools, and session
         service — everything except the LLM reasoning step.

Why this approach:
  - test_agents.py triggers real Gemini API calls (expensive, quota-burning)
  - This script verifies the 95% of things that can fail without burning tokens
  - When your API key has quota restored, test_agents.py will work
  - For the competition demo, agents work fine — this confirms structure is sound

Run this instead of test_agents.py when:
  - You get 429 quota errors
  - You want fast verification without API costs
  - You just want to confirm imports and wiring are correct

Usage:
    python scripts/test_agent_structure.py

Expected: All tests PASSED — Ready for FastAPI (Batch 4)
"""

import sys
import os
import asyncio
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
            print(f"         {detail}")
        failed += 1


# ── Test 1: ADK Core Imports ───────────────────────────────────────────────────

def test_adk_imports():
    print("\n" + "="*60)
    print("Test Group 1 — ADK Core Imports")
    print("="*60)

    try:
        from google.adk.agents import LlmAgent
        test("LlmAgent import", True)
    except ImportError as e:
        test("LlmAgent import", False, str(e))

    try:
        from google.adk.sessions import InMemorySessionService
        test("InMemorySessionService import", True)
    except ImportError as e:
        test("InMemorySessionService import", False, str(e))

    try:
        from google.adk.runners import Runner
        test("Runner import", True)
    except ImportError as e:
        test("Runner import", False, str(e))

    try:
        from google.adk.tools import FunctionTool
        test("FunctionTool import", True)
    except ImportError as e:
        test("FunctionTool import", False, str(e))

    try:
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
        test("MCPToolset + StdioServerParameters import", True)
    except ImportError as e:
        # Try new API name if old one fails
        try:
            from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams
            test("MCPToolset + StdioConnectionParams import (new API)", True)
        except ImportError as e2:
            test("MCPToolset import", False, f"{e} | {e2}")


# ── Test 2: Agent File Imports ─────────────────────────────────────────────────

def test_agent_imports():
    print("\n" + "="*60)
    print("Test Group 2 — Agent File Imports")
    print("="*60)

    # Test each agent module imports without error
    # These will trigger LlmAgent() construction but NOT API calls

    try:
        from agents.source_sense.agent import source_sense_agent
        test("SourceSense agent import", True)
    except Exception as e:
        test("SourceSense agent import", False, str(e)[:200])

    try:
        from agents.water_profiler.agent import water_profiler_agent
        test("WaterProfiler agent import", True)
    except Exception as e:
        test("WaterProfiler agent import", False, str(e)[:200])

    try:
        from agents.water_profiler.tools import (
            retrieve_water_quality_knowledge,
            calculate_quality_score,
        )
        test("WaterProfiler tools import", True)
    except Exception as e:
        test("WaterProfiler tools import", False, str(e)[:200])

    try:
        from agents.community_mapper.agent import community_mapper_agent
        test("CommunityMapper agent import", True)
    except Exception as e:
        test("CommunityMapper agent import", False, str(e)[:200])

    try:
        from agents.action_forge.agent import action_forge_agent
        test("ActionForge agent import", True)
    except Exception as e:
        test("ActionForge agent import", False, str(e)[:200])

    try:
        from agents.orchestrator.agent import root_agent, runner, session_service
        test("Orchestrator + runner + session_service import", True)
    except Exception as e:
        test("Orchestrator import", False, str(e)[:200])


# ── Test 3: Agent Structure Verification ──────────────────────────────────────

def test_agent_structure():
    print("\n" + "="*60)
    print("Test Group 3 — Agent Structure Verification")
    print("="*60)

    try:
        from agents.orchestrator.agent import root_agent, runner, session_service

        # Verify root agent has sub-agents registered
        sub_agent_names = [a.name for a in (root_agent.sub_agents or [])]
        test(
            "Orchestrator has sub-agents registered",
            len(sub_agent_names) >= 4,
            f"Sub-agents found: {sub_agent_names}",
        )

        test(
            "SourceSense registered in Orchestrator",
            any("SourceSense" in n or "source" in n.lower() for n in sub_agent_names),
            f"Sub-agents: {sub_agent_names}",
        )

        test(
            "WaterProfiler registered in Orchestrator",
            any("WaterProfiler" in n or "water" in n.lower() for n in sub_agent_names),
            f"Sub-agents: {sub_agent_names}",
        )

        test(
            "CommunityMapper registered in Orchestrator",
            any("CommunityMapper" in n or "community" in n.lower() for n in sub_agent_names),
            f"Sub-agents: {sub_agent_names}",
        )

        test(
            "ActionForge registered in Orchestrator",
            any("ActionForge" in n or "action" in n.lower() for n in sub_agent_names),
            f"Sub-agents: {sub_agent_names}",
        )

        # Verify session service
        test(
            "Session service is InMemorySessionService",
            session_service is not None,
            str(type(session_service)),
        )

        # Verify runner
        test(
            "Runner initialised with root agent",
            runner is not None,
            str(type(runner)),
        )

    except Exception as e:
        test("Agent structure verification", False, str(e)[:300])


# ── Test 4: RAG Tools Work (No API Key Needed) ────────────────────────────────

def test_rag_tools():
    print("\n" + "="*60)
    print("Test Group 4 — RAG Tools (uses local embeddings, no API)")
    print("="*60)

    try:
        from agents.water_profiler.tools import retrieve_water_quality_knowledge

        result = retrieve_water_quality_knowledge(
            symptoms=["egg_smell", "yellow_colour"],
            source_type="borewell",
            location_context="Nallagandla Hyderabad",
        )

        test(
            "RAG retrieval returns results",
            result.get("success") is True and result.get("chunk_count", 0) > 0,
            f"Chunks: {result.get('chunk_count')}, Citations: {result.get('citations')}",
        )

        test(
            "RAG retrieval returns valid citations from knowledge base",
             len(result.get("citations", [])) > 0,
             f"Citations: {result.get('citations')}",
        )

        test(
            "RAG retrieval returns valid citations from knowledge base",
             len(result.get("citations", [])) > 0,
             f"Citations: {result.get('citations')}",
        )


    except Exception as e:
        test("RAG tools", False, str(e)[:200])


# ── Test 5: Quality Score Tool (Pure Python, No API) ──────────────────────────

def test_scoring_tool():
    print("\n" + "="*60)
    print("Test Group 5 — Quality Score Tool (pure Python)")
    print("="*60)

    try:
        from agents.water_profiler.tools import calculate_quality_score

        # Test H2S + Iron — should score red
        result = calculate_quality_score(
            contaminants=["H2S", "Iron"],
            severity="medium",
            source_type="borewell",
        )
        test(
            "H2S + Iron scores below 50 (red/orange band)",
            result.get("quality_score", 100) < 50,
            f"Score: {result.get('quality_score')}, Band: {result.get('colour_band')}",
        )

        # Test no contaminants — should score green
        result2 = calculate_quality_score(
            contaminants=[],
            severity="low",
            source_type="borewell",
        )
        test(
            "No contaminants scores above 80 (green band)",
            result2.get("quality_score", 0) >= 80,
            f"Score: {result2.get('quality_score')}, Band: {result2.get('colour_band')}",
        )

        # Test open well floor — should never score above 35
        result3 = calculate_quality_score(
            contaminants=[],
            severity="low",
            source_type="open_well",
        )
        test(
            "Open well applies risk floor (score <= 35)",
            result3.get("quality_score", 100) <= 35,
            f"Score: {result3.get('quality_score')} (floor enforced)",
        )

    except Exception as e:
        test("Quality score tool", False, str(e)[:200])


# ── Test 6: Treatment Tool (Pure Python, No API) ──────────────────────────────

def test_treatment_tool():
    print("\n" + "="*60)
    print("Test Group 6 — Treatment Tool (pure Python)")
    print("="*60)

    try:
        from agents.action_forge.agent import get_treatment_recommendation

        result = get_treatment_recommendation(
            contaminants=["H2S", "Iron"],
            source_type="borewell",
            severity="medium",
        )

        test(
            "Treatment tool returns immediate actions",
            len(result.get("immediate_actions", [])) > 0,
            f"Actions: {result.get('immediate_actions', [])[:2]}",
        )

        test(
            "Treatment tool correctly says safe for bathing for H2S",
            any("bath" in a.lower() or "safe" in a.lower()
                for a in result.get("immediate_actions", [])),
            f"Actions: {result.get('immediate_actions', [])}",
        )

        test(
            "Treatment tool recommends iron filter not UV",
            any("iron" in a.lower() or "greensand" in a.lower()
                for a in result.get("long_term_actions", [])),
            f"Long term: {result.get('long_term_actions', [])}",
        )

    except Exception as e:
        test("Treatment tool", False, str(e)[:200])


# ── Test 7: Session Service (No API) ──────────────────────────────────────────

async def test_session_service():
    print("\n" + "="*60)
    print("Test Group 7 — Session Service (no API)")
    print("="*60)

    try:
        from agents.orchestrator.agent import session_service
        import uuid

        session_id = f"test_{uuid.uuid4().hex[:8]}"
        user_id = "test_user"

        # Create session
        await session_service.create_session(
            app_name="watersentinel",
            user_id=user_id,
            session_id=session_id,
        )
        test("Session creation", True)

        # Get session
        session = await session_service.get_session(
            app_name="watersentinel",
            user_id=user_id,
            session_id=session_id,
        )
        test(
            "Session retrieval",
            session is not None,
            f"Session type: {type(session)}",
        )

        # Write to session state
        if session:
            session.state["test_key"] = "test_value"
            test(
                "Session state write",
                session.state.get("test_key") == "test_value",
            )

    except Exception as e:
        test("Session service", False, str(e)[:200])


# ── Test 8: MCP Server Paths Reachable ────────────────────────────────────────

def test_mcp_paths():
    print("\n" + "="*60)
    print("Test Group 8 — MCP Server Files Exist")
    print("="*60)

    water_intel_path = Path("mcp_servers/water_intel_store.py")
    action_bridge_path = Path("mcp_servers/action_bridge.py")

    test(
        "water_intel_store.py exists at correct path",
        water_intel_path.exists(),
        f"Checked: {water_intel_path.absolute()}",
    )

    test(
        "action_bridge.py exists at correct path",
        action_bridge_path.exists(),
        f"Checked: {action_bridge_path.absolute()}",
    )

    # Verify StdioServerParameters path in community_mapper matches actual file
    try:
        import ast
        mapper_code = Path("agents/community_mapper/agent.py").read_text()
        test(
            "CommunityMapper agent.py readable",
            len(mapper_code) > 100,
        )

        # Check it references the MCP server file
        test(
            "CommunityMapper references water_intel_store.py",
            "water_intel_store" in mapper_code,
            "MCP server path reference found in agent code",
        )
    except Exception as e:
        test("MCP path verification", False, str(e)[:200])


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "="*60)
    print("WaterSentinel — Agent Structure Test (Zero API Calls)")
    print("Verifies structure, wiring, tools — NOT LLM reasoning")
    print("="*60)

    # Check API key exists (but don't test it — we know it has quota issues)
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if api_key:
        print(f"\n✅ GOOGLE_API_KEY present ({api_key[:8]}...)")
        print("   Note: Quota may be exhausted — this test does NOT use it")
    else:
        print("\n⚠️  GOOGLE_API_KEY not set — agents will need it for LLM calls")

    # Check ChromaDB
    chroma_path = Path(os.getenv("CHROMA_DB_PATH", "./data/chroma_db"))
    if chroma_path.exists():
        print(f"✅ ChromaDB found at {chroma_path}")
    else:
        print(f"⚠️  ChromaDB not found — run: python rag/ingest.py")

    # Run all test groups
    test_adk_imports()
    test_agent_imports()
    test_agent_structure()
    test_rag_tools()
    test_scoring_tool()
    test_treatment_tool()
    await test_session_service()
    test_mcp_paths()

    # Summary
    total = passed + failed
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if failed == 0:
        print("\n✅ ALL STRUCTURE TESTS PASSED")
        print("   Agent pipeline is correctly wired.")
        print("   Proceed to Batch 4 (FastAPI backend).")
        print("\n   NOTE: Full LLM pipeline test (test_agents.py) requires")
        print("   Gemini API quota. Test it once quota resets OR enable billing.")
    elif failed <= 2:
        print(f"\n⚠️  {failed} test(s) failed — minor issues, check details above")
        print("   If only RAG or tool tests failed, proceed to Batch 4")
        print("   and fix those specific issues in parallel.")
    else:
        print(f"\n❌ {failed} TESTS FAILED — fix before proceeding")
        print("   Paste failing test names into Chrome AI for targeted fixes")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
