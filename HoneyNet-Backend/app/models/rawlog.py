
from sqlalchemy import Column, Integer, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base


class RawLog(Base):
    __tablename__ = "raw_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_json = Column(JSONB, nullable=False)

    # How many honeypots of this event's type were running when it was logged,
    # captured from the honeynet state at ingest. Pre-existing column (NOT NULL,
    # defaults to 1 — historically there was one honeypot of each type).
    active_honeypot_count = Column(Integer, nullable=False, server_default="1")

    # md5 of the canonical raw_json, UNIQUE — the dedup guard. Identical events
    # (forwarder re-sends) collide here and are dropped at insert. Nullable so
    # rows created without it (e.g. tests inserting directly) don't clash; the
    # /log ingest path always sets it. See app/routes/log.py.
    content_hash = Column(Text, unique=True, index=True, nullable=True)