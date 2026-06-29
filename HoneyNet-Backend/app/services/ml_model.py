# app/services/ml_model.py

from typing import Dict

# The honeypot containers that make up the honeynet (see docs/system_pipeline).
# The distribution returned by the model is over exactly these types.
HONEYPOT_TYPES = ["ssh", "http", "redis", "mysql", "ftp", "smtp"]


def predict_distribution() -> Dict[str, float]:
    """
    Return the target honeynet composition as a probability distribution
    over honeypot types.

    This is a placeholder for the ML model, which has not been delivered yet.
    Per its spec, the real function takes **no parameters**: it reads the
    attack data straight from the database (the same data exposed by our
    other endpoints) and returns a distribution describing what kind of
    honeypots the honeynet should be running right now.

    Until that function lands, we return a uniform distribution so the
    endpoint and the rest of the control loop can be wired up and tested.
    Swap the body of this function for the real model when it arrives; the
    signature and return shape are the contract the rest of the app relies on.
    """
    weight = 1 / len(HONEYPOT_TYPES)
    return {honeypot: weight for honeypot in HONEYPOT_TYPES}
