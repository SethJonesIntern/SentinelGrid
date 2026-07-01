#!/bin/bash
# ============================================================
# SentinelGrid Honeynet  v4 — ClarityMed Health Systems
# Run from: /opt/sentinelgrid/
# Usage:    bash deploy.sh
# ============================================================
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[SG]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo -e "${GREEN}"
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║   SentinelGrid  v4 — ClarityMed Health Systems   ║"
echo "  ║   Adaptive Honeynet Deploy                        ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo -e "${NC}  $(date)"
echo "  ─────────────────────────────────────────────────────"

# ── Prereqs ───────────────────────────────────────────────────────────────────
command -v docker   >/dev/null 2>&1 || err "Docker not found."
command -v iptables >/dev/null 2>&1 || apt-get install -y iptables -q
[[ -f "docker-compose/sentinelgrid-honeypots.yml" ]] || \
  err "Run from sentinelgrid/ root. Current dir: $(pwd)"
log "Docker: $(docker --version | cut -d' ' -f3)"

# Resolve the Compose command. Prefer the V2 plugin (`docker compose`); fall back
# to the standalone V1 (`docker-compose`). Fresh droplets often have Docker but
# not its CLI plugins, so install the plugin if neither is available.
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  warn "Docker Compose not found; installing docker-compose-plugin..."
  apt-get update -q && apt-get install -y docker-compose-plugin docker-buildx-plugin -q || true
  if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
  else
    err "Docker Compose unavailable. Install it manually: apt-get install -y docker-compose-plugin  (or: curl -fsSL https://get.docker.com | sh)"
  fi
fi
log "Compose: $DC"

# ── Network ───────────────────────────────────────────────────────────────────
log "Checking Docker network..."
if ! docker network ls --format '{{.Name}}' | grep -q "^sentinelgrid-net$"; then
  log "  Creating sentinelgrid-net..."
  docker network create --driver bridge sentinelgrid-net
else
  log "  sentinelgrid-net exists ✓"
fi

# ── Build images ──────────────────────────────────────────────────────────────
log "Building honeypot images..."
for svc in http ftp mysql smtp redis; do
  log "  → sg-${svc}-honeypot"
  docker build -t "sg-${svc}-honeypot:latest" "./honeypots/${svc}/" \
    --label "sg.honeypot=true" --label "sg.identity=claritymed" -q \
    && echo "    ✅ sg-${svc}-honeypot:latest"
done

# ── iptables containment ──────────────────────────────────────────────────────
log "Applying iptables containment rules..."
SG_SUBNET=$(docker network inspect sentinelgrid-net \
  --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "172.20.0.0/16")
log "  Subnet: $SG_SUBNET"

iptables -F SG_HONEYPOT 2>/dev/null || true
iptables -X SG_HONEYPOT 2>/dev/null || true
iptables -N SG_HONEYPOT 2>/dev/null || true
iptables -A SG_HONEYPOT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A SG_HONEYPOT -s "$SG_SUBNET" -d "$SG_SUBNET" -j ACCEPT
iptables -A SG_HONEYPOT -p udp --dport 53 -j ACCEPT
iptables -A SG_HONEYPOT -p tcp --dport 53 -j ACCEPT
iptables -A SG_HONEYPOT -s "$SG_SUBNET" -p tcp --dport 443 -j ACCEPT
iptables -A SG_HONEYPOT -s "$SG_SUBNET" -j DROP
iptables -I FORWARD 1 -j SG_HONEYPOT 2>/dev/null || true

# Port 22 → Cowrie redirect
iptables -t nat -D PREROUTING -p tcp --dport 22 -j REDIRECT --to-port 2222 2>/dev/null || true
iptables -t nat -A PREROUTING -p tcp --dport 22 -j REDIRECT --to-port 2222
log "  Port 22 → 2222 redirect active ✓"

# Persist rules
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4
CRON_JOB="@reboot iptables-restore < /etc/iptables/rules.v4"
(crontab -l 2>/dev/null | grep -v "iptables-restore"; echo "$CRON_JOB") | crontab -
log "  iptables persisted via cron ✓"

# ── Stop old containers ───────────────────────────────────────────────────────
log "Stopping existing SentinelGrid containers..."
docker compose -f ./docker-compose/sentinelgrid-honeypots.yml down 2>/dev/null || true
for c in sg-ssh-01 sg-http-01 sg-ftp-01 sg-mysql-01 sg-smtp-01 sg-redis-01 sg-forwarder; do
  # force-remove (stop+rm) each; `|| true` so a missing container doesn't trip
  # `set -e` on a fresh droplet and abort the deploy before `up -d`.
  docker rm -f "$c" 2>/dev/null || true
done

# ── Deploy ────────────────────────────────────────────────────────────────────
log "Deploying ClarityMed honeynet stack..."
docker compose -f ./docker-compose/sentinelgrid-honeypots.yml up -d

log "Waiting 12s for containers to start..."
sleep 12

# ── Status ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}  ✅ ClarityMed Honeynet v4 is live${NC}"
echo "  ─────────────────────────────────────────────────────"
echo ""
echo "  CONTAINERS:"
docker ps --format "    {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=sg-"
echo ""
echo "  PORTS:"
echo "    :22    → SSH/Cowrie  (claritymed-app01 identity)"
echo "    :8080  → HTTP        (patient portal, EHR, admin, phpMyAdmin, wiki)"
echo "    :21    → FTP         (deep bait filesystem with fake credentials)"
echo "    :3307  → MySQL       (claritymed_production DB)"
echo "    :25    → SMTP        (mail.claritymed.com)"
echo "    :6380  → Redis       (claritymed-cache-01)"
echo ""
echo "  USEFUL COMMANDS:"
echo "    docker logs sg-forwarder -f     # live forwarding to your API"
echo "    docker logs sg-ssh-01 -f        # Cowrie SSH events"
echo "    docker logs sg-http-01 -f       # HTTP honeypot events"
echo ""
echo "  TEST COMMANDS (from this server):"
echo "    curl http://localhost:8080/"
echo "    curl http://localhost:8080/.env"
echo "    ftp -n localhost 21"
echo "    redis-cli -p 6380 ping"
echo "    telnet localhost 25"
echo ""
echo "  FORWARDER (last 20 lines):"
sleep 3
docker logs sg-forwarder --tail 20 2>/dev/null || warn "Forwarder still starting"
