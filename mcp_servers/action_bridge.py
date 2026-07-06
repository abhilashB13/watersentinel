"""
Module: mcp_servers/action_bridge.py
Purpose: MCP Server 2 — Civic action generation layer.
         Generates municipal complaint letters, RTI drafts, and
         escalation logs. Stateless — no database, pure generation.
Component: MCP Server 2 — ActionBridge
Inputs: Contaminant data, location, affected count from ActionForge agent
Outputs: Formatted complaint text, authority contacts, RTI drafts
Key Design Decisions:
  - Stateless design: ActionBridge generates documents but does not
    store state. WaterIntel Store handles all persistence.
  - Gemini API for complaint text: LLM generates professionally worded
    complaints. Falls back to template if API unavailable.
  - Hardcoded authority map: HMWSSB/VWSS contacts are stable government
    data. No need for external API.
Competition Concepts Demonstrated:
  - MCP Server (second MCP server — separation of concerns)
  - Agent skills (complaint generation as a reusable skill)
  - Security (no PII in complaint — area name and pincode only)
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError("fastmcp not installed. Run: uv add fastmcp")

load_dotenv()

ACTION_BRIDGE_LOG_PATH = os.getenv("ACTION_BRIDGE_LOG_PATH", "./data/escalations.log")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

mcp = FastMCP(
    name="ActionBridge",
    instructions=(
        "Civic action generation server for WaterSentinel. "
        "Generates municipal complaint letters, RTI drafts, and authority "
        "contact information for water quality escalations in Indian cities."
    ),
)

# ── Authority Contact Database ─────────────────────────────────────────────────

AUTHORITY_CONTACTS = {
    "municipal_pipeline": {
        "500032": {
            "name": "HMWSSB — Distribution Zone II (Serilingampally)",
            "email": "complaints@hmwssb.gov.in",
            "phone": "040-23290101",
            "portal": "https://hmwssb.telangana.gov.in/complaints",
            "address": "HMWSSB Zonal Office, Miyapur, Hyderabad",
        },
        "500049": {
            "name": "HMWSSB — Distribution Zone III (Miyapur)",
            "email": "complaints@hmwssb.gov.in",
            "phone": "040-23290101",
            "portal": "https://hmwssb.telangana.gov.in/complaints",
            "address": "HMWSSB Zonal Office, Kukatpally, Hyderabad",
        },
        "520001": {
            "name": "VWSS — Vijayawada Water Supply & Sewerage",
            "email": "waterboard@vmc.gov.in",
            "phone": "0866-2578888",
            "portal": "https://vmc.gov.in/water-supply",
            "address": "VMC Office, MG Road, Vijayawada",
        },
        "DEFAULT_HYDERABAD": {
            "name": "HMWSSB — Hyderabad Metropolitan Water Supply & Sewerage Board",
            "email": "complaints@hmwssb.gov.in",
            "phone": "155313",
            "portal": "https://hmwssb.telangana.gov.in/complaints",
            "address": "HMWSSB Head Office, Khairatabad, Hyderabad — 500004",
        },
        "DEFAULT": {
            "name": "Local Municipal Water Supply Authority",
            "email": "waterboard@municipality.gov.in",
            "phone": "Contact local municipal office",
            "portal": "Contact local municipal corporation website",
            "address": "Local Municipal Corporation Office",
        },
    },
    "hand_pump": {
        "DEFAULT": {
            "name": "GHMC Ward Office / Gram Panchayat",
            "email": "wardoffice@ghmc.gov.in",
            "phone": "040-21111111",
            "portal": "https://ghmc.gov.in/grievance",
            "address": "Local GHMC Ward Office",
        },
    },
    "borewell": {
        "DEFAULT": {
            "name": "CGWB — Central Ground Water Board (South Eastern Region)",
            "email": "cgwb-ser@nic.in",
            "phone": "040-23220892",
            "portal": "https://cgwb.gov.in",
            "address": "CGWB SER Office, Hyderabad",
        },
    },
    "open_well": {
        "DEFAULT": {
            "name": "Local Gram Panchayat / Ward Committee",
            "email": "Contact local Panchayat office",
            "phone": "Contact local Panchayat",
            "portal": "https://lgd.gov.in",
            "address": "Local Gram Panchayat Office",
        },
    },
}


def get_authority(source_type: str, pincode: str) -> dict:
    """Look up correct municipal authority for source type and pincode."""
    contacts = AUTHORITY_CONTACTS.get(source_type, {})
    if pincode in contacts:
        return contacts[pincode]
    if pincode.startswith("500") and "DEFAULT_HYDERABAD" in contacts:
        return contacts["DEFAULT_HYDERABAD"]
    if "DEFAULT" in contacts:
        return contacts["DEFAULT"]
    return {
        "name": "Local Municipal Authority",
        "email": "Contact local municipal office",
        "phone": "Contact local municipal helpline",
        "portal": "Contact local municipal website",
        "address": "Local Municipal Office",
    }


def _generate_fallback_complaint(
    area, pincode, contaminants_text, affected_count,
    authority, bis_text, symptoms_text, date_str, complaint_ref
) -> str:
    """Template complaint when Gemini API is unavailable."""
    return f"""Date: {date_str}
