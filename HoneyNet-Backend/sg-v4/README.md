# SentinelGrid Honeynet  v4 — ClarityMed Health Systems

Adaptive honeynet for attacker TTP collection.
Fictional identity: ClarityMed Health Systems (healthcare company demo).
6 honeypots + universal log forwarder + iptables containment.

## Quick Deploy (fresh droplet)

```bash
cd /opt
curl -L "YOUR_URL/sentinelgrid-v4.zip" -o sentinelgrid-v4.zip
apt install -y unzip
unzip sentinelgrid-v4.zip
cd sentinelgrid
bash deploy.sh
```

## Honeypots

| Container    | Port | Identity                        | What it catches                        |
|--------------|------|---------------------------------|----------------------------------------|
| sg-ssh-01    | 22   | claritymed-app01 (Cowrie)       | SSH credential stuffing, commands      |
| sg-http-01   | 8080 | ClarityMed Patient Portal       | Login attempts, scanner probes, .env   |
| sg-ftp-01    | 21   | ClarityMed Secure FTP           | Credential attempts, file downloads    |
| sg-mysql-01  | 3307 | claritymed-db-01                | DB recon queries, credential attempts  |
| sg-smtp-01   | 25   | mail.claritymed.com             | AUTH capture, relay attempts           |
| sg-redis-01  | 6380 | claritymed-cache-01             | RCE attempts, CONFIG SET, SLAVEOF      |

## Key fixes from v3

- **Forwarder volume path** — deploy.sh copies `forward_logs.py` into
  `docker-compose/forwarder/` so the relative `./forwarder:/app` mount
  always resolves correctly regardless of where you run compose from
- **Redis filter bug** — v3 checked `_severity("redis.command")` which
  always returned "low" so no commands were filtered. v4 checks the
  command name directly against an INTERESTING_CMDS set
- **ClarityMed identity** — all honeypots branded as a fictional healthcare
  company to attract and engage attackers longer

## Forwarder event schema

Every event sent to your API:

```json
{
  "timestamp":     "2024-03-15T14:22:01Z",
  "source_ip":     "1.2.3.4",
  "source_port":   54321,
  "event_type":    "http.login.attempt",
  "honeypot_type": "http",
  "sensor_id":     "sg-do-claritymed-01",
  "severity":      "high",
  "session_id":    "a1b2c3d4",
  "data": {
    "method":      "POST",
    "path":        "/login",
    "credentials": {"username": "admin", "password": "admin123"},
    "user_agent":  "python-requests/2.28.0"
  }
}
```

## Severity levels

| Level  | Events                                                              |
|--------|---------------------------------------------------------------------|
| high   | Login success, credential capture, file download, DB queries, RCE  |
| medium | Admin probes, login failures, relay attempts, auth attempts         |
| low    | Session connects, page visits, scanner probes, heartbeats           |

## Useful commands

```bash
# Watch live forwarding
docker logs sg-forwarder -f

# Test SSH honeypot
ssh-keygen -R '[localhost]:2222' 2>/dev/null
ssh -p 2222 -o PreferredAuthentications=password root@localhost

# Test HTTP
curl http://localhost:8080/
curl http://localhost:8080/.env
curl -X POST http://localhost:8080/ehr/login -d "username=admin&password=admin"

# Test FTP
ftp -n localhost 21 <<< $'user anonymous test\nls\nquit'

# Test MySQL
mysql -h 127.0.0.1 -P 3307 -u root -padmin -e "SHOW DATABASES;" 2>/dev/null || true

# Test SMTP
printf 'EHLO test.com\r\nAUTH LOGIN\r\nQUIT\r\n' | nc -q2 localhost 25

# Test Redis
redis-cli -h localhost -p 6380 info
redis-cli -h localhost -p 6380 keys '*'
redis-cli -h localhost -p 6380 config get dir

# Check what's in the log volume
find /var/lib/docker/volumes -name "*.json" 2>/dev/null

# Tear down
docker compose -f docker-compose/sentinelgrid-honeypots.yml down
```

## Environment variables (forwarder)

| Variable      | Default                                    | Description            |
|---------------|--------------------------------------------|------------------------|
| API_URL       | https://uddiejez3g...apprunner.com/log     | Your backend API       |
| SENSOR_ID     | sg-do-claritymed-01                        | Droplet identifier     |
| BATCH_SIZE    | 20                                         | Events per POST        |
| HEARTBEAT_INT | 60                                         | Heartbeat interval (s) |

Edit in `docker-compose/sentinelgrid-honeypots.yml` under `sg-forwarder.environment`.
