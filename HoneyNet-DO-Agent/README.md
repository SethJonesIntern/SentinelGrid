# HoneyNet DO Agent

The **data plane** for HoneyNet — a tiny service that runs **on the DigitalOcean
Droplet** (where Docker and the honeypot containers actually live) and keeps the
running containers in sync with what the backend wants.

The backend (on AWS App Runner) is the brain: it decides how many honeypots of
each type should run. It can't touch Docker on the Droplet, so this agent does.

## How it works (pull model)

Every `POLL_SECONDS` the agent:

1. `GET {BACKEND_URL}/redistribution` → reads the desired **target** counts per type.
2. Reconciles local Docker to that target (`docker compose --scale`).
3. `PUT {BACKEND_URL}/honeynet/state` → reports the **real** running counts back,
   so the backend's state reflects reality (not assumptions).

Only **outbound** calls leave the Droplet — no inbound control port is opened on
a machine that is deliberately exposed to attackers.

```
AWS App Runner (backend)            DigitalOcean Droplet
  /redistribution   ◄────GET────────  agent.py ──► docker compose --scale
  /honeynet/state   ◄────PUT────────  agent.py ◄── docker ps
```

## Deploy on the Droplet (step by step)

> **Read this whole section before starting.** The order matters: the backend
> must share the agent token, and the honeypot images/network must exist *before*
> the agent runs, or the agent will start but reconcile nothing.
>
> **Layout assumption:** the agent runs **from the sentinelgrid root**
> (`/opt/sentinelgrid`, the directory that contains `docker-compose/`,
> `honeypots/`, `forwarder/`, `deploy.sh`). `agent.py` and `config.env` are
> copied **into that same directory**. This is required because `COMPOSE_FILE` is
> the *relative* path `docker-compose/sentinelgrid-honeypots.yml` and the
> forwarder mounts a relative `./forwarder` path — both resolve against this dir.

### Prerequisites
- Docker + the `docker compose` plugin installed and running on the Droplet.
- Python 3 (stdlib only — no `pip install` needed).
- `iptables` (the deploy script installs it if missing).

### Step 0 — Backend token (do this FIRST, off the Droplet)
The agent authenticates with a static bearer token. The backend **fails closed**:
if its `AGENT_TOKEN` env var is unset or different, **every** agent call returns
`401` and nothing syncs.

1. Pick the shared secret (the value that will go in `config.env` below).
2. In the **AWS App Runner** service config for the backend, set an environment
   variable `AGENT_TOKEN` to that exact value and redeploy the service.
3. The two routes the agent uses (`GET /redistribution`, `PUT /honeynet/state`)
   are already protected by this token server-side — no backend code change is
   needed, only the env var.

### Step 1 — Get the sentinelgrid bundle onto the Droplet
Put the honeynet bundle at `/opt/sentinelgrid` (the `sg-v4` contents:
`docker-compose/`, `honeypots/`, `forwarder/`, `deploy.sh`, `README.md`).

```bash
sudo mkdir -p /opt/sentinelgrid
# copy/scp the sg-v4 bundle contents into /opt/sentinelgrid
cd /opt/sentinelgrid
ls docker-compose/sentinelgrid-honeypots.yml   # sanity check: this must exist
```

### Step 2 — Add the agent files into the same directory
Copy `agent.py`, `config.example.env`, and `honeynet-agent.service` from this
repo into `/opt/sentinelgrid`:

```bash
cd /opt/sentinelgrid
# copy/scp agent.py, config.example.env, honeynet-agent.service here, then:
cp config.example.env config.env
sudo nano config.env          # fill in the real values (see below)
chmod 600 config.env          # secrets — root-readable only
```

`config.env` must contain (the token MUST equal the App Runner `AGENT_TOKEN`
from Step 0):

```ini
BACKEND_URL=https://uddiejez3g.us-east-1.awsapprunner.com
AGENT_TOKEN=<the same shared secret you set on App Runner>
POLL_SECONDS=15
COMPOSE_FILE=docker-compose/sentinelgrid-honeypots.yml
```

