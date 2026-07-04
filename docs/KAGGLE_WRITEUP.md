# WaterSentinel — Kaggle Writeup
## AI Agents Intensive Capstone 2026 | Agents for Good Track

---

## The Problem

Every day, millions of Indian families drink water they cannot verify is safe.

The contamination signals are visible — egg-like sulphur smell, yellow iron
staining on taps, white scale deposits from high TDS, occasional black water
from sewage mixing events. But residents have no framework to interpret what
they observe, no platform to report it collectively, and no visibility into
whether their neighbours are experiencing the same problem.

India's monitoring infrastructure cannot close this gap. CPCB maintains
approximately 4,000 water quality stations nationally — one per 330,000
people. HMWSSB in Hyderabad monitors treatment plant output, not tap
delivery. Jal Jeevan Mission's dashboard relies on self-reported state data.
The last mile from distribution network to citizen tap is officially
unmonitored.

The contamination profile varies sharply by water source type — a distinction
no existing app captures:

- **Borewell (250–500ft, Deccan Plateau):** H₂S + iron from anaerobic
  geology. Owner has full agency and budget to act. Personal advisory
  is the right response.
- **Municipal pipeline:** One hour of supply per day, stored in underground
  cement tanks. Tank contamination or pressure-drop sewage mixing are
  the primary risks. Complaint to HMWSSB is the right response.
- **Hand pump:** Shared infrastructure, no individual ownership. Community
  escalation to Ward Office or Panchayat is the right response.
- **Open well:** Always assume bacterial contamination. Boiling is the
  minimum safe action.

The same symptom — yellow water — requires a completely different response
depending on whether it comes from a borewell (personal iron removal filter)
or a municipal pipeline (complaint to the distribution zone office). No
existing system makes this distinction.

**WaterSentinel makes it automatically.**

---

## The Solution

WaterSentinel is a citizen-powered water quality intelligence system for
Indian cities. Citizens describe what they observe — smell, colour, taste,
deposits — via a mobile app. Five ADK agents analyse the report, diagnose
contaminants against BIS IS 10500:2012 Indian standards using RAG retrieval,
detect whether the issue is isolated or a community pattern, and generate
both a personal advisory and (when warranted) a pre-filled municipal
complaint.

The topology map — WaterSentinel's AQI equivalent for water — shows every
city's water quality at colony and road level, colour-coded from green
(safe) to red (critical). It is built entirely from citizen reports, not
government sensors.

**The core insight:** Citizens who notice egg-smelling water or brown pipe
stains already have the data. They just have no system to contribute it,
interpret it, or act on it collectively. WaterSentinel turns individual
observations into community intelligence — and community intelligence into
civic action.

---

## Why Agents

WaterSentinel's value cannot be delivered by a search engine or a simple
chatbot. It requires:

1. **Source classification** before diagnosis — the same symptom means
   different things from different sources
2. **Knowledge retrieval** from authoritative Indian standards — not general
   LLM knowledge which may be inaccurate for BIS-specific limits
3. **Community memory** — checking whether the same issue was reported by
   neighbours in the past 7 days
4. **Conditional action routing** — escalate to municipality only for shared
   infrastructure, not private borewells
5. **Document generation** — producing a properly formatted complaint
   addressed to the correct zonal office

These five responsibilities require five distinct agents, each with different
tools and different knowledge. A single LLM call cannot hold all of this
context simultaneously and act correctly on all of it.

---

## Architecture

### 5 ADK Agents

**Agent 0 — Orchestrator (Root LlmAgent)**
Parent agent. Routes incoming reports sequentially through the four
specialist sub-agents using ADK's transfer_to_agent pattern. Maintains
shared InMemorySessionService so each sub-agent can read the previous
agent's output without additional API calls.

**Agent 1 — SourceSense**
Intake specialist. Identifies water source type from natural language
description. Standardises symptoms to a controlled vocabulary. Optionally
analyses uploaded photos using Gemini Vision (with EXIF stripping for
privacy). Writes `source_classification` to shared session state.

**Agent 2 — WaterProfiler (RAG-powered)**
Diagnosis specialist. Before reasoning, retrieves the 3 most relevant
chunks from the BIS/WHO/CGWB knowledge base using Google text-embedding-004
and ChromaDB. Diagnoses contaminants based on retrieved evidence — not
hallucination. Cites specific BIS IS 10500:2012 limits in every diagnosis.
Makes the critical safe-for-drinking vs safe-for-bathing distinction.
Calculates a deterministic quality score (0–100) via a scoring tool.
Writes `water_profile` to session state.

**Agent 3 — CommunityMapper (MCP-connected)**
Community intelligence specialist. Connects to WaterIntel Store MCP server
via ADK's MCPToolset with StdioServerParameters. Submits the current report,
then calls get_cluster_status to check whether ≥3 matching reports exist in
the same pincode within 7 days. When the threshold is crossed, generates
the community alert automatically — without the citizen asking. Updates the
topology map score. Writes `community_status` to session state.

