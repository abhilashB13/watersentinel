# WaterSentinel — Antigravity Mission Briefing
**Version:** 1.0 | **Platform:** Google Antigravity 2.0 Desktop (Windows)  
**Model:** Gemini 3.5 Flash (primary) | Fallback: Claude Sonnet 4.6  
**Mode:** Plan Mode → Agent-Driven Development  
**Author:** Abhilash Battu | **Deadline:** July 7, 2026 12:29 PM IST

---

## OPERATOR INSTRUCTIONS FOR ANTIGRAVITY

Before starting ANY task, switch to **Plan Mode**. Generate a Plan Artifact
for every major component. Do not proceed to execution until the plan is
reviewed and confirmed. This project has a hard deadline — failed builds
waste unrecoverable time.

Use **Agent-Assisted Development** mode (not full autopilot). The operator
will review every Plan Artifact before execution. Run terminal commands
automatically without prompting unless they involve deletion or deployment.

---

## 1. MISSION OVERVIEW

You are building **WaterSentinel** — a citizen-powered water quality
intelligence system for Indian cities — as a solo Kaggle competition
submission under the Agents for Good track.

**What you are building:**
- 5 ADK agents (Python, Google ADK framework)
- 2 MCP servers (Python, fastmcp)
- 1 RAG knowledge base (ChromaDB + Google text-embedding-004)
- 1 FastAPI backend server
- 1 React Native mobile app (Expo) with Leaflet.js map

**The single most important outcome:** A working end-to-end demo where
a citizen submits a water quality report and the system automatically
identifies contamination, detects community clusters, updates a live
topology map, and generates a municipal complaint — all without human
intervention between steps.

---

## 2. ENVIRONMENT CONTEXT

**Operating System:** Windows 11  
**Pre-installed:** Python 3.12, Node.js (latest LTS)  
**Package manager (Python):** uv (install if not present)  
**Package manager (Node):** npm (already available via Node.js)  
**Shell:** PowerShell (use PowerShell syntax for all terminal commands)  
**Google API Key:** Will be provided by operator as environment variable  
**Deployment target:** Google Cloud Run (free tier)

**CRITICAL WINDOWS RULES:**
- Use backslashes OR forward slashes in paths — Python handles both
- Use `$env:VARIABLE_NAME` syntax for environment variables in PowerShell
- Use `python` not `python3` on Windows
- Use `.venv\Scripts\activate` not `source .venv/bin/activate`
- Never use `&&` to chain commands in PowerShell — use `;` instead
- For line continuation in PowerShell use backtick `` ` `` not backslash
- SQLite works natively on Windows — no installation needed
- ChromaDB works on Windows with Python 3.12 — no special setup needed

---

## 3. PROJECT STRUCTURE TO CREATE

Create this exact folder structure at the start. Do not deviate.

```
watersentinel\
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── Dockerfile
│
├── agents\
│   ├── __init__.py
│   ├── orchestrator\
│   │   ├── __init__.py
│   │   └── agent.py
│   ├── source_sense\
│   │   ├── __init__.py
│   │   └── agent.py
│   ├── water_profiler\
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── tools.py
│   ├── community_mapper\
│   │   ├── __init__.py
│   │   └── agent.py
│   └── action_forge\
│       ├── __init__.py
│       └── agent.py
│
├── mcp_servers\
│   ├── water_intel_store.py
│   └── action_bridge.py
│
├── rag\
│   ├── ingest.py
│   ├── query.py
│   └── knowledge_base\
│       ├── bis_is10500_2012.md
│       ├── who_guidelines_2022.md
│       ├── cgwb_telangana_2023.md
│       ├── cgwb_ap_2023.md
│       ├── symptom_contaminant_map.md
│       ├── india_water_sources_guide.md
│       └── treatment_recommendations.md
│
├── api\
│   ├── main.py
│   └── routers\
│       ├── report.py
│       ├── map_data.py
│       └── health.py
│
├── scripts\
│   ├── seed_mock_data.py
│   └── test_agents.py
│
├── data\                          ← created at runtime, not in git
│   ├── reports.db
│   ├── chroma_db\
│   └── escalations.log
│
└── mobile_app\
    ├── package.json
    ├── app.json
    ├── App.tsx
    └── src\
        ├── screens\
        │   ├── ReportScreen.tsx
        │   ├── ResultScreen.tsx
        │   ├── MapScreen.tsx
        │   └── AboutScreen.tsx
        ├── components\
        │   ├── SourceSelector.tsx
        │   ├── SymptomPicker.tsx
        │   ├── QualityGauge.tsx
        │   └── LeafletMap.tsx
        ├── api\
        │   └── watersentinel.ts
        └── assets\
            └── mock_map_data.json
