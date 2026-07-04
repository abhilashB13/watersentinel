# WaterSentinel — Product Requirements Document
**Version:** 1.0 | **Date:** June 27, 2026  
**Author:** Abhilash Battu | **Role:** Solo Product Manager & Builder  
**Track:** Kaggle AI Agents Intensive — Agents for Good  
**Status:** Baselined

---

## Table of Contents
1. Executive Summary
2. Problem Statement
3. Why Now
4. User Segmentation
5. Pain Points by Segment
6. Competitive Landscape
7. Solution Overview
8. Why Agents — Not Just Google
9. Product Architecture (Summary)
10. MVP Scope
11. Metrics & Success Indicators
12. Monetisation Strategy
13. Risks & Mitigations
14. Future Roadmap (V2+)
15. Appendix — Research & Validation

---

## 1. Executive Summary

India has a water crisis that is invisible to data systems. Over 600 million Indians depend on groundwater. Municipal supply covers urban areas for barely one hour per day. Borewells go down 250–500 feet into geology that varies block by block. And yet, no system exists to tell a resident whether the water coming out of their tap is safe to drink.

WaterSentinel is the water quality intelligence map India never had — built not by government sensors, but by citizens who already know what their water looks, smells, and tastes like. Powered by five ADK agents, two MCP servers, and a RAG knowledge base grounded in BIS and WHO standards, WaterSentinel turns individual citizen observations into community-level intelligence and municipal action — automatically.

**The one-line story:**  
*"WaterSentinel turns a mother's complaint about egg-smelling water into a ward-level municipal escalation — in seconds, without any sensor hardware."*

---

## 2. Problem Statement

### 2.1 The Scale of the Problem

India's water quality crisis operates at two levels that are rarely discussed together:

**Level 1 — Access:** While over 90% of India's population has access to a basic drinking water source, only approximately 55–60% have access to "safely managed" drinking water — defined as water that is available on premises, accessible when needed, and free from contamination. The gap between "access" and "safe access" is where the real crisis lives.

**Level 2 — Awareness:** The majority of contamination incidents go undetected not because they are invisible — they produce visible symptoms like yellow staining, egg-like odour, white deposits, and discoloured water — but because residents have no framework to interpret what they observe. They do not know what is safe and what is not. They do not know who to contact. And they have no visibility into whether their neighbours are experiencing the same problem.

### 2.2 How Water Actually Reaches Indian Residents

Understanding the problem requires understanding the four distinct water supply models in Indian cities and peri-urban areas:

**Model 1 — Borewell (Personal)**  
The most common source in Hyderabad's western corridor, Bangalore's outer areas, and Tier-2 cities. Residents or RWAs have drilled borewells at personal expense — typically 250 feet in alluvial soil areas, 400–500 feet in rocky Deccan Plateau terrain. Water quality is entirely dependent on local geology and is the owner's personal responsibility. No government oversight. No monitoring. No recourse except personal action.

**Model 2 — Municipal Pipeline**  
Available for approximately one hour each morning in most Indian cities. Residents have dug underground cement storage tanks (1,000–2,000 litres capacity) to capture and store this supply for daily use. The storage tank itself introduces contamination risk — bacterial growth, sediment accumulation, and — critically — potential sewage mixing if pipeline pressure drops below sewer pressure, which is a documented problem in older city infrastructure.

**Model 3 — Hand Pump**  
Common in peri-urban areas and lower-income urban neighbourhoods. Shared community infrastructure. No individual ownership, therefore no individual motivation to report issues or take action. Requires collective community or authority response.

**Model 4 — Open Well**  
Rural and semi-rural areas. Highest contamination risk. Seasonal variation is extreme — water table drops in summer, contamination concentrates. Least awareness among users.

### 2.3 The Contamination Reality

The following contaminants are documented across Indian groundwater systems and produce identifiable symptoms that ordinary residents can observe:

