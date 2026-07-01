from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class HoneypotCount(Base):
    """
    One row per honeypot type: how many of that type are currently running.

    This is the persistent backing for `HoneynetState` so the count survives
    container restarts (App Runner replaces the container on every deploy, which
    wipes in-memory state).

    Registered in `app/models/__init__.py` and created in the shared DB via
    `migrations/create_honeynet_state.py` (seeded with one row per type at
    count 1). The live `honeynet_state` singleton does not use this table yet —
    to activate persistence, construct it with
    `HoneynetState(store=DbHoneynetStore())` in honeynet_state.py.
    """

    __tablename__ = "honeynet_state"

    honeypot_type = Column(Text, primary_key=True)
    count = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
