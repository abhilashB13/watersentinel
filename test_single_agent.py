"""
Module: scripts/test_single_agent.py
Purpose: Test ONE agent in isolation with ONE real Gemini API call.
         Cheapest possible LLM-behavior test — costs ~1 API call instead
         of the 5+ calls a full pipeline run costs.
Component: Testing — Single Agent Isolation
Usage:
    python scripts/test_single_agent.py

Run this BEFORE test_two_agent_handoff.py, and BEFORE the full
test_agents.py pipeline. If SourceSense fails here, fix it here —
don't discover it 4 agents deep into a full pipeline run.

Cost: 1 Gemini API call. If you're quota-limited, this is the
cheapest way to confirm the LLM layer actually works at all.
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def test_source_sense_alone():
    """
    Run SourceSense agent by itself — not through the Orchestrator.
    Confirms: agent accepts input, calls Gemini, calls its tool,
    returns a structured classification. This is the minimum proof
    that the LLM layer works end-to-end for one agent.
    """
    print("\n" + "="*60)
    print("Single Agent Test — SourceSense (1 API call)")
    print("="*60)

    try:
        from google.adk.sessions import InMemorySessionService
        from google.adk.runners import Runner
        from google.genai.types import Content, Part
        from agents.source_sense.agent import source_sense_agent
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=source_sense_agent,
        app_name="watersentinel_test",
        session_service=session_service,
    )

    session_id = f"single_test_{uuid.uuid4().hex[:8]}"
    user_id = "test_user"

    await session_service.create_session(
        app_name="watersentinel_test",
        user_id=user_id,
        session_id=session_id,
    )

    test_message = (
        "My borewell water in Nallagandla smells like rotten eggs and "
        "my taps have a yellowish stain. Pincode 500032. Been happening 5 days."
    )

    print(f"\nInput: {test_message[:80]}...")
    print("\nCalling Gemini via SourceSense agent (1 API call)...")

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
        print(f"\n❌ Agent call failed: {e}")
        print("\nIf this is a 429 RESOURCE_EXHAUSTED error:")
        print("  - Your daily quota is exhausted, wait for reset, OR")
        print("  - Enable billing at aistudio.google.com")
        sys.exit(1)

    # Check session state for structured output
    session = await session_service.get_session(
        app_name="watersentinel_test",
        user_id=user_id,
        session_id=session_id,
    )
    classification = dict(session.state).get("source_classification", {}) if session else {}

    print(f"\n{'='*60}")
    print("RESULT")
    print(f"{'='*60}")
    print(f"\nAgent response text:\n{final_response[:500]}")
    print(f"\nStructured classification written to session state:")
    print(f"  source_type: {classification.get('source_type')}")
    print(f"  symptoms: {classification.get('symptoms_standardised')}")
    print(f"  severity: {classification.get('severity')}")

    # Verdict
    success = (
        len(final_response) > 20
        and classification.get("source_type") in
            ["borewell", "municipal_pipeline", "hand_pump", "open_well"]
    )

    print(f"\n{'='*60}")
    if success:
        print("✅ PASS — SourceSense correctly calls Gemini and its tool.")
        print("   LLM layer confirmed working for this agent.")
        print("   Next: run test_two_agent_handoff.py")
    else:
        print("❌ FAIL — SourceSense did not produce valid classification.")
        print("   Check: did it call classify_water_source tool?")
        print("   Check: is source_type one of the 4 valid values?")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_source_sense_alone())
