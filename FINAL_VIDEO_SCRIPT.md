# WaterSentinel — Final Demo Video Script (5 minutes)
### Structured around the 5 elements the rubric explicitly asks for

---

## Recording Setup
- Backend running: `uv run uvicorn api.main:app --reload --port 8000`
- Frontend running: `npm run dev`, browser at `localhost:3000`, zoom reset
- Have a real report ready to submit live (borewell, egg smell + one more symptom, real pincode)

---

## SEGMENT 1 — PROBLEM STATEMENT (0:00–0:35)

**[ON SCREEN: Home page, hero section]**

> "Six hundred million Indians depend on groundwater with no way to know if it's safe. In Indore and Kanpur, sewage contamination incidents weren't failures of chemistry — they were failures of detection speed. Individual households noticed symptoms for days before anyone connected the pattern. Even a single pincode is too coarse — the same pincode can have one colony on a clean municipal line and the colony next door on a contaminated borewell."

---

## SEGMENT 2 — WHY AGENTS (0:35–1:15)

**[ON SCREEN: Stay on Home, scroll to "Built on Authoritative Standards"]**

> "A single AI call can't hold source-type context, BIS and WHO standards, community history, and civic escalation logic all at once, correctly. WaterSentinel uses five ADK agents, each owning one job — classify, diagnose, detect community patterns, take civic action — coordinated through shared session state. Each agent's output becomes the next one's verified input."

---

## SEGMENT 3 — ARCHITECTURE (1:15–2:00)

**[ON SCREEN: Show the architecture diagram image — static image overlay, not live UI]**

> "Five ADK agents. Two MCP servers with ten tools total. A RAG knowledge base — BIS IS 10500, WHO guidelines, CGWB regional data — running on local embeddings, completely offline-capable, live on every single request regardless of API quota. The scoring model itself uses two independent axes: a baseline reflecting real infrastructure safety by source type, and a fixed severity for genuine contaminants that never gets diluted based on where the water came from."

---

## SEGMENT 4 — DEMO (2:00–4:15, the bulk)

**[ON SCREEN: Map tab]**

> "Here's the community map. Watch this — filtering by water source, Municipal Pipe only, this colony scores clean. Borewell only — same colony, completely different story. This isn't cosmetic filtering, this is real infrastructure-aware scoring."

**[Click a colony to expand]**

> "And this is colony-level, not just area-level. Same pincode, same broad locality — three genuinely different water realities."

**[Click State/City dropdown]**

> "We've also built this to scale beyond one city — real government pincode data for Hyderabad, Kanpur, and Vijayawada, with a state and city filter so data from different cities never gets mixed."

**[Switch to Report tab]**

> "Let's file a report. Borewell source, egg smell, and I'll use GPS to auto-detect my location—"

**[Click GPS button, show privacy message]**

> "—your GPS is used once, to detect pincode and area, then discarded immediately. Never linked to your identity."

**[Continue through questionnaire, submit]**

> "Watch the agent pipeline run — five real agents, in sequence."

**[Let AgentProgress finish, click View Results]**

**[Show score, click Explain My Score]**

> "Every deduction shown as a real point value against a named factor — not a black box. And this citation — retrieved live via RAG from BIS IS 10500 — isn't a lookup table, it's genuinely retrieved at the moment of diagnosis."

**[Scroll to Community Alert]**

> "Here's the moment that matters most — other households in this citizen's own colony reported the same symptoms this week. Not the wider area. Their actual neighbours. And a complaint, addressed to the correct municipal authority, ready to submit — generated without the citizen writing a word."

---

## SEGMENT 5 — THE BUILD (4:15–4:50)

**[ON SCREEN: Quick flash of code — tools.py comments, test_scoring_logic.py running in terminal]**

> "Built entirely with Claude, over ten-plus days, solo. Every fix went through real testing — two dedicated test suites, one unit-testing the scoring engine directly, one end-to-end testing the map and filters, both built from real bugs found during development, not written after the fact. And because the architecture is standard Python and React — no tool-specific lock-in — it opens and runs identically in Antigravity too."

---

## CLOSING (4:50–5:00)

**[ON SCREEN: Back to Map, hold on the expanded colony view]**

> "WaterSentinel — the AQI map India never had for water. Built by citizens who already know what their water looks, smells, and tastes like."

---

## Timing Summary

| Segment | Duration |
|---|---|
| Problem Statement | 35s |
| Why Agents | 40s |
| Architecture | 45s |
| Demo | 2:15 |
| The Build | 35s |
| Closing | 10s |
| **Total** | **~5:00** |
