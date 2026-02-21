from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func

Base = declarative_base()

class RawLog(Base):
    __tablename__ = "raw_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_json = Column(Text, nullable=False)