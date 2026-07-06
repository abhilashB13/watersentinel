"""
Module: agents/water_profiler/photo_analyzer.py
Purpose: Real Gemini Vision analysis of citizen-submitted water sample
photos. This is genuine multimodal API code — not a fallback, not a
placeholder — requiring a working Gemini API key with available quota to
execute. When quota is unavailable, this fails gracefully and the caller
falls back to text/voice/manual-symptom-only scoring (see report.py).

WHY THIS IS THE RIGHT ARCHITECTURE:
Photo analysis (is this water, what colour, is sediment visible) is
fundamentally a computer vision task that cannot be meaningfully
approximated with rule-based logic the way text symptom extraction can.
There is no honest non-LLM fallback for this — attempting one (e.g. crude
average-pixel-colour analysis) would produce unreliable results that could
mislead a citizen more than having no photo analysis at all. This module
therefore calls Gemini Vision directly and is explicit about failing when
quota is unavailable, rather than faking a result.
"""

import os
import json
import base64
import logging

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"

VISION_ANALYSIS_PROMPT = """You are analyzing a photo submitted by a citizen reporting a water quality concern in India, as part of a water safety diagnostic tool.

Analyze the image and respond with ONLY a valid JSON object (no markdown, no explanation) in exactly this structure:

{
  "is_water_photo": true or false,
  "confidence": a number from 0 to 100 representing your confidence that this image genuinely shows water in a container/vessel/tap/source,
  "water_colour": one of "clear", "yellow", "brown", "black", "milky_white", "greenish", "unclear",
  "visible_sediment": true or false,
  "visible_foam_or_bubbles": true or false,
  "visible_oily_sheen": true or false,
  "container_type": one of "glass", "steel_vessel", "bucket", "tap_directly", "bottle", "other", "not_applicable",
  "notes": a brief one-sentence factual observation about what is visible, in plain English

If the image does NOT show water (e.g. it's a person, an unrelated object, a screenshot, or too blurry to tell), set is_water_photo to false and confidence to your actual confidence level, and set water_colour to "unclear".

Respond with ONLY the JSON object, nothing else."""


def analyze_water_photo(photo_base64: str) -> dict:
    """
    Sends a citizen-submitted photo to Gemini Vision for real multimodal
    analysis. Returns a structured dict of visual findings, or an explicit
    error dict if the API call fails (quota exhausted, invalid key, etc.) —
    callers must check for the "success" key before using the result, and
    must NOT silently treat a failed call as "no findings" without flagging
    that analysis did not actually run.
    """
    if not photo_base64:
        return {"success": False, "error": "No photo provided", "analysis_attempted": False}

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "GOOGLE_API_KEY not configured",
            "analysis_attempted": False,
        }

    try:
        from google import genai
        from google.genai import types

        # Strip data URL prefix if present (e.g. "data:image/jpeg;base64,")
        if "," in photo_base64 and photo_base64.strip().startswith("data:"):
            photo_base64 = photo_base64.split(",", 1)[1]

        image_bytes = base64.b64decode(photo_base64)

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                VISION_ANALYSIS_PROMPT,
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,  # low temperature — this is a factual extraction task, not creative
                max_output_tokens=300,
            ),
        )

        raw_text = response.text.strip()
        # Strip markdown code fences if Gemini wraps the JSON in ```json ... ```
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        parsed = json.loads(raw_text)

        return {
            "success": True,
            "analysis_attempted": True,
            "is_water_photo": parsed.get("is_water_photo", False),
            "confidence": parsed.get("confidence", 0),
            "water_colour": parsed.get("water_colour", "unclear"),
            "visible_sediment": parsed.get("visible_sediment", False),
            "visible_foam_or_bubbles": parsed.get("visible_foam_or_bubbles", False),
            "visible_oily_sheen": parsed.get("visible_oily_sheen", False),
            "container_type": parsed.get("container_type", "not_applicable"),
            "notes": parsed.get("notes", ""),
        }

    except json.JSONDecodeError as e:
        logger.warning(f"Photo analysis returned non-JSON response: {e}")
        return {
            "success": False,
            "error": f"Vision model returned unparseable response: {e}",
            "analysis_attempted": True,
        }
    except Exception as e:
        error_str = str(e)
        logger.warning(f"Photo analysis failed: {error_str}")
        return {
            "success": False,
            "error": error_str,
            "analysis_attempted": True,
            "quota_exhausted": "429" in error_str or "RESOURCE_EXHAUSTED" in error_str,
        }


CONFIDENCE_THRESHOLD = 60  # below this, treat as "couldn't determine" not a false negative


def photo_findings_to_symptoms(vision_result: dict) -> list[str]:
    """
    Converts Gemini Vision's structured findings into the same symptom
    identifier vocabulary used elsewhere in the app (yellow_colour,
    black_colour, milky_appearance, etc.) — so a photo can contribute to
    scoring using the EXACT SAME severity table as manually-selected chips
    or voice-extracted symptoms, rather than a separate parallel scoring path.

    CONFIDENCE GATING: AI vision/voice processing is probabilistic, not
    deterministic like rule-based symptom matching — the same photo can
    occasionally be misjudged (bad lighting, ambiguous container, etc.).
    Rather than silently feeding a low-confidence guess into a citizen's
    water-safety score, findings below CONFIDENCE_THRESHOLD are treated as
    "AI could not determine this confidently" — same honest degradation
    already used for full API failures — rather than acted on as if certain.
    """
    if not vision_result.get("success") or not vision_result.get("is_water_photo"):
        return []

    confidence = vision_result.get("confidence", 0)
    if confidence < CONFIDENCE_THRESHOLD:
        return []  # honest non-detection — caller shows "low confidence" messaging, doesn't silently score it

    symptoms = []
    colour = vision_result.get("water_colour", "")

    if colour in ("yellow", "brown"):
        symptoms.append("yellow_colour")
    elif colour == "black":
        symptoms.append("black_colour")
    elif colour == "milky_white":
        symptoms.append("milky_appearance")
    elif colour == "greenish":
        symptoms.append("blue_green_stain")

    if vision_result.get("visible_sediment"):
        symptoms.append("gritty_texture")
    if vision_result.get("visible_foam_or_bubbles"):
        symptoms.append("foamy_water")
    if vision_result.get("visible_oily_sheen"):
        symptoms.append("oily_sheen")

    return symptoms
