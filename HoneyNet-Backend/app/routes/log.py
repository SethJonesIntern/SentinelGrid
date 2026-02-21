from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.event import HoneypotEvent
from app.db.models import RawLog
from app.db.database import get_db

router = APIRouter()

@router.post("/log")
def log_event(
    event: HoneypotEvent,
    db: Session = Depends(get_db)
):
    """
    Accepts a HoneypotEvent and persists it to the database.
    """

    # Create ORM row from incoming event JSON
    row = RawLog(raw_json=event.model_dump())

    # Stage insert
    db.add(row)

    # Commit transaction
    db.commit()

    # Refresh so we can access generated fields (like id)
    db.refresh(row)

    return {
        "status": "accepted",
        "id": row.id   # useful confirmation
    }