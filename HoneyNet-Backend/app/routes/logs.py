from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.models import RawLog

router = APIRouter()

@router.get("/logs")
@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db), limit: int = 1000000):
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
            }
            for r in rows
        ],
    }