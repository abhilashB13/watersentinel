"""
Module: api/routers/geolocation.py
Purpose: Reverse geocode a citizen's GPS coordinates into pincode + area
name, for auto-filling the Report form's location fields. The raw lat/lng
is used ONLY for this one lookup and is NEVER stored anywhere — not in
water_reports, not in any log, not linked to any user identifier. This
matches the same privacy commitment already made for photo EXIF stripping
and pincode-only storage.
"""

import os
import logging
import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(tags=["geolocation"])

GOOGLE_GEOCODING_API_KEY = os.getenv("GOOGLE_GEOCODING_API_KEY", "") or os.getenv("GOOGLE_PLACES_API_KEY", "")


@router.get("/geolocation/reverse")
async def reverse_geocode(
    lat: float = Query(...),
    lng: float = Query(...),
):
    """
    Converts GPS coordinates to pincode + locality name.

    PRIVACY NOTE: lat/lng arrives in this request, is used ONCE to call the
    geocoding API, and is discarded the moment this function returns — it
    is never written to any table, log file, or session. Only the
    RESOLVED pincode/area (administrative-level location, same precision
    as what citizens already type manually) is returned to the frontend,
    which the citizen can then review/edit before submitting their report.
    """
    if not GOOGLE_GEOCODING_API_KEY:
        return {
            "success": False,
            "reason": "no_api_key",
            "message": "Location auto-detection is not configured. Please enter your pincode and area manually.",
        }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"latlng": f"{lat},{lng}", "key": GOOGLE_GEOCODING_API_KEY},
            )
            data = response.json()

            if data.get("status") != "OK" or not data.get("results"):
                return {
                    "success": False,
                    "reason": f"geocoding_failed_{data.get('status')}",
                    "message": "Could not determine your location. Please enter your pincode and area manually.",
                }

            result = data["results"][0]
            pincode = None
            area_name = None

            for component in result.get("address_components", []):
                types = component.get("types", [])
                if "postal_code" in types:
                    pincode = component.get("long_name")
                if "sublocality_level_1" in types or "sublocality" in types:
                    area_name = component.get("long_name")
                elif "locality" in types and not area_name:
                    area_name = component.get("long_name")

            if not pincode:
                return {
                    "success": False,
                    "reason": "no_pincode_found",
                    "message": "Could not determine your pincode precisely. Please enter it manually.",
                }

            return {
                "success": True,
                "pincode": pincode,
                "area_name": area_name or "",
                # NOTE: colony_name is intentionally NOT auto-filled — reverse
                # geocoding cannot reliably resolve to colony-level detail
                # (e.g. "MIG Colony Phase 1"). The citizen still confirms or
                # types this themselves, since it's the one field that
                # genuinely improves community-alert precision and can't be
                # safely guessed from coordinates alone.
                "message": "Location detected. Please confirm your colony name below.",
            }

    except Exception as e:
        logger.warning(f"Reverse geocoding failed: {e}")
        return {
            "success": False,
            "reason": str(e)[:100],
            "message": "Could not determine your location right now. Please enter it manually.",
        }