```

---

## 4. BUILD SEQUENCE — STRICTLY IN THIS ORDER

Do not skip steps. Do not build step N+1 until step N is verified working.
Each step ends with a verification test. If the test fails, fix before
proceeding.

### STEP 1 — Project Scaffolding & Dependencies
Create the full folder structure. Create pyproject.toml with all Python
dependencies. Create package.json for mobile app. Create .env.example.
Create .gitignore. Do NOT create data\ folder — it is runtime only.

**Verify:** `uv sync` completes without errors. `npm install` in mobile_app\
completes without errors.

### STEP 2 — RAG Knowledge Base Documents
Create all 7 markdown files in rag\knowledge_base\. See Section 7 for
exact content requirements. Then build rag\ingest.py and run it to populate
ChromaDB. Then build rag\query.py with a test function.

**Verify:** Run `python rag\ingest.py`. Confirm ChromaDB collection created
in data\chroma_db\. Run a test query for "egg smell borewell" and confirm
relevant BIS content is returned.

### STEP 3 — MCP Server 1: WaterIntel Store
Build mcp_servers\water_intel_store.py with all 6 tools. SQLite database
auto-creates at data\reports.db on first run.

**Verify:** Run server standalone. Call submit_report() with a test payload.
Call get_pincode_profile() for that pincode. Confirm data persists.

### STEP 4 — MCP Server 2: ActionBridge
Build mcp_servers\action_bridge.py with all 4 tools. Municipal complaint
generation uses Gemini API to format the complaint text.

**Verify:** Call generate_municipal_complaint() with test data. Confirm
formatted complaint text is returned with correct authority name.

### STEP 5 — ADK Agents
Build all 5 agents in sequence: Orchestrator → SourceSense →
WaterProfiler → CommunityMapper → ActionForge.
Each agent must include detailed docstrings explaining its role,
inputs, outputs, and tool usage. Comments are a judging criterion.

**Verify:** Run scripts\test_agents.py with a test report for
"borewell water with egg smell in Nallagandla, 500032". Confirm
all 5 agents fire in sequence and return a complete response.

### STEP 6 — FastAPI Backend
Build api\main.py integrating ADK via get_fast_api_app(). Build
the three routers. Enable CORS for mobile app access.

**Verify:** Run server with `uvicorn api.main:app --reload --port 8000`.
POST to /report with test payload. GET /map/topology and confirm
data returns. GET /health returns 200.

### STEP 7 — Seed Mock Data
Build and run scripts\seed_mock_data.py to insert 20 mock Hyderabad
data points. This is REQUIRED for the demo — the topology map must
show data immediately without live citizen reports.

**Verify:** GET /map/topology returns exactly 20 data points.
Three data points in pincode 500032 must exist (triggers Antigravity
cluster detection moment in demo).

### STEP 8 — Mobile App
Build all 4 screens in React Native (Expo). LeafletMap.tsx uses
WebView to render Leaflet.js with OpenStreetMap tiles. Pass heatmap
data from /map/topology API via injectedJavaScript.

**Verify:** Run `npx expo start` in mobile_app\. Open on device via
Expo Go app. Confirm all 4 screens render. Confirm map shows
heatmap data from seeded mock points. Confirm report submission
reaches the FastAPI backend.

### STEP 9 — End-to-End Integration Test
Submit a new report from the mobile app for pincode 500032.
Confirm: SourceSense classifies → WaterProfiler diagnoses →
CommunityMapper detects cluster (3+ existing reports) →
ActionForge generates complaint → Map updates → Result screen
shows community alert and complaint draft.

**Verify:** The full loop completes in under 15 seconds. The
cluster alert fires because 3+ seeded reports already exist
for 500032.

### STEP 10 — Documentation
Write README.md with: problem statement, solution overview,
architecture diagram (ASCII or image), setup instructions,
environment variables, how to run each component, deployment
instructions. This is 20 points of the 100-point rubric.

---

## 5. AGENT SPECIFICATIONS

### Agent 0 — Orchestrator (agents\orchestrator\agent.py)

```
Type: ADK LlmAgent (root/parent)
Model: gemini-2.0-flash
Purpose: Root agent. Receives all requests. Routes to sub-agents
via transfer_to_agent(). Assembles final response from session state.

System prompt to embed:
"You are the WaterSentinel Orchestrator. You coordinate a team of
specialist agents to analyse citizen water quality reports for Indian
cities. When you receive a report, route it sequentially through:
1. SourceSense (classify source and symptoms)
2. WaterProfiler (diagnose contaminants via BIS/WHO knowledge base)
3. CommunityMapper (detect community patterns and update topology)
4. ActionForge (generate personal advisory and municipal complaint)
Always maintain context in session state between agent handoffs.
Provide a clear, empathetic final response to the citizen."

