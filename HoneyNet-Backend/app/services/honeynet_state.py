# app/services/honeynet_state.py

from typing import Dict

from app.services.ml_model import HONEYPOT_TYPES

# The honeynet always runs one "base" honeypot of every type, so every kind of
# attack has somewhere to land regardless of what the model says. With 6 types
# that's 6 fixed honeypots.
BASE_PER_TYPE = 1

# Total honeypots running at once. The base honeypots take up
# BASE_PER_TYPE * len(HONEYPOT_TYPES) of these; the rest are the "distributable"
# pool that the ML distribution gets to place (12 - 6 = 6 of them).
TOTAL_HONEYPOTS = 12


class HoneynetState:
    """
    Tracks how many honeypots of each type are currently running in the
    honeynet.

    The ML model only tells us the *target distribution* (a set of fractions
    that sum to 1) for the distributable pool. It has no idea how many
    containers we actually have, so it cannot tell us how many to start or stop.
    This object holds that missing piece: the current count per honeypot type.
    Combined with a target distribution it lets us compute a concrete
    redistribution plan (see ``plan_redistribution``).

    This is in-memory, single-process state. If/when the control loop needs to
    survive restarts or run across workers, back this with the database instead
    — the public surface here is the contract to preserve.
    """

    def __init__(self, counts: Dict[str, int] | None = None):
        self._counts: Dict[str, int] = {hp: 0 for hp in HONEYPOT_TYPES}
        if counts:
            self.set_counts(counts)

    @property
    def total(self) -> int:
        """Total number of honeypots currently running across all types."""
        return sum(self._counts.values())

    def counts(self) -> Dict[str, int]:
        """A copy of the current per-type counts (callers can't mutate state)."""
        return dict(self._counts)

    def set_counts(self, counts: Dict[str, int]) -> None:
        """
        Overwrite the current per-type counts. Used to sync our view of the
        honeynet with reality (e.g. after the orchestrator reports what's
        actually deployed).
        """
        for honeypot, count in counts.items():
            if honeypot not in self._counts:
                raise ValueError(f"Unknown honeypot type: {honeypot!r}")
            if count < 0:
                raise ValueError(f"Honeypot count cannot be negative: {honeypot}={count}")
        for honeypot, count in counts.items():
            self._counts[honeypot] = count


def _largest_remainder(distribution: Dict[str, float], total: int) -> Dict[str, int]:
    """
    Split ``total`` integer slots across the honeypot types in proportion to
    ``distribution``, summing to exactly ``total``.

    Naive rounding of ``weight * total`` rarely sums back to ``total``, so we
    floor every value and then hand the leftover slots to the types with the
    largest fractional parts.
    """
    raw = {hp: distribution.get(hp, 0.0) * total for hp in HONEYPOT_TYPES}
    counts = {hp: int(value) for hp, value in raw.items()}

    leftover = total - sum(counts.values())
    by_remainder = sorted(
        HONEYPOT_TYPES,
        key=lambda hp: raw[hp] - counts[hp],
        reverse=True,
    )
    for hp in by_remainder[:leftover]:
        counts[hp] += 1

    return counts


def allocate(
    distribution: Dict[str, float],
    total: int = TOTAL_HONEYPOTS,
    base_per_type: int = BASE_PER_TYPE,
) -> Dict[str, int]:
    """
    Turn the model's distribution into concrete per-type honeypot counts.

    Every type first gets ``base_per_type`` honeypots (the always-on base),
    then the remaining "distributable" slots are spread across the types
    according to ``distribution`` using the largest-remainder method. The
    returned counts sum to exactly ``total`` and every type is guaranteed at
    least its base.
    """
    base = base_per_type * len(HONEYPOT_TYPES)
    distributable = total - base
    if distributable < 0:
        raise ValueError(
            f"total ({total}) is smaller than the base allocation ({base}); "
            f"can't give every type {base_per_type} honeypot(s)"
        )

    extra = _largest_remainder(distribution, distributable)
    return {hp: base_per_type + extra[hp] for hp in HONEYPOT_TYPES}


def plan_redistribution(
    distribution: Dict[str, float],
    state: HoneynetState,
    total: int = TOTAL_HONEYPOTS,
) -> Dict[str, object]:
    """
    Compute how to move from the current honeynet state to the target
    composition: one base honeypot per type plus the model's distribution over
    the remaining slots, summing to ``total``.

    Returns the target per-type counts and the per-type deltas (positive =
    start that many, negative = stop that many) so the orchestrator knows
    exactly what to spin up and tear down.
    """
    current = state.counts()
    target = allocate(distribution, total)
    delta = {hp: target[hp] - current[hp] for hp in HONEYPOT_TYPES}
    return {"current": current, "target": target, "delta": delta}


# Module-level singleton holding the live honeynet state for this process.
honeynet_state = HoneynetState()
