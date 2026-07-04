# WaterSentinel — Technical Specification
**Version:** 1.0 | **Date:** June 27, 2026 | **Track:** Kaggle Agents for Good
**Author:** Abhilash Battu | **Stack:** Google ADK + Python + FastAPI + React Native

---

## 1. Project Overview

WaterSentinel is a citizen-powered water quality intelligence system for Indian cities. Citizens report water symptoms (smell, colour, taste) via a mobile app. Five ADK agents analyse reports, diagnose contaminants against BIS/WHO standards via RAG, detect community clusters, and generate automated municipal complaints. A topology map visualises water quality hotspots by pincode.

---

## 2. Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| Agent Framework | Google ADK (Python) | Competition requirement, Gemini-native |
| Language | Python 3.12 | ADK requirement |
| Package Manager | uv | Google-recommended for ADK projects |
| MCP Framework | fastmcp | Lightweight Python MCP server builder |
| RAG Vector Store | ChromaDB | Free, local, no API key required |
| RAG Embeddings | Google text-embedding-004 | Free via Gemini API |
| API Server | FastAPI + ADK get_fast_api_app | Exposes agents as REST endpoints |
| Mobile App | React Native (Expo) | JS/TS stack, Expo simplifies build |
| Map Library | Leaflet.js + OpenStreetMap | 100% free, no API key needed |
| Heatmap Plugin | Leaflet.heat | Free heatmap overlay |
| Geocoding | Nominatim (OSM) | Free, no API key |
| Database | SQLite (dev) → PostgreSQL (prod) | Zero-cost local dev |
| Deployment | Google Cloud Run (free tier) | Competition deployability requirement |
| Auth | None (anonymous reporting) | Privacy-by-design, faster to build |

---

## 3. Agent Architecture

### 3.1 Agent 0 — Orchestrator (Root Agent)

**Type:** ADK LlmAgent (parent/root)
**Model:** gemini-2.0-flash
**Role:** Traffic controller. Receives all incoming requests from the API layer. Decides which sub-agent to invoke based on request type. Maintains shared session state across the pipeline.

**Input:**
```json
{
  "request_type": "report | query | map_data",
  "user_message": "string",
  "session_id": "string",
  "location": { "pincode": "500032", "area_name": "Nallagandla" }
}
```

**Output:** Assembled final response from sub-agents via shared session state.

**ADK Pattern:** Parent agent with sub-agents registered. Uses `transfer_to_agent()` for handoffs.

---

### 3.2 Agent 1 — SourceSense

**Type:** ADK LlmAgent (sub-agent)
**Model:** gemini-2.0-flash
**Role:** Intake and classification. Identifies water source type. Collects structured symptom data from the citizen's natural language description.

**Input:** Raw user message + location
**Output (to session state):**
```json
{
  "source_type": "borewell | municipal_pipeline | hand_pump | open_well",
  "depth_feet": 300,
  "symptoms": ["egg_smell", "yellow_colour", "white_deposits"],
  "severity_self_reported": "high | medium | low",
  "photo_attached": true,
  "photo_analysis": "yellowish tint observed, iron staining likely"
}
```

**Key Questions SourceSense asks:**
1. What is your water source? (borewell / municipal pipeline / hand pump / open well)
2. What symptoms do you notice? (smell, colour, taste, appearance)
3. Is it only when water is first turned on, or persistent?
4. How long have you noticed this?
5. Would you like to upload a photo?

---

### 3.3 Agent 2 — WaterProfiler (RAG-powered)

**Type:** ADK LlmAgent (sub-agent) with RAG tool
**Model:** gemini-2.0-flash
**Role:** Diagnosis. Maps symptoms to contaminants using RAG retrieval over the BIS/WHO/CGWB knowledge base. Generates a structured water quality score.

**RAG Tool:** `query_knowledge_base(symptoms, source_type, location_context)`

