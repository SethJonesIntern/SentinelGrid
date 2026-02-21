# app/db/database.py

import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables from a .env file in the project root (if present)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # checks connections before using them
    future=True,         # SQLAlchemy 2.0 style behavior
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

def get_db():
    """
    FastAPI dependency that provides a per-request SQLAlchemy Session
    and guarantees it is closed after the request completes.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()