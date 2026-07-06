# WaterSentinel
### Citizen-Powered Water Quality Intelligence for Indian Cities

**Built solo by Abhilash Battu, Hyderabad — Google ADK, free tier, 10+ days**

---

## The Problem

Over 600 million Indians depend on groundwater. No system exists to tell a resident whether their tap water is safe — let alone whether it's specifically their borewell or their neighbourhood's shared municipal line that's the problem. Contaminated water incidents in Indore and Kanpur were failures of *detection speed*, not chemistry — individual households noticed symptoms in isolation for days before any authority connected the pattern.

Even a single pincode is too coarse a unit. The same pincode can contain one colony on a contaminated borewell and a neighbouring colony on a clean municipal line — two genuinely different realities blurred into one statistic.

## The Solution

WaterSentinel turns individual citizen observations into **colony-level community intelligence**, and that intelligence into **automatic municipal action** — via a 5-agent ADK pipeline, RAG-grounded diagnosis, and colony-first cluster detection.

---

## Architecture

```
Citizen Report
      │
      ▼
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│ Orchestrator │────▶│  SourceSense │────▶│  WaterProfiler  │
│ (coordinates)│     │ (classifies +│     │ (RAG diagnosis +│
└─────────────┘     │ Vision photo)│     │ 2-axis scoring) │
                     └──────────────┘     └────────┬────────┘
                                                     │
                            ┌────────────────────────┘
                            ▼
                  ┌──────────────────┐     ┌──────────────┐
                  │ CommunityMapper  │────▶│ ActionForge   │
                  │ (colony-first    │     │ (advisory +   │
                  │  cluster detect) │     │  complaint)   │
                  └──────────────────┘     └──────────────┘
```

**5 ADK Agents** — Orchestrator, SourceSense, WaterProfiler, CommunityMapper, ActionForge — each with one distinct responsibility, coordinated via shared session state.

**2 MCP Servers** — `water_intel_store.py` (6 tools: report submission, colony-first cluster detection, topology aggregation) and `action_bridge.py` (4 tools: complaint generation with a genuine non-Gemini template fallback, RTI drafting).

**1 RAG Knowledge Base** — 7 documents (BIS IS 10500:2012, WHO Guidelines 2022, CGWB regional data) in ChromaDB, using local sentence-transformers embeddings — genuinely offline-capable, zero API key required, queried live on **every** request regardless of Gemini's availability.

---

## Key Features

