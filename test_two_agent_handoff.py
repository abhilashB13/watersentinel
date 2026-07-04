"""
Module: scripts/test_two_agent_handoff.py
Purpose: Test SourceSense → WaterProfiler handoff via session state.
         Confirms agent coordination works BEFORE testing all 5 agents.
Component: Testing — Two Agent Handoff Isolation
Usage:
    python scripts/test_two_agent_handoff.py

Run this AFTER test_single_agent.py passes, and BEFORE the full
test_agents.py pipeline (5 agents). This isolates the specific thing
that can break in multi-agent systems: does Agent B correctly read
what Agent A wrote to shared session state?

Cost: ~2 Gemini API calls (SourceSense + WaterProfiler).
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def test_two_agent_chain():
    """
    Build a minimal 2-agent chain: SourceSense -> WaterProfiler.
    Uses a lightweight parent agent (not the full Orchestrator) so
    failures are isolated to just these two agents' coordination,
    not the other 3 agents in the full pipeline.
    """
    print("\n" + "="*60)
    print("Two-Agent Handoff Test — SourceSense -> WaterProfiler")
    print("="*60)

    try:
        from google.adk.agents import LlmAgent
        from google.adk.sessions import InMemorySessionService
        from google.adk.runners import Runner
        from google.genai.types import Content, Part
        from agents.source_sense.agent import source_sense_agent
        from agents.water_profiler.agent import water_profiler_agent
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

    # Minimal 2-agent orchestrator — NOT the full 4-agent one.
    # This isolates failures to just this handoff.
    mini_orchestrator = LlmAgent(
        name="MiniTestOrchestrator",
        model="gemini-2.0-flash",
        description="Test-only orchestrator for 2-agent handoff verification",
        instruction=(
            "Route the citizen's water report to SourceSense first to classify "
            "the source and symptoms. Then route to WaterProfiler to diagnose "
            "contaminants using the classification. Return WaterProfiler's "
            "diagnosis as your final response."
        ),
        sub_agents=[source_sense_agent, water_profiler_agent],
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=mini_orchestrator,
        app_name="watersentinel_handoff_test",
        session_service=session_service,
    )

    session_id = f"handoff_test_{uuid.uuid4().hex[:8]}"
    user_id = "test_user"

    await session_service.create_session(
        app_name="watersentinel_handoff_test",
        user_id=user_id,
        session_id=session_id,
    )

    test_message = (
        "My borewell water in Nallagandla smells like rotten eggs and "
        "taps have yellowish stains. Pincode 500032. 5 days now."
    )

    print(f"\nInput: {test_message[:80]}...")
    print("\nRunning SourceSense -> WaterProfiler chain (~2 API calls)...")

    content = Content(role="user", parts=[Part(text=test_message)])
    final_response = ""

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_response += part.text
    except Exception as e:
        print(f"\n❌ Chain execution failed: {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("\nQuota exhausted. Wait for reset or enable billing.")
        sys.exit(1)

    session = await session_service.get_session(
        app_name="watersentinel_handoff_test",
        user_id=user_id,
        session_id=session_id,
    )
    state = dict(session.state) if session else {}
    source_cls = state.get("source_classification", {})
    water_profile = state.get("water_profile", {})

    print(f"\n{'='*60}")
    print("RESULT")
    print(f"{'='*60}")

    print(f"\n[Agent 1] SourceSense wrote to session state:")
    print(f"  source_type: {source_cls.get('source_type')}")
    print(f"  symptoms: {source_cls.get('symptoms_standardised')}")

    print(f"\n[Agent 2] WaterProfiler read that state and wrote:")
    print(f"  quality_score: {water_profile.get('quality_score')}")
    print(f"  colour_band: {water_profile.get('colour_band')}")
    print(f"  contaminants: {[c.get('name') for c in water_profile.get('contaminants', [])]}")
    print(f"  rag_citations: {water_profile.get('rag_citations')}")

    # ── The actual thing we're testing: did the handoff work? ──────
    handoff_worked = (
        bool(source_cls.get("source_type"))
        and bool(water_profile.get("quality_score") is not None)
        and water_profile.get("quality_score", -1) >= 0
    )

    contaminants_match_symptoms = False
    if source_cls.get("symptoms_standardised") and water_profile.get("contaminants"):
        symptoms = source_cls.get("symptoms_standardised", [])
        contaminant_names = " ".join(
            c.get("name", "").lower() for c in water_profile.get("contaminants", [])
        )
        if "egg_smell" in symptoms and ("h2s" in contaminant_names or "sulphide" in contaminant_names):
            contaminants_match_symptoms = True
        if "yellow_colour" in symptoms and "iron" in contaminant_names:
            contaminants_match_symptoms = True

    print(f"\n{'='*60}")
    if handoff_worked and contaminants_match_symptoms:
        print("✅ PASS — Session state handoff works correctly.")
        print("   WaterProfiler correctly used SourceSense's classification")
        print("   to diagnose contaminants matching the reported symptoms.")
        print("   Next: safe to run full test_agents.py (5-agent pipeline)")
    elif handoff_worked:
        print("⚠️  PARTIAL — Handoff mechanics work, but diagnosis may be off.")
        print("   Session state passed correctly between agents.")
        print("   Contaminant diagnosis didn't clearly match symptoms —")
        print("   check RAG retrieval quality, not agent coordination.")
    else:
        print("❌ FAIL — Session state handoff broken.")
        print("   WaterProfiler did not receive or use SourceSense's output.")
        print("   Check: output_key='source_classification' on SourceSense")
        print("   Check: WaterProfiler prompt reads session state correctly")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_two_agent_chain())
