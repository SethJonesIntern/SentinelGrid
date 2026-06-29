#!/usr/bin/env python3
"""
HoneyNet DO Agent  —  the "hands" that run on the DigitalOcean Droplet.

Pull-model reconciler (SKELETON):
  1. GET  {BACKEND_URL}/redistribution   -> desired target counts per honeypot type
  2. reconcile local Docker to that target (docker compose --scale)
  3. PUT  {BACKEND_URL}/honeynet/state    -> report the REAL running counts back

Why pull, not push: the Droplet only makes OUTBOUND calls, so we never open a
"run docker" control port on a machine that is deliberately exposed to attackers.

Zero third-party deps on purpose (stdlib only) so it's trivial to run on a fresh
Droplet: `python3 agent.py`. Config comes from environment (see config.example.env).

NOTE: the two reconcile/report functions are stubs marked TODO — drop the real
start/stop specifics in there once you have them.
"""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

# --- config (from environment / config.env) ---------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "https://your-app-runner-url").rstrip("/")
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "")            # bearer token for the backend
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "15"))
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "docker-compose.honeypots.yml")

# Maps a honeypot TYPE (from the backend) -> the docker compose SERVICE name.
# Keep these in sync with the services defined in COMPOSE_FILE.
TYPE_TO_SERVICE = {
    "ssh": "ssh",
    "http": "http",
    "redis": "redis",
    "mysql": "mysql",
    "ftp": "ftp",
    "smtp": "smtp",
}


# --- backend I/O ------------------------------------------------------------

def _request(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if AGENT_TOKEN:
        headers["Authorization"] = f"Bearer {AGENT_TOKEN}"
    req = urllib.request.Request(BACKEND_URL + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def fetch_target() -> dict[str, int]:
    """Ask the backend what the honeynet SHOULD look like (desired counts)."""
    plan = _request("GET", "/redistribution")
    return plan["target"]


def report_actual(counts: dict[str, int]) -> None:
    """Tell the backend what is ACTUALLY running, so its state == reality."""
    _request("PUT", "/honeynet/state", body=counts)


# --- docker reconcile / inspect (STUBS — fill with your specifics) ----------

def reconcile(target: dict[str, int]) -> None:
    """
    Make local Docker match `target` (e.g. {"ssh": 3, "http": 2, ...}).

    TODO: confirm the exact start/stop mechanism with the honeypot setup.
    The compose `--scale` approach below reconciles to a desired count in one
    shot (it figures out the +/- itself), which matches the backend's model.
    """
    scale_args = []
    for hp_type, count in target.items():
        service = TYPE_TO_SERVICE.get(hp_type)
        if service is None:
            print(f"[warn] no compose service mapped for type {hp_type!r}; skipping")
            continue
        scale_args += ["--scale", f"{service}={count}"]

    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d", "--remove-orphans", *scale_args]
    print("[reconcile]", " ".join(cmd))
    # TODO: un-stub once the compose file + port strategy are confirmed.
    # subprocess.run(cmd, check=True)


def actual_counts() -> dict[str, int]:
    """
    Count running containers per honeypot type from Docker itself.

    TODO: implement using whatever label/name scheme the honeypot compose uses,
    e.g. `docker ps --filter label=com.docker.compose.service=<svc> -q | wc -l`.
    """
    counts: dict[str, int] = {}
    for hp_type, service in TYPE_TO_SERVICE.items():
        # TODO: replace stub with a real `docker ps` count for `service`.
        # out = subprocess.run(
        #     ["docker", "ps", "--filter",
        #      f"label=com.docker.compose.service={service}", "-q"],
        #     capture_output=True, text=True, check=True)
        # counts[hp_type] = len([l for l in out.stdout.splitlines() if l.strip()])
        counts[hp_type] = 0
    return counts


# --- loop -------------------------------------------------------------------

def tick() -> None:
    target = fetch_target()
    print(f"[tick] target = {target}")
    reconcile(target)
    actual = actual_counts()
    report_actual(actual)
    print(f"[tick] reported actual = {actual}")


def main() -> None:
    print(f"HoneyNet DO Agent starting. backend={BACKEND_URL} every {POLL_SECONDS}s")
    while True:
        try:
            tick()
        except urllib.error.URLError as e:
            print(f"[error] backend unreachable: {e}")
        except subprocess.CalledProcessError as e:
            print(f"[error] docker command failed: {e}")
        except Exception as e:  # keep the loop alive
            print(f"[error] unexpected: {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