Session state keys to maintain:
- source_classification (from SourceSense)
- water_profile (from WaterProfiler)
- community_status (from CommunityMapper)
- action_output (from ActionForge)
```

### Agent 1 — SourceSense (agents\source_sense\agent.py)

```
Type: ADK LlmAgent (sub-agent)
Model: gemini-2.0-flash
Purpose: Intake agent. Collects and classifies water source type
and symptoms from citizen's natural language description.

System prompt to embed:
"You are SourceSense, a water source classification specialist.
Your job is to understand what type of water source the citizen
is using and what symptoms they observe. Ask clarifying questions
if needed. Always determine:
1. Source type: borewell / municipal_pipeline / hand_pump / open_well
2. Symptoms: from [egg_smell, yellow_colour, brown_colour, white_deposits,
   metallic_taste, black_water, blue_green_stain, no_visible_symptom,
   stomach_issues, skin_issues]
3. Severity: high / medium / low (based on symptom combination)
4. Duration: how long the issue has been noticed
5. Photo: whether a photo has been uploaded

Output a structured JSON to session state under 'source_classification'."

Tools to include:
- analyse_photo(image_base64) → uses Gemini Vision to describe water
  colour, clarity, particles from uploaded photo
```

### Agent 2 — WaterProfiler (agents\water_profiler\agent.py)

```
Type: ADK LlmAgent (sub-agent) with RAG tool
Model: gemini-2.0-flash
Purpose: Diagnosis agent. Maps symptoms to contaminants using RAG
retrieval over BIS/WHO/CGWB knowledge base. Generates quality score.

System prompt to embed:
"You are WaterProfiler, a water quality diagnosis specialist trained
on Indian BIS IS 10500 standards and WHO guidelines. Using the symptom
classification provided, retrieve relevant knowledge from the BIS/WHO
knowledge base and diagnose:
1. Likely contaminants with confidence scores
2. Whether each contaminant exceeds BIS limits
3. Health implications specific to Indian context
4. A water quality score from 0-100 (0=severely contaminated, 100=safe)
5. Whether water is safe for drinking vs bathing separately
Always cite the specific BIS standard (e.g. 'BIS IS 10500:2012 Table 1')
when stating a limit. Never guess — only state what the knowledge base
confirms."

RAG tool:
query_knowledge_base(symptoms: list, source_type: str) → returns
top-3 relevant chunks from ChromaDB with source citations

Quality score bands:
80-100: Safe (green) | 60-79: Monitor (yellow) |
40-59: Treat (orange) | 0-39: Do not drink (red)
```

### Agent 3 — CommunityMapper (agents\community_mapper\agent.py)

```
Type: ADK LlmAgent (sub-agent) with MCP tools
Model: gemini-2.0-flash
Purpose: Community intelligence agent. Detects clusters. Determines
if issue is personal plumbing or community supply problem. Triggers
escalation. This is where the ANTIGRAVITY MOMENT lives.

System prompt to embed:
"You are CommunityMapper, a community water intelligence specialist.
Your job is to determine whether a citizen's water problem is isolated
(their own plumbing or borewell) or a community-level supply issue
(affecting multiple households). Use the WaterIntel MCP tools to:
1. Submit the current report to the community database
2. Check if 3+ similar reports exist in the same pincode within 7 days
3. If cluster detected: set escalation_required = true and generate
   a community alert message naming the number of affected households
4. Update the topology map score for this pincode
5. Determine isolation verdict: personal vs community

ANTIGRAVITY TRIGGER: When cluster is detected, your response must
include: 'X other households in [area] reported similar symptoms
this week. This appears to be a community supply issue.'

MCP Tools: submit_report, get_cluster_status, get_pincode_profile,
update_topology_score (all from WaterIntel Store MCP server)"
```

### Agent 4 — ActionForge (agents\action_forge\agent.py)

```
Type: ADK LlmAgent (sub-agent) with MCP tools
Model: gemini-2.0-flash
Purpose: Output generation agent. Produces personal advisory,
municipal complaint draft, and map data point simultaneously.

System prompt to embed:
"You are ActionForge, a water action specialist. Based on the
diagnosis and community analysis, generate three outputs:

1. PERSONAL ADVISORY: Source-specific guidance
   - Borewell: filter type recommendation + nearest testing lab
   - Municipal: boil water notice + complaint guidance
   - Hand pump: community action guidance

