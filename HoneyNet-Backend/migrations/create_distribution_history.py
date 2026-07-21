#!/usr/bin/env python3
"""
Create the `distribution_history` table (change log of the honeynet's honeypot
COUNTS over time).

Drops any existing table first: the earlier version stored weight percentages in
a `distribution` column; this stores integer counts in a `counts` column, so the
old rows/schema are replaced. Idempotent — safe to run more than once.

  python migrations/create_distribution_history.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
from app.models.distribution_history import DistributionHistory


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set (check the backend .env).", file=sys.stderr)
        return 1

    engine = create_engine(database_url, future=True)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS distribution_history"))
        conn.commit()
    DistributionHistory.__table__.create(bind=engine, checkfirst=True)
    print("Recreated table 'distribution_history' (counts schema).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
