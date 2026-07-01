#!/bin/bash
# ============================================================
# SentinelGrid — fresh-droplet bootstrap
# Takes a BLANK Ubuntu/Debian droplet to a fully running adaptive honeynet:
#   installs Docker (+ compose/buildx plugins) -> deploys honeypots ->
#   installs the DO agent as a systemd service.
#
# Usage (as root):
#   1. Upload this whole folder to the droplet (e.g. /opt/sentinelgrid)
#   2. cd into it
#   3. cp config.example.env config.env && nano config.env   # set AGENT_TOKEN
#   4. bash bootstrap.sh
#
# Re-runnable: safe to run again after fixing config or on updates.
# ============================================================
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[BOOT]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

# Bind everything to THIS folder, wherever it was uploaded (no hard-coded /opt path).
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
log "Working dir: $ROOT"

[[ $EUID -eq 0 ]] || err "Run as root (needed for Docker install, iptables, systemd)."

# ── 1. Docker + CLI plugins ─────────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  log "Docker not found — installing via get.docker.com..."
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker >/dev/null 2>&1 || true

if ! docker compose version >/dev/null 2>&1; then
  log "Installing Docker Compose/buildx plugins..."
  apt-get update -q && apt-get install -y docker-compose-plugin docker-buildx-plugin -q || true
fi
docker compose version >/dev/null 2>&1 || \
  err "Docker Compose still unavailable. Try: apt-get install -y docker-compose-plugin"
log "Docker: $(docker --version | cut -d' ' -f3), Compose: $(docker compose version --short 2>/dev/null)"

# ── 2. Python 3 (agent runtime; stdlib only) ────────────────────────────────
command -v python3 >/dev/null 2>&1 || { log "Installing python3..."; apt-get install -y python3 -q; }

# ── 3. config.env (holds the agent token) ───────────────────────────────────
if [[ ! -f config.env ]]; then
  cp config.example.env config.env
  warn "Created config.env from the example."
  warn "EDIT IT before continuing:  nano $ROOT/config.env   (set AGENT_TOKEN), then re-run this script."
  exit 1
fi
if grep -q "AGENT_TOKEN=CHANGE_ME" config.env; then
  err "config.env still has AGENT_TOKEN=CHANGE_ME. Set the real token, then re-run."
fi
chmod 600 config.env

# ── 4. Deploy the honeynet (build images, network, iptables, start containers) ──
log "Deploying honeynet..."
bash deploy.sh

# ── 5. Install the agent as a systemd service (paths bound to $ROOT) ─────────
log "Installing honeynet-agent service..."
cat > /etc/systemd/system/honeynet-agent.service <<EOF
[Unit]
Description=HoneyNet DO Agent (reconciles honeypot containers to backend target)
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT
EnvironmentFile=$ROOT/config.env
ExecStart=/usr/bin/python3 $ROOT/agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now honeynet-agent

echo ""
log "✅ Done. Honeynet + agent are live."
echo "   Honeypots:   docker ps --filter name=sg-"
echo "   Agent logs:  journalctl -u honeynet-agent -f"
echo "   Forwarder:   docker logs sg-forwarder -f"