2. MUNICIPAL COMPLAINT (if escalation_required = true):
   Generate a formal complaint addressed to the correct authority:
   - Municipal pipeline → HMWSSB (Hyderabad) or VWSS (Vijayawada)
   - Hand pump → Local Panchayat or Ward Office
   - Borewell → CGWB regional office (for advisory only)
   Include: area, pincode, contaminant type, affected count,
   BIS standard reference, date, request for inspection.

3. MAP DATA POINT: Structured data for topology map update
   {pincode, lat, lng, quality_score, colour_band, contaminants,
   report_count, timestamp}

MCP Tools: generate_municipal_complaint, get_authority_contact,
log_escalation (all from ActionBridge MCP server)"
```

---

## 6. MCP SERVER SPECIFICATIONS

### MCP Server 1 — WaterIntel Store

```python
# mcp_servers/water_intel_store.py
# Framework: fastmcp
# Database: SQLite at data/reports.db (auto-create on first run)
# Transport: stdio for local ADK connection

# SQLite schema:
CREATE TABLE IF NOT EXISTS water_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pincode TEXT NOT NULL,
    area_name TEXT,
    source_type TEXT NOT NULL,
    quality_score INTEGER NOT NULL,
    contaminants TEXT,        -- JSON array as string
    symptoms TEXT,            -- JSON array as string
    lat REAL,
    lng REAL,
    is_mock INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS topology_scores (
    pincode TEXT PRIMARY KEY,
    area_name TEXT,
    avg_score REAL,
    report_count INTEGER,
    primary_contaminant TEXT,
    colour_band TEXT,
    lat REAL,
    lng REAL,
    last_updated TEXT
);

# 6 tools to implement:
# submit_report() → inserts into water_reports, updates topology_scores
# get_pincode_profile() → returns aggregate for one pincode
# get_cluster_status() → counts matching reports in time window
# get_area_history() → time series for one pincode
# update_topology_score() → updates topology_scores table
# get_all_topology_data() → returns all rows from topology_scores
```

### MCP Server 2 — ActionBridge

```python
# mcp_servers/action_bridge.py
# Framework: fastmcp
# No database — stateless generation + logging only
# Log file: data/escalations.log

# Authority routing logic (hardcode as dict):
AUTHORITY_MAP = {
    "municipal_pipeline": {
        "500032": {"name": "HMWSSB - Distribution Zone II",
                   "email": "complaints@hmwssb.gov.in",
                   "portal": "hmwssb.telangana.gov.in/complaints"},
        "500049": {"name": "HMWSSB - Distribution Zone III", ...},
        "DEFAULT": {"name": "HMWSSB - Hyderabad Metropolitan Water Supply",
                    "email": "complaints@hmwssb.gov.in",
                    "portal": "hmwssb.telangana.gov.in/complaints"}
    },
    "hand_pump": {
        "DEFAULT": {"name": "GHMC Ward Office",
                    "email": "wardoffice@ghmc.gov.in",
                    "portal": "ghmc.gov.in/grievance"}
    },
    "borewell": {
        "DEFAULT": {"name": "CGWB South Eastern Region",
                    "email": "cgwb-ser@nic.in",
                    "portal": "cgwb.gov.in"}
    }
}

