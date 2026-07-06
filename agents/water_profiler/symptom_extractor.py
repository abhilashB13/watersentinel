"""
Module: agents/water_profiler/symptom_extractor.py
Purpose: Extract structured symptom identifiers from free-text (voice
transcript or typed description) using word-boundary-safe regex matching
against a known, closed vocabulary — NOT an LLM call, and NOT naive
substring matching (which caused a real false-positive bug earlier in this
project, where "diagnosed" appearing anywhere in a message incorrectly
triggered a fabricated faecal/coliform result).

WHY RULE-BASED MATCHING IS CORRECT HERE, NOT A WEAKNESS:
The symptom vocabulary is small (~19 identifiers) and domain-specific.
A closed-vocabulary matching problem like this is more reliably solved by
an explicit synonym dictionary with word-boundary regex than by an LLM call
— it's deterministic, auditable, requires no API quota, and cannot
hallucinate a symptom that wasn't actually described. This lets voice and
typed free-text descriptions genuinely contribute structured data to
scoring and the community map, not just sit as decorative unparsed text.

Supports English, Hindi, and Telugu phrases, matching the app's trilingual
frontend.
"""

import re

# Each symptom ID maps to a list of trigger phrases across all 3 supported
# languages. Matching uses word boundaries (\b) so "eggs" doesn't falsely
# match "egg", and so partial substrings inside unrelated words never fire —
# this is the direct fix for the earlier false-positive bug pattern.
SYMPTOM_TRIGGER_PHRASES = {
    "sewage_smell": [
        r"\bsewage\b", r"\bdrainage smell\b", r"\btoilet smell\b", r"\bfaecal\b", r"\bfecal\b",
        r"मल की गंध", r"सीवेज", r"नाली की गंध",
        r"మల వాసన", r"మురుగు వాసన",
    ],
    "egg_smell": [
        r"\begg smell\b", r"\bsulphur\b", r"\bsulfur\b", r"\brotten egg\b",
        r"अंडे की गंध", r"गंधक",
        r"గుడ్డు వాసన", r"గంధకం",
    ],
    "yellow_colour": [
        r"\byellow water\b", r"\bbrown water\b", r"\byellowish\b", r"\brownish\b",
        r"पीला पानी", r"भूरा पानी",
        r"పసుపు నీరు", r"గోధుమ నీరు",
    ],
    "black_colour": [
        r"\bblack water\b", r"\bdark water\b", r"\bdirty black\b",
        r"काला पानी", r"गहरा पानी",
        r"నలుపు నీరు", r"ముదురు నీరు",
    ],
    "white_deposits": [
        r"\bwhite deposit", r"\bwhite scale\b", r"\bwhite residue\b",
        r"सफेद जमाव", r"सफेद परत",
        r"తెల్లని నిక్షేపాలు", r"తెల్లని పొర",
    ],
    "blue_green_stain": [
        r"\bblue.?green stain", r"\bblue stain", r"\bgreen stain",
        r"नीला.?हरा", r"नीले दाग",
        r"నీలం.?ఆకుపచ్చ", r"నీలం మరక",
    ],
    "metallic_taste": [
        r"\bmetallic taste\b", r"\btastes like metal\b", r"\biron taste\b",
        r"धातु.*स्वाद", r"लोहे.*स्वाद",
        r"లోహపు రుచి", r"ఇనుము రుచి",
    ],
    "salty_taste": [
        r"\bsalty\b", r"\bbitter taste\b", r"\bsalt.?water taste\b",
        r"नमकीन", r"कड़वा स्वाद",
        r"ఉప్పు రుచి", r"చేదు రుచి",
    ],
    "milky_appearance": [
        r"\bmilky\b", r"\bcloudy water\b", r"\bwhitish.*water\b",
        r"दूधिया", r"धुंधला पानी",
        r"పాలలాంటి", r"మబ్బు నీరు",
    ],
    "stomach_issues": [
        r"\bstomach pain\b", r"\bstomach ache\b", r"\bstomach issue", r"\bdiarrh(o|e)a\b", r"\bvomit",
        r"पेट दर्द", r"पेट की समस्या", r"उल्टी",
        r"కడుపు నొప్పి", r"కడుపు సమస్య", r"వాంతులు",
    ],
    "chlorine_smell": [
        r"\bchlorine smell\b", r"\bbleach smell\b", r"\bsmells like chlorine\b",
        r"क्लोरीन.*गंध", r"ब्लीच.*गंध",
        r"క్లోరిన్ వాసన",
    ],
    "colour_after_standing": [
        r"\bchanges colou?r\b", r"\bturns yellow after\b", r"\bafter standing\b",
        r"रखने पर.*रंग", r"रंग बदल",
        r"రంగు మారుతుంది", r"నిల్వ ఉంచినప్పుడు",
    ],
    "gritty_texture": [
        r"\bgritty\b", r"\bsandy\b", r"\bfeels like sand\b",
        r"किरकिरी", r"रेतीली",
        r"గరుకైన", r"ఇసుక వంటి",
    ],
    "foamy_water": [
        r"\bfoamy\b", r"\bbubbly water\b", r"\bfoam(ing)? in water\b",
        r"झागदार", r"बुलबुले",
        r"నురుగు", r"బుడగలు",
    ],
    "oily_sheen": [
        r"\boily\b", r"\boil (sheen|film|layer)\b", r"\bpetroleum smell\b",
        r"तैलीय", r"तेल की परत",
        r"నూనె పొర", r"ఆయిల్",
    ],
    "insects_visible": [
        r"\binsects?\b", r"\blarvae\b", r"\bworms? in water\b", r"\bbugs? in water\b",
        r"कीड़े", r"लार्वा",
        r"కీటకాలు", r"లార్వా",
    ],
    "skin_irritation": [
        r"\bskin irritation\b", r"\bskin rash\b", r"\bitchy skin\b", r"\bitching after bath",
        r"त्वचा.*जलन", r"खुजली",
        r"చర్మ చికాకు", r"దురద",
    ],
    "vessel_staining": [
        r"\bvessel stain", r"\bstains? on (my |the )?(steel|utensil|vessel)", r"\bstained utensils?\b",
        r"बर्तन.*दाग", r"बर्तनों पर मरक",
        r"పాత్రలపై మరక", r"వెసెల్ స్టెయినింగ్",
    ],
}


