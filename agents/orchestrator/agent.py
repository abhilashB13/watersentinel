"""
Module: agents/orchestrator/agent.py
Purpose: Root orchestrator agent. Entry point for all WaterSentinel requests.
         Coordinates the 4 specialist sub-agents via ADK parent-child pattern.
Component: Agent 0 — Orchestrator (Root Agent)
Inputs: Raw citizen request from FastAPI /report endpoint
Outputs: Assembled final response combining all sub-agent outputs
Key Design Decisions:
  - LlmAgent as root: ADK's parent agent pattern routes sub-agents
    automatically based on conversation context and transfer_to_agent calls.
  - Shared session state (InMemorySessionService): all sub-agents read and
    write to the same session state dict, enabling clean data handoff
    without repeated API calls.
  - Sequential routing: SourceSense → WaterProfiler → CommunityMapper →
    ActionForge. Each agent enriches session state for the next.
  - gemini-2.0-flash for all agents: fast, cost-effective, sufficient
    for structured diagnosis tasks.
Competition Concepts Demonstrated:
  - Multi-agent system (ADK) — primary demonstration
  - Agent skills — orchestration as a coordination skill
"""

import os
from dotenv import load_dotenv

# ── Force Developer Tier Infrastructure Routing ────────────────────────────────
load_dotenv()

# Enforce the specific environment key layout expected by the underlying SDK layer
if os.getenv("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# ── ADK Imports ────────────────────────────────────────────────────────────────
try:
    from google.adk.agents import LlmAgent
    from google.adk.sessions import InMemorySessionService
    from google.adk.runners import Runner
except ImportError:
    raise ImportError(
        "google-adk not installed. Run: uv add google-adk\n"
        "Fallback: pip install google-adk"
    )

# Import all sub-agents
from agents.source_sense.agent import source_sense_agent
from agents.water_profiler.agent import water_profiler_agent
from agents.community_mapper.agent import community_mapper_agent
from agents.action_forge.agent import action_forge_agent

# ── Orchestrator System Prompt ─────────────────────────────────────────────────

ORCHESTRATOR_PROMPT = """
You are the WaterSentinel Orchestrator — the coordinator of a team of
specialist agents that help Indian citizens understand and act on their
water quality issues.

Your role is to:
1. Receive the citizen's water quality report or question
2. Route it through the specialist agents IN THIS EXACT ORDER:
   a. SourceSense — to classify water source and symptoms
   b. WaterProfiler — to diagnose contaminants using BIS/WHO standards
   c. CommunityMapper — to detect community patterns and update the map
   d. ActionForge — to generate personal advisory and complaint if needed
3. Assemble the final response from all agents into a clear, empathetic,
   actionable reply for the citizen

ROUTING RULES:
- For new water quality reports: always run all 4 agents in sequence
- For map data queries (GET /map/topology): call only CommunityMapper
- For complaint follow-up queries: call only ActionForge

TONE RULES:
- Be empathetic — citizens are reporting a real problem affecting their family
- Be specific — always reference BIS standards and specific contaminants
- Be actionable — every response must end with a clear next step
- Be honest — if data is insufficient for diagnosis, say so clearly

SESSION STATE KEYS (shared across all agents):
- source_classification: output from SourceSense
- water_profile: output from WaterProfiler
- community_status: output from CommunityMapper
- action_output: output from ActionForge

Always maintain context across the agent pipeline.
The citizen should receive ONE final cohesive response, not 4 separate answers.
"""

# ── Root Agent Definition ──────────────────────────────────────────────────────

root_agent = LlmAgent(
    name="WaterSentinel_Orchestrator",
    model="gemini-2.0-flash",   
    description=(
        "Root orchestrator for WaterSentinel. Coordinates SourceSense, "
        "WaterProfiler, CommunityMapper, and ActionForge agents to analyse "
        "citizen water quality reports and generate community intelligence."
    ),
    instruction=ORCHESTRATOR_PROMPT,
    sub_agents=[
        source_sense_agent,
        water_profiler_agent,
        community_mapper_agent,
        action_forge_agent,
    ],
)

# ── Session Service ────────────────────────────────────────────────────────────

session_service = InMemorySessionService()

# ── Runner ─────────────────────────────────────────────────────────────────────

runner = Runner(
    agent=root_agent,
    app_name="watersentinel",
    session_service=session_service,
)

# ── Programmatic Pipeline Hook (Isolating Only Orchestrator) ──────────────────

def run_pipeline(session_id: str, message: str) -> str:
    """
    Programmatically executes ONLY the Orchestrator agent logic.
    Mocks sub-agent steps to bypass API rate limits during isolation testing.
    """
    # Fetch the shared session state context
    session = session_service.get_session(session_id=session_id)
    
    # Initialize session state if blank
    if not session.state:
        session.state = {
            "source_classification": None,
            "water_profile": None,
            "community_status": None,
            "action_output": None
        }

    # 1. MOCK THE DATA (Simulating what sub-agents would do)
    session.state["source_classification"] = {"source": "borewell", "symptoms": ["egg_smell", "yellow_colour"]}
    session.state["water_profile"] = {"contaminants": ["H2S", "Iron"], "quality_score": 30}
    session.state["community_status"] = {"cluster_detected": True, "cluster_count": 4}
    session.state["action_output"] = {"immediate_actions": ["Boil water"]}

    # 2. RUN ONLY THE ORCHESTRATOR
    # Let the orchestrator compile the final response from this state
    orchestrator_prompt = f"Compile a final user response based on this raw data: {session.state}"
    final_output = root_agent.run(message=orchestrator_prompt, session=session)
    
    return final_output.content