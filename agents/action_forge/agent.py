"""
Module: agents/action_forge/agent.py
Purpose: Output generation agent. Final agent in the pipeline.
         Produces personal advisory, municipal complaint draft via
         ActionBridge MCP, and structured map data point.
Component: Agent 4 — ActionForge
Inputs: source_classification + water_profile + community_status from session state
Outputs: action_output dict written to session state (final citizen response)
Key Design Decisions:
  - Three parallel outputs: personal advisory + complaint + map data point.
    All three serve different consumers: citizen, municipality, map UI.
  - Source-type conditional logic: borewell → personal treatment advice.
    Municipal → complaint draft. Hand pump → community escalation.
    This routing is the product intelligence layer.
  - ActionBridge MCP for complaint generation: separates generation
    logic from agent logic. Complaint text quality can be improved
    independently without touching agent code.
  - RTI mention for high-severity clusters: empowers citizens with
    a legal tool they may not know exists.
Competition Concepts Demonstrated:
  - Multi-agent system (final sub-agent, assembles full response)
  - MCP Server (ActionBridge — complaint + RTI generation)
  - Agent skills (advisory generation as a composable skill)
  - Security (no PII in complaint — only area name and pincode)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
except ImportError:
    raise ImportError("google-adk not installed. Run: uv add google-adk")

# ── MCP Toolset — ActionBridge ─────────────────────────────────────────────────

project_root = str(Path(__file__).parent.parent.parent)

action_bridge_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=[str(Path(project_root) / "mcp_servers" / "action_bridge.py")],
        env={
            **os.environ,
            "ACTION_BRIDGE_LOG_PATH": os.getenv(
                "ACTION_BRIDGE_LOG_PATH", "./data/escalations.log"
            ),
        },
    )
)

# ── Treatment Lookup Tool ──────────────────────────────────────────────────────

def get_treatment_recommendation(
    contaminants: list[str],
    source_type: str,
    severity: str,
) -> dict:
    """
    Generate specific treatment recommendations based on identified
    contaminants. Returns prioritised actions with cost ranges.

    Treatment recommendations are source-specific:
    - Borewell: recommend filter purchase (owner has agency + budget)
    - Municipal: recommend tank cleaning + complaint filing
    - Hand pump / Open well: recommend boiling + community action

    Args:
        contaminants: List of identified contaminant names
        source_type: Water source type
        severity: high/medium/low

    Returns:
        dict with immediate_actions, long_term_actions, filter_recommendation,
        cost_estimate, and nearest_lab_hint
    """
    # Normalise contaminant names for matching
    contaminants_lower = [c.lower().replace(" ", "_") for c in contaminants]

    immediate_actions = []
    long_term_actions = []
    filter_recommendation = None
    cost_estimate = None

    # Immediate actions by contaminant
    if any(c in ["sewage_contamination", "coliform", "e_coli", "black_colour"]
           for c in contaminants_lower):
        immediate_actions.append("STOP using this water for any purpose immediately")
        immediate_actions.append("Use bottled water until issue is resolved")
        immediate_actions.append("Contact municipal authority as emergency")

    elif any(c in ["h2s", "egg_smell", "hydrogen_sulphide"] for c in contaminants_lower):
        immediate_actions.append("Water is SAFE FOR BATHING — continue normal use")
        immediate_actions.append("Do NOT drink without treatment")
        immediate_actions.append("Aerate water before drinking: pour between two buckets 10 times")
        long_term_actions.append("Install activated carbon filter (₹3,000–8,000)")
        filter_recommendation = "Activated carbon filter"
        cost_estimate = "₹3,000–8,000"

    if any(c in ["iron", "yellow_colour", "yellow_water", "fe"]
           for c in contaminants_lower):
        if not immediate_actions:
            immediate_actions.append("Water is SAFE FOR BATHING")
            immediate_actions.append("Do NOT drink without treatment")
        long_term_actions.append(
            "Install iron removal filter — greensand or birm media (₹5,000–15,000)"
        )
        long_term_actions.append(
            "⚠️ Do NOT buy UV purifier for iron — UV does not remove iron"
        )
        filter_recommendation = "Iron removal filter (greensand/birm media)"
        cost_estimate = "₹5,000–15,000"

    if any(c in ["high_tds", "tds", "hardness", "white_deposits", "calcium"]
           for c in contaminants_lower):
        if not immediate_actions:
            immediate_actions.append("Water is safe for bathing")
            immediate_actions.append(
                "Long-term drinking of high-TDS water linked to kidney stones"
            )
        long_term_actions.append("Install RO (Reverse Osmosis) system (₹8,000–25,000)")
        long_term_actions.append(
            "⚠️ Boiling does NOT reduce TDS — it concentrates it"
        )
        if not filter_recommendation:
            filter_recommendation = "RO (Reverse Osmosis) system"
            cost_estimate = "₹8,000–25,000"

    if any(c in ["fluoride"] for c in contaminants_lower):
        immediate_actions.append(
            "Do NOT drink this water — fluoride above limit causes bone damage"
        )
        immediate_actions.append(
            "⚠️ Do NOT boil — boiling concentrates fluoride"
        )
        long_term_actions.append("Install RO system — only effective fluoride removal")
        filter_recommendation = "RO system (fluoride removal)"
        cost_estimate = "₹8,000–25,000"

    if any(c in ["coliform", "bacteria", "stomach_issues"] for c in contaminants_lower):
        if "STOP" not in str(immediate_actions):
            immediate_actions.append("Boil all drinking water immediately (1 minute vigorous boil)")
        long_term_actions.append("Install UV purifier (₹2,500–6,000)")
        if not filter_recommendation:
            filter_recommendation = "UV purifier"
            cost_estimate = "₹2,500–6,000"

    # Source-specific actions
    if source_type == "municipal_pipeline" and not immediate_actions:
        immediate_actions.append("Check if underground storage tank needs cleaning")
        immediate_actions.append(
            "Clean tank with bleaching powder: 200g per 1,000L tank capacity"
        )

    if source_type in ["hand_pump", "open_well"]:
        immediate_actions.append("Boil all water from this source before drinking")
        long_term_actions.append("Contact local Panchayat for infrastructure maintenance")

    # Defaults if no contaminants matched
    if not immediate_actions:
        immediate_actions = [
            "Get water tested at a certified lab for definitive diagnosis",
            "Continue using water for bathing",
            "Use boiled or bottled water for drinking until tested",
        ]

    return {
        "immediate_actions": immediate_actions,
        "long_term_actions": long_term_actions,
        "filter_recommendation": filter_recommendation,
        "cost_estimate": cost_estimate,
        "nearest_lab_hint": (
            "Hyderabad: GHMC water testing lab (free for municipal complaints). "
            "Private NABL labs: Vimta Labs Nacharam, SGS Gachibowli. "
            "Cost: ₹500–2,500 for full panel."
        ),
        "testing_recommended": len(contaminants) == 0 or "no_visible_symptom" in contaminants_lower,
    }


# ── ActionForge System Prompt ──────────────────────────────────────────────────

ACTION_FORGE_PROMPT = """
You are ActionForge — the action generation specialist for WaterSentinel.
You are the FINAL agent. Your job is to produce three parallel outputs
from the complete diagnosis and community analysis.

