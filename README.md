# 💧 WaterSentinel
### The water quality intelligence map India never had

> *"WaterSentinel turns a mother's complaint about egg-smelling water into a ward-level municipal escalation — in seconds, without any sensor hardware."*

**Kaggle AI Agents Intensive 2026 — Agents for Good Track**

---

## Table of Contents
1. [Problem Statement](#1-problem-statement)
2. [Why Agents — Not Just Google](#2-why-agents--not-just-google)
3. [Architecture](#3-architecture)
4. [Agent Descriptions](#4-agent-descriptions)
5. [MCP Servers](#5-mcp-servers)
6. [RAG Knowledge Base](#6-rag-knowledge-base)
7. [Competition Criteria Coverage](#7-competition-criteria-coverage)
8. [Setup Instructions](#8-setup-instructions-windows)
9. [Environment Variables](#9-environment-variables)
10. [How to Run](#10-how-to-run)
11. [How to Run the Demo](#11-how-to-run-the-demo)
12. [Deployment](#12-deployment-google-cloud-run)
13. [Security Features](#13-security-features)
14. [Future Roadmap](#14-future-roadmap)
15. [Acknowledgements](#15-acknowledgements)

---

## 1. Problem Statement

India has a water crisis that is invisible to data systems.

Over 600 million Indians depend on groundwater. Municipal pipeline supply covers urban areas for approximately **one hour per day**. Residents store this water in underground cement tanks of 1,000–2,000 litres. Borewells are drilled at personal expense to depths of 250–500 feet into geology that varies block by block. And yet — no system exists to tell a resident whether the water coming out of their tap is safe to drink.

The contamination is not invisible. It produces observable symptoms:
- **Egg smell** → Hydrogen Sulphide (H₂S) — common in deep Deccan Plateau borewells
- **Yellow/brown water** → Iron — widespread in Hyderabad's western corridor
- **White deposits on taps** → High TDS — linked to kidney stone formation
- **Black water** → Manganese or sewage contamination — requires immediate action

Residents notice these signals daily. But they have no framework to interpret them, no platform to report them, and no way to know if their neighbours are experiencing the same problem. Individual observations never become community intelligence. Individual complaints never trigger civic action.

**WaterSentinel changes that.**

### The Data Gap

Current government monitoring is structurally inadequate:
- **CPCB** monitors ~4,000 water stations nationally — one per 330,000 people
- **HMWSSB** (Hyderabad) monitors treatment plant output, not tap delivery
- **Jal Jeevan Mission** dashboard relies on self-reported state data, not ground truth
- The last mile — from distribution network to citizen's tap — is **officially unmonitored**

### Why Now

Three forces converge in 2026:
1. **Policy gap**: Jal Jeevan Mission is behind schedule and needs last-mile monitoring
2. **Behaviour shift**: Post-COVID health consciousness has normalised "checking"
3. **Technology unlock**: Google ADK makes a 5-agent diagnostic system buildable solo in 10 days

---

## 2. Why Agents — Not Just Google

When a resident searches "water smells like eggs India" on Google, they get 10 generic articles. None of them know:

- Whether the water came from a 400-foot borewell in Deccan Plateau geology or a municipal pipeline
- Whether the BIS IS 10500 limit for H₂S is 0.05 mg/L and whether their symptoms suggest they exceed it
- Whether three of their neighbours reported the same smell this week
- That the correct body to complain to is HMWSSB's Distribution-II office, not the general helpline
- What a formatted complaint to that specific office should contain

**The agent knows all of this simultaneously.** It holds source type context, the BIS knowledge base, community report history, and authority contact data — and reasons across all of them to produce a decision specific to one resident's situation. That is not search. That is intelligence.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CITIZEN (Mobile App)                          │
│         Symptom description · Photo · Pincode                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ POST /report
┌──────────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend                                │
│              Rate limiting · Input sanitisation · CORS           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              Agent 0 — ORCHESTRATOR (Root LlmAgent)              │
│         Routes · Shared session state · Assembles response       │
└──┬──────────────┬──────────────┬──────────────┬─────────────────┘
   │              │              │              │
   ▼              ▼              ▼              ▼
┌──────┐    ┌──────────┐  ┌───────────┐  ┌───────────┐
│Agent1│    │ Agent 2  │  │  Agent 3  │  │  Agent 4  │
│Source│    │  Water   │  │Community  │  │  Action   │
│Sense │    │Profiler  │  │  Mapper   │  │  Forge    │
│      │    │  (RAG)   │  │  (MCP 1) │  │  (MCP 2) │
└──────┘    └────┬─────┘  └─────┬─────┘  └─────┬─────┘
                 │              │              │
                 ▼              ▼              ▼
          ┌──────────┐  ┌──────────┐  ┌──────────────┐
          │   RAG    │  │  MCP 1   │  │    MCP 2     │
          │Knowledge │  │WaterIntel│  │ActionBridge  │
          │   Base   │  │  Store   │  │              │
          │BIS·WHO·  │  │(SQLite)  │  │(Complaints)  │
          │  CGWB    │  └──────────┘  └──────────────┘
          └──────────┘
                 │              │              │
                 └──────────────┴──────────────┘
                                │
┌──────────────────────────────▼──────────────────────────────────┐
│                         OUTPUTS                                  │
│  Personal Advisory │ Topology Map Update │ Municipal Complaint   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. Citizen submits report via mobile app
2. **SourceSense** classifies source type (borewell/municipal/hand pump/open well) and standardises symptoms
3. **WaterProfiler** retrieves relevant chunks from BIS/WHO/CGWB knowledge base via RAG, diagnoses contaminants, calculates quality score (0–100)
4. **CommunityMapper** submits report to WaterIntel MCP Store, checks for cluster (≥3 reports, same pincode, 7 days), updates topology map — **Antigravity moment fires here**
5. **ActionForge** generates personal advisory via treatment tool, calls ActionBridge MCP for municipal complaint if cluster detected, returns map data point
6. FastAPI assembles structured response and returns to mobile app

---

## 4. Agent Descriptions

### Agent 0 — Orchestrator
**Type:** ADK LlmAgent (root/parent)
**Model:** gemini-2.0-flash

The traffic controller. Receives every incoming report from the FastAPI layer. Routes sequentially through SourceSense → WaterProfiler → CommunityMapper → ActionForge using ADK's parent-child sub-agent pattern. Maintains shared session state across the pipeline so each agent can read the previous agent's output without repeated API calls.

**Inputs:** Raw citizen message, pincode, area name, source type, symptoms, optional photo
**Outputs:** Assembled final response combining all sub-agent outputs

---

### Agent 1 — SourceSense
**Type:** ADK LlmAgent (sub-agent)
**Model:** gemini-2.0-flash

Intake and classification specialist. Identifies which of the four Indian water source types the citizen is using — because the same symptom means different things from a 400-foot borewell versus a municipal storage tank. Optionally analyses uploaded photos using Gemini Vision. EXIF data (including GPS) is stripped before processing.

**Inputs:** Natural language description of water issue
**Outputs:** `source_classification` → session state
```json
{
  "source_type": "borewell",
  "symptoms_standardised": ["egg_smell", "yellow_colour"],
  "severity": "medium",
  "duration_days": 5,
  "photo_analysis": "yellowish tint, iron staining likely"
}
```

---

### Agent 2 — WaterProfiler *(RAG-powered)*
**Type:** ADK LlmAgent (sub-agent) with RAG tool
**Model:** gemini-2.0-flash

Diagnosis specialist. Before reasoning, retrieves the 3 most relevant chunks from the BIS/WHO/CGWB knowledge base using semantic search. Diagnoses contaminants based on retrieved evidence — not hallucination. Always cites the specific BIS standard when stating a limit (e.g. "BIS IS 10500:2012 limit for iron is 0.3 mg/L"). Makes the critical `safe_for_drinking` vs `safe_for_bathing` distinction — H₂S water is safe to bathe in but not drink, which prevents unnecessary alarm.

**Inputs:** `source_classification` from session state
**Outputs:** `water_profile` → session state
```json
{
  "contaminants": [{"name": "H2S", "confidence": 0.95, "bis_limit": "0.05 mg/L", "bis_reference": "BIS IS 10500:2012"}],
  "quality_score": 32,
  "colour_band": "red",
  "safe_for_drinking": false,
  "safe_for_bathing": true,
  "rag_citations": ["BIS IS 10500:2012", "CGWB Telangana 2023"]
}
```

---

### Agent 3 — CommunityMapper *(MCP-connected)*
**Type:** ADK LlmAgent (sub-agent) with MCPToolset
**Model:** gemini-2.0-flash

Community intelligence specialist. Connects to WaterIntel Store MCP server via ADK's `MCPToolset` with `StdioServerParameters`. Submits the current report, then checks if ≥3 matching reports exist in the same pincode within 7 days. When the cluster threshold is crossed, it automatically generates the community alert — **this is the Antigravity moment**. Also updates the topology map score that feeds the Leaflet heatmap.

**Inputs:** `source_classification` + `water_profile` from session state
**Outputs:** `community_status` → session state
```json
{
  "cluster_detected": true,
  "cluster_count": 4,
  "community_alert": "3 other households in Nallagandla reported egg smell this week. This appears to be a community supply issue — not just your home.",
  "escalation_required": true,
  "topology_updated": true
}
```

---

### Agent 4 — ActionForge *(MCP-connected)*
**Type:** ADK LlmAgent (sub-agent) with MCPToolset
**Model:** gemini-2.0-flash

Output generation specialist. The final agent. Generates three parallel outputs: a personal advisory with source-specific treatment recommendations and cost estimates; a formatted municipal complaint via ActionBridge MCP (if cluster escalation required); and a structured map data point for the topology update. Knows not to recommend UV filters for iron contamination. Knows not to recommend boiling for TDS or fluoride.

**Inputs:** Full session state (all three previous agent outputs)
**Outputs:** `action_output` → session state (final citizen response)

---

## 5. MCP Servers

### MCP Server 1 — WaterIntel Store
**File:** `mcp_servers/water_intel_store.py`
**Framework:** fastmcp
**Transport:** stdio (ADK launches as subprocess)
**Database:** SQLite at `data/reports.db`

The community intelligence database. Every citizen report flows through this server. The topology map is built entirely from data in this server.

| Tool | Purpose |
|---|---|
| `submit_report()` | Save citizen report, auto-update topology scores |
| `get_pincode_profile()` | Aggregate quality data for one pincode |
| `get_cluster_status()` | **Antigravity trigger** — count matching reports in time window |
| `get_area_history()` | Time-series quality data for trend charts |
| `update_topology_score()` | Update map colour layer for a pincode |
| `get_all_topology_data()` | Serve all pincode scores to the Leaflet heatmap |

### MCP Server 2 — ActionBridge
**File:** `mcp_servers/action_bridge.py`
**Framework:** fastmcp
**Transport:** stdio
**Storage:** Append-only escalation log at `data/escalations.log`

Stateless civic action generation. Separated from WaterIntel Store by design — data intelligence and civic action are distinct responsibilities that should be independently maintainable.

| Tool | Purpose |
|---|---|
| `generate_municipal_complaint()` | Gemini-formatted complaint letter with authority details |
| `get_authority_contact()` | Routes to correct HMWSSB/VWSS/GHMC by pincode + source type |
| `generate_rti_draft()` | RTI application if complaint unresolved >30 days |
| `log_escalation()` | Append-only audit trail of all civic escalations |

---

## 6. RAG Knowledge Base

**Vector store:** ChromaDB (local persistent)
**Embeddings:** Google text-embedding-004
**Retrieval:** Top-3 chunks by cosine similarity
**Task type:** RETRIEVAL_QUERY for queries, RETRIEVAL_DOCUMENT for ingestion

### Documents

| File | Content | Source |
|---|---|---|
| `bis_is10500_2012.md` | All BIS drinking water parameters with limits, health impacts, treatment | Bureau of Indian Standards |
| `who_guidelines_2022.md` | WHO health-based targets, comparison with BIS | WHO 4th Edition 2022 |
| `cgwb_telangana_2023.md` | Hyderabad pincode-level contamination data, Deccan Plateau geology | CGWB South Eastern Region |
| `cgwb_ap_2023.md` | Vijayawada, Guntur, Godavari delta water quality data | CGWB South Eastern Region |
| `symptom_contaminant_map.md` | Custom: maps observable symptoms to contaminants with confidence levels | Authored — field research |
| `india_water_sources_guide.md` | Custom: borewell/municipal/hand pump/open well guide, HMWSSB contacts | Authored — field research |
| `treatment_recommendations.md` | Custom: filter types, costs, what works for what contaminant | Authored — India market prices |

### Why RAG Instead of a Prompt

Without RAG, WaterProfiler relies on general LLM knowledge which may be inaccurate for specific BIS limits. With RAG, the agent retrieves the exact BIS IS 10500:2012 entry for the relevant parameter and cites it in the output. A judge reading the response can verify the citation. The diagnosis is grounded, not hallucinated.

---

## 7. Competition Criteria Coverage

| Criterion | How Demonstrated | Where |
|---|---|---|
| **Multi-agent system (ADK)** | 5 agents: Orchestrator + 4 specialists with session state handoff | `agents/` |
| **MCP Server** | 2 MCP servers: WaterIntel Store (6 tools) + ActionBridge (4 tools) | `mcp_servers/` |
| **RAG** | WaterProfiler retrieves BIS/WHO/CGWB chunks before diagnosis | `rag/`, `agents/water_profiler/` |
| **Antigravity** | Cluster auto-detection fires without citizen prompting — live demo in video | `agents/community_mapper/` |
| **Security** | Pincode-only storage, EXIF stripping, anonymous reporting, rate limiting, input sanitisation | `api/`, `agents/source_sense/` |
| **Deployability** | FastAPI on Google Cloud Run, Expo mobile app, live URL | `Dockerfile`, Cloud Run |
| **Agent Skills** | Symptom classification skill (SourceSense), complaint generation skill (ActionForge) | `agents/` |

**Required: 3 concepts. Demonstrated: 7.**

---

## 8. Setup Instructions (Windows)

### Prerequisites
- Python 3.12 (already installed)
- Node.js LTS (already installed)
- Google API Key from [aistudio.google.com](https://aistudio.google.com)

### Step 1 — Clone and configure

```powershell
# Navigate to project folder
cd C:\Users\YourName\watersentinel

# Copy environment template
copy .env.example .env

# Open .env in Notepad and add your Google API key
notepad .env
```

### Step 2 — Install Python dependencies

```powershell
# Install uv package manager (if not already installed)
pip install uv

# Install all Python dependencies
uv sync
```

### Step 3 — Ingest RAG knowledge base

```powershell
python rag\ingest.py
```

Expected output: `✅ Ingestion complete! Total chunks stored: ~85`

### Step 4 — Seed mock data

```powershell
python scripts\seed_mock_data.py
```

Expected output: `✅ Seeding complete! Reports inserted: 20`

### Step 5 — Verify MCP servers

```powershell
python scripts\test_mcp_servers.py
```

Expected output: `Results: 11/11 tests passed`

### Step 6 — Install mobile app dependencies

```powershell
cd mobile_app
npm install
cd ..
```

---

## 9. Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# Required
GOOGLE_API_KEY=AIzaSy...your_key_here

# Optional — defaults work for local development
WATER_INTEL_DB_PATH=./data/reports.db
ACTION_BRIDGE_LOG_PATH=./data/escalations.log
CHROMA_DB_PATH=./data/chroma_db
KNOWLEDGE_BASE_PATH=./rag/knowledge_base
API_HOST=0.0.0.0
API_PORT=8000
```

**Never commit `.env` to git.** The `.gitignore` excludes it.

---

## 10. How to Run

### Terminal 1 — FastAPI Backend

```powershell
cd C:\Users\YourName\watersentinel
uvicorn api.main:app --reload --port 8000
```

Verify at: `http://localhost:8000/health` — all components should show `ready`
API docs at: `http://localhost:8000/docs`

### Terminal 2 — Mobile App

```powershell
cd mobile_app
npx expo start
```

Scan QR code with **Expo Go** app on Android or iOS.

**Note for physical device:** Update `API_BASE_URL` in `mobile_app/src/api/watersentinel.ts`:
```typescript
// Replace localhost with your machine's local IP
const API_BASE_URL = 'http://192.168.1.XXX:8000';

// OR use ngrok for HTTPS:
// ngrok http 8000
// const API_BASE_URL = 'https://abc123.ngrok.io';
```

### Test the full pipeline

```powershell
python scripts\test_agents.py
```

---

## 11. How to Run the Demo

This sequence reproduces the **Antigravity moment** for the video recording.

**Prerequisites:** Backend running, mobile app open, seed data already loaded (pincode 500032 has 4 pre-seeded reports).

**Step 1:** Open the mobile app. Tap the **Report** tab.

**Step 2:** Select source type: **Borewell** (⛏️)

**Step 3:** Select symptoms: **Egg / Sulphur Smell** + **Yellow / Brown Water**

**Step 4:** In description field type:
> *"My water smells like rotten eggs and the taps have yellowish stains. My family is worried."*

**Step 5:** Enter pincode: `500032` and area: `BHEL MIG Colony`

**Step 6:** Tap **Analyse My Water**. Wait 30–60 seconds.

**Step 7 (Antigravity):** The result screen shows the community alert banner:
> *"3 other households in Nallagandla reported similar symptoms this week. This appears to be a community supply issue — not just your home."*

**Step 8:** Tap **View on Map**. The map shows the 500032 cluster as a red zone.

**Step 9:** Show the generated complaint draft. The complaint is addressed to HMWSSB with BIS IS 10500:2012 citations and ready to submit.

**That is the complete demo arc: individual complaint → community intelligence → civic action.**

---

## 12. Deployment (Google Cloud Run)

### Build and deploy

```powershell
# Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Deploy to Cloud Run (free tier — asia-south1 region)
gcloud run deploy watersentinel `
  --source . `
  --region asia-south1 `
  --allow-unauthenticated `
  --set-env-vars GOOGLE_API_KEY=$env:GOOGLE_API_KEY `
  --memory 2Gi `
  --timeout 120
```

Live URL format: `https://watersentinel-xxxxx-el.a.run.app`

Update `API_BASE_URL` in `mobile_app/src/api/watersentinel.ts` to the Cloud Run URL.

### Dockerfile

Included at project root. Uses Python 3.12 slim, installs via uv, exposes port 8080 (Cloud Run standard).

---

## 13. Security Features

| Feature | Implementation | File |
|---|---|---|
| No PII storage | Location stored as pincode only — never street address or GPS | `mcp_servers/water_intel_store.py` |
| EXIF stripping | Photos processed in memory via Gemini Vision, no EXIF retained | `agents/source_sense/agent.py` |
| Anonymous reporting | No user accounts, no login, no cookies, no device ID | `api/routers/report.py` |
| No API keys in code | All secrets via environment variables only | `.env.example`, `.gitignore` |
| Input sanitisation | HTML tag stripping, length limits, pincode format validation | `api/routers/report.py` |
| Rate limiting | 10 requests per IP per minute on `/report` endpoint | `api/main.py` (slowapi) |
| Fallback response | Agent pipeline failure returns safe advisory, never exposes errors | `api/routers/report.py` |

---

## 14. Future Roadmap

### V1.5 (3 months)
- Telugu and Hindi language input via Gemini's multilingual capability
- WhatsApp bot integration (Meta Business API)
- Lab referral integration with NABL-certified labs in Hyderabad
- RWA dashboard web view

### V2 (6–12 months)
- Live HMWSSB complaint API integration (government partnership)
- Seasonal water quality alerting (pre/post-monsoon advisories)
- Soil type and Deccan Plateau geology correlation layer
- RTI tracking — auto follow-up if complaint unresolved in 30 days

### V3 (12–24 months)
- Expand to 3 cities: Hyderabad, Vijayawada, Bangalore
- CPCB monitoring station data as a baseline layer
- IoT sensor integration API for hardware-capable communities
- Open data API for researchers and urban planners

### Long-term vision
Government absorption as infrastructure by CPCB or Jal Jeevan Mission — becoming the citizen-monitoring layer for India's national water quality programme.

---

## 15. Acknowledgements

**Standards and Data:**
- Bureau of Indian Standards — IS 10500:2012 Drinking Water Specification
- World Health Organization — Guidelines for Drinking-water Quality, 4th Edition (2022)
- Central Ground Water Board — Groundwater Quality Reports, Telangana and Andhra Pradesh (2023)
- CPCB — Water Quality Status of Indian Rivers (2024)

**Technology:**
- Google ADK (Agent Development Kit) — multi-agent framework
- Google Gemini 2.0 Flash — LLM for all agents
- Google text-embedding-004 — RAG embeddings
- fastmcp — MCP server framework
- ChromaDB — local vector store
- FastAPI — backend API framework
- React Native + Expo — mobile app
- Leaflet.js + OpenStreetMap — free mapping (© OpenStreetMap contributors)
- leaflet.heat — heatmap plugin

**Competition:**
Submitted to Kaggle AI Agents Intensive Capstone 2026 — Agents for Good Track.
Built solo by Abhilash Battu in 10 days.

---

*WaterSentinel v1.0 — June 2026*
*"Built not by sensors, but by citizens who already know what their water looks, smells, and tastes like."*
