#!/usr/bin/env python3
"""
Remove duplicate rows from the `raw_logs` table.

A duplicate is a row whose `raw_json` equals another row's. We compare on
`md5(raw_json::text)`: JSONB's text form is canonical in Postgres (keys sorted,
whitespace normalized), so equal values hash equally — and hashing once per row
is far cheaper than an O(n^2) `raw_json = raw_json` self-join, which trips the
DB statement timeout. This happens when the forwarder re-sends a batch (retry /
restart) and the same normalized event gets inserted more than once. Within each
group of equal rows we KEEP the earliest (lowest id) and delete the rest.

Safe by default: this only PREVIEWS what it would delete. Pass --apply to
actually delete. Config (DATABASE_URL) comes from the backend .env, same as the
app.

  python dedupe_logs.py            # dry run: show what would be deleted
  python dedupe_logs.py --apply    # actually delete the duplicates
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# How many doomed rows to delete per transaction. Keeps each statement small so
# it stays well under the DB statement timeout and holds locks only briefly.
BATCH_SIZE = 25000

# Materialize the ids to delete ONCE: the oldest row (lowest id) in each
# duplicate group is kept, every other copy is doomed. Computing the window over
# the whole table once (into a temp table) is far cheaper than re-running it per
# batch. Temp table lives for the connection session.
BUILD_DOOMED = text(
    """
    CREATE TEMP TABLE doomed_ids ON COMMIT PRESERVE ROWS AS
    SELECT id FROM (
        SELECT id,
               row_number() OVER (
                   PARTITION BY md5(raw_json::text) ORDER BY id
               ) AS rn
        FROM raw_logs
    ) ranked
    WHERE rn > 1
    """
)

# Pop a batch of ids out of doomed_ids and delete those rows from raw_logs in one
# atomic step, so we never delete a row we haven't also removed from the worklist.
DELETE_BATCH = text(
    """
    WITH batch AS (
        DELETE FROM doomed_ids
        WHERE id IN (SELECT id FROM doomed_ids LIMIT :batch)
        RETURNING id
    )
    DELETE FROM raw_logs WHERE id IN (SELECT id FROM batch)
    """
)

# dupes = total rows - distinct rows.
COUNT_DUPES = text(
    """
    SELECT count(*) - count(DISTINCT md5(raw_json::text)) AS dupes
    FROM raw_logs
    """
)

# A small preview of the worst offenders (how many copies each kept row has).
PREVIEW_DUPES = text(
    """
    SELECT min(id) AS keep_id, count(*) AS copies
    FROM raw_logs
    GROUP BY md5(raw_json::text)
    HAVING count(*) > 1
    ORDER BY copies DESC, keep_id
    LIMIT 10
    """
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove duplicate raw_logs rows.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete duplicates. Without this flag, only previews.",
    )
    args = parser.parse_args()

    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set (check the backend .env).", file=sys.stderr)
        return 1

    engine = create_engine(database_url, future=True)

    with engine.connect() as conn:
        # Give the dedupe room to run on larger tables (default pooler timeout
        # is short). Applies for this session only.
        conn.execute(text("SET statement_timeout = '120s'"))

        total = conn.execute(text("SELECT count(*) FROM raw_logs")).scalar_one()
        dupes = conn.execute(COUNT_DUPES).scalar_one()

        print(f"raw_logs: {total} row(s), {dupes} duplicate(s) to remove "
              f"({total - dupes} would remain).")

        if dupes == 0:
            print("Nothing to do -- no duplicates found.")
            return 0

        print("\nTop duplicate groups (kept id -> total copies):")
        for keep_id, copies in conn.execute(PREVIEW_DUPES):
            print(f"  id {keep_id}: {copies} copies ({copies - 1} extra)")

        if not args.apply:
            print("\nDry run -- nothing deleted. Re-run with --apply to delete.")
            return 0

        # Close the read transaction that the queries above auto-started, so the
        # explicit per-step transactions below can begin cleanly. Commit (not
        # rollback) so the SET statement_timeout stays in effect for this session.
        conn.commit()

        # Destructive section: build the worklist once, then delete in batches,
        # each its own transaction so progress is durable and locks stay short.
        with conn.begin():
            conn.execute(BUILD_DOOMED)

        deleted = 0
        while True:
            with conn.begin():
                result = conn.execute(DELETE_BATCH, {"batch": BATCH_SIZE})
            if result.rowcount == 0:
                break
            deleted += result.rowcount
            print(f"  deleted {deleted}/{dupes}...")

        print(f"\nDeleted {deleted} duplicate row(s).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
