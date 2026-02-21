from fastapi import APIRouter, Depends
from app.schemas.event import HoneypotEvent
from app.db.models import RawLog
from app.db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

# Temporary in-memory store (checkpoint only)
LOG_STORE = []

@router.post("/log")
def log_event(event: HoneypotEvent, db: Session = Depends(get_db)): #STILL HAVE TO WRITE GET_DB, ON TODO LIST
    
    row = RawLog(raw_json=event.model_dump_json())
    db.add(row)
    db.commit()

    return {
        "status": "accepted",
        "stored_count": len(LOG_STORE)
    }