# 4 tools to implement:
# generate_municipal_complaint() → uses Gemini to format complaint text
# get_authority_contact() → looks up AUTHORITY_MAP by pincode+source
# generate_rti_draft() → generates RTI application text via Gemini
# log_escalation() → appends to data/escalations.log
```

---

## 7. RAG KNOWLEDGE BASE — EXACT CONTENT TO CREATE

Create these markdown files with accurate content. These are judging
artifacts — content quality matters.

### bis_is10500_2012.md
Indian drinking water standards. Include these exact parameters with
acceptable limits and remarks:

- TDS: 500 mg/L (acceptable), 2000 mg/L (permissible in absence of alt)
- Iron (Fe): 0.3 mg/L — causes yellow/brown staining, metallic taste
- Fluoride: 1.0 mg/L (acceptable), 1.5 mg/L (permissible)
- Nitrate: 45 mg/L — indicates agricultural runoff or sewage
- Sulphate: 200 mg/L (acceptable), 400 mg/L (permissible)
- Hydrogen Sulphide (H2S): 0.05 mg/L — causes egg smell
- Manganese: 0.1 mg/L — causes black water in high concentrations
- Copper: 0.05 mg/L — causes blue-green staining
- pH: 6.5-8.5 acceptable range
- Turbidity: 1 NTU (acceptable), 5 NTU (permissible)
- Total Coliform: 0 MPN/100ml — indicates sewage contamination
- Hardness (as CaCO3): 200 mg/L (acceptable), 600 mg/L (permissible)
  — causes white scale deposits, linked to kidney stone formation

Include: health implications, detection methods, treatment options
for each parameter. Reference: BIS IS 10500:2012 Second Revision.

### who_guidelines_2022.md
WHO drinking water quality guidelines (4th edition, 2022 update).
Include: health-based targets, guideline values for key parameters,
risk assessment framework, microbial vs chemical risk distinction.
Note where WHO values differ from Indian BIS standards.

### cgwb_telangana_2023.md
Central Ground Water Board — Telangana groundwater quality summary.
Include documented findings:
- Iron contamination above BIS limits in Ranga Reddy and Medak districts
- Fluoride above limits in Nalgonda (historically severe), Khammam
- TDS above acceptable in Hyderabad western corridor (Ranga Reddy)
- Nitrate contamination near agricultural zones (Sangareddy, Warangal)
- Depth correlation: shallower borewells (<150ft) have higher
  bacterial risk; deeper borewells (>300ft) have higher mineral risk
- Deccan Plateau geology: basalt/granite — higher iron and H2S
  in borewells 300-500ft depth (Deccan trap formation)

### cgwb_ap_2023.md
CGWB Andhra Pradesh groundwater quality summary.
Include documented findings:
- Fluoride: severe in Prakasam, Nellore, Kurnool districts
- TDS: above limits in coastal Krishna and Guntur districts
  (saltwater intrusion in low-lying areas near sea)
- Iron: above limits in East and West Godavari (alluvial plains)
- Nitrate: above limits near agricultural zones in Guntur, Prakasam
- Vijayawada specific: Alluvial Krishna delta — high TDS and hardness
  in borewells below 100ft; municipal supply from Krishna river treated

### symptom_contaminant_map.md
CUSTOM AUTHORED — This is the critical document. Map every observable
symptom to likely contaminants with confidence levels:

SMELL-BASED:
- Egg/rotten smell → H2S (high confidence), Sulphur bacteria (medium)
- Chlorine smell → Municipal treatment (normal, not a defect)
- Musty/earthy smell → Algae or organic matter (bacterial risk)
- No smell → Cannot rule out contamination (nitrate, fluoride are odourless)

COLOUR-BASED:
- Yellow/light brown → Iron (high), Manganese (medium)
- Dark brown/black → Manganese (high), Sewage contamination (medium)
- Blue-green tinge → Copper pipe corrosion (high)
- Milky white (clears when standing) → Dissolved air (harmless)
- Milky white (does not clear) → High turbidity, possible contamination
- Greenish → Algae (open well), Copper (pipe)

TASTE-BASED:
- Metallic → Iron (high), Manganese (medium), Copper (low)
- Salty → High TDS, Chloride (coastal areas)
- Bitter → High TDS, Sulphate, possible chemical contamination
- Soapy → High pH, Sodium
- No taste but GI issues → Bacterial/coliform (high risk)

VISUAL (deposits/staining):
- White scale on vessels → High TDS, Calcium hardness
- Yellow/orange pipe staining → Iron (very high confidence)
- Blue-green staining on brass → Copper corrosion
- Black particles → Manganese, rubber pipe degradation
- Red sediment → Iron oxide, clay intrusion

SOURCE-SPECIFIC CORRELATIONS (Indian context):
- Borewell >300ft + egg smell → H2S from anaerobic bacteria or
  hydrogen sulphide in Deccan trap formations
- Municipal storage tank + dark water → Bacterial growth in unclean tank
  (tank not cleaned in >6 months is primary cause)
- Hand pump + yellow water → Iron from ferrous aquifer
- Open well + any colour → High bacterial risk (no treatment)

### india_water_sources_guide.md
CUSTOM AUTHORED:
- Borewell: depth ranges (150-500ft), geology correlation, personal
  ownership model, maintenance requirements, testing frequency
- Municipal pipeline: 1-hour supply pattern, underground tank storage
  (1000-2000L), tank cleaning protocol (every 6 months), contamination
  risk from pressure drop causing sewage back-siphoning
- Hand pump: shared infrastructure, INDIA MARK II standard design,
  20-50ft depth typical, community maintenance model, seasonal
  water table impact
- Open well: <30ft depth, highest contamination risk, monsoon
  flooding contamination, not recommended for drinking without treatment

### treatment_recommendations.md
CUSTOM AUTHORED — Treatment by contaminant type:
- H2S/Egg smell: Aeration + chlorination OR activated carbon filter
  (₹3,000-8,000); safe to use for bathing even without treatment
- Iron (Fe): Iron removal filter (greensand or birm media)
  (₹5,000-15,000); do NOT use UV filter (UV does not remove iron)
- High TDS: RO (Reverse Osmosis) system (₹8,000-25,000);
  note: RO also removes beneficial minerals
- Bacterial/coliform: UV purifier (₹2,500-6,000) + boiling as backup
- Fluoride: RO system only effective option for home treatment
- Manganese: Oxidation filter + manganese greensand (₹8,000-20,000)
- Multiple contaminants: RO + UV combination (₹12,000-30,000)

Testing labs (Hyderabad): GHMC water testing labs (free for municipal
complaints), NABl-accredited private labs (₹500-2,000 for full panel)

---

## 8. MOCK DATA SEED SCRIPT

scripts\seed_mock_data.py must insert exactly these 20 records into
WaterIntel Store via the MCP tool OR directly into SQLite:

CRITICAL: Pincode 500032 must have at least 4 records with H2S/Iron
symptoms to guarantee the Antigravity cluster moment fires in the demo.

| area_name | pincode | lat | lng | score | contaminants | source |
|---|---|---|---|---|---|---|
| Nallagandla | 500032 | 17.4532 | 78.3241 | 28 | H2S,Iron | borewell |
| BHEL MIG Colony | 500032 | 17.4620 | 78.3150 | 32 | H2S | borewell |
| BHEL LIG Colony | 500032 | 17.4580 | 78.3200 | 35 | Iron | borewell |
| BHEL HIG Colony | 500032 | 17.4650 | 78.3100 | 41 | H2S,Iron | borewell |
| Ramachandrapuram | 500055 | 17.4400 | 78.3600 | 48 | High_TDS | municipal |
| Kondapur | 500084 | 17.4900 | 78.3900 | 71 | Low_TDS | borewell |
| Madhapur | 500081 | 17.4479 | 78.3882 | 65 | Acceptable | municipal |
| Gachibowli | 500032 | 17.4401 | 78.3489 | 38 | Fluoride | borewell |
| Miyapur | 500049 | 17.4960 | 78.3549 | 55 | Iron | municipal |
| Kukatpally | 500072 | 17.4849 | 78.3994 | 52 | TDS | municipal |
| Manikonda | 500089 | 17.4048 | 78.3763 | 61 | Acceptable | borewell |
| Puppalaguda | 500089 | 17.4120 | 78.3700 | 44 | Iron | borewell |
| Narsingi | 500075 | 17.3965 | 78.3650 | 39 | H2S | borewell |
| Tellapur | 500019 | 17.4701 | 78.2801 | 33 | Iron,H2S | borewell |
| Osman Nagar | 500019 | 17.4780 | 78.2900 | 29 | H2S | borewell |
| Chanda Nagar | 500050 | 17.4942 | 78.3228 | 58 | Acceptable | municipal |
| Patancheru | 500086 | 17.5280 | 78.2648 | 22 | Iron,Nitrate | borewell |
| Sangareddy | 502001 | 17.6200 | 78.0900 | 19 | Fluoride,Iron | borewell |
| LB Nagar | 500074 | 17.3547 | 78.5524 | 67 | Acceptable | municipal |
| Uppal | 500039 | 17.4065 | 78.5593 | 59 | TDS | municipal |

---

## 9. MOBILE APP — LEAFLET MAP COMPONENT

LeafletMap.tsx must use React Native WebView with this exact Leaflet
implementation injected as HTML string:

```javascript
// HTML string to inject into WebView
const leafletHTML = `
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js">
  </script>
  <style>
    #map { height: 100vh; width: 100vw; margin: 0; padding: 0; }
    body { margin: 0; padding: 0; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = L.map('map').setView([17.4532, 78.3800], 11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Heatmap data injected from React Native
    const heatData = HEATMAP_DATA_PLACEHOLDER;
    L.heatLayer(heatData, {
      radius: 30, blur: 20, maxZoom: 14,
      gradient: {0.2: 'green', 0.5: 'yellow', 0.7: 'orange', 1.0: 'red'}
    }).addTo(map);

    // Cluster markers with popup
    const markers = MARKERS_PLACEHOLDER;
    markers.forEach(m => {
      L.circleMarker([m.lat, m.lng], {
        radius: 8,
        color: m.colour,
        fillOpacity: 0.8
      }).addTo(map).bindPopup(
        '<b>' + m.area + '</b><br>' +
        'Score: ' + m.score + '/100<br>' +
        'Reports: ' + m.count + '<br>' +
        'Issue: ' + m.contaminant
      );
    });
  </script>
</body>
</html>`;
```

Pass topology data from /map/topology API to replace
HEATMAP_DATA_PLACEHOLDER and MARKERS_PLACEHOLDER before injecting.

---

## 10. API ENDPOINTS

### FastAPI — api\main.py

```
POST /report
  Body: {user_message, pincode, area_name, source_type (optional),
         symptoms (optional), photo_base64 (optional)}
  Returns: {advisory, community_alert, complaint_draft, map_data_point,
            quality_score, contaminants, citations}

