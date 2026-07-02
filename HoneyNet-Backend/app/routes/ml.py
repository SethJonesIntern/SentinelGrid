import threading
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from app.services.ml_model import predict_distribution
from app.services.honeynet_state import honeynet_state, plan_redistribution
from app.services.security import require_agent_token
from app.services.ml_scheduler import run_pipeline_once

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