> `config.env` is gitignored on purpose — never commit it. Only
> `config.example.env` (placeholders) belongs in git.

### Step 3 — Build images + bring up the baseline honeynet (run ONCE)
The agent *scales* containers but does **not** build images or create the Docker
network. `deploy.sh` does both, and stands up one of each honeypot as a baseline:

```bash
cd /opt/sentinelgrid
sudo bash deploy.sh
docker ps --filter name=sg-     # expect sg-ssh-01, sg-http-01, ... + sg-forwarder
```

### Step 4 — Smoke-test the agent in the foreground
Confirm it can reach the backend and reconcile before making it a service:

```bash
cd /opt/sentinelgrid
set -a; . ./config.env; set +a
python3 agent.py
```

Healthy output looks like a repeating cycle of:
```
[tick] target = {'ssh': 1, 'http': 1, ...}
[reconcile] up -d --remove-orphans --scale sg-ssh-01=1 ...
[tick] reported actual = {'ssh': 1, 'http': 1, ...}
```
If you see `backend unreachable` or HTTP `401`, fix `BACKEND_URL` / the token
match (Step 0) before continuing. Stop with Ctrl-C.

### Step 5 — Install as a systemd service (survives reboots)
```bash
sudo cp /opt/sentinelgrid/honeynet-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now honeynet-agent     # `enable` = also start on boot
journalctl -u honeynet-agent -f                # watch it run
```

**`enable` (not just `start`) is what makes it survive a reboot.** The unit also
has `Restart=always`, so it recovers from crashes.

### Reboot behaviour (what to expect)
After a Droplet reboot, with the above in place:
- Docker restarts the honeypot containers (`restart: unless-stopped` in compose).
- The `@reboot` cron restores iptables (set up by `deploy.sh`).
- systemd restarts the agent, which reconciles to the backend target within one
  `POLL_SECONDS` cycle — so even if anything drifted, it self-corrects.

### Verify end-to-end
```bash
# On the Droplet: agent logs show ticks with no 401/unreachable errors.
journalctl -u honeynet-agent -n 30
# The backend's state should now reflect reality:
curl -H "Authorization: Bearer <AGENT_TOKEN>" \
  https://uddiejez3g.us-east-1.awsapprunner.com/honeynet/state
```

### Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `401` in agent logs | token mismatch | make `config.env` `AGENT_TOKEN` == App Runner `AGENT_TOKEN` (Step 0) |
| `backend unreachable` | wrong/blocked URL | check `BACKEND_URL`; confirm outbound HTTPS works |
| reconcile runs but counts stay 0 | images/network missing | run `deploy.sh` (Step 3) before the agent |
| `no configuration file provided` / compose not found | wrong working dir | agent must run from `/opt/sentinelgrid`; check the unit's `WorkingDirectory` |
| service gone after reboot | not enabled | `sudo systemctl enable honeynet-agent` |

## Notes on scaling (so the counts behave as expected)
- Five types scale freely: **ssh, http, mysql, smtp, redis**. Each publishes a
  host **port range** in the compose file, so `--scale N` gives every replica a
  distinct host port (current ranges hold 10; the backend asks for at most 7).
- **FTP is capped at 1** by the agent: its passive-data ports (60000–60100) must
  map 1:1 host↔container, leaving no room for per-replica ports. The agent warns
  if the backend ever requests more.
- Extra replicas land on **non-standard** host ports (8081, 3308, …); on a single
  Droplet IP only the standard port sees real attacker traffic. Counts >1 add
  capacity, not extra coverage, on one host.
- If you raise the backend's `TOTAL_HONEYPOTS` so one type could exceed 10,
  widen the port ranges in `docker-compose/sentinelgrid-honeypots.yml` to match.

## Securing the channel

The agent can run Docker = effectively root on the host, so:

- The backend's `/redistribution` and `/honeynet/state` should require auth; the
  agent sends `Authorization: Bearer {AGENT_TOKEN}`. (The backend already has the
  bearer-token machinery from the auth work — protect those two routes and issue
  the agent a token.)
- Keep `config.env` readable only by root (`chmod 600`).
