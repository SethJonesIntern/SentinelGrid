from typing import Dict

from fastapi import APIRouter

from app.services.ml_model import predict_distribution
from app.services.honeynet_state import honeynet_state, plan_redistribution

router = APIRouter()


@router.get("/distribution")
def get_distribution():
    """
    Return the ML model's target honeynet composition: a distribution over
    honeypot types describing what the honeynet should be running right now.

    The model reads attack data from the database itself, so this endpoint
    takes no input.
    """
    return {"distribution": predict_distribution()}


@router.get("/honeynet/state")
def get_state():
    """
    Return how many honeypots of each type are currently running, plus the
    total. This is the state we redistribute against.
    """
    return {"counts": honeynet_state.counts(), "total": honeynet_state.total}


@router.put("/honeynet/state")
def put_state(counts: Dict[str, int]):
    """
    Sync our view of the honeynet with the counts actually deployed. The body
    is a mapping of honeypot type -> count.
    """
    honeynet_state.set_counts(counts)
    return {"counts": honeynet_state.counts(), "total": honeynet_state.total}


@router.get("/redistribution")
def get_redistribution():
    """
    Combine the model's target distribution with the current honeynet state to
    produce a concrete redistribution plan: the target count per honeypot type
    and the delta (start/stop) needed to get there, keeping the total fixed.
    """
    distribution = predict_distribution()
    return plan_redistribution(distribution, honeynet_state)
