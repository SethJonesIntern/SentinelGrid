# app/services/ml_scheduler.py
#
# Background refresher for the ML deployment plan.
#
# The ML pipeline (machine-learning/honeypot_pipeline) is a batch job that takes
# ~20-35s: it reads recent sessions from the backend, runs its models, and writes
# recommended_honeypot_distribution to a plan JSON. predict_distribution() reads
# that plan. This module runs the pipeline periodically in a background thread so
# the plan stays fresh WITHOUT the 20-35s cost ever landing in a request.
#
# Gated behind ML_SCHEDULER_ENABLED so it only runs where we want it (the Docker
# image sets it); tests and local dev leave it off.

import logging
import os
import subprocess
import sys
import threading
import time

logger = logging.getLogger("ml_scheduler")

# Pipeline stages in order. The last (decision_rules) writes the plan JSON that
# predict_distribution() reads.
PIPELINE_SCRIPTS = [
    "data_loader.py",
    "feature_engineering.py",
    "behavioral_analysis.py",
    "heuristic_labeling.py",
    "decision_rules.py",
]


def _enabled() -> bool:
    return os.getenv("ML_SCHEDULER_ENABLED", "").lower() in ("1", "true", "yes")


def _pipeline_dir() -> str:
    return os.getenv("ML_PIPELINE_DIR", "/app/machine-learning/honeypot_pipeline")


def run_pipeline_once() -> bool:
    """
    Run the ML pipeline once, regenerating the deployment plan. Returns True on
    success. Never raises — failures are logged so the scheduler loop survives.
    """
    cwd = _pipeline_dir()
    for script in PIPELINE_SCRIPTS:
        try:
            subprocess.run(
                [sys.executable, script],
                cwd=cwd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
            )
        except subprocess.CalledProcessError as exc:
            tail = " | ".join((exc.stderr or "").strip().splitlines()[-3:])
            logger.error("ML pipeline step %s failed: %s", script, tail)
            return False
        except Exception as exc:  # timeout, missing dir, etc.
            logger.error("ML pipeline step %s errored: %s", script, exc)
            return False

    logger.info("ML pipeline refreshed the deployment plan")
    return True


def _loop(interval: int, initial_delay: int) -> None:
    # Let the API finish coming up before the first run — the pipeline's
    # data_loader fetches from this backend's own /sessions endpoint.
    time.sleep(initial_delay)
    while True:
        run_pipeline_once()
        time.sleep(interval)


def start_scheduler() -> None:
    """
    Start the background thread that periodically regenerates the ML plan.

    No-op unless ML_SCHEDULER_ENABLED is set, so it never runs in tests or local
    dev. Safe to call from app startup; the thread is a daemon and its failures
    are logged, never raised, so the API keeps serving regardless.
    """
    if not _enabled():
        return

    interval = int(os.getenv("ML_REFRESH_SECONDS", "600"))
    initial_delay = int(os.getenv("ML_INITIAL_DELAY_SECONDS", "45"))
    thread = threading.Thread(
        target=_loop,
        args=(interval, initial_delay),
        daemon=True,
        name="ml-scheduler",
    )
    thread.start()
    logger.info(
        "ML scheduler started (every %ss, first run in %ss)", interval, initial_delay
    )
