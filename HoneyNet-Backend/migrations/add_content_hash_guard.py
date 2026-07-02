#!/usr/bin/env python3
"""
Add the content_hash dedup guard to raw_logs:
  1. add the `content_hash` column (if missing)
  2. backfill it for existing rows (using the SAME hash the app uses)
  3. remove existing duplicates (keep the lowest id per hash)
  4. create the UNIQUE index

After this, the /log endpoint's INSERT can't create duplicate events — identical
re-sends collide on content_hash and are dropped. Idempotent / re-runnable.

  python migrations/add_content_hash_guard.py
"""

import os
import sys

# Make the project root importable when run as `python migrations/<file>.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
from app.routes.log import _content_hash  # exact same hash the app writes


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set (check the backend .env).", file=sys.stderr)
        return 1

    engine = create_engine(database_url, future=True)
    with engine.connect() as conn:
        conn.execute(text("SET statement_timeout = '120s'"))
        conn.commit()

        # 1. column
        conn.execute(text("ALTER TABLE raw_logs ADD COLUMN IF NOT EXISTS content_hash text"))
        conn.commit()
        print("Ensured content_hash column exists.")

        # 2. backfill (only rows missing it)
        rows = conn.execute(
            text("SELECT id, raw_json FROM raw_logs WHERE content_hash IS NULL")
        ).fetchall()
        print(f"Backfilling {len(rows)} row(s)...")
        params = [{"h": _content_hash(r.raw_json), "id": r.id} for r in rows]
        for i in range(0, len(params), 1000):
            conn.execute(
                text("UPDATE raw_logs SET content_hash = :h WHERE id = :id"),
                params[i : i + 1000],
            )
            conn.commit()

        # 3. remove existing duplicates (keep the lowest id per content_hash)
        result = conn.execute(
            text(
                """
                DELETE FROM raw_logs
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id, row_number() OVER (
                            PARTITION BY content_hash ORDER BY id
                        ) AS rn
                        FROM raw_logs
                    ) ranked
                    WHERE rn > 1
                )
                """
            )
        )
        conn.commit()
        print(f"Removed {result.rowcount} duplicate row(s).")

        # 4. unique index
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS raw_logs_content_hash_uniq "
                "ON raw_logs (content_hash)"
            )
        )
        conn.commit()
        print("Created UNIQUE index raw_logs_content_hash_uniq.")

        total = conn.execute(text("SELECT count(*) FROM raw_logs")).scalar_one()
        print(f"Done. raw_logs now has {total} row(s), dedup guard active.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
