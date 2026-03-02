from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder


from app.schemas.event import HoneypotEvent
from app.models import RawLog
from app.db.database import get_db
from app.services.normalize_event import normalize_event_dict

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
    row = RawLog(raw_json=jsonable_encoder(normalize_event_dict(event)))

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