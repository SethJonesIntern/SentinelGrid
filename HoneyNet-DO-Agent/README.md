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

## Install on the Droplet

```bash
sudo mkdir -p /opt/honeynet-agent && cd /opt/honeynet-agent
# copy agent.py, your docker-compose.honeypots.yml, and config.env here
cp config.example.env config.env && nano config.env   # set BACKEND_URL, AGENT_TOKEN

# run once to test
set -a; . ./config.env; set +a
python3 agent.py

# run persistently
sudo cp honeynet-agent.service /etc/systemd/system/
sudo systemctl enable --now honeynet-agent
journalctl -u honeynet-agent -f
```

Requires only Python 3 (stdlib) and Docker + the compose plugin on the Droplet.

## What's a SKELETON (fill these in)

`agent.py` is wired end-to-end **except** the two Docker functions, left as TODO
until the start/stop specifics are confirmed:

- `reconcile(target)` — the `docker compose --scale` call is built but the
  `subprocess.run` is commented out.
- `actual_counts()` — returns zeros; needs a real `docker ps` count per service.

Also confirm:
- **`TYPE_TO_SERVICE`** in `agent.py` matches the services in your compose file.
- The **port/scaling strategy** (see the caveat in
  `docker-compose.honeypots.example.yml`) — multiple containers of one type can't
  share a fixed host port. This decides whether "multiple per type on one host"
  is even viable, or whether you scale across Droplets.

## Securing the channel

The agent can run Docker = effectively root on the host, so:

- The backend's `/redistribution` and `/honeynet/state` should require auth; the
  agent sends `Authorization: Bearer {AGENT_TOKEN}`. (The backend already has the
  bearer-token machinery from the auth work — protect those two routes and issue
  the agent a token.)
- Keep `config.env` readable only by root (`chmod 600`).