def extract_symptoms_from_text(text: str) -> list[dict]:
    """
    Scans free text (voice transcript or typed description) for known
    symptom trigger phrases using word-boundary regex matching.

    Returns a list of dicts: [{"symptom_id": str, "matched_phrase": str}, ...]
    Each entry records the ACTUAL phrase that matched, for transparency in
    the score breakdown's "triggered_by" field — so a citizen or reviewer
    can see exactly what text caused each detected symptom, rather than a
    black-box inference.

    Deliberately conservative: only fires on explicit phrase matches from
    the dictionary above. Does not attempt fuzzy matching, sentiment
    analysis, or inference beyond literal phrase presence — this keeps the
    extraction auditable and prevents the false-positive class of bug seen
    earlier with naive substring matching.
    """
    if not text or not text.strip():
        return []

    text_lower = text.lower()
    matches = []

    for symptom_id, patterns in SYMPTOM_TRIGGER_PHRASES.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                matches.append({
                    "symptom_id": symptom_id,
                    "matched_phrase": match.group(0),
                })
                break  # one match per symptom is enough, move to next symptom

    return matches


def extract_symptom_ids_only(text: str) -> list[str]:
    """Convenience wrapper — returns just the symptom_id strings, for
    direct use as a `symptoms` list alongside manually-selected chips."""
    return [m["symptom_id"] for m in extract_symptoms_from_text(text)]
