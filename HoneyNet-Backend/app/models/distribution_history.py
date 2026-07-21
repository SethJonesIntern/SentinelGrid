from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class DistributionHistory(Base):
    """
    One row per UNIQUE honeypot-count composition the honeynet has run — a
    change log of how the mix (integer counts per type, summing to the total)
    has adapted over time. The service (app/services/distribution_history.py)
    keeps the list unique + trims to the most recent few, so this table stays
    tiny.
    """

    __tablename__ = "distribution_history"

    id = Column(Integer, primary_key=True, index=True)
    counts = Column(JSONB, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
