"""
Module: api/routers/health.py
Purpose: Health check endpoint. Used by Cloud Run, mobile app,
         and deployment pipeline to verify server is alive.
"""

import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint. Returns server status and readiness
    of all required components (API key, ChromaDB, database).
    """
    api_key = os.getenv("GOOGLE_API_KEY", "")
    chroma_ready = Path(os.getenv("CHROMA_DB_PATH", "./data/chroma_db")).exists()
    db_ready = Path(os.getenv("WATER_INTEL_DB_PATH", "./data/reports.db")).exists()

    all_ready = bool(api_key) and chroma_ready and db_ready

    return {
        "status": "ok" if all_ready else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "google_api_key": "configured" if api_key else "MISSING — add to .env",
            "chroma_db": "ready" if chroma_ready else "not found — run rag/ingest.py",
            "sqlite_db": "ready" if db_ready else "not found — run seed_mock_data.py",
        },
        "agents_ready": all_ready,
        "message": (
            "All systems ready" if all_ready
            else "Some components missing — check components above"
        ),
    }