GET /map/topology
  Returns: [{pincode, area_name, lat, lng, avg_score, colour_band,
             report_count, primary_contaminant}]

GET /health
  Returns: {status: "ok", timestamp, agents_ready: true}

GET /map/pincode/{pincode}/history?days=30
  Returns: [{date, score, contaminants}] — for trend chart
```

CORS: Allow all origins in development. Restrict to Expo app URL
in production.

---

## 11. SECURITY IMPLEMENTATION (SCORED CRITERION)

Implement ALL of these — security is explicitly on the judging rubric:

1. **No PII storage:** Location stored as pincode only. Never store
   street address, full GPS coordinates, or device ID.

2. **EXIF stripping:** Before processing any photo, strip GPS EXIF
   data using Pillow: `PIL.Image.open(photo).save(cleaned_path)`
   — PIL automatically strips EXIF on re-save.

3. **Anonymous reporting:** No user accounts. No login. No phone number.
   No cookies. Each report is stateless.

4. **API key safety:** All API keys via environment variables only.
   .env file in .gitignore. .env.example shows key NAMES not values.
   Add a pre-commit check: if any file contains "GOOGLE_API_KEY=AI"
   followed by characters, refuse to commit.

5. **Input sanitisation:** Strip HTML tags and limit input length
   (user_message max 1000 chars, pincode must be 6 digits).

6. **Rate limiting:** Max 10 requests per IP per minute on /report
   endpoint. Use slowapi library.

7. **No hardcoded secrets:** Scan all generated code before presenting
   to operator. Flag any string that looks like an API key.

---

## 12. FALLBACK INSTRUCTIONS

When a tool or library fails, use these fallbacks IN ORDER. Do not
stop and ask — try the fallback immediately and report what happened.

### If uv fails to install:
→ Fallback: `pip install -r requirements.txt`
→ If that fails: `python -m pip install [package]` one by one

### If fastmcp fails to install:
→ Fallback: Use `mcp` base library directly
→ If that fails: Implement MCP server as a FastAPI app with
  JSON-RPC endpoints that ADK can call via HTTP tool

### If ChromaDB fails on Windows:
→ Fallback 1: Try `pip install chromadb --pre` (pre-release may fix Windows bugs)
→ Fallback 2: Replace ChromaDB with FAISS:
  `pip install faiss-cpu`, use `faiss.IndexFlatL2` with numpy arrays,
  save index as .pkl file in data\
→ Fallback 3: Use simple keyword matching with a JSON lookup table
  in rag\knowledge_base\contaminant_index.json (provide this file)

### If Google text-embedding-004 API call fails:
→ Fallback: Use sentence-transformers library with
  `all-MiniLM-L6-v2` model (runs locally, free, no API key needed)
  `pip install sentence-transformers`

### If ADK get_fast_api_app() is not available:
→ Fallback: Run agents directly via Python function calls,
  wrap in standard FastAPI endpoint manually

### If React Native WebView + Leaflet fails to render on Windows:
→ Fallback 1: Use react-native-maps with MapView (requires Google
  Maps API key — use Maps JavaScript API free tier $200 credit)
→ Fallback 2: Build the map as a separate React web app (Vite + React)
  deployed to Vercel (free). Mobile app links to the web map URL.
  For demo purposes this is visually identical.
→ Fallback 3: For the video demo only — run the React web app in
  Chrome, record the demo in Chrome browser. Label it
  "Web app — React Native version in development."

### If Expo Go cannot connect to local FastAPI server:
→ Use ngrok to expose localhost: `ngrok http 8000`
→ Update API_BASE_URL in mobile_app\src\api\watersentinel.ts to
  the ngrok HTTPS URL

### If Google Cloud Run deployment fails:
→ Fallback 1: Deploy to Hugging Face Spaces (Docker support, free)
→ Fallback 2: Deploy to Railway.app (free tier, Docker support)
→ Fallback 3: Use ngrok as a temporary live URL for the video demo
  and note in README that Cloud Run deployment is the production target

### If Gemini API rate limit is hit during build:
→ Switch Antigravity model to Claude Sonnet 4.6 for that session
→ ADK agents can also use claude-sonnet-4-6 as model parameter
  as a temporary measure. Switch back to gemini-2.0-flash before
  final demo recording.

### If MCP server stdio transport fails with ADK on Windows:
→ Fallback: Switch MCP transport to HTTP/SSE:
  Run MCP server as FastAPI app on port 8001 (WaterIntel) and
  8002 (ActionBridge). Connect ADK agents via MCPToolset with
  server_url parameter instead of stdio.

---

## 13. CODE QUALITY REQUIREMENTS (JUDGING CRITERION)

Every Python file must include:

```python
"""
Module: [filename]
Purpose: [one sentence]
Agent/Component: [which agent or component this serves]
Inputs: [what data comes in]
Outputs: [what data goes out]
Key Design Decisions:
  - [decision 1 and why]
  - [decision 2 and why]
Competition Concepts Demonstrated:
  - [which of the 6 judging criteria this file demonstrates]
"""
```

Every function/method must include a docstring with:
- What it does
- Parameters with types
- Return value with type
- Any known limitations or edge cases

Comments must explain WHY, not WHAT:
```python
# Good: Cluster threshold is 3 because fewer reports cannot
#       statistically distinguish a supply issue from coincidence
CLUSTER_THRESHOLD = 3

