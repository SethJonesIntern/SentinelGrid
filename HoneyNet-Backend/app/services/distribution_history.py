# app/services/distribution_history.py
#
# Rolling history of the last few UNIQUE honeypot-count compositions the honeynet
# has run — integer counts per type (e.g. {"smtp": 5, "ssh": 2, ...}), summing to
# the total. Stored in the `distribution_history` table so it survives restarts.
#
# We track COUNTS, not the ML weight percentages: the weights jitter on every
# inference (0.58, 0.66, ...) so they'd never dedup, whereas the integer counts
# only change when the actual composition changes. record() maintains a unique,
# most-recently-used list: an existing composition is moved to the front rather
# than duplicated. Resilient — a DB error is logged, never raised, so it can't
# break the endpoint serving the request.

import logging
from typing import Dict, List

from sqlalchemy import delete, select

from app.models.distribution_history import DistributionHistory

logger = logging.getLogger("distribution_history")

MAX_HISTORY = 5


def _session():
    # Imported lazily so tests' SessionLocal override is respected.
    from app.db.database import SessionLocal

    return SessionLocal()


def _ints(counts: Dict[str, int]) -> Dict[str, int]:
    return {k: int(v) for k, v in counts.items()}


def record(counts: Dict[str, int]) -> None:
    """
    Move a honeypot-count composition to the front of the unique history.

    The history holds distinct compositions only. If this one already exists
    anywhere in the list it's moved to the front (most recent); otherwise it's
    added at the front. Re-recording the one already at the front is a no-op, so
    steady-state polling doesn't churn.
    """
    comp = _ints(counts)
    try:
        with _session() as db:
            rows = (
                db.execute(
                    select(DistributionHistory).order_by(DistributionHistory.id.desc())
                )
                .scalars()
                .all()
            )
            match = next((r for r in rows if _ints(r.counts) == comp), None)

            if match is not None and rows[0].id == match.id:
                return  # already at the front — nothing to do

            if match is not None:
                db.delete(match)  # remove from its current position

            db.add(DistributionHistory(counts=comp))  # re-insert at the front
            db.commit()

            # Trim to the most recent MAX_HISTORY rows.
            keep = (
                db.execute(
                    select(DistributionHistory.id)
                    .order_by(DistributionHistory.id.desc())
                    .limit(MAX_HISTORY)
                )
                .scalars()
                .all()
            )
            if keep:
                db.execute(
                    delete(DistributionHistory).where(DistributionHistory.id < min(keep))
                )
                db.commit()
    except Exception as exc:  # never let history recording break the request
        logger.warning("could not record distribution history: %s", exc)


def get_history() -> List[dict]:
    """The last MAX_HISTORY unique count compositions, most recent first."""
    try:
        with _session() as db:
            rows = (
                db.execute(
                    select(DistributionHistory)
                    .order_by(DistributionHistory.id.desc())
                    .limit(MAX_HISTORY)
                )
                .scalars()
                .all()
            )
            return [
                {
                    "counts": r.counts,
                    "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.warning("could not read distribution history: %s", exc)
        return []


def clear() -> None:
    """Delete all history rows (used by tests)."""
    with _session() as db:
        db.execute(delete(DistributionHistory))
        db.commit()