**Input (from session state):** SourceSense output
**Output (to session state):**
```json
{
  "contaminants": [
    {
      "name": "Hydrogen Sulphide (H2S)",
      "confidence": 0.92,
      "bis_limit": "0.05 mg/L",
      "bis_reference": "BIS IS 10500:2012 Table 1",
      "health_risk": "Safe for bathing, unsafe for drinking above limit",
      "source_correlation": "Common in borewells >300ft in Deccan Plateau geology"
    }
  ],
  "quality_score": 34,
  "quality_band": "Poor",
  "tds_estimate": "high | medium | low | unknown",
  "safe_for_drinking": false,
  "safe_for_bathing": true,
  "rag_citations": ["BIS IS 10500:2012", "CGWB Telangana 2023"]
}
```

**Quality Score Calculation (0–100):**
- 80–100: Safe (green)
- 60–79: Acceptable with monitoring (yellow)
- 40–59: Caution — treatment recommended (orange)
- 0–39: Poor — do not drink (red)

---

### 3.4 Agent 3 — CommunityMapper

**Type:** ADK LlmAgent (sub-agent) with MCP tools
**Model:** gemini-2.0-flash
**Role:** Community intelligence. Reads existing reports from WaterIntel MCP store. Detects clusters. Determines if report is isolated (personal plumbing issue) or community pattern (supply/source problem). Triggers escalation flag.

**MCP Tools Used:** WaterIntel Store — `get_cluster_status`, `get_pincode_profile`, `submit_report`, `update_topology_score`

**Cluster Threshold:** ≥3 reports with same contaminant type within same pincode within 7 days = cluster detected.

**Input (from session state):** WaterProfiler output + location
**Output (to session state):**
```json
{
  "is_cluster": true,
  "cluster_count": 4,
  "cluster_radius": "same_pincode",
  "cluster_contaminants": ["H2S", "Iron"],
  "isolation_verdict": "Community supply issue — not internal plumbing",
  "escalation_required": true,
  "topology_update": {
    "pincode": "500032",
    "new_score": 34,
    "colour_band": "red"
  },
  "antigravity_moment": "3 other households in Nallagandla reported egg smell this week"
}
```

---

### 3.5 Agent 4 — ActionForge

**Type:** ADK LlmAgent (sub-agent) with MCP tools
**Model:** gemini-2.0-flash
**Role:** Output generation. Produces three parallel outputs: personal advisory, map data update, and (if cluster) municipal complaint draft.

**MCP Tools Used:** ActionBridge — `generate_municipal_complaint`, `get_authority_contact`, `generate_rti_draft`, `log_escalation`

**Decision Logic:**

| Source Type | Cluster? | Severity | Output |
|---|---|---|---|
| Borewell | N/A | Any | Personal advisory + filter recommendation |
| Municipal | No | Low/Medium | Personal advisory + boil water notice |
| Municipal | Yes | Any | Personal advisory + municipal complaint draft |
| Hand pump | Yes | High | Community alert + Panchayat escalation |
| Any | Yes | High | RTI draft if complaint unresolved >30 days |

**Output (final response):**
```json
{
  "personal_advisory": {
    "immediate_actions": ["Do not drink without boiling", "Use UV filter"],
    "long_term_actions": ["Get water tested at certified lab", "Install iron removal filter"],
    "nearest_test_lab": "Sri Sai Water Testing Lab, Kondapur — 2.3km",
    "bis_safe_limit_reference": "Iron: 0.3 mg/L (BIS IS 10500)"
  },
  "community_alert": "4 households in your area reported similar symptoms this week",
  "municipal_complaint": {
    "authority": "HMWSSB — Hyderabad Metropolitan Water Supply",
    "complaint_text": "[Full formatted complaint]",
    "reference_standards": "BIS IS 10500:2012",
    "follow_up": "If unresolved in 30 days, RTI draft available"
  },
  "map_data_point": {
    "pincode": "500032",
    "lat": 17.4532,
    "lng": 78.3241,
    "quality_score": 34,
    "colour": "red",
    "report_count": 4,
    "primary_contaminant": "H2S + Iron"
  }
}
```

---

## 4. MCP Servers

### 4.1 MCP Server 1 — WaterIntel Store