| Symptom | Likely Contaminant | BIS Limit | Health Impact |
|---|---|---|---|
| Egg smell | Hydrogen Sulphide (H2S) | 0.05 mg/L | Safe to bathe; unsafe to drink above limit |
| Yellow/brown water or pipe staining | Iron (Fe) | 0.3 mg/L | Not immediately toxic; damages appliances; indicates other contamination risk |
| White deposits on taps/vessels | High TDS / Calcium hardness | 500 mg/L (TDS) | Kidney stone formation with prolonged consumption |
| Blue-green staining | Copper pipe corrosion | 0.05 mg/L | Liver damage at high levels |
| Metallic taste | Iron or Manganese | Fe: 0.3, Mn: 0.1 mg/L | Neurological impact (Mn); gastrointestinal (Fe) |
| Black or very dark water | Sewage contamination / Manganese | — | Acute gastrointestinal disease risk |
| No visible symptom but stomach issues | Bacterial / Coliform contamination | 0 MPN/100ml | Waterborne diseases; highest mortality risk |

### 2.4 The Data Gap

Current government monitoring is top-down and structurally inadequate for last-mile awareness:

- **CPCB** monitors approximately 4,000 water quality stations nationally — one station per 330,000 people
- **HMWSSB** (Hyderabad) monitors treatment plant output, not tap delivery
- **Jal Jeevan Mission** dashboard shows self-reported state-level data, not ground truth
- **No system exists** that captures what water quality looks and smells like when it reaches a resident's tap

The last mile — from distribution network to tap — is officially unmonitored.

---

## 3. Why Now

Three converging forces create a unique window for WaterSentinel in 2026 that did not exist three years ago:

**Policy Tailwind — Jal Jeevan Mission Running Behind**  
The Government of India's Jal Jeevan Mission committed ₹3.6 lakh crore to provide tap water to every rural household. It is running significantly behind schedule. The mission's own monitoring dashboard relies on self-reported completion data from states — not actual quality verification. A citizen-powered quality monitoring layer is exactly what the mission's last-mile accountability gap requires. Government interest in technology solutions to close this gap is at its highest point.

**Behaviour Shift — Post-COVID Health Consciousness**  
COVID-19 fundamentally changed Indian households' relationship with health monitoring. Home testing kits, air purifiers, and water filters saw category-level growth in 2021–2023. Residents who would not have thought twice about tap water quality in 2019 are now actively interested in understanding what they consume. The behaviour of "checking" rather than assuming has been normalised.

**Technology Unlock — Accessible AI Agents**  
Until 2025, building a system that could interpret symptom descriptions, match them against technical water quality standards, and generate formatted official complaints would have required a specialised team. Google ADK, Gemini, and MCP servers now make this buildable by a solo developer in 10 days. The technology has crossed the accessibility threshold.

**Smart City Momentum — Budget Exists**  
100 Smart Cities under India's Ministry of Housing have dedicated technology budgets. Water quality monitoring is an approved Smart City use case. Municipal bodies are actively looking for technology partners for citizen engagement. The procurement pathway exists.

---

## 4. User Segmentation

WaterSentinel serves four distinct user segments, each with a different water source, different motivation, and different required response from the system.

### Segment 1 — Borewell Owner (Urban/Semi-Urban)

**Profile:** Homeowner or RWA member in Hyderabad, Bangalore, Pune outer areas. Has invested ₹1–3 lakhs in boring a personal well. Middle to upper-middle income. Has a smartphone. Has motivation to act because the infrastructure is their personal asset.

**Primary concern:** Is my borewell water safe for my family?  
**Agency:** High — can independently install filters, get water tested, take personal action  
**Required response:** Personal advisory with specific filter recommendation and nearest certified testing lab

### Segment 2 — Municipal Pipeline User (Urban)

**Profile:** Resident of an apartment or independent house in a city that has municipal water supply. Depends on one-hour morning supply stored in underground tank. Middle income. May have a basic purifier but relies on municipal supply as primary source.

**Primary concern:** Why does my water smell? Is it a building problem or a supply problem?  
**Agency:** Medium — can raise complaints but needs to know who to contact and what to say  
**Required response:** Diagnosis + municipal complaint draft pre-filled with the right authority

### Segment 3 — Hand Pump / Shared Infrastructure User (Peri-Urban)

**Profile:** Resident of a peri-urban colony or lower-income urban neighbourhood. Uses a shared community hand pump. Lower income. May have a basic Android smartphone. No individual ownership of the water source.

