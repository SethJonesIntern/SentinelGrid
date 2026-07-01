# SentinelGrid — Fresh Droplet Setup

One script takes a **blank** Ubuntu/Debian droplet to a fully running adaptive
honeynet. You only do 4 things.

## Steps (run as root)

```bash
# 1. Put this folder on the droplet, e.g. at /opt/sentinelgrid, and cd into it
cd /opt/sentinelgrid

# 2. Create your config and set the token (sent to you separately by Seth)
cp config.example.env config.env
nano config.env            # set AGENT_TOKEN=<the token>   (BACKEND_URL is already filled)
chmod 600 config.env

# 3. Run the bootstrap
bash bootstrap.sh
```

`bootstrap.sh` will:
1. Install Docker + the Compose/buildx plugins (if missing)
2. Install python3 (if missing)
3. Run `deploy.sh` — builds the honeypot images, creates the network, applies
   iptables containment, and starts one of each honeypot
4. Install the DO agent as a systemd service (`honeynet-agent`) that pulls the
   ML-driven target from the backend and scales the containers to match

## Verify it worked

```bash
docker ps --filter name=sg-           # 6 honeypots + sg-forwarder running
journalctl -u honeynet-agent -f       # [tick] target=..., [reconcile] ..., no 401
docker logs sg-forwarder -f           # events forwarding to the backend
```

Within ~15s of the agent starting, it will scale the honeypots to the backend's
current target (e.g. `ssh:2 http:2 redis:2 mysql:1 ftp:1 smtp:4`).

## If something fails

| Symptom | Fix |
|---|---|
| `bootstrap.sh` says config still has `CHANGE_ME` | edit `config.env`, set the real `AGENT_TOKEN`, re-run |
| Agent logs show `401` | `AGENT_TOKEN` in `config.env` must match the backend's — re-check the value |
| `docker compose` errors | re-run bootstrap; it installs the compose plugin |
| Honeypots not running | `docker ps -a` to see exit reasons; `docker logs <name>` |
| Reboot | everything auto-restarts (containers via `restart: unless-stopped`, agent via systemd) |

## Notes
- Re-runnable: fixing `config.env` and running `bash bootstrap.sh` again is safe.
- The agent only makes **outbound** calls to the backend — no inbound control port.
- FTP always stays at 1 instance (its passive ports can't be scaled); the other
  five scale per the backend's ML distribution.