**File:** `mcp_servers/water_intel_store.py`
**Framework:** fastmcp
**Transport:** stdio (local) / HTTP (deployed)
**Database:** SQLite (reports.db)

**Tools Exposed:**

```python
@mcp.tool()
async def submit_report(
    pincode: str,
    area_name: str,
    source_type: str,
    quality_score: int,
    contaminants: list[str],
    symptoms: list[str],
    lat: float,
    lng: float,
    timestamp: str
) -> dict: ...

@mcp.tool()
async def get_pincode_profile(pincode: str) -> dict: ...
# Returns: avg_score, report_count, common_contaminants, last_updated

@mcp.tool()
async def get_cluster_status(pincode: str, radius_km: float = 1.0, days: int = 7) -> dict: ...
# Returns: is_cluster, count, contaminants, earliest_report

@mcp.tool()
async def get_area_history(pincode: str, days: int = 30) -> list[dict]: ...
# Returns: time-series of quality scores for trend chart

@mcp.tool()
async def update_topology_score(pincode: str, new_score: int, colour_band: str) -> dict: ...
# Updates the map layer data

@mcp.tool()
async def get_all_topology_data() -> list[dict]: ...
# Returns all pincode scores for map rendering
```

---

### 4.2 MCP Server 2 — ActionBridge

**File:** `mcp_servers/action_bridge.py`
**Framework:** fastmcp
**Transport:** stdio (local) / HTTP (deployed)

**Tools Exposed:**

```python
@mcp.tool()
async def generate_municipal_complaint(
    area: str,
    pincode: str,
    contaminants: list[str],
    affected_count: int,
    source_type: str,
    bis_references: list[str]
) -> dict: ...
# Returns: complaint_text, authority_name, authority_email, complaint_ref_id

@mcp.tool()
async def get_authority_contact(pincode: str, source_type: str) -> dict: ...
# Returns: authority_name, email, phone, portal_url
# Logic: Municipal pipeline → HMWSSB/VWSS. Hand pump → Panchayat. Borewell → CGWB helpline.

@mcp.tool()
async def generate_rti_draft(
    complaint_ref: str,
    complaint_date: str,
    days_elapsed: int
) -> dict: ...
# Returns: rti_text, filing_authority, submission_instructions

@mcp.tool()
async def log_escalation(
    pincode: str,
    severity: str,
    contaminants: list[str],
    timestamp: str
) -> dict: ...
# Returns: escalation_id, logged status
```

---

## 5. RAG Knowledge Base

### 5.1 Document Corpus (~5–7 files)

| File | Format | Content | Source |
|---|---|---|---|
| `bis_is10500_2012.md` | Markdown | BIS drinking water standards — all parameters, limits, and test methods | BIS IS 10500:2012 (public) |
| `who_guidelines_2022.md` | Markdown | WHO drinking water quality guidelines — health-based values | WHO 2022 (public) |
| `cgwb_telangana_2023.md` | Markdown | CGWB groundwater quality data for Telangana — iron, fluoride, TDS hotspots | CGWB portal (public) |
| `cgwb_ap_2023.md` | Markdown | CGWB groundwater quality data for Andhra Pradesh | CGWB portal (public) |
| `symptom_contaminant_map.md` | Markdown | Custom authored — maps odour/colour/taste symptoms to likely contaminants, Indian-specific | Authored by AB |
| `india_water_sources_guide.md` | Markdown | Borewell geology, municipal supply patterns, hand pump maintenance — Indian urban/peri-urban | Authored by AB |
| `treatment_recommendations.md` | Markdown | Filter types (UV, RO, iron removal), cost ranges, when to use each | Authored by AB |

### 5.2 RAG Pipeline

```
Documents (MD files)
      ↓
Chunking (chunk_size=500, overlap=50)
      ↓
Embeddings (Google text-embedding-004)
      ↓
ChromaDB vector store (local persistent)
      ↓
WaterProfiler agent → query_knowledge_base() tool
      ↓
Top-3 relevant chunks retrieved
      ↓
Gemini reasons over chunks + generates diagnosis with citations
```

