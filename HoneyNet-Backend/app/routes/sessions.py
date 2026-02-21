from fastapi import APIRouter, Depends
from app.db.database import get_db

router = APIRouter()

@router.get("/sessions")
def get_sessions(db = Depends(get_db)):
    # temporary skeleton until real query is added
    return {
        "status": "connected",
        "message": "DB retrieval not implemented yet"
    }