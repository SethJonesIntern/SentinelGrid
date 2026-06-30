#!/usr/bin/env python3
"""
HoneyNet DO Agent  —  the "hands" that run on the DigitalOcean Droplet.

Pull-model reconciler:
  1. GET  {BACKEND_URL}/redistribution   -> desired target counts per honeypot type
  2. reconcile local Docker to that target (docker compose --scale)
  3. PUT  {BACKEND_URL}/honeynet/state    -> report the REAL running counts back

Why pull, not push: the Droplet only makes OUTBOUND calls, so we never open a
"run docker" control port on a machine that is deliberately exposed to attackers.

Zero third-party deps on purpose (stdlib only) so it's trivial to run on a fresh
Droplet: `python3 agent.py`. Config comes from environment (see config.example.env).

About counts (variable per type, distinct ports): the scalable honeypots in
sg-v4 (ssh, http, mysql, smtp, redis) have no container_name and publish a host
port RANGE (see docker-compose/sentinelgrid-honeypots.yml), so we reconcile each
to the backend's target with `docker compose up -d --scale <svc>=N` and compose
gives every replica its own distinct host port. FTP is the exception: its
passive-data ports must map 1:1 host<->container, leaving no room for per-replica
ports, so it stays a single instance (see SINGLE_INSTANCE_TYPES) and we cap its
target at 1, warning if the backend asks for more.
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
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "docker-compose/sentinelgrid-honeypots.yml")

# Maps a honeypot TYPE (from the backend) -> the docker compose SERVICE name.
# In sg-v4 the service key == container_name (e.g. "sg-ssh-01"), so this same
# value is both what we pass to `docker compose` and the value of the
# `com.docker.compose.service` label we filter on when counting (see below).
# Keep these in sync with the services defined in COMPOSE_FILE.
TYPE_TO_SERVICE = {
    "ssh": "sg-ssh-01",
    "http": "sg-http-01",
    "redis": "sg-redis-01",
    "mysql": "sg-mysql-01",
    "ftp": "sg-ftp-01",
    "smtp": "sg-smtp-01",
}

# Types that can't run as multiple replicas on one host, so their target is
# capped at 1. FTP's passive-data ports (60000-60100) must map 1:1
# host<->container, which leaves no host ports for compose to assign per replica;
# it keeps a fixed container_name + fixed ports in COMPOSE_FILE.
SINGLE_INSTANCE_TYPES = {"ftp"}


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


# --- docker reconcile / inspect --------------------------------------------

def _docker(*args: str) -> subprocess.CompletedProcess:
    """Run a `docker ...` command, capturing output. Raises on non-zero exit."""
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True)


def _compose(*args: str) -> subprocess.CompletedProcess:
    """Run a `docker compose -f COMPOSE_FILE ...` command."""
    return _docker("compose", "-f", COMPOSE_FILE, *args)


def reconcile(target: dict[str, int]) -> None:
    """
    Make local Docker match `target` (e.g. {"ssh": 3, "http": 2, ...}) by
    scaling each compose service to its desired replica count in one shot:
    `docker compose up -d --scale <svc>=N` figures out the +/- itself and hands
    each replica a distinct host port from that service's range. Scaling to 0
    tears a type down. SINGLE_INSTANCE_TYPES are capped at 1 (see note there).
    """
    scale_args: list[str] = []
    for hp_type, service in TYPE_TO_SERVICE.items():
        count = target.get(hp_type, 0)
        if hp_type in SINGLE_INSTANCE_TYPES and count > 1:
            print(f"[warn] {hp_type!r} can't run replicas (passive/data ports); capping {count} -> 1")
            count = 1
        scale_args += ["--scale", f"{service}={count}"]

    print(f"[reconcile] up -d --remove-orphans {' '.join(scale_args)}")
    _compose("up", "-d", "--remove-orphans", *scale_args)


def actual_counts() -> dict[str, int]:
    """
    Count running containers per honeypot type from Docker itself, so the state
    we report back is reality rather than what we intended.

    Filters on the compose service label (its value is the service key, e.g.
    "sg-ssh-01"), which all replicas of a service share, so this returns the
    real replica count per type.
    """
    counts: dict[str, int] = {}
    for hp_type, service in TYPE_TO_SERVICE.items():
        out = _docker(
            "ps",
            "--filter", f"label=com.docker.compose.service={service}",
            "--filter", "status=running",
            "-q",
        )
        counts[hp_type] = len([line for line in out.stdout.splitlines() if line.strip()])
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
