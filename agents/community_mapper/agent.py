"""
Module: agents/community_mapper/agent.py
Purpose: Community intelligence agent. Detects contamination clusters
         by querying WaterIntel MCP Store. Updates topology map.
         Triggers the ANTIGRAVITY MOMENT when cluster is detected.
Component: Agent 3 — CommunityMapper
Inputs: source_classification + water_profile from session state
Outputs: community_status dict written to session state
Key Design Decisions:
  - MCP tools via MCPToolset: CommunityMapper uses WaterIntel Store
    MCP server for all data operations. Demonstrates MCP integration.
  - Cluster threshold = 3 reports in 7 days: statistically meaningful
    minimum to distinguish supply-level issue from individual plumbing.
  - Antigravity trigger is automatic: agent does not need to be
    instructed to check — it always checks. The surprise is that it
    fires without the citizen asking about neighbours.
  - Isolation verdict logic: same symptom from borewell = personal
    issue. Same symptom from municipal + cluster = supply problem.
    This distinction drives the entire downstream action path.
Competition Concepts Demonstrated:
  - Multi-agent system (MCP-connected sub-agent)
  - MCP Server (primary consumer of WaterIntel Store MCP tools)
  - Antigravity (cluster auto-detection without citizen prompt)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
except ImportError:
    raise ImportError("google-adk not installed. Run: uv add google-adk")

# ── MCP Toolset — WaterIntel Store ────────────────────────────────────────────
# ADK launches water_intel_store.py as a subprocess via stdio transport.
# Agent calls tools as if they were local Python functions.

project_root = str(Path(__file__).parent.parent.parent)

water_intel_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=[str(Path(project_root) / "mcp_servers" / "water_intel_store.py")],
        env={
            **os.environ,
            "WATER_INTEL_DB_PATH": os.getenv("WATER_INTEL_DB_PATH", "./data/reports.db"),
        },
    )
)

# ── Helper Tool ────────────────────────────────────────────────────────────────

def determine_isolation_verdict(
    source_type: str,
    cluster_detected: bool,
    cluster_count: int,
    contaminants: list[str],
) -> dict:
    """
    Determine whether a water issue is personal (internal plumbing/borewell)
    or a community supply problem based on source type and cluster status.

    This verdict drives the entire action path:
    - Personal → personal advisory only
    - Community → personal advisory + municipal complaint

    Args:
        source_type: Water source type from SourceSense
        cluster_detected: Whether CommunityMapper found a cluster
        cluster_count: Number of matching reports in cluster
        contaminants: Identified contaminants from WaterProfiler

    Returns:
        dict with verdict, escalation_required, and explanation
    """
    # Borewell is ALWAYS personal — it is private infrastructure
    if source_type == "borewell":
        return {
            "verdict": "personal_infrastructure",
            "escalation_required": False,
            "explanation": (
                "Borewell water quality is the owner's responsibility. "
                "The municipality does not manage private borewells. "
                "Personal treatment is the recommended action."
            ),
            "municipal_complaint_applicable": False,
        }

    # Open well — escalate to Panchayat if community shared
    if source_type == "open_well":
        return {
            "verdict": "community_shared_infrastructure",
            "escalation_required": cluster_detected,
            "explanation": (
                "Open well is shared community infrastructure. "
                "Escalate to local Panchayat for remediation."
                if cluster_detected
                else "Open well — personal advisory issued. "
                     "Recommend boiling or UV treatment."
            ),
            "municipal_complaint_applicable": cluster_detected,
        }

    # Municipal pipeline or hand pump — escalation possible
    if cluster_detected and cluster_count >= 3:
        return {
            "verdict": "community_supply_issue",
            "escalation_required": True,
            "explanation": (
                f"{cluster_count} households in the same area report similar "
                f"issues. This is consistent with a supply-level contamination "
                f"rather than individual plumbing. Municipal escalation warranted."
            ),
            "municipal_complaint_applicable": True,
        }

    return {
        "verdict": "possibly_isolated",
        "escalation_required": False,
        "explanation": (
            "Only your report detected in this area recently. "
            "This may be a building-level issue (storage tank) "
            "rather than a supply-level problem. "
            "Check if your storage tank needs cleaning first."
        ),
        "municipal_complaint_applicable": False,
    }


# ── CommunityMapper System Prompt ──────────────────────────────────────────────

COMMUNITY_MAPPER_PROMPT = """
You are CommunityMapper — the community intelligence specialist for WaterSentinel.
Your job is to determine if a citizen's water problem is isolated or part of
a larger community pattern, and to update the topology map with their report.

YOUR PROCESS (follow this EXACTLY):
1. Read source_classification and water_profile from session state
2. Extract: pincode, area_name, lat, lng, quality_score, colour_band,
   contaminants, symptoms, source_type from session state
3. Call submit_report (WaterIntel MCP tool) to save this report
4. Call get_cluster_status (WaterIntel MCP tool) for this pincode
5. Call determine_isolation_verdict with cluster results
6. Call update_topology_score (WaterIntel MCP tool) with new score
7. Write community_status to session state
8. Transfer to ActionForge

THE ANTIGRAVITY MOMENT:
When cluster_detected = True, your community_status MUST include:
  "community_alert": "X other households in [area] reported [contaminant]
   this week. This appears to be a [supply/distribution] issue affecting
   your neighbourhood — not just your home."

This is the moment that surprises the citizen. They came with a personal
problem and discovered a community crisis. Make it clear and impactful.

ISOLATION VERDICT RULES:
- borewell + any cluster → still personal (borewell is private infrastructure)
- municipal_pipeline + cluster >= 3 → community supply issue → escalate
- hand_pump + cluster >= 3 → community infrastructure → escalate to Panchayat
- open_well → always recommend treatment regardless of cluster

OUTPUT FORMAT for community_status session state:
{
  "report_submitted": true,
  "report_id": 42,
  "cluster_detected": true,
  "cluster_count": 4,
  "community_alert": "3 other households in Nallagandla reported egg smell...",
  "isolation_verdict": "community_supply_issue",
  "escalation_required": true,
  "topology_updated": true,
  "pincode": "500032",
  "area_name": "Nallagandla"
}
"""

community_mapper_agent = LlmAgent(
    name="CommunityMapper",
    model="gemini-2.0-flash",
    description=(
        "Community intelligence specialist. Uses WaterIntel MCP Store to "
        "submit citizen reports, detect contamination clusters, determine "
        "isolation vs community verdicts, and update the topology map. "
        "Powers the Antigravity moment — cluster auto-detection."
    ),
    instruction=COMMUNITY_MAPPER_PROMPT,
    tools=[
        water_intel_toolset,                          # MCP tools: submit_report,
                                                      # get_cluster_status,
                                                      # update_topology_score,
                                                      # get_pincode_profile
        FunctionTool(func=determine_isolation_verdict),
    ],
    output_key="community_status",
)
