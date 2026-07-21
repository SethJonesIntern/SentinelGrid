#!/usr/bin/env python3
"""
Clear all raw_logs rows for a source IP — demo reset between presentation runs.

Default IP is the demo/test source; pass another as an argument to override.

  python clear_demo_ip.py                 # clears 66.42.25.3
  python clear_demo_ip.py 1.2.3.4         # clears a different IP
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

DEFAULT_IP = "66.42.25.3"


def main() -> int:
    ip = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IP

    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set (check the backend .env).", file=sys.stderr)
        return 1

    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        deleted = conn.execute(
            text("DELETE FROM raw_logs WHERE raw_json->>'src_ip' = :ip"), {"ip": ip}
        ).rowcount
        conn.commit()
        remaining = conn.execute(
            text("SELECT count(*) FROM raw_logs WHERE raw_json->>'src_ip' = :ip"),
            {"ip": ip},
        ).scalar_one()
        total = conn.execute(text("SELECT count(*) FROM raw_logs")).scalar_one()

    print(f"{ip}: deleted {deleted}  |  remaining {remaining}  |  raw_logs total {total}")
    if remaining:
        print("(a straggler or two may land within a second — the source is live)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