Reference: {complaint_ref}

To,
The Executive Engineer,
{authority['name']},
{authority['address']}

Subject: Urgent Complaint — Contaminated Water Supply in {area} ({pincode})

Respected Sir/Madam,

I am writing to report a serious water quality issue affecting the residents
of {area}, Pincode {pincode}. Community monitoring through WaterSentinel has
identified contamination affecting approximately {affected_count} households.

Symptoms observed: {symptoms_text}
Contaminants identified: {contaminants_text}

These findings indicate potential violation of {bis_text} standards for
drinking water quality. The affected residents are at risk of health
complications from continued consumption of contaminated water.

I request your urgent intervention:
1. Immediate inspection of the water supply to {area}
2. Water quality testing at source and distribution points
3. Remediation action to restore safe drinking water supply
4. Written confirmation of action taken within 7 working days

Yours faithfully,
[Resident Name]
{area}, {pincode}
Date: {date_str}"""


# ── MCP Tool 1: generate_municipal_complaint ──────────────────────────────────

def generate_template_complaint(area, pincode, contaminants, affected_count, source_type, authority_name=None) -> str:
    """
    Public wrapper exposing the template-only complaint path directly,
    for callers (like report.py) that want to explicitly force the
    non-Gemini fallback rather than relying on internal try/except.
    """
    authority = get_authority(source_type, pincode)
    contaminants_text = ", ".join(contaminants) if contaminants else "reported water quality issues"
    date_str = datetime.now().strftime("%d %B %Y")
    complaint_ref = f"WS-{pincode}-{datetime.now().strftime('%Y%m%d%H%M')}"
    return _generate_fallback_complaint(
        area, pincode, contaminants_text, affected_count,
        authority, "BIS IS 10500:2012", contaminants_text, date_str, complaint_ref
    )


@mcp.tool()
def generate_municipal_complaint(
    area: str,
    pincode: str,
    contaminants: list,
    affected_count: int,
    source_type: str,
    bis_references: list,
    symptoms: list = None,
) -> dict:
    """
    Generate a professionally formatted municipal complaint letter.
    Uses Gemini to produce formal complaint text. Falls back to template
    if Gemini API is unavailable. Mock integration — complaint is generated
    ready to submit but WaterSentinel does not automatically file it.
    """
    authority = get_authority(source_type, pincode)
    symptoms_text = ", ".join(symptoms or []).replace("_", " ")
    contaminants_text = ", ".join(contaminants)
    bis_text = "; ".join(bis_references) if bis_references else "BIS IS 10500:2012"
    date_str = datetime.now().strftime("%d %B %Y")
    complaint_ref = f"WS-{pincode}-{datetime.now().strftime('%Y%m%d%H%M')}"

    complaint_text = None

    if GENAI_AVAILABLE and GOOGLE_API_KEY:
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = f"""Generate a formal water quality complaint letter for an Indian
municipal water authority. Professional English. Under 300 words.

Area: {area}, Pincode: {pincode}
Water Source: {source_type.replace('_', ' ')}
Contaminants: {contaminants_text}
Symptoms: {symptoms_text}
Affected households: {affected_count}
BIS references: {bis_text}
Authority: {authority['name']}
Date: {date_str}
Reference: {complaint_ref}

