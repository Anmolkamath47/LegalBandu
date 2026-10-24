from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..config import settings
from ..database import get_db
from ..services.ai_service import is_gemini_configured

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def check_health(db: Session = Depends(get_db)):
    """Health check endpoint confirming API status, database connectivity, and Gemini AI status."""
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database_connected": db_connected,
        "gemini_configured": is_gemini_configured(),
    }
