from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.models import RawLog

router = APIRouter()

# Hard ceiling on how many rows a single /logs response can serialize. Without
# this, a caller (or the ML pipeline) requesting the whole table loads hundreds
# of thousands of rows into memory at once and OOM-kills the instance.
MAX_LIMIT = 20000


@router.get("/logs")
@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db), limit: int = 200):
    limit = max(1, min(limit, MAX_LIMIT))
    rows = (
        db.query(RawLog)
        .order_by(desc(RawLog.id))
        .limit(limit)
        .all()
    )

    return {
        "count": len(rows),
        "logs": [
            {
                "id": r.id,
                "raw_json": r.raw_json,
                "created_at": r.created_at,
                "active_honeypot_count": r.active_honeypot_count,
            }
            for r in rows
        ],
    }