# Bad: Set threshold to 3
CLUSTER_THRESHOLD = 3
```

---

## 14. README.md REQUIREMENTS

The README is 20 points of the 100-point rubric. It must contain:

1. Project title + one-line description
2. Problem statement (3-4 sentences, India-specific context)
3. Why agents? (not just search or a simple chatbot)
4. Architecture diagram (ASCII art OR embed docs\architecture.png)
5. Agent descriptions (one paragraph each, inputs/outputs)
6. MCP server descriptions (tools exposed by each)
7. RAG knowledge base description (what documents, why these sources)
8. Competition concepts demonstrated (table: concept → where in code)
9. Setup instructions (Windows-specific, step by step)
10. Environment variables (.env.example reference)
11. How to run (each component: MCP servers, API, mobile app)
12. How to run the demo (exact steps to reproduce the Antigravity moment)
13. Deployment instructions (Cloud Run)
14. Security features implemented
15. Future roadmap (V2 features)
16. Acknowledgements (BIS, WHO, CGWB, Google ADK, OpenStreetMap)

---

## 15. DEMO SCRIPT (FOR VIDEO RECORDING)

The video must be exactly 5 minutes. Script the demo to follow this
sequence precisely when the API server and mobile app are running:

**0:00–0:45 — Problem Statement (voiceover + slides)**
"India has a water crisis that is invisible to data systems. 600 million
Indians depend on groundwater. But no system exists to tell a resident
whether their water is safe to drink. WaterSentinel changes that."

**0:45–1:30 — Architecture Overview (screen: architecture diagram)**
Show the 5-agent flow. Name each agent. Show the 2 MCP servers.
Show the RAG knowledge base. One sentence per component.

**1:30–2:30 — Demo: Single Report**
Open mobile app. Select source: Borewell. Enter symptom: "My water
smells like rotten eggs and taps have a yellow stain."
Enter pincode: 500032. Submit.
Show: SourceSense classifies → WaterProfiler diagnoses H2S + Iron
with BIS IS 10500 citation → quality score 32 (red band).
Show personal advisory: "Do not drink. Safe to bathe."

**2:30–3:15 — THE ANTIGRAVITY MOMENT**
Show the result screen: "3 other households in Nallagandla reported
similar symptoms this week."
Zoom to map. Watch the 500032 cluster pulse red.
Explain: "The agent detected this community cluster automatically —
no one asked it to. That's the intelligence layer."

**3:15–4:00 — Municipal Complaint Generated**
Show the complaint text generated for HMWSSB.
Explain the MCP ActionBridge tool that formatted it.
Show the RTI follow-up option.
"One citizen report. One tap of a button. A formal municipal
complaint ready to submit."

**4:00–4:30 — Code Walkthrough (15 seconds each)**
Flash through: agent.py (ADK), water_intel_store.py (MCP),
ingest.py (RAG), LeafletMap.tsx (topology map).
Show the competition criteria coverage table from README.

**4:30–5:00 — Vision + Close**
"This is not a demo. This is the foundation of India's first
citizen-powered water intelligence map. One report at a time.
One neighbourhood at a time."
Show the full heatmap of Hyderabad.

---

## 16. FIRST TASK FOR ANTIGRAVITY

When this system prompt is loaded, your first task is:

**"Create the complete WaterSentinel project structure as defined in
Section 3. Create all folders and placeholder files. Create
pyproject.toml with all Python dependencies. Create package.json
for the mobile app. Create .env.example. Create .gitignore.
Then install all Python dependencies with uv sync.
Report back with a Plan Artifact showing the full structure
before creating any files."**

Do not begin coding agents or MCP servers until the structure
is confirmed and uv sync succeeds.

---

*WaterSentinel System Prompt v1.0 — June 27, 2026*
*Pair this with: PRD.md and TECHNICAL_SPEC.md in the same folder*
*Load all three files into Antigravity knowledge base before starting*
