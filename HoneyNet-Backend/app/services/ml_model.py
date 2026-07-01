# app/services/ml_model.py

import json
import os
from pathlib import Path
from typing import Dict

# The honeypot containers that make up the honeynet (see docs/system_pipeline).
# The distribution returned by the model is over exactly these types.
HONEYPOT_TYPES = ["ssh", "http", "redis", "mysql", "ftp", "smtp"]

# FTP can't run more than one instance (its passive-data ports must map 1:1
# host<->container), so it always stays at its single base honeypot and never
# receives any of the distributable slots. Its weight is spread across the rest.
_NON_SCALABLE = "ftp"

# Where the ML pipeline writes its plan (machine-learning/.../honeypot_deployment.json).
# Resolved relative to the repo root; override with ML_PLAN_PATH (e.g. in a
# backend-only deploy where the machine-learning tree isn't present).
_DEFAULT_PLAN_PATH = (
    Path(__file__).resolve().parents[3]
    / "machine-learning" / "data" / "outputs" / "json" / "honeypot_deployment.json"
)

# Small mtime-keyed cache so the 15s redistribution poll doesn't re-read/parse
# the plan every call.
_cache: Dict[str, object] = {}


def _plan_path() -> Path:
    return Path(os.getenv("ML_PLAN_PATH", str(_DEFAULT_PLAN_PATH)))


def _uniform() -> Dict[str, float]:
    weight = 1 / len(HONEYPOT_TYPES)
    return {hp: weight for hp in HONEYPOT_TYPES}


def adapt_distribution(raw: Dict[str, float]) -> Dict[str, float]:
    """
    Convert the ML pipeline's ``recommended_honeypot_distribution`` into the
    weight vector the backend allocates the distributable slots over.

    Two transforms:
      1. Keys: the pipeline emits ``ssh_honeypot``/``http_honeypot``/...; strip
         the ``_honeypot`` suffix down to our HONEYPOT_TYPES (tolerating keys
         that already lack the suffix).
      2. FTP: it can't scale, so it takes none of the distributable slots. Its
         weight is removed and spread evenly across the other five types
         (``ftp_weight / 5`` added to each), then everything is normalised to
         sum to 1. This keeps FTP at exactly its base count of 1.
    """
    weights = {
        hp: float(raw.get(f"{hp}_honeypot", raw.get(hp, 0.0)))
        for hp in HONEYPOT_TYPES
    }

    others = [hp for hp in HONEYPOT_TYPES if hp != _NON_SCALABLE]
    share = weights[_NON_SCALABLE] / len(others)
    for hp in others:
        weights[hp] += share
    weights[_NON_SCALABLE] = 0.0

    total = sum(weights.values())
    if total > 0:
        weights = {hp: w / total for hp, w in weights.items()}
    return weights


def predict_distribution() -> Dict[str, float]:
    """
    Return the target honeynet composition as a distribution over honeypot
    types, sourced from the ML pipeline's saved plan.

    Reads ``recommended_honeypot_distribution`` from the plan JSON (path via
    ML_PLAN_PATH, cached by file mtime), runs it through ``adapt_distribution``,
    and returns it. Falls back to a uniform distribution if the plan is missing
    or unreadable, so the redistribution control loop keeps working without the
    model. Takes no parameters — the model sources its data itself.
    """
    path = _plan_path()
    try:
        mtime = path.stat().st_mtime
        if _cache.get("path") == str(path) and _cache.get("mtime") == mtime:
            return dict(_cache["dist"])  # type: ignore[arg-type]

        with path.open() as f:
            plan = json.load(f)
        dist = adapt_distribution(plan["recommended_honeypot_distribution"])
        _cache.update({"path": str(path), "mtime": mtime, "dist": dist})
        return dict(dist)
    except (OSError, KeyError, ValueError, TypeError):
        return _uniform()
