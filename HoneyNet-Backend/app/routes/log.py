import hashlib
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.encoders import jsonable_encoder


from app.schemas.event import HoneypotEvent
from app.models import RawLog
from app.db.database import get_db
from app.services.normalize_event import normalize_event_dict, resolve_honeypot_type
from app.services.honeynet_state import honeynet_state


def _content_hash(raw: dict) -> str:
    """Stable md5 of the normalized event, used as the dedup key."""
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(canonical.encode()).hexdigest()

router = APIRouter()

@router.post("/log")
def log_event(
    event: HoneypotEvent,
    db: Session = Depends(get_db)
):
    """
    Accepts a HoneypotEvent and persists it to the database.
    """

    # Drop forwarder liveness pings — operational telemetry, not attack data.
    # Return 200 so the forwarder treats it as delivered (won't retry/DLQ it).
    if event.event_type.strip().lower().startswith("forwarder"):
        return {"status": "ignored", "reason": "forwarder heartbeat not persisted"}

    # Snapshot how many honeypots of this event's type are currently running,
    # so each log captures the honeynet state at the moment it was recorded.
    # active_honeypot_count is NOT NULL, so fall back to 1 when the type is
    # unknown (matches the column's historical default).
    hp_type = resolve_honeypot_type(event)
    type_count = honeynet_state.counts().get(hp_type) if hp_type else None
    active_count = type_count if type_count is not None else 1

    # Create ORM row from incoming event JSON
    raw = jsonable_encoder(normalize_event_dict(event))
    row = RawLog(
        raw_json=raw,
        active_honeypot_count=active_count,
        content_hash=_content_hash(raw),
    )

    # Stage insert
    db.add(row)

    # Commit; the UNIQUE content_hash rejects duplicate events (forwarder
    # re-sends) — treat that as an accepted no-op rather than an error.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate"}

    # Refresh so we can access generated fields (like id)
    db.refresh(row)

    return {
        "status": "accepted",
        "id": row.id,             # useful confirmation
        "active_honeypot_count": row.active_honeypot_count,
    }