**Agent 4 — ActionForge (MCP-connected)**
Output generation specialist. Calls get_treatment_recommendation tool for
source-specific advisory with cost estimates. If escalation is required,
calls ActionBridge MCP to generate a municipal complaint addressed to the
correct zonal office, and logs the escalation. Returns three parallel
outputs: personal advisory, complaint draft, and map data point.

### 2 MCP Servers

**WaterIntel Store** — Community data intelligence layer. SQLite-backed.
6 tools: submit_report, get_pincode_profile, get_cluster_status,
get_area_history, update_topology_score, get_all_topology_data.
The cluster detection tool is the Antigravity trigger.

**ActionBridge** — Civic action generation layer. Stateless. 4 tools:
generate_municipal_complaint (Gemini-formatted), get_authority_contact
(routes by pincode to correct HMWSSB/VWSS/GHMC zone), generate_rti_draft,
log_escalation. Separated from WaterIntel Store by design — data
intelligence and civic action are distinct responsibilities.

### 1 RAG Knowledge Base

7 documents ingested into ChromaDB with Google text-embedding-004 embeddings:
BIS IS 10500:2012, WHO Guidelines 2022, CGWB Telangana 2023, CGWB AP 2023,
and three custom-authored documents: symptom-contaminant mapping (India-specific
confidence levels for 20+ symptom combinations), India water sources guide
(borewell geology, municipal supply patterns, HMWSSB contacts), and treatment
recommendations (filter types, costs, what treats what — critical because
UV does not remove iron and boiling concentrates fluoride).

The custom documents are the project's unfair advantage — they encode ground
truth about Indian water supply that cannot be retrieved from any public
dataset.

---

## The Antigravity Moment

A citizen in BHEL MIG Colony, pincode 500032, opens WaterSentinel.
Her water smells like eggs and the taps are yellowed. She submits a report.

SourceSense classifies: borewell, symptoms egg_smell + yellow_colour.
WaterProfiler retrieves BIS IS 10500 entries for H₂S (limit: 0.05 mg/L)
and iron (limit: 0.3 mg/L). Diagnosis: H₂S + iron, quality score 32/100
(red band), safe for bathing, not for drinking.

CommunityMapper calls get_cluster_status for pincode 500032. The database
already contains 3 other reports from the same pincode within the last 7
days — from Nallagandla, BHEL LIG Colony, and BHEL HIG Colony — all
reporting egg smell and yellow water.

Without the citizen asking anything about her neighbours, the system
generates:

> *"3 other households in your area reported similar symptoms this week.
> This appears to be a community supply issue affecting your neighbourhood
> — not just your home."*

The topology map updates. The 500032 cluster shifts to red. ActionForge
generates a complaint addressed to HMWSSB Distribution Zone II.

That is the Antigravity moment: an agent that thinks beyond the individual
user without being told to. The citizen came with a personal problem and
discovered a community crisis.

---

## Competition Criteria

| Criterion | Implementation |
|---|---|
| Multi-agent system (ADK) | 5 agents with session state handoff — code |
| MCP Server | 2 servers, 10 tools total — code |
| RAG | WaterProfiler retrieves BIS/WHO/CGWB before diagnosis — code |
| Antigravity | Cluster auto-detection, live map update — video |
| Security | Pincode-only, EXIF strip, rate limit, no PII — code + video |
| Deployability | FastAPI on Cloud Run, Expo mobile app — video |
| Agent Skills | Symptom classification, complaint generation — code |

Required: 3. Demonstrated: 7.

---

## What Makes This Submission Different

Most submissions in this competition will build agents that answer questions.
WaterSentinel builds agents that take action on behalf of citizens who did
not know they needed to act.

The source taxonomy — borewell, municipal pipeline, hand pump, open well —
is not in any general-purpose AI's training data as an actionable decision
tree. It came from field observation of how water actually reaches people
in Indian cities. The custom RAG documents encode that knowledge in a form
the agent can retrieve and reason over.

The citizen-as-sensor model means WaterSentinel gets more valuable with
every report. A single complaint is a personal problem. A hundred complaints
from the same pincode is a civic dataset. A thousand complaints across a
city is the infrastructure map that HMWSSB and Jal Jeevan Mission cannot
build with their existing resources.

The endgame is not a competition submission. The endgame is government
absorption — WaterSentinel becoming the citizen-monitoring layer for India's
national water quality programme, one report at a time, one neighbourhood
at a time.

---

## Project Links

- GitHub Repository: [github.com/abhilashbattu/watersentinel]
- Live Demo (Cloud Run): [watersentinel-xxxxx-el.a.run.app]
- Demo Video (YouTube): [youtube.com/watch?v=xxxxx]

---

*Built solo by Abhilash Battu — Hyderabad, India — June 2026*
*"Built not by sensors, but by citizens who already know what their
water looks, smells, and tastes like."*
