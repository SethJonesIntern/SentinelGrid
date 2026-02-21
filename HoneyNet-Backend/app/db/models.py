from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class RawLog(Base):
    __tablename__ = "raw_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_json = Column(JSONB, nullable=False)