- **Two-axis Water Quality Score** — source-type baseline + fixed, source-independent contaminant severity (sewage is equally catastrophic whether it's in a municipal pipe or a borewell — the score never dilutes a real health risk for the sake of visual balance)
- **Colony-level Antigravity moment** — cluster detection checks the citizen's specific colony first, falling back to the wider area only when colony data isn't available, so alerts say "your actual neighbours reported this," not a diffuse city-wide statistic
- **Trilingual (EN/HI/TE)** — the entire citizen journey is translated via a single centralized dictionary, not per-component hardcoding
- **Voice & Photo, with honest confidence-gating** — real Gemini Vision analysis and word-boundary-safe voice/text symptom extraction; AI findings below 60% confidence are treated as "could not determine," never silently scored as fact
- **GPS-assisted location** — one-tap detection, coordinates used once and never stored, with the privacy commitment shown *before* the citizen clicks
- **Real government pincode/city/state hierarchy** — seeded from India Post's actual pincode directory, scoped to Hyderabad/Kanpur/Vijayawada with a tested, single-config-change path to all-India coverage
- **HTTP-aware resilience** — 429/5xx errors retry with backoff (transient, worth waiting for); 400/401/403/404 fail fast (configuration problems that won't self-resolve)

---

## Project Structure

```
watersentinel/
├── agents/                    5 ADK agents
│   ├── orchestrator/
│   ├── source_sense/
│   ├── water_profiler/        tools.py — two-axis scoring engine
│   │   ├── tools.py
│   │   ├── symptom_extractor.py    voice/text extraction (regex, no LLM)
│   │   ├── photo_analyzer.py       Gemini Vision + confidence gating
│   │   └── error_classifier.py     HTTP retry-vs-fail-fast logic
│   ├── community_mapper/
│   └── action_forge/
├── mcp_servers/
│   ├── water_intel_store.py
│   ├── action_bridge.py
│   ├── contaminant_classifier.py   canonical contaminant format
│   └── location_canonicalizer.py   fuzzy-match typo correction
├── rag/                        ChromaDB + local embeddings
├── api/
│   ├── main.py
│   └── routers/
│       ├── report.py
│       ├── map_data.py
│       ├── feedback.py
│       ├── geolocation.py
│       ├── location_suggestions.py
│       └── local_services.py
├── watersentinel_web/          React + Vite frontend
├── test_scoring_logic.py       12-group unit test suite (no server needed)
├── audit_all_filters.py        end-to-end map/filter integrity checks
├── seed_pincode_master.py      real India Post pincode seeding
└── data/reports.db             SQLite (gitignored)
```

---

## Setup

### Prerequisites
- Python 3.12+, `uv` package manager
- Node.js 18+, npm
- A Gemini API key (free tier works; live agent path requires available quota)

### 1. Backend

```powershell
cd watersentinel
uv sync
```

Create `.env` in the project root:
```
GOOGLE_API_KEY=your_gemini_api_key_here
# Optional, for GPS/local services features:
GOOGLE_PLACES_API_KEY=your_key_here
```

**Seed the databases** (run once, in this order):
```powershell
python -m rag.ingest                    # builds the ChromaDB RAG index
python seed_pincode_master.py           # seeds real India Post pincode data
```

**Start the backend:**
```powershell
uv run uvicorn api.main:app --reload --port 8000
```

### 2. Frontend

```powershell
cd watersentinel_web
npm install
npm run dev
```

Visit `http://localhost:3000`.

### 3. Run the Test Suite

```powershell
python test_scoring_logic.py     # unit tests, no server needed
python audit_all_filters.py      # end-to-end, requires backend running
```

---

## Competition Criteria Demonstrated

| Concept | Where |
|---|---|
| Multi-agent system (ADK) | Code — 5 real agents, genuine session-state handoff |
| MCP Server | Code — 2 servers, 10 tools, colony-aware |
| Security | Code — pincode-only storage, EXIF stripping, GPS never persisted, mandatory-field validation, AI confidence-gating |
| Agent Skills | Code — RAG retrieval, symptom extraction, complaint generation, photo vision analysis |

Four concepts demonstrated through code alone, exceeding the required minimum of three.

---

## Honest Limitations

- **Colony data starts empty for any new city** and grows only through real citizen reports — this is the correct design, not a gap, since no dataset anywhere (government or free/open) tracks colony-level names in India.
- **Pincode/city coverage is currently scoped** to Hyderabad, Kanpur, and Vijayawada for testing. All-India coverage is a single config change in `seed_pincode_master.py` (`STATE_FILTER = None`), not new engineering.
- **GPS/Places API features require Google Cloud billing** to be configured. Without it, the app degrades honestly to manual entry — never fails silently.
- **The live 5-agent Gemini pipeline is architecturally sound and code-reviewed**, but full end-to-end live execution has been constrained during development by free-tier quota limits. The deterministic fallback path (not a mock) ensures every citizen still receives an accurate, medically-grounded score regardless of quota availability.
- **CSS `zoom`-based font scaling** (readability improvement) works in Chrome/Edge/Safari; Firefox does not support the `zoom` property and will show the original smaller sizing there.

---

## Testing Discipline

`test_scoring_logic.py` unit-tests the scoring engine directly, in isolation — no server required. It includes explicit regression tests for real bugs found through manual testing during development (bathing/drinking status independence, category mis-tracing from descriptive text, the original false-positive faecal-contamination bug, confidence-gating), so none of them can silently reappear.

`audit_all_filters.py` end-to-end tests the live map API across every source/time/contaminant/state/city combination, including an explicit cross-contamination check confirming one city's citizen reports never leak into another city's filtered view.

---

*WaterSentinel — the AQI map India never had for water. Built not by government sensors, but by citizens who already know what their water looks, smells, and tastes like.*
