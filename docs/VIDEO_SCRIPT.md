# WaterSentinel — 5-Minute Video Script
## Kaggle AI Agents Intensive 2026 | Agents for Good

---

## Pre-Recording Checklist

Before pressing Record:
- [ ] FastAPI backend running: `uvicorn api.main:app --port 8000`
- [ ] Mobile app open on phone via Expo Go
- [ ] Pincode 500032 has 4 seeded reports (run seed_mock_data.py)
- [ ] Map tab shows Hyderabad heatmap with red zones visible
- [ ] Screen recording running on phone AND laptop simultaneously
- [ ] Architecture diagram open on laptop (docs/architecture.png)
- [ ] Terminal open showing FastAPI logs (so agent calls are visible)
- [ ] Voice is clear, minimal background noise

---

## SEGMENT 1 — Problem Statement (0:00–0:45)

**[Show: Slide or text on screen — simple white background]**

**SPEAK:**

"Every day, millions of Indian families drink water they cannot verify is
safe. The contamination is not invisible — egg smell, yellow staining,
white deposits on taps — these are all signals. But there is no system
that helps citizens interpret those signals, report them collectively,
or turn them into civic action.

India's groundwater monitoring has one station per 330,000 people. The
last mile — from distribution pipe to tap — is officially unmonitored.

WaterSentinel changes that. It turns individual citizen observations into
community intelligence, and community intelligence into municipal action.
Automatically."

---

## SEGMENT 2 — Architecture (0:45–1:30)

**[Show: Architecture diagram — agents/orchestrator flow]**

**SPEAK:**

"WaterSentinel runs 5 ADK agents, 2 MCP servers, and 1 RAG knowledge base
grounded in BIS IS 10500 Indian water standards and WHO guidelines.

The Orchestrator coordinates four specialist agents. SourceSense classifies
which water source the citizen is using — because a borewell and a municipal
pipeline require completely different responses. WaterProfiler retrieves
relevant BIS standards using RAG and diagnoses contaminants. CommunityMapper
checks whether neighbours reported the same issue this week — this is where
the intelligence happens. ActionForge generates the personal advisory and,
when needed, the municipal complaint.

Two MCP servers handle the data and action layers separately. WaterIntel
Store manages community reports. ActionBridge generates complaints addressed
to the correct municipal authority."

---

## SEGMENT 3 — Demo: Single Report (1:30–2:30)

**[Switch to: Phone screen recording — mobile app open on Report tab]**

**SPEAK:**

"Let me show you how it works."

**[TAP: Borewell source card]**

"A resident in BHEL MIG Colony, Hyderabad, notices her water smells like
rotten eggs and the taps have yellowed."

**[TAP: Egg/Sulphur Smell + Yellow/Brown Water symptoms]**

**[TYPE in description field:]**
"My water smells like rotten eggs and the taps have yellowish stains.
My family is worried."

**[TYPE pincode: 500032, area: BHEL MIG Colony]**

**[TAP: Analyse My Water]**

"Five agents are now working on her report simultaneously."

**[Show: Terminal logs on laptop — agent calls appearing]**

"SourceSense classified the source as borewell with H2S and iron symptoms.
WaterProfiler retrieved BIS IS 10500 entries for both contaminants and
calculated a quality score of 32 out of 100 — red band, do not drink."

**[Wait for Result screen to appear — 30 to 60 seconds]**

"Quality score: 32. Safe for bathing. Not safe for drinking. BIS limit for
H2S is 0.05 milligrams per litre. This borewell likely exceeds it."

---

## SEGMENT 4 — The Antigravity Moment (2:30–3:15)

**[PAUSE on Result screen — zoom in on the orange community alert banner]**

**SPEAK:**

"But here is what makes WaterSentinel different."

**[READ the community alert on screen:]**

"3 other households in Nallagandla reported similar symptoms this week.
This appears to be a community supply issue — not just your home."

"The resident did not ask about her neighbours. She reported her own
problem. The agent detected the cluster automatically — because community
intelligence is built into the architecture, not bolted on as a feature.

