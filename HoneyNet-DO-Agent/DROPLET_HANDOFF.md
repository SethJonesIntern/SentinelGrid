# DO Droplet Handoff — Adaptive Honeynet (agent + scalable compose)

This covers everything that changed for the **DigitalOcean droplet** so the
honeynet can be **scaled automatically by the ML-driven backend**. The backend
(App Runner) now computes a target count per honeypot type; the **DO agent** on
the droplet pulls that target and reconciles the running containers to match.

> **Loop:** backend `GET /redistribution` → agent pulls target → agent runs
> `docker compose --scale` → agent `PUT /honeynet/state` (reports real counts).
> The droplet only makes **outbound** calls — no inbound control port.

---

## ⚠️ Read this first — two sources, one is NOT in git

| What | Where | In git? |
|---|---|---|
| **Agent files** (`agent.py`, `honeynet-agent.service`, `config.example.env`) | `HoneyNet-DO-Agent/` | ✅ Yes — on branch `hostedBack` |
| **Updated honeynet compose** (`sentinelgrid-honeypots.yml`) | `HoneyNet-Backend/sg-v4/` | ❌ **No — gitignored** |

The compose file is **gitignored**, so `git pull` will **not** deliver it. The
full updated file is included verbatim below — you must place it on the droplet
manually. If you only pull git you'll get the new agent + the **old** compose,
and scaling will fail on port/name collisions.

---

## 1. Updated compose — `docker-compose/sentinelgrid-honeypots.yml` (FULL FILE)

**What changed vs. the old one:** the five scalable services (ssh, http, mysql,
smtp, redis) had `container_name:` **removed** and their single host port changed
to a **range** (so `--scale N` gives each replica its own host port). **FTP is
unchanged** — it keeps `container_name` + fixed ports and stays a single instance
(its passive-data ports must map 1:1). `sg-forwarder` is unchanged.

Place this at `/opt/sentinelgrid/docker-compose/sentinelgrid-honeypots.yml`:

```yaml
# SentinelGrid Honeynet  v4 — ClarityMed Health Systems
# Deploy: cd /opt/sentinelgrid && bash deploy.sh
# Logs:   docker logs sg-forwarder -f
#
# Variable count per type (distinct ports):
#   The five scalable honeypots (ssh, http, mysql, smtp, redis) have NO
#   container_name and publish a host port RANGE instead of a single port, so
#   the DO agent can `docker compose up -d --scale <svc>=N` and compose hands
#   each replica its own distinct host port from the range. The first replica
#   lands on the original well-known port (e.g. :25, :6380); extras climb the
#   range. Ranges hold 10 each (backend caps a single type at 1 base + 6
#   distributable = 7).
#
#   FTP is the exception: its passive-data ports (60000-60100) must map 1:1
#   host<->container, which leaves no room for per-replica host ports, so it
#   keeps a fixed name + fixed ports and stays a single instance.

networks:
  sentinelgrid-net:
    external: true

volumes:
  sg-logs:
    driver: local
  sg-cowrie-logs:
    driver: local
  sg-forwarder-state:
    driver: local

services:

  sg-ssh-01:
    image: cowrie/cowrie:latest
    restart: unless-stopped
    networks: [sentinelgrid-net]
    ports:
      - "2222-2231:2222"
    volumes:
      - sg-cowrie-logs:/cowrie/cowrie-git/var/log/cowrie
    environment:
      - COWRIE_HOSTNAME=claritymed-app01
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "3" }

  sg-http-01:
    image: sg-http-honeypot:latest
    restart: unless-stopped
    networks: [sentinelgrid-net]
    ports:
      - "8080-8089:80"
    volumes:
      - sg-logs:/var/log/honeypot
    environment:
      - SENSOR_ID=sg-http-01
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "3" }

  sg-ftp-01:
    image: sg-ftp-honeypot:latest
    container_name: sg-ftp-01
    restart: unless-stopped
    networks: [sentinelgrid-net]
    ports:
      - "21:21"
      - "60000-60100:60000-60100"
    volumes:
      - sg-logs:/var/log/honeypot
    environment:
      - SENSOR_ID=sg-ftp-01
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "3" }

  sg-mysql-01:
    image: sg-mysql-honeypot:latest
    restart: unless-stopped
    networks: [sentinelgrid-net]
    ports:
      - "3307-3316:3306"
    volumes:
      - sg-logs:/var/log/honeypot
    environment:
      - SENSOR_ID=sg-mysql-01
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "3" }

  sg-smtp-01:
    image: sg-smtp-honeypot:latest
    restart: unless-stopped
    networks: [sentinelgrid-net]
    ports:
      - "25-34:25"
    volumes:
      - sg-logs:/var/log/honeypot
    environment:
      - SENSOR_ID=sg-smtp-01
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "3" }

  sg-redis-01:
    image: sg-redis-honeypot:latest
    restart: unless-stopped
    networks: [sentinelgrid-net]
    ports:
      - "6380-6389:6379"
    volumes:
      - sg-logs:/var/log/honeypot
    environment:
      - SENSOR_ID=sg-redis-01
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "3" }

  sg-forwarder:
    image: python:3.11-slim
    container_name: sg-forwarder
    restart: unless-stopped
    networks: [sentinelgrid-net]
    volumes:
      - sg-logs:/logs
      - sg-cowrie-logs:/logs/cowrie
      - sg-forwarder-state:/var/lib/sg-forwarder
      - ./forwarder:/app
    working_dir: /app
    command: >
      sh -c "pip install requests --quiet --no-cache-dir && python forward_logs.py"
    environment:
      - API_URL=https://uddiejez3g.us-east-1.awsapprunner.com/log
      - SENSOR_ID=sg-claritymed-01
      - BATCH_SIZE=20
      - HEARTBEAT_INT=60
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "2" }
```