**ChromaDB Collection:** `water_quality_knowledge`
**Embedding Model:** `models/text-embedding-004` (free via Gemini API)
**Retrieval:** Top-3 chunks by cosine similarity
**Ingestion Script:** `rag/ingest.py` — run once before demo

---

## 6. Mock Strategy (No Paid APIs)

### 6.1 Map — Leaflet.js + OpenStreetMap (100% Free)

**No API key required.** Use OpenStreetMap tile server directly.

```javascript
// React Native: react-native-leaflet or WebView with Leaflet HTML
// Web app: react-leaflet

const map = L.map('map').setView([17.3850, 78.4867], 11); // Hyderabad centre

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Heatmap layer (leaflet.heat plugin — free)
const heatData = [
  [17.4532, 78.3241, 0.9],  // Nallagandla — red
  [17.4400, 78.3600, 0.6],  // Ramachandrapuram — orange
  [17.4900, 78.3900, 0.2],  // Kondapur — green
];
L.heatLayer(heatData, { radius: 25, blur: 15 }).addTo(map);
```

### 6.2 Pre-Seeded Mock Data (For Demo)

Seed 20 mock reports across real Hyderabad pincodes BEFORE recording the demo video. This guarantees:
- The topology map shows a credible heatmap immediately
- The Antigravity moment fires reliably (3+ reports in Nallagandla pincode)

**Mock Pincodes to Seed:**

| Area | Pincode | Lat | Lng | Score | Contaminant | Source |
|---|---|---|---|---|---|---|
| Nallagandla | 500032 | 17.4532 | 78.3241 | 32 | H2S + Iron | Borewell |
| Ramachandrapuram | 500055 | 17.4400 | 78.3600 | 48 | High TDS | Municipal |
| BHEL MIG | 500032 | 17.4620 | 78.3150 | 28 | Iron | Borewell |
| BHEL LIG | 500032 | 17.4580 | 78.3200 | 35 | H2S | Borewell |
| Kondapur | 500084 | 17.4900 | 78.3900 | 71 | Low TDS | Borewell |
| Madhapur | 500081 | 17.4479 | 78.3882 | 65 | Acceptable | Municipal |
| Gachibowli | 500032 | 17.4401 | 78.3489 | 44 | Fluoride trace | Borewell |
| Miyapur | 500049 | 17.4960 | 78.3549 | 55 | Iron | Municipal |

**Seeding Script:** `scripts/seed_mock_data.py`

### 6.3 Municipal API — Mock (No Live API Exists)

HMWSSB does not have a public complaints API. Mock it with:

```python
# action_bridge.py
async def generate_municipal_complaint(...):
    # Generate complaint text using Gemini
    # Return formatted complaint — no actual API call
    return {
        "authority": "HMWSSB — O/o Executive Engineer, Distribution-II",
        "email": "complaints@hmwssb.gov.in",  # Real email
        "complaint_text": generated_text,
        "status": "DRAFT — Copy and submit at hmwssb.telangana.gov.in/complaints"
    }
```

Be transparent in the README and video: *"Municipal complaint integration is mocked — the agent generates a formatted complaint ready to submit. Live API integration would be built in partnership with HMWSSB."*

### 6.4 Photo Analysis — Gemini Vision (Free Tier)

```python
# In SourceSense agent tool
import google.generativeai as genai

def analyse_water_photo(image_base64: str) -> str:
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content([
        "Analyse this water sample photo. Describe colour, clarity, visible particles, staining. Be specific.",
        {"mime_type": "image/jpeg", "data": image_base64}
    ])
    return response.text
```

---

## 7. Mobile App

### 7.1 Technology Decision

**React Native with Expo** — Final Answer

**Why not Flutter:**
- You don't know Dart. React Native uses JavaScript/TypeScript.
- Gemini CLI and Cursor work better with JS/TS codebases.
- Expo simplifies build — no Android Studio or Xcode required for demo.
- react-leaflet and WebView integration for maps is well-documented.

**Why not web-only:**
- Competition judges expect "deployability" — a mobile app URL on Expo Go is more impressive than a localhost demo.
- Photo capture from device camera requires mobile.
- Maps look better on mobile for the video demo.