This is the Antigravity moment."

**[SWITCH to: Map tab]**

"Watch the map. Pincode 500032 — BHEL and Nallagandla — lights up red.
Four households. One cluster. One community crisis that was invisible
five minutes ago."

**[Tap the red cluster on the map — popup shows area name, score, report count]**

"This is what the AQI map does for air quality. WaterSentinel does it
for water. Built not by government sensors — by citizens."

---

## SEGMENT 5 — Municipal Complaint (3:15–4:00)

**[SWITCH back to: Result screen — scroll to complaint section]**

**SPEAK:**

"Because CommunityMapper detected a cluster on a municipal pipeline, the
system automatically escalated."

**[TAP: View complaint]**

"ActionForge called the ActionBridge MCP server to generate a formal
complaint addressed to HMWSSB Distribution Zone II — the correct zonal
office for pincode 500032. The complaint cites BIS IS 10500:2012, names
the contaminants, references the affected household count, and requests
inspection within 7 working days."

**[TAP: Copy complaint to clipboard]**

"One tap. The complaint is ready to submit at the HMWSSB portal or by
email. No knowledge of complaint formats required. No searching for
the right authority. The agent handles it."

**[SHOW: If no response in 30 days — RTI option visible]**

"And if the municipality does not respond in 30 days — the agent can
generate an RTI application under the Right to Information Act."

---

## SEGMENT 6 — Code and Criteria (4:00–4:30)

**[Switch to: VS Code / file explorer — flash through key files]**

**SPEAK:**

"Quickly — the technical foundation."

**[Show: agents/orchestrator/agent.py — 2 seconds]**
"Five ADK agents with shared session state."

**[Show: mcp_servers/water_intel_store.py — 2 seconds]**
"MCP Server 1 — community data store. The cluster detection tool powers
the Antigravity moment."

**[Show: rag/knowledge_base/ folder — 2 seconds]**
"Seven documents in the RAG knowledge base — BIS IS 10500, WHO guidelines,
CGWB regional data, and three custom-authored Indian water quality guides."

**[Show: README competition criteria table — 2 seconds]**
"Seven competition criteria demonstrated. Required: three."

---

## SEGMENT 7 — Vision and Close (4:30–5:00)

**[Switch to: Full Hyderabad map — all 20 data points visible, red and orange zones]**

**SPEAK:**

"This is what one city looks like after 20 citizen reports.

Imagine 4,000 reports — one in every thousand Hyderabad residents. The
topology map becomes what HMWSSB cannot build with their existing
infrastructure. Ward engineers can see contamination clusters before
they become health crises. Jal Jeevan Mission gets last-mile data they
have never had. Citizens get answers in seconds instead of waiting for
government surveys that may never come.

WaterSentinel is not a chatbot. It is civic infrastructure.
Built with agents. Powered by citizens."

**[Hold on map for 3 seconds]**

"Thank you."

---

## Post-Recording Checklist

- [ ] Video is under 5 minutes (trim if needed)
- [ ] Antigravity community alert is clearly visible and readable
- [ ] Quality score gauge is visible on Result screen
- [ ] Map heatmap is visible with red zones
- [ ] Complaint text is shown briefly
- [ ] Architecture diagram appears in Segment 2
- [ ] Upload to YouTube as Unlisted
- [ ] Copy YouTube URL for Kaggle submission
- [ ] Thumbnail: screenshot of map with red zones + "WaterSentinel" title

---

## Common Recording Mistakes to Avoid

- Do NOT narrate while waiting for agents (fill with architecture explanation)
- Do NOT show the terminal for more than 5 seconds (distraction)
- Do NOT read the full complaint text (just show it exists, it is ready)
- Do NOT rush Segment 4 — the Antigravity moment is 10 judging points
- DO pause for 2 full seconds on the community alert banner before speaking

---

*Script v1.0 — June 2026*
*Target time: 4:45 to 4:55 — do not exceed 5:00*