**Primary concern:** Why are people in my area getting sick?  
**Agency:** Low individually — requires collective community or Panchayat response  
**Required response:** Community alert + Panchayat escalation template + awareness advisory

### Segment 4 — RWA / Housing Society Administrator

**Profile:** Secretary or committee member of a Resident Welfare Association. Manages water quality for 50–500 households. Educated. Has authority to act and budget to implement solutions. Wants data, not just advice.

**Primary concern:** What is the water quality trend in our society over the last 6 months?  
**Agency:** High — can procure treatment solutions, mandate testing, communicate to residents  
**Required response:** Dashboard view with trend data, aggregate quality scores, exportable complaint history

---

## 5. Pain Points by Segment

### 5.1 Universal Pain Points (All Segments)

**No interpretation layer:** Residents observe symptoms — egg smell, brown water, white deposits — but have no framework to interpret what these symptoms mean, which contaminants they indicate, or what the health implications are. Google search returns generic international results that do not account for Indian geology, BIS standards, or regional contamination patterns.

**No action pathway:** Even residents who correctly identify a problem do not know who to contact, what to say, or what format a complaint should take. The HMWSSB complaint portal exists but is not discoverable and requires specific information that most residents do not know to provide.

**No community visibility:** A resident experiencing yellow water does not know whether their three neighbours are experiencing the same issue. Without that community context, they cannot determine whether the problem is in their internal plumbing (personal responsibility) or the supply line (municipal responsibility). This ambiguity causes inaction.

**No follow-up loop:** Even residents who file complaints have no visibility into resolution status, no follow-up mechanism, and no way to verify if the situation has improved over time.

### 5.2 Segment-Specific Pain Points

**Borewell owners:** No understanding of how local geology affects water quality. Do not know what depth-related contamination patterns exist. Do not know which filter type is appropriate for which contaminant. Waste money on wrong solutions (e.g., buying a UV filter when the problem is iron — UV does not remove iron).

**Municipal users:** Cannot distinguish between a supply-level problem and a building-level problem (e.g., dirty storage tank vs. contaminated supply). Cannot easily reach the right HMWSSB zonal office. Complaint process is opaque.

**Hand pump users:** No individual agency. Collective action is required but there is no platform to organise or escalate collectively.

**RWA administrators:** No aggregate data. Cannot demonstrate a pattern of complaints to the municipality. No trend visibility. Cannot easily communicate water quality status to residents.

---

## 6. Competitive Landscape

### 6.1 Existing Solutions and Why They Have Failed

**Government Apps — Swachhata, JJM Mobile App, CPCB Water Quality Portal**

These apps are top-down, government-operated, and give citizens no personal value in return for their report. A citizen submits a complaint and receives no diagnosis, no advisory, no community context. The apps function as complaint submission forms — not intelligent systems. Citizen adoption has been negligible because the value exchange is entirely one-directional: citizen gives data, receives nothing. WaterSentinel inverts this — citizen gives a symptom description, receives a BIS-grounded diagnosis, a community cluster context, and a pre-filled complaint. The return value drives adoption.

**IoT Hardware Companies — SmartTerra, Ketos, Aguazone**

These companies build sensor hardware for municipal water treatment plants and industrial water monitoring. They serve B2B enterprise customers — municipalities, factories, large commercial complexes. They have no citizen-facing product. Their sensors cost ₹50,000–5,00,000+ per unit. They require installation infrastructure. They are entirely inaccessible to individual residents or small RWAs. More critically, they monitor treatment plant output — not last-mile tap quality.

**Generic Water Quality Apps — Water Quality Index apps, WHO symptom checkers**

Generic international tools with no India-specific calibration. Do not account for BIS IS 10500 Indian standards. Do not understand the borewell vs. municipal vs. hand pump source distinction. Do not have local municipal authority contact data. Cannot generate a complaint to HMWSSB. Useless for the Indian context.

**Lab Testing Services — Purelab, Dr. Water, local NABL labs**

These services require the resident to physically collect a water sample and either visit a lab or mail the sample. Results take 3–7 days and cost ₹500–2,000. They provide a lab report with numerical values but no interpretation, no advisory, and no action pathway. They serve residents who have already decided to act — not the majority who are uncertain whether action is warranted.