### 7.2 App Screens

**Screen 1 — Report (Home)**
- Source type selector (4 icons: Borewell, Municipal, Hand pump, Open well)
- Symptom multi-select (Egg smell, Yellow colour, White deposits, Metallic taste, Black water, No issue)
- Free text description field
- Camera/photo upload button
- Pincode auto-detect or manual entry
- Submit button → triggers agent pipeline

**Screen 2 — My Report Result**
- Contaminant diagnosis with BIS citation
- Quality score gauge (0–100, colour-coded)
- Immediate action advisory
- If cluster detected: "4 neighbours reported same issue" banner
- Generated complaint (copy to clipboard)

**Screen 3 — Community Map**
- Leaflet map (WebView) centred on Hyderabad
- Heatmap overlay (red/orange/green zones)
- Tap pincode cluster → popup with report count + primary contaminant
- Live feed of recent reports (scrollable below map)

**Screen 4 — About / How It Works**
- 3-step explainer: Report → AI Analyses → Community Acts
- Links to BIS standards, WHO guidelines
- Privacy policy (anonymous, pincode-only)

---

## 8. Folder Structure

```
watersentinel/
│
├── README.md                          # Competition submission README
├── pyproject.toml                     # uv project config
├── .env.example                       # Environment variable template
├── requirements.txt                   # pip fallback
│
├── agents/                            # All ADK agent definitions
│   ├── __init__.py
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── agent.py                   # Root orchestrator agent
│   ├── source_sense/
│   │   ├── __init__.py
│   │   └── agent.py                   # SourceSense sub-agent
│   ├── water_profiler/
│   │   ├── __init__.py
│   │   ├── agent.py                   # WaterProfiler sub-agent
│   │   └── tools.py                   # RAG query tool
│   ├── community_mapper/
│   │   ├── __init__.py
│   │   └── agent.py                   # CommunityMapper sub-agent
│   └── action_forge/
│       ├── __init__.py
│       └── agent.py                   # ActionForge sub-agent
│
├── mcp_servers/                       # MCP server implementations
│   ├── water_intel_store.py           # MCP Server 1 — data layer
│   └── action_bridge.py              # MCP Server 2 — civic action
│
├── rag/                               # RAG pipeline
│   ├── ingest.py                      # Document ingestion script
│   ├── query.py                       # Retrieval utility
│   └── knowledge_base/               # Source documents
│       ├── bis_is10500_2012.md
│       ├── who_guidelines_2022.md
│       ├── cgwb_telangana_2023.md
│       ├── cgwb_ap_2023.md
│       ├── symptom_contaminant_map.md
│       ├── india_water_sources_guide.md
│       └── treatment_recommendations.md
│
├── api/                               # FastAPI server
│   ├── main.py                        # FastAPI app + ADK integration
│   └── routers/
│       ├── report.py                  # POST /report endpoint
│       ├── map_data.py               # GET /map/topology endpoint
│       └── health.py                 # GET /health
│
├── scripts/                           # Utility scripts
│   ├── seed_mock_data.py              # Seeds 20 mock Hyderabad reports
│   └── test_agents.py                # End-to-end agent pipeline test
│
├── mobile_app/                        # React Native Expo app
│   ├── package.json
│   ├── app.json                       # Expo config
│   ├── App.tsx
│   └── src/
│       ├── screens/
│       │   ├── ReportScreen.tsx
│       │   ├── ResultScreen.tsx
│       │   ├── MapScreen.tsx
│       │   └── AboutScreen.tsx
│       ├── components/
│       │   ├── SourceSelector.tsx
│       │   ├── SymptomPicker.tsx
│       │   ├── QualityGauge.tsx
│       │   └── LeafletMap.tsx         # WebView wrapper for Leaflet
│       ├── api/
│       │   └── watersentinel.ts       # API client
│       └── assets/
│           └── mock_map_data.json     # Fallback mock topology data
│
├── docs/
│   ├── architecture.png               # Architecture diagram (for README)
│   ├── KAGGLE_WRITEUP.md             # Competition writeup
│   └── VIDEO_SCRIPT.md               # 5-minute video script
│
└── Dockerfile                         # For Cloud Run deployment
```