**Port map (host → what):**

| Service | Host ports (range) | Container | Scales? |
|---|---|---|---|
| sg-ssh-01 (cowrie) | 2222–2231 | 2222 | ✅ |
| sg-http-01 | 8080–8089 | 80 | ✅ |
| sg-mysql-01 | 3307–3316 | 3306 | ✅ |
| sg-smtp-01 | 25–34 | 25 | ✅ |
| sg-redis-01 | 6380–6389 | 6379 | ✅ |
| sg-ftp-01 | 21 + 60000–60100 | 21 | ❌ always 1 |

---

## 2. The agent — `HoneyNet-DO-Agent/` (from git, branch `hostedBack`)

These files ARE in git. Key changes:

### `agent.py`
Now fully implements the reconcile loop (was a skeleton). Behavior:
- Reads config from env (`config.env`).
- Maps honeypot type → compose service, and caps FTP at 1:

```python
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "docker-compose/sentinelgrid-honeypots.yml")

TYPE_TO_SERVICE = {
    "ssh": "sg-ssh-01",
    "http": "sg-http-01",
    "redis": "sg-redis-01",
    "mysql": "sg-mysql-01",
    "ftp": "sg-ftp-01",
    "smtp": "sg-smtp-01",
}
SINGLE_INSTANCE_TYPES = {"ftp"}   # FTP capped at 1 (passive ports can't scale)
```

- `reconcile(target)` runs one `docker compose -f <COMPOSE_FILE> up -d
  --remove-orphans --scale <svc>=N ...` for all types (FTP forced to ≤1).
- `actual_counts()` counts running containers per type via the
  `com.docker.compose.service` label and reports them with `PUT /honeynet/state`.

### `config.env` (create on the droplet — NOT committed)
`config.env` is gitignored; create it from `config.example.env`. **The real
`BACKEND_URL` and `AGENT_TOKEN` were sent separately (Discord).**

```ini
BACKEND_URL=https://uddiejez3g.us-east-1.awsapprunner.com
AGENT_TOKEN=<the shared secret sent via Discord — must match App Runner's AGENT_TOKEN>
POLL_SECONDS=15
COMPOSE_FILE=docker-compose/sentinelgrid-honeypots.yml
```
Then `chmod 600 config.env`.

### `honeynet-agent.service` (systemd unit — FULL FILE)
Runs the agent from the sentinelgrid root so the relative `COMPOSE_FILE`
resolves. Install to `/etc/systemd/system/honeynet-agent.service`:

```ini
[Unit]
Description=HoneyNet DO Agent (reconciles honeypot containers to backend target)
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/sentinelgrid
EnvironmentFile=/opt/sentinelgrid/config.env
ExecStart=/usr/bin/python3 /opt/sentinelgrid/agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 3. Deploy order (on the droplet)

Target layout: everything lives in `/opt/sentinelgrid/` (the sentinelgrid root
that contains `docker-compose/`, `honeypots/`, `forwarder/`, `deploy.sh`).

```bash
# 0. Put the updated sg-v4 bundle at /opt/sentinelgrid (incl. the compose from §1)
cd /opt/sentinelgrid
ls docker-compose/sentinelgrid-honeypots.yml   # sanity check

# 1. Drop the agent files into the SAME dir
#    (agent.py + honeynet-agent.service from HoneyNet-DO-Agent/)
cp config.example.env config.env
nano config.env            # fill BACKEND_URL + AGENT_TOKEN (from Discord)
chmod 600 config.env

# 2. Build images + create network + baseline honeynet (once)
sudo bash deploy.sh
docker ps --filter name=sg-

# 3. Smoke-test the agent in the foreground
set -a; . ./config.env; set +a
python3 agent.py           # expect [tick] target=..., [reconcile] ..., no 401
#   Ctrl-C once it looks healthy

# 4. Install as a service (survives reboots)
sudo cp honeynet-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now honeynet-agent
journalctl -u honeynet-agent -f
```

---

## 4. Prerequisites / gotchas

- **`AGENT_TOKEN` must match** on both sides: the value in `config.env` **and**
  the `AGENT_TOKEN` env var in the App Runner backend service. The backend fails
  closed — a mismatch means every agent call returns `401`.
- **Run `deploy.sh` before the agent.** The agent scales containers but does not
  build images or create the `sentinelgrid-net` network; `deploy.sh` does both.
- **`enable`, not just `start`** — that's what makes it survive a reboot.
- **This changes the LIVE honeynet.** Once enabled, the agent automatically
  adds/removes honeypot containers to match the backend's ML target.
- **Reboot behavior:** containers come back via `restart: unless-stopped`, the
  agent restarts via systemd and re-reconciles within one `POLL_SECONDS` cycle.

### Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `401` in agent logs | token mismatch | make `config.env` `AGENT_TOKEN` == App Runner `AGENT_TOKEN` |
| `backend unreachable` | wrong URL / no egress | check `BACKEND_URL`; confirm outbound HTTPS |
| reconcile runs but counts stay 0 | images/network missing | run `deploy.sh` first |
| `no configuration file provided` | wrong working dir | agent must run from `/opt/sentinelgrid` |
| scale >1 fails on ports/names | old compose in place | use the compose from §1 (ranges, no container_name) |
| service gone after reboot | not enabled | `sudo systemctl enable honeynet-agent` |

---

## Note (backend side — handled separately, not on the droplet)
The App Runner backend must be **rebuilt from the repo root** and redeployed for
the ML-driven target to be live:
`docker build -f HoneyNet-Backend/Dockerfile -t honeynet-backend:latest .`
Until then `/redistribution` returns a uniform distribution (the agent still
works, it just won't be ML-driven yet).