### 6.2 Competitive Differentiation Matrix

| Capability | WaterSentinel | Govt Apps | IoT Hardware | Lab Testing |
|---|---|---|---|---|
| Works without sensor hardware | ✅ | ✅ | ❌ | ❌ |
| India-specific BIS calibration | ✅ | Partial | ✅ | ✅ |
| Instant diagnosis | ✅ | ❌ | ❌ | ❌ |
| Community cluster detection | ✅ | ❌ | ❌ | ❌ |
| Automated municipal complaint | ✅ | ❌ | ❌ | ❌ |
| Source-type aware (borewell/pipeline) | ✅ | ❌ | ❌ | ❌ |
| Free for citizens | ✅ | ✅ | ❌ | ❌ |
| Topology map | ✅ | ❌ | Partial | ❌ |
| No lab visit required | ✅ | ✅ | ✅ | ❌ |

### 6.3 The Core Differentiator

WaterSentinel's moat is not technology — it is the combination of:
1. **Ground-truth source taxonomy** (borewell/municipal/hand pump/open well) that drives different diagnostic and action paths
2. **Citizen-as-sensor model** that generates community intelligence without hardware
3. **Immediate personal value** (diagnosis + advisory) that creates the incentive for citizens to report

None of the existing players have all three. Most have none.

---

## 7. Solution Overview

WaterSentinel is a citizen-powered water quality intelligence system with three layers:

**Layer 1 — Report (Individual):**  
Citizens describe water symptoms via a mobile app. Five ADK agents interpret the description, diagnose likely contaminants against BIS/WHO standards using RAG retrieval, and provide an immediate personalised advisory.

**Layer 2 — Intelligence (Community):**  
Every report is aggregated by pincode. When three or more reports from the same area indicate the same contaminant within seven days, the system automatically identifies a cluster and generates a municipal complaint without the citizen needing to initiate it.

**Layer 3 — Action (Civic):**  
The topology map — WaterSentinel's AQI equivalent for water — shows every Indian city's water quality at colony/road level, colour-coded from green (safe) to red (critical). This map is the product's long-term value — it becomes more accurate and more useful with every citizen report.

---

## 8. Why Agents — Not Just Google

This is the question that must be answered in the pitch. Here is the structured answer:

**Google search gives information. WaterSentinel gives a decision specific to your situation.**

When a resident searches "water smells like eggs India" on Google, they receive 10 generic articles about hydrogen sulphide from international sources. None of them know:
- Whether the water came from a 400-foot borewell in Deccan Plateau geology or a municipal pipeline
- Whether the BIS IS 10500 limit for H2S is 0.05 mg/L and whether their symptom description suggests they are above it
- Whether three of their neighbours reported the same smell this week
- That the correct body to complain to is HMWSSB's Distribution-II office, not the general HMWSSB helpline
- What a formatted complaint to that specific office should contain

The agent knows all of this — because it holds the source type context, the BIS knowledge base, the community report history, and the authority contact database simultaneously. It reasons across all of these to produce a decision specific to one resident's situation. That is not search. That is intelligence.

---

## 9. Product Architecture Summary

*(Full technical specification in TECHNICAL_SPEC.md)*

**5 ADK Agents:**
- Orchestrator — root agent, session state, routing
- SourceSense — intake, source classification, photo analysis
- WaterProfiler — RAG-powered diagnosis, BIS-grounded quality score
- CommunityMapper — cluster detection, topology update, escalation trigger
- ActionForge — personal advisory, municipal complaint, map data point

**2 MCP Servers:**
- WaterIntel Store — citizen report database, pincode profiles, cluster queries, topology data
- ActionBridge — municipal complaint generation, authority contacts, RTI drafts, escalation logging

**1 RAG Knowledge Base:**
- BIS IS 10500:2012, WHO Guidelines 2022, CGWB Telangana/AP groundwater data, symptom-contaminant mapping, India water sources guide, treatment recommendations
- ChromaDB vector store, Google text-embedding-004, top-3 retrieval

**Frontend:** React Native (Expo) + Leaflet.js + OpenStreetMap (100% free, no API key)

---

## 10. MVP Scope

### In Scope (V1 — Competition Submission)

