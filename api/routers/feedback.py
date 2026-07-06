"""
Module: api/routers/feedback.py
Real persistence for the "Rate our Agent" feature — previously fully
cosmetic (rating/text captured in local UI state, discarded on submit,
never sent anywhere). Now genuinely stored, with an aggregate endpoint
for Home page display.
"""

import sqlite3
import logging
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(tags=["feedback"])

DB_PATH = "data/reports.db"


class FeedbackRequest(BaseModel):
    session_id: str = Field(default="")
    rating: int = Field(..., ge=1, le=5)
    feedback_chips: list[str] = Field(default=[])
    feedback_text: str = Field(default="", max_length=1000)


def _init_feedback_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            rating INTEGER NOT NULL,
            feedback_chips TEXT,
            feedback_text TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Persists citizen feedback. Wrapped so a DB failure never breaks the
    citizen-facing flow — feedback is low-stakes compared to a failed
    water-safety score, so we fail silently on the backend here while
    the frontend still shows its thank-you confirmation either way.
    """
    try:
        _init_feedback_table()
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO agent_feedback (session_id, rating, feedback_chips, feedback_text, timestamp) VALUES (?, ?, ?, ?, ?)",
            (request.session_id, request.rating, ",".join(request.feedback_chips), request.feedback_text, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        logger.warning(f"Feedback persistence failed (non-fatal): {e}")
        return {"success": False}


@router.get("/feedback/summary")
async def get_feedback_summary():
    """
    Aggregate rating for Home page display. Returns average_rating and
    total_count. Caller (frontend) should gate display on a minimum sample
    size (e.g. only show if total_count >= 10) to avoid presenting a
    misleadingly small sample as meaningful social proof.
    """
    try:
        _init_feedback_table()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT AVG(rating), COUNT(*) FROM agent_feedback")
        avg_rating, total_count = cursor.fetchone()
        conn.close()
        return {
            "average_rating": round(avg_rating, 1) if avg_rating else 0,
            "total_count": total_count or 0,
        }
    except Exception as e:
        logger.warning(f"Feedback summary query failed: {e}")
        return {"average_rating": 0, "total_count": 0}
