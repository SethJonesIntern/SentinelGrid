import os
import threading
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from app.services.ml_model import (
    HONEYPOT_TYPES,
    clear_override,
    predict_distribution,
    set_override,
)
from app.services.honeynet_state import honeynet_state, plan_redistribution
from app.services.security import require_agent_token
from app.services.ml_scheduler import defer_next_run, run_pipeline_once

router = APIRouter()

# Guards on-demand refreshes so concurrent triggers can't stack multiple heavy
# pipeline runs at once (they'd compete for memory).
_refresh_lock = threading.Lock()


@router.get("/distribution")
def get_distribution():
    """
    Return the ML model's target honeynet composition: a distribution over
    honeypot types describing what the honeynet should be running right now.

    The model reads attack data from the database itself, so this endpoint
    takes no input.
    """
    return {"distribution": predict_distribution()}


@router.post("/distribution/refresh", dependencies=[Depends(require_agent_token)])
def refresh_distribution():
    """
    Re-run the ML pipeline on demand and return the freshly computed
    distribution. Blocks ~20-35s while the pipeline runs.

    Protected (agent token): it's a heavy operation. 409 if a refresh is already
    running; 502 if the pipeline run fails (see server logs).
    """
    if not _refresh_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A pipeline refresh is already running")
    try:
        if not run_pipeline_once():
            raise HTTPException(status_code=502, detail="ML pipeline run failed; see server logs")
        return {"refreshed": True, "distribution": predict_distribution()}
    finally:
        _refresh_lock.release()


@router.post("/distribution/override", dependencies=[Depends(require_agent_token)])
def override_distribution(distribution: Dict[str, float]):
    """
    Pin a specific distribution instead of the ML model's, for a hold window
    (defaults to ML_REFRESH_SECONDS). The scheduled inference timer is pushed out
    by the same window, so the override isn't immediately overwritten.

    Body: a JSON object of honeypot type -> weight, e.g. {"smtp": 1.0}. Values
    are normalised and FTP is forced to 0 (it can't scale). After the hold
    expires, the ML model takes over again.
    """
    unknown = set(distribution) - set(HONEYPOT_TYPES)
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown honeypot types: {sorted(unknown)}")
    if any(w < 0 for w in distribution.values()):
        raise HTTPException(status_code=400, detail="weights must be non-negative")
    if sum(distribution.values()) <= 0:
        raise HTTPException(status_code=400, detail="distribution must have a positive total")

    hold = float(os.getenv("ML_REFRESH_SECONDS", "900"))
    stored = set_override(distribution, hold)
    defer_next_run(hold)  # don't let the scheduler re-infer during the hold
    return {"override": True, "hold_seconds": hold, "distribution": stored}


@router.delete("/distribution/override", dependencies=[Depends(require_agent_token)])
def clear_distribution_override():
    """Drop the manual override so the ML model resumes on the next cycle."""
    clear_override()
    defer_next_run(0)  # let the scheduler re-infer on its next poll
    return {"override": False, "distribution": predict_distribution()}


@router.get("/honeynet/state")
def get_state():
    """
    Return how many honeypots of each type are currently running, plus the
    total. This is the state we redistribute against.

    Public (no token): read-only display data for the frontend to poll. Only the
    PUT below — which actually changes state — requires the agent token.
    """
    return {"counts": honeynet_state.counts(), "total": honeynet_state.total}


@router.put("/honeynet/state", dependencies=[Depends(require_agent_token)])
def put_state(counts: Dict[str, int]):
    """
    Sync our view of the honeynet with the counts actually deployed. The body
    is a mapping of honeypot type -> count.
    """
    honeynet_state.set_counts(counts)
    return {"counts": honeynet_state.counts(), "total": honeynet_state.total}


@router.get("/redistribution", dependencies=[Depends(require_agent_token)])
def get_redistribution():
    """
    Combine the model's target distribution with the current honeynet state to
    produce a concrete redistribution plan: the target count per honeypot type
    and the delta (start/stop) needed to get there, keeping the total fixed.
    """
    distribution = predict_distribution()
    return plan_redistribution(distribution, honeynet_state)