- Four-screen mobile app: Report, Result, Community Map, About
- All 5 ADK agents working end-to-end
- Both MCP servers with full tool implementations
- RAG knowledge base with 7 documents ingested
- Topology map with pre-seeded Hyderabad mock data (20 data points)
- Leaflet heatmap (green/orange/red zones)
- Municipal complaint generation (mock — no live HMWSSB API)
- Security features: pincode-only location, EXIF stripping, anonymous reporting
- Deployment: Google Cloud Run (live URL)
- README with architecture, setup instructions, and diagrams

### Out of Scope (V2+)

- WhatsApp integration (Meta Business API approval required — too slow)
- Live municipal API integration (requires government partnership)
- Telugu/Hindi vernacular input (V1.5 feature)
- Seasonal maintenance calendar
- Soil/geology correlation layer
- RWA dashboard (subscription feature)
- Lab referral integration
- Real-time IoT sensor data ingestion

---

## 11. Metrics & Success Indicators

### 11.1 North Star Metric

**One complete loop:** A contamination cluster detected by agents → escalated to a municipal body → acknowledged → resolved → confirmed by follow-up citizen reports showing improved quality scores in the same pincode.

This is the metric that proves WaterSentinel works as civic infrastructure, not just as a demo.

### 11.2 Competition Demo Metrics (July 7, 2026)

These are the metrics referenced in the Kaggle writeup to demonstrate product thinking:

**Input Metrics (what goes in)**
- Report completion rate: % of users who provide all 5 attributes (source + symptoms + location + severity + optional photo)
- Source type distribution across submitted reports (validates 4-source taxonomy assumption)
- Photo submission rate (validates visual input hypothesis)

**Output Metrics (what comes out)**
- Contaminant identification confidence score (WaterProfiler output, target >0.80 for common contaminants)
- Complaint generation time: seconds from report submission to complete complaint draft (target: <10 seconds end-to-end)
- Cluster detection threshold: defined as ≥3 reports, same contaminant type, same pincode, within 7 days

**System Metrics**
- Agent pipeline end-to-end latency (target: <10 seconds for full 5-agent chain)
- MCP server tool response time (target: <2 seconds per tool call)
- RAG retrieval accuracy: relevant BIS/WHO citation returned for top-10 symptom combinations

### 11.3 90-Day Pilot Success Metrics

These are the metrics presented to a potential CSR funder or municipal body:

**Adoption**
- 500 citizen reports submitted across minimum 3 pincodes in one city
- 50+ reports per week by week 8 (organic growth, not launch spike)
- Returning reporter rate: 30% of reporters submit a second report within 30 days

**Quality**
- 10 distinct colony-level clusters identified on the topology map
- False positive rate on cluster detection: <20% (1 in 5 escalations confirmed as isolated, not community)
- BIS standard citation accuracy: correct limit cited in >90% of diagnoses

**Impact**
- 50 municipal complaints auto-generated in 90 days
- Complaint acknowledgement rate: % receiving municipal response within 30 days
- Resolution rate: % of complaints showing quality score improvement in follow-up reports

**Coverage**
- Minimum 2 distinct socioeconomic zones reporting (validates cross-segment reach)
- 5+ pincodes with minimum 5 reports each (map density threshold for meaningful visualisation)
- Minimum 2 RWAs using the community map view

### 11.4 Scale Threshold (12–24 Months)

When 1 in 1,000 residents in a city actively reports, the topology map becomes statistically meaningful for municipal decision-making. For Hyderabad (4 million residents): **4,000 active reporters** is the scale threshold where the data transitions from a civic project to civic infrastructure.

### 11.5 Counter Metrics (What We Must Not Break)

- Privacy: Zero incidents of street-level address being stored or exposed
- Trust: Report-to-advisory time must not exceed 15 seconds (longer = user abandonment)
- Safety: Zero instances of agent recommending water as safe when BIS parameters indicate contamination

---

## 12. Monetisation Strategy

### Core Principle

WaterSentinel is a public good product. Citizens who benefit most — residents drinking contaminated water — cannot be charged. The payer and the beneficiary are different. This is the norm in civic tech.

**Citizen reporting is permanently free. Always.**

### 12.1 Primary Revenue — B2G SaaS (Municipal Bodies)