Include: date, reference, to/from, subject, problem description,
BIS violations, health impact, request for inspection within 7 working days.
Use [Resident Name] as placeholder for signature."""
            response = model.generate_content(prompt)
            complaint_text = response.text
        except Exception:
            pass

    if not complaint_text:
        complaint_text = _generate_fallback_complaint(
            area, pincode, contaminants_text, affected_count,
            authority, bis_text, symptoms_text, date_str, complaint_ref
        )

    return {
        "complaint_ref": complaint_ref,
        "generated_at": datetime.now().isoformat(),
        "authority": authority,
        "complaint_text": complaint_text,
        "submission_instructions": (
            f"1. Copy complaint text above.\n"
            f"2. Submit at: {authority['portal']}\n"
            f"3. OR email: {authority['email']}\n"
            f"4. OR call: {authority['phone']}\n"
            f"5. Keep reference {complaint_ref} for follow-up.\n"
            f"6. If no response in 30 days, use the RTI option."
        ),
    }


# ── MCP Tool 2: get_authority_contact ─────────────────────────────────────────

@mcp.tool()
def get_authority_contact(pincode: str, source_type: str) -> dict:
    """
    Look up the correct municipal authority contact for a pincode
    and water source type.
    """
    authority = get_authority(source_type, pincode)
    return {
        "pincode": pincode,
        "source_type": source_type,
        "authority": authority,
        "helpline_note": (
            "HMWSSB 24x7 Helpline: 155313 (Hyderabad)\n"
            "VWSS Helpline: 0866-2578888 (Vijayawada)\n"
            "CGWB Helpline: 040-23220892 (Groundwater)\n"
            "National Water Quality Helpline: 1800-180-1551"
        ),
    }


# ── MCP Tool 3: generate_rti_draft ────────────────────────────────────────────

@mcp.tool()
def generate_rti_draft(
    complaint_ref: str,
    complaint_date: str,
    area: str,
    pincode: str,
    authority_name: str,
    days_elapsed: int,
) -> dict:
    """
    Generate an RTI application draft when a municipal complaint has not
    received a response within 30 days. RTI Act 2005 — authorities must
    respond within 30 days or face penalties.
    """
    date_str = datetime.now().strftime("%d %B %Y")
    rti_ref = f"RTI-{complaint_ref}"

    rti_text = f"""Date: {date_str}
RTI Reference: {rti_ref}

To,
The Public Information Officer (PIO),
{authority_name}

Subject: Application under Right to Information Act, 2005
         Regarding Water Quality Complaint {complaint_ref}

Respected Sir/Madam,

Under Section 6 of the Right to Information Act, 2005, I request the
following information regarding complaint {complaint_ref} filed on
{complaint_date} about contaminated water supply in {area}, Pincode {pincode}.

It has been {days_elapsed} days since the complaint was filed with no response.

Information Requested:
1. Current status of complaint {complaint_ref}
2. Name and designation of officer assigned
3. Date of field inspection conducted (if any)
4. Water quality test results from {area} (if tested)
5. Action plan and timeline for remediation
6. If rejected, reasons for the same

Application Fee: Rs.10 (Indian Postal Order attached)

Yours faithfully,
[Applicant Name]
[Address], {area}, {pincode}
Date: {date_str}"""

    return {
        "rti_ref": rti_ref,
        "rti_text": rti_text,
        "filing_authority": f"Public Information Officer, {authority_name}",
        "application_fee": "Rs.10 (Indian Postal Order or Court Fee Stamp)",
        "deadline_for_response": "30 days from filing (RTI Act 2005, Section 7)",
        "submission_instructions": (
            "1. Print this RTI application.\n"
            "2. Attach Rs.10 Indian Postal Order.\n"
            "3. Send by registered post to PIO.\n"
            "4. Keep acknowledgement for tracking.\n"
            "5. File First Appeal if no response in 30 days."
        ),
    }


# ── MCP Tool 4: log_escalation ────────────────────────────────────────────────

@mcp.tool()
def log_escalation(
    pincode: str,
    area_name: str,
    severity: str,
    contaminants: list,
    affected_count: int,
    complaint_ref: str,
    source_type: str,
) -> dict:
    """
    Log a civic escalation event for audit trail.
    Append-only log — never deletes records.
    """
    log_path = Path(ACTION_BRIDGE_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    escalation_id = f"ESC-{pincode}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    log_entry = {
        "escalation_id": escalation_id,
        "timestamp": timestamp,
        "pincode": pincode,
        "area_name": area_name,
        "severity": severity,
        "contaminants": contaminants,
        "affected_count": affected_count,
        "complaint_ref": complaint_ref,
        "source_type": source_type,
    }

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        return {
            "success": True,
            "escalation_id": escalation_id,
            "logged_at": timestamp,
            "message": (
                f"Escalation logged: {area_name} ({pincode}), "
                f"severity={severity}, affected={affected_count}"
            ),
        }
    except Exception as e:
        return {
            "success": False,
            "escalation_id": escalation_id,
            "error": str(e),
        }


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("ActionBridge MCP Server starting...", flush=True)
    print(f"Escalation log: {ACTION_BRIDGE_LOG_PATH}", flush=True)
    mcp.run(transport="stdio")