---

## 9. Environment Variables

```bash
# .env (never commit this)
GOOGLE_API_KEY=your_gemini_api_key_here
GOOGLE_CLOUD_PROJECT=your_gcp_project_id

# MCP Server config
WATER_INTEL_DB_PATH=./data/reports.db
ACTION_BRIDGE_LOG_PATH=./data/escalations.log

# RAG config
CHROMA_DB_PATH=./data/chroma_db

# API server
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,https://your-expo-app-url
```

---

## 10. Security Features (Scored Criterion)

| Feature | Implementation | Where |
|---|---|---|
| No PII stored | Location stored as pincode only — never street address or GPS coordinates | WaterIntel MCP Store |
| EXIF stripping | Photos stripped of GPS EXIF data before storage | SourceSense tool |
| Anonymous reporting | No user accounts, no phone number, no login required | App design |
| No API keys in code | All keys via environment variables | .env.example shows template only |
| Input sanitisation | All user text inputs sanitised before agent processing | API layer |
| Rate limiting | Max 5 reports per pincode per hour (prevents spam flooding) | API middleware |

---

## 11. Deployment (Cloud Run Free Tier)

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
# Deploy to Cloud Run
gcloud run deploy watersentinel \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY
```

**Live URL format:** `https://watersentinel-xxxxx-el.a.run.app`

---

## 12. Day-by-Day Build Plan

| Day | Date | What to Build | Output |
|---|---|---|---|
| 1 | June 28 | MCP Server 1 (WaterIntel Store) — all 5 tools + SQLite schema | `mcp_servers/water_intel_store.py` tested |
| 2 | June 29 | MCP Server 2 (ActionBridge) — all 4 tools + complaint template | `mcp_servers/action_bridge.py` tested |
| 3 | June 30 | RAG pipeline — ingest 7 docs, ChromaDB setup, query tool | `rag/` complete, WaterProfiler tool tested |
| 4 | July 1 | SourceSense + WaterProfiler agents + Orchestrator wiring | Agents 0–2 working end-to-end |
| 5 | July 2 | CommunityMapper + ActionForge agents + full pipeline test | All 5 agents working, Antigravity fires |
| 6 | July 3 | FastAPI server + seed mock data + mobile app skeleton | API live locally, map renders with mock data |
| 7 | July 4 | Mobile app polish (4 screens) + Expo deployment | Expo Go QR code works |
| 8 | July 5 | README.md + architecture diagram + code comments | Documentation complete |
| 9 | July 6 | Video recording (5 min) — follow VIDEO_SCRIPT.md | YouTube link ready |
| 10 | July 7 | Kaggle writeup + thumbnail + final submission | Submitted before 12:29 PM IST |

---

## 13. Gemini Prompts for Building Each Component

Use these as your Gemini CLI / Cursor prompts:

**Day 1 prompt:**
> "Build a fastmcp MCP server in Python called WaterIntelStore. It uses SQLite for storage. Implement these 5 async tools: submit_report, get_pincode_profile, get_cluster_status, get_area_history, update_topology_score, get_all_topology_data. Follow the technical spec: [paste Section 4.1]. Include docstrings. Use uv for dependency management."

**Day 3 prompt:**
> "Build a RAG ingestion pipeline using ChromaDB and Google text-embedding-004. Ingest markdown files from ./rag/knowledge_base/. Chunk at 500 tokens with 50 token overlap. Create a query function that takes symptoms and source_type and returns top-3 relevant chunks with citations. Save the collection as 'water_quality_knowledge'."

**Day 4 prompt:**
> "Build a Google ADK multi-agent system with these agents: Orchestrator (root LlmAgent), SourceSense, WaterProfiler (uses RAG tool), CommunityMapper (uses MCPToolset for WaterIntel MCP server). Follow the spec for each agent's input/output schema in session state. Use gemini-2.0-flash. Include transfer_to_agent patterns per ADK docs."

---

*End of Technical Specification v1.0*
