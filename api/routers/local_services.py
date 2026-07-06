"""
Module: api/routers/local_services.py
Real Google Places API integration for nearby water tank cleaning / RO
service providers, using the citizen's lat/lng. Falls back to the existing
static list if the API key is missing, quota/billing fails, or zero real
results are found for that specific area — reframed honestly as
"general services" rather than presented as location-specific when it isn't.
"""

import os
import logging
import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(tags=["local_services"])

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

# Existing static list — used as the honest fallback, not the primary source
STATIC_FALLBACK_SERVICES = [
    {"name": "Tara Water Tank Cleaning", "desc": "Underground & overhead tank cleaning — Hyderabad", "phone": "98490-XXXXX", "icon": "🚿", "is_live": False},
    {"name": "Aqua Pure RO Services", "desc": "RO installation, AMC, filter replacement", "phone": "94400-XXXXX", "icon": "🔧", "is_live": False},
]


@router.get("/local-services")
async def get_local_services(
    lat: float = Query(...),
    lng: float = Query(...),
    query: str = Query(default="water tank cleaning RO service"),
):
    """
    Returns real nearby water services via Google Places if available,
    otherwise the static fallback list, clearly marked with is_live so the
    frontend can honestly label which type of result is being shown.
    """
    if not GOOGLE_PLACES_API_KEY:
        return {"services": STATIC_FALLBACK_SERVICES, "source": "static_fallback", "reason": "no_api_key"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params={
                    "location": f"{lat},{lng}",
                    "radius": 5000,
                    "keyword": query,
                    "key": GOOGLE_PLACES_API_KEY,
                },
            )
            data = response.json()

            if data.get("status") != "OK" or not data.get("results"):
                logger.warning(f"Places API returned no results or error: {data.get('status')}")
                return {"services": STATIC_FALLBACK_SERVICES, "source": "static_fallback", "reason": f"no_results_or_error_{data.get('status')}"}

            services = []
            for place in data["results"][:5]:
                services.append({
                    "name": place.get("name", "Unknown"),
                    "desc": place.get("vicinity", ""),
                    "phone": "",  # Nearby Search doesn't return phone; would need Place Details call
                    "icon": "📍",
                    "rating": place.get("rating"),
                    "is_live": True,
                })

            return {"services": services, "source": "google_places", "reason": None}

    except Exception as e:
        logger.warning(f"Places API call failed, using static fallback: {e}")
        return {"services": STATIC_FALLBACK_SERVICES, "source": "static_fallback", "reason": str(e)[:100]}
