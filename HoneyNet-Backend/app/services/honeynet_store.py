# app/services/honeynet_store.py
#
# Persistence layer for the honeynet state — SKELETON.
#
# `HoneynetState` (in honeynet_state.py) keeps the per-type counts in memory.
# A "store" is the thing that loads those counts on startup and saves them when
# they change, so the state survives a container restart / runs across workers.
#
# Two implementations:
#   - InMemoryHoneynetStore : the default; no persistence, behaves like today.
#   - DbHoneynetStore        : backs the counts with the `honeynet_state` table.
#
# The contract is intentionally tiny: a store maps to/from a plain
# {honeypot_type: count} dict. That keeps HoneynetState's public surface
# unchanged whether or not persistence is wired in.

from abc import ABC, abstractmethod
from typing import Dict

from app.services.ml_model import HONEYPOT_TYPES


class HoneynetStateStore(ABC):
    """Loads/saves the honeynet's per-type counts. Implementations decide where."""

    @abstractmethod
    def load(self) -> Dict[str, int]:
        """Return the persisted counts (missing types default to 0)."""
        raise NotImplementedError

    @abstractmethod
    def save(self, counts: Dict[str, int]) -> None:
        """Persist the full set of per-type counts."""
        raise NotImplementedError


class InMemoryHoneynetStore(HoneynetStateStore):
    """Non-persistent store — keeps counts in a dict. The current behaviour."""

    def __init__(self, counts: Dict[str, int] | None = None):
        self._counts: Dict[str, int] = {hp: 0 for hp in HONEYPOT_TYPES}
        if counts:
            self._counts.update(counts)

    def load(self) -> Dict[str, int]:
        return dict(self._counts)

    def save(self, counts: Dict[str, int]) -> None:
        self._counts.update(counts)


class DbHoneynetStore(HoneynetStateStore):
    """
    Persists counts to the `honeynet_state` table (one row per honeypot type).

    SKELETON STATUS: the read/write logic below is wired up, but this is NOT
    used by the live `honeynet_state` singleton yet. Before switching to it:
      1. Register `HoneypotCount` in app/models/__init__.py (or create the
         `honeynet_state` table some other way) — it's a shared DB, coordinate.
      2. Construct the singleton as `HoneynetState(store=DbHoneynetStore())`
         in honeynet_state.py.
      3. Decide write ownership: PUT /honeynet/state and the redistribution
         loop both call set_counts(), which will then persist here.
    """

    def __init__(self, session_factory=None):
        # Lazy default so test conftest's engine/session override is respected
        # and importing this module never requires a live DATABASE_URL.
        self._session_factory = session_factory

    def _factory(self):
        if self._session_factory is not None:
            return self._session_factory
        from app.db.database import SessionLocal

        return SessionLocal

    def load(self) -> Dict[str, int]:
        from sqlalchemy import select

        from app.models.honeynet_state import HoneypotCount

        counts = {hp: 0 for hp in HONEYPOT_TYPES}
        with self._factory()() as db:
            for row in db.execute(select(HoneypotCount)).scalars():
                if row.honeypot_type in counts:
                    counts[row.honeypot_type] = row.count
        return counts

    def save(self, counts: Dict[str, int]) -> None:
        from app.models.honeynet_state import HoneypotCount

        with self._factory()() as db:
            for honeypot_type, count in counts.items():
                row = db.get(HoneypotCount, honeypot_type)
                if row is None:
                    db.add(HoneypotCount(honeypot_type=honeypot_type, count=count))
                else:
                    row.count = count
            db.commit()