**Target customers:** HMWSSB (Hyderabad), BWSSB (Bangalore), VWSS (Vijayawada), Chennai Metro Water, and equivalent bodies in 15+ major Indian cities.

**Value proposition to municipal bodies:** WaterSentinel gives them something they currently have zero visibility into — ground-truth citizen-reported water quality data at the ward level, after water leaves the treatment plant. This is the last-mile monitoring gap they cannot fill with their existing infrastructure.

**Pricing model:** Annual SaaS subscription per city.
- Tier 1 (cities <1M population): ₹25–50 lakhs/year
- Tier 2 (cities 1–5M population): ₹75–150 lakhs/year
- Tier 3 (metro cities 5M+): ₹150–300 lakhs/year

**Revenue potential:** 10 Tier-2 cities at ₹100 lakhs/year = ₹10 crore ARR. Conservative 3-year target.

**Sales motion:** Pilot with one city using competition prototype → produce impact report → present to Smart City Mission procurement committee.

### 12.2 Bridge Revenue — CSR Funding

**Target funders:** Tata Trust, Infosys Foundation, Wipro Cares, HUL's water sanitation programme, Asian Paints.

**Rationale:** Under Companies Act 2013, companies above a threshold must spend 2% of net profit on CSR. Water and sanitation (SDG 6) is an approved CSR category. WaterSentinel provides structured impact reporting — number of reports, areas covered, complaints filed, quality improvements — which CSR programmes need for their mandatory annual disclosures.

**Grant size:** ₹50 lakhs–₹2 crore for a city-level pilot programme. Achievable within 12 months of a working prototype.

### 12.3 International Development Grants

**Target funders:** UNICEF India, WHO India water programme, Gates Foundation WASH initiative, USAID.

**Grant pathway:** A working prototype with real citizen data from even one Indian city is sufficient to apply. Grant sizes: $100,000–$2,000,000 for pilot programmes. Timeline: 6–18 months from application to funding.

### 12.4 B2B Data Products (Long Term, 24+ Months)

Once topology data covers multiple cities with sufficient density:

**Real estate data API:** Neighbourhood water quality scores are material information for home buyers and builders. MagicBricks, 99acres, NoBroker could license pincode-level water quality scores as a data feed. Revenue model: annual data licence or per-query API.

**Water filter affiliate:** A resident who has just learned their TDS is 800ppm and their water has iron contamination is the highest-intent buyer in the water filter market. Contextual filter recommendations from Eureka Forbes, Kent, Livpure — revenue model: lead generation fee per conversion or affiliate commission.

**Health insurance risk data:** Waterborne disease risk by geography is actuarially valuable for underwriting and outreach. Anonymised, aggregated pincode-level risk scores. Revenue model: annual data licence.

### 12.5 RWA Subscription (Near-Term, 6–12 Months)

Resident Welfare Associations already pay for services. A WaterSentinel RWA dashboard — showing building water profile, trend over time, automated complaint tracking — is worth ₹500–2,000/month per RWA. 50,000+ registered RWAs in India. Even 0.5% penetration = 250 RWAs = ₹15–60 lakhs/year at low cost to serve.

### 12.6 Revenue Priority Sequence

| Phase | Revenue Stream | Timeline | Why |
|---|---|---|---|
| Phase 0 | CSR grant | 0–12 months | Fastest path to funding, no sales cycle |
| Phase 1 | Municipal SaaS (one pilot city) | 12–24 months | Builds the credibility case |
| Phase 2 | RWA subscriptions | 6–12 months | Low friction, validates willingness to pay |
| Phase 3 | Municipal SaaS (scale) | 24–36 months | Primary long-term revenue |
| Phase 4 | Data products | 36+ months | Requires density threshold |

---

## 13. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Cold start — no community data at launch | High | High | Pre-seed 20 mock Hyderabad data points for demo; use referral-driven onboarding in real launch |
| Agent hallucination of BIS standards | Medium | High | RAG grounds every diagnosis in retrieved document chunks; citations shown to user for verification |
| Municipal complaint not accepted (mock only) | High (demo) | Low | Be transparent in README and video — live API requires government partnership; complaint text is valid |
| Solo build timeline overrun | Medium | High | React Native replaced with React web app if mobile takes >1 day; V1 scope locked, no scope creep |
| Map API cost at scale | Low (demo) | Medium | Leaflet + OpenStreetMap is free forever; no API key risk |
| Low citizen adoption post-launch | Medium | High | Immediate personal value (diagnosis) is the core retention mechanic; partner with RWAs for seeded launch |
| Government data partnership delay | High | Low (for V1) | V1 runs entirely on citizen-reported data; government partnership is V2 feature |