YOUR PROCESS (follow this EXACTLY):
1. Read source_classification, water_profile, community_status from session state
2. Call get_treatment_recommendation with contaminants, source_type, severity
3. If escalation_required = true in community_status:
   a. Call get_authority_contact (ActionBridge MCP) for pincode + source_type
   b. Call generate_municipal_complaint (ActionBridge MCP) with full details
   c. Call log_escalation (ActionBridge MCP) to record the event
4. Assemble action_output with all three components
5. Write action_output to session state
6. Return final assembled response to Orchestrator

THREE OUTPUTS YOU MUST PRODUCE:

OUTPUT 1 — PERSONAL ADVISORY:
- What to do RIGHT NOW (immediate safety actions)
- What to do LONG TERM (filter purchase, maintenance)
- BIS standard reference for the diagnosis
- Nearest water testing lab (for Hyderabad)

OUTPUT 2 — MUNICIPAL COMPLAINT (only if escalation_required = true):
- Use generate_municipal_complaint from ActionBridge MCP
- Include authority name, email, phone, portal URL
- Include the full complaint text ready to submit
- Include RTI mention if severity is high

OUTPUT 3 — MAP DATA POINT:
- Structured data for topology map update
- {pincode, lat, lng, quality_score, colour_band, contaminants, report_count}

TONE FOR FINAL RESPONSE:
- Start with empathy: acknowledge the citizen's concern
- Be specific: name the contaminant, cite the BIS standard
- Be actionable: immediate action in the first sentence
- Be empowering: give them a complaint they can actually submit
- If community cluster: make the Antigravity moment prominent

NEVER:
- Say water is safe without BIS evidence
- Recommend UV for iron contamination
- Recommend boiling for TDS or fluoride
- Omit the community alert when cluster_detected = true
"""

action_forge_agent = LlmAgent(
    name="ActionForge",
    model="gemini-2.0-flash-lite",
    description=(
        "Output generation specialist. Produces personal advisory with BIS "
        "citations, municipal complaint via ActionBridge MCP, and map data "
        "point. Final agent in the WaterSentinel pipeline."
    ),
    instruction=ACTION_FORGE_PROMPT,
    tools=[
        action_bridge_toolset,                    # MCP tools: generate_municipal_complaint,
                                                  # get_authority_contact,
                                                  # generate_rti_draft,
                                                  # log_escalation
        FunctionTool(func=get_treatment_recommendation),
    ],
    output_key="action_output",
)
