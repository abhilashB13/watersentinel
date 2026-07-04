"""
Module: agents/water_profiler/agent.py
Purpose: RAG-powered diagnosis agent. Maps symptoms to contaminants
         using retrieved BIS/WHO/CGWB knowledge. Generates quality score.
Component: Agent 2 — WaterProfiler
Inputs: source_classification from session state (SourceSense output)
Outputs: water_profile dict written to session state
Key Design Decisions:
  - RAG before reasoning: agent retrieves knowledge FIRST, then
    reasons over retrieved chunks. This ensures BIS citations in
    output are accurate, not hallucinated.
  - Explicit safe-for-bathing vs safe-for-drinking distinction:
    H2S water is safe to bathe in but not drink. This distinction
    matters enormously for citizen advisory — many people panic
    unnecessarily about bathing with H2S water.
  - Deterministic quality score via tool: LLM scores would vary
    between runs. Tool-calculated score is consistent for same inputs.
Competition Concepts Demonstrated:
  - RAG (primary RAG demonstration — grounded diagnosis with citations)
  - Multi-agent system (sub-agent receiving session state from SourceSense)
"""

from dotenv import load_dotenv
load_dotenv()

try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
except ImportError:
    raise ImportError("google-adk not installed. Run: uv add google-adk")

from agents.water_profiler.tools import (
    retrieve_water_quality_knowledge,
    calculate_quality_score,
)

# ── WaterProfiler System Prompt ────────────────────────────────────────────────

WATER_PROFILER_PROMPT = """
You are WaterProfiler — the water quality diagnosis specialist for WaterSentinel.
You are trained on Indian BIS IS 10500:2012 standards and WHO guidelines.

YOUR PROCESS (follow this EXACTLY):
1. Read source_classification from session state
2. Call retrieve_water_quality_knowledge with the symptoms and source_type
3. Read the retrieved knowledge carefully — it contains BIS limits and health data
4. Identify contaminants based on symptoms + retrieved knowledge
5. Call calculate_quality_score with the identified contaminants
6. Determine safe_for_drinking and safe_for_bathing separately
7. Write complete water_profile to session state
8. Transfer to CommunityMapper

DIAGNOSIS RULES:
- ALWAYS cite the specific BIS standard when stating a limit
  (e.g. "BIS IS 10500:2012 limit for iron is 0.3 mg/L")
- Egg smell = H2S → safe to bathe, unsafe to drink without treatment
- Yellow/brown water = Iron → safe to bathe, unsafe to drink
- Black water = possible sewage → unsafe for ALL use
- White deposits = high TDS → safe to bathe, caution for long-term drinking
- Blue-green stain = copper → investigate pipe age and pH
- No visible symptom does NOT mean safe (fluoride, nitrate are odourless)

CONFIDENCE LEVELS:
- 0.90+ = very high confidence (single dominant symptom matches clearly)
- 0.70-0.89 = high confidence (symptom combination matches well)
- 0.50-0.69 = medium confidence (symptom is ambiguous, multiple causes)
- Below 0.50 = recommend lab testing

OUTPUT FORMAT for water_profile session state:
{
  "contaminants": [
    {
      "name": "Hydrogen Sulphide (H2S)",
      "confidence": 0.95,
      "bis_limit": "0.05 mg/L",
      "bis_reference": "BIS IS 10500:2012",
      "health_risk": "Safe for bathing. Unsafe for drinking above limit.",
      "source_correlation": "Common in deep borewells >250ft in Deccan Plateau"
    }
  ],
  "quality_score": 32,
  "colour_band": "red",
  "band_label": "Poor — Do Not Drink",
  "safe_for_drinking": false,
  "safe_for_bathing": true,
  "rag_citations": ["BIS IS 10500:2012", "CGWB Telangana 2023"],
  "diagnosis_confidence": "high",
  "lab_test_recommended": false
}
"""

water_profiler_agent = LlmAgent(
    name="WaterProfiler",
    model="gemini-2.0-flash-lite",
    description=(
        "RAG-powered water quality diagnosis specialist. Retrieves relevant "
        "chunks from BIS IS 10500, WHO guidelines, and CGWB regional data "
        "to diagnose contaminants and calculate quality scores."
    ),
    instruction=WATER_PROFILER_PROMPT,
    tools=[
        FunctionTool(func=retrieve_water_quality_knowledge),
        FunctionTool(func=calculate_quality_score),
    ],
    output_key="water_profile",
)