---

## 14. Future Roadmap (V2+)

### V1.5 (3 months post-competition)
- Telugu and Hindi language input via Gemini's multilingual capability
- WhatsApp bot integration (Meta Business API approval)
- Lab referral integration with 2–3 certified labs in Hyderabad
- RWA dashboard (web view)

### V2 (6–12 months)
- Live HMWSSB complaint API integration (requires partnership)
- Seasonal water quality alerting (pre-monsoon, post-monsoon advisories)
- Soil type and geology correlation layer (CGWB dataset integration)
- RTI tracking — automated follow-up if complaint unresolved in 30 days

### V3 (12–24 months)
- Expand to 3 cities: Hyderabad, Vijayawada, Bangalore
- Government data ingestion: CPCB monitoring station data as a baseline layer
- IoT sensor integration API (for communities that want hardware-grade data)
- Open data API for researchers and urban planners

### Long-Term Vision
WaterSentinel is absorbed as infrastructure by a government body — CPCB, Jal Jeevan Mission, or a Smart City — and operates as the citizen-monitoring layer for India's national water quality programme. The commercial entity continues as the technology and data partner.

---

## 15. Appendix — Research & Validation

### 15.1 User Research

**Method:** Ethnographic observation and structured conversations  
**Sample:** 10 residents across Hyderabad and Vijayawada  
**Profile mix:** 6 borewell users, 3 municipal pipeline users, 1 hand pump user  
**Key findings:**

1. All 10 users had noticed at least one water quality symptom in the past 6 months (egg smell, yellow staining, or white deposits)
2. 8 of 10 did not know what the symptom indicated or whether it was a health risk
3. 7 of 10 had not filed any complaint — primary reason: "don't know who to contact"
4. 5 of 10 had purchased a water filter based on a neighbour's recommendation, not a diagnosis
5. All 10 expressed interest in knowing whether their neighbours were experiencing the same issue
6. 9 of 10 said they would use a free app that told them what was wrong with their water and what to do

**Validation of source taxonomy:** All 10 users could immediately identify their primary water source type from the four categories (borewell, municipal, hand pump, open well) without confusion. The taxonomy is intuitive.

**Validation of symptom language:** Users described symptoms using exactly the vocabulary built into SourceSense — "egg smell," "yellow water," "white marks on vessels." No translation layer is needed between user language and agent interpretation for the most common symptoms.

### 15.2 Secondary Research Sources

- BIS IS 10500:2012 — Indian Standard: Drinking Water Specification
- WHO Guidelines for Drinking-water Quality (2022 Edition)
- CGWB Ground Water Quality Data — Telangana (2023)
- CGWB Ground Water Quality Data — Andhra Pradesh (2023)
- CPCB Water Quality Status of Indian Rivers (2024)
- Jal Jeevan Mission Dashboard — jaljeevan.nic.in (accessed June 2026)
- HMWSSB Annual Report 2023–24
- India Smart Cities Mission — Technology Guidelines (2024)

### 15.3 Contamination Evidence — Documented Indian Cases

- **Kanpur, 2024:** Municipal supply water turned black due to sewage pipeline mixing with water supply lines — documented by local media. Affected ~15,000 households. Resolution took 9 days.
- **Hyderabad Western Corridor:** Iron contamination in borewells is a documented pattern in Nallagandla, Gachibowli, and Kondapur due to Deccan Plateau geology and borewell depths of 300–500 feet.
- **Vijayawada:** Fluoride contamination above BIS limits documented in peri-urban groundwater (CGWB 2022 report).

These cases validate both the problem statement and the symptom-to-contaminant mapping in the RAG knowledge base.

---

*PRD Version 1.0 — Baselined June 27, 2026*  
*Next review: Post-competition — July 2026*
