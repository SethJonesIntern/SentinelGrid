#!/usr/bin/env python3
"""
Create and seed the `honeynet_state` table (one row per honeypot type holding
its current running count).

`Base.metadata.create_all` is disabled for the live DB, so this one-off
migration creates the table from the `HoneypotCount` model and seeds a row for
every honeypot type at count 1 (historically there has been one of each).

Idempotent: the table is created only if missing, and seeding skips types that
already have a row. Safe to run more than once.

  python migrations/create_honeynet_state.py
"""

import os
import sys

# Make the project root importable when run as `python migrations/<file>.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.honeynet_state import HoneypotCount
from app.services.ml_model import HONEYPOT_TYPES

SEED_COUNT = 1


def main() -> int:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set (check the backend .env).", file=sys.stderr)
        return 1

    engine = create_engine(database_url, future=True)

    # Create just this table if it doesn't exist.
    HoneypotCount.__table__.create(bind=engine, checkfirst=True)
    print("Ensured table 'honeynet_state' exists.")

    Session = sessionmaker(bind=engine, future=True)
    with Session() as db:
        existing = {
            row.honeypot_type
            for row in db.execute(select(HoneypotCount)).scalars()
        }
        added = 0
        for hp_type in HONEYPOT_TYPES:
            if hp_type not in existing:
                db.add(HoneypotCount(honeypot_type=hp_type, count=SEED_COUNT))
                added += 1
        db.commit()

        rows = db.execute(select(HoneypotCount)).scalars().all()
        print(f"Seeded {added} new row(s). honeynet_state now has {len(rows)} row(s):")
        for row in sorted(rows, key=lambda r: r.honeypot_type):
            print(f"  {row.honeypot_type}: {row.count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
