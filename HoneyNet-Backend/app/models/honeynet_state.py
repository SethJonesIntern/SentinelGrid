from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class HoneypotCount(Base):
    """
    One row per honeypot type: how many of that type are currently running.

    This is the persistent backing for `HoneynetState` so the count survives
    container restarts (App Runner replaces the container on every deploy, which
    wipes in-memory state).

    NOTE: deliberately NOT imported in `app/models/__init__.py` yet, so
    `Base.metadata.create_all` on startup will NOT create this table in the
    shared hosted DB until we choose to. Before enabling the DB store, either
    register it there or create the `honeynet_state` table explicitly (and give
    the team a heads-up — it's a shared database).
    """

    __tablename__ = "honeynet_state"

    honeypot_type = Column(Text, primary_key=True)
    count = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
