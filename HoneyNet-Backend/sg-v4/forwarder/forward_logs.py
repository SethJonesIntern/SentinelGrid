#!/usr/bin/env python3
"""
SentinelGrid Universal Log Forwarder  v4.0
==========================================
Identity: ClarityMed Health Systems
Fixes from v3:
  - Redis interesting-command filter bug FIXED
  - Volume paths match what docker compose actually creates
  - Cowrie uses separate sg-cowrie-logs volume at /logs/cowrie
  - severity on every event
  - Binary content filter on SMTP
  - No raw blobs in payloads
  - Dead-letter queue + offset tracking + heartbeat
"""
import json, os, threading, time, queue, requests
from pathlib import Path
from datetime import datetime, timezone

# ── CONFIG ────────────────────────────────────────────────────────────────────
API_URL       = os.getenv("API_URL",       "https://uddiejez3g.us-east-1.awsapprunner.com/log")
API_BATCH_URL = os.getenv("API_BATCH_URL", API_URL.replace("/log", "/logs/batch"))
SENSOR_ID     = os.getenv("SENSOR_ID",     "sg-claritymed-01")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "0.25"))
BATCH_SIZE    = int(os.getenv("BATCH_SIZE",       "20"))
BATCH_TIMEOUT = float(os.getenv("BATCH_TIMEOUT",  "2.0"))
HEARTBEAT_INT = float(os.getenv("HEARTBEAT_INT",  "60.0"))
OFFSET_DIR    = Path(os.getenv("OFFSET_DIR", "/var/lib/sg-forwarder/offsets"))
DLQ_PATH      = Path(os.getenv("DLQ_PATH",   "/var/lib/sg-forwarder/dead_letter.jsonl"))

# Paths match docker compose volume mounts exactly:
#   sg-logs        → /logs        (http, ftp, mysql, smtp, redis)
#   sg-cowrie-logs → /logs/cowrie (cowrie — separate volume)
LOG_SOURCES = {
    "/logs/cowrie/cowrie.json": "cowrie",
    "/logs/http.json":          "http",
    "/logs/ftp.json":           "ftp",
    "/logs/mysql.json":         "mysql",
    "/logs/smtp.json":          "smtp",
    "/logs/redis.json":         "redis",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def _severity(event_type: str) -> str:
    HIGH = {
        "cowrie.login.success", "cowrie.session.file_download", "cowrie.session.file_upload",
        "http.login.attempt", "http.admin.probe",
        "ftp.login.success", "ftp.file.download", "ftp.file.upload",
        "mysql.login.success", "mysql.query",
        "smtp.login.attempt", "smtp.message.received",
        "redis.rce.attempt", "redis.slaveof.attempt",
        "redis.replicaof.attempt", "redis.debug.attempt", "redis.flush.attempt",
    }
    LOW = {
        "cowrie.session.connect", "ftp.session.connect", "ftp.session.disconnect",
        "smtp.session.connect", "smtp.session.disconnect", "smtp.ehlo",
        "http.page.visit", "http.api.probe", "http.scan.probe",
        "redis.session.connect", "redis.session.disconnect",
        "mysql.session.connect",
    }
    if event_type in HIGH: return "high"
    if event_type in LOW:  return "low"
    return "medium"

def _is_clean(s: str, threshold: float = 0.15) -> bool:
    if not s: return True
    bad = sum(1 for c in s if ord(c) < 32 and c not in "\t\n\r")
    return (bad / len(s)) < threshold

# ── NORMALIZERS ───────────────────────────────────────────────────────────────
def normalize_cowrie(raw: dict):
    KEEP = {
        "cowrie.session.connect", "cowrie.login.success", "cowrie.login.failed",
        "cowrie.command.input", "cowrie.session.file_download",
        "cowrie.session.closed", "cowrie.direct-tcpip.request",
        "cowrie.session.file_upload",
    }
    event_type = raw.get("eventid", "")
    if event_type not in KEEP:
        return None
    return {
        "timestamp":     raw.get("timestamp"),
        "source_ip":     raw.get("src_ip"),
        "source_port":   raw.get("src_port"),
        "event_type":    event_type,
        "sensor_id":     raw.get("sensor", SENSOR_ID),
        "honeypot_type": "ssh",
        "severity":      _severity(event_type),
        "session_id":    raw.get("session"),
        "data": {
            "username": raw.get("username"),
            "password": raw.get("password"),
            "command":  raw.get("input"),
            "url":      raw.get("url"),
            "destfile": raw.get("destfile"),
        },
    }

def normalize_http(raw: dict):
    if raw.get("event_type") == "http.server.start":
        return None
    event_type = raw.get("event_type", "")
    return {
        "timestamp":     raw.get("timestamp"),
        "source_ip":     raw.get("source_ip"),
        "source_port":   raw.get("source_port"),
        "event_type":    event_type,
        "sensor_id":     raw.get("sensor_id", SENSOR_ID),
        "honeypot_type": "http",
        "severity":      _severity(event_type),
        "session_id":    raw.get("session_id"),
        "data": {
            "method":      raw.get("method"),
            "path":        raw.get("path"),
            "page":        raw.get("page"),
            "user_agent":  raw.get("user_agent"),
            "credentials": raw.get("credentials"),
            "probe_path":  raw.get("probe_path"),
        },
    }

def normalize_ftp(raw: dict):
    if raw.get("event_type") == "ftp.server.start":
        return None
    event_type = raw.get("event_type", "")
    return {
        "timestamp":     raw.get("timestamp"),
        "source_ip":     raw.get("source_ip"),
        "source_port":   raw.get("source_port"),
        "event_type":    event_type,
        "sensor_id":     raw.get("sensor_id", SENSOR_ID),
        "honeypot_type": "ftp",
        "severity":      _severity(event_type),
        "data": {
            "credentials": raw.get("credentials"),
            "username":    raw.get("username"),
            "file":        raw.get("file"),
        },
    }

def normalize_mysql(raw: dict):
    if raw.get("event_type") == "mysql.server.start":
        return None
    event_type = raw.get("event_type", "")
    return {
        "timestamp":     raw.get("timestamp"),
        "source_ip":     raw.get("source_ip"),
        "source_port":   raw.get("source_port"),
        "event_type":    event_type,
        "sensor_id":     raw.get("sensor_id", SENSOR_ID),
        "honeypot_type": "mysql",
        "severity":      _severity(event_type),
        "data": {
            "credentials": raw.get("credentials"),
            "username":    raw.get("username"),
            "query":       raw.get("query", "")[:500],
        },
    }

def normalize_smtp(raw: dict):
    SKIP = {"smtp.server.start", "smtp.command"}
    event_type = raw.get("event_type", "")
    if event_type in SKIP:
        return None
    for field in ["command", "ehlo_host", "mail_from"]:
        val = raw.get(field, "")
        if val and not _is_clean(val):
            return None
    return {
        "timestamp":     raw.get("timestamp"),
        "source_ip":     raw.get("source_ip"),
        "source_port":   raw.get("source_port"),
        "event_type":    event_type,
        "sensor_id":     raw.get("sensor_id", SENSOR_ID),
        "honeypot_type": "smtp",
        "severity":      _severity(event_type),
        "data": {
            "mail_from":    raw.get("mail_from"),
            "rcpt_to":      raw.get("rcpt_to"),
            "ehlo_host":    raw.get("ehlo_host"),
            "credentials":  raw.get("credentials"),
            "body_preview": raw.get("body_preview", "")[:300],
            "body_size":    raw.get("body_size"),
        },
    }

def normalize_redis(raw: dict):
    if raw.get("event_type") == "redis.server.start":
        return None

    event_type = raw.get("event_type", "")

    # FIX: was calling _severity("redis.command") which always returned "low"
    # Now we check the actual command string to decide whether to forward
    if event_type == "redis.command":
        cmd = raw.get("command", "").upper()
        INTERESTING = {
            "CONFIG", "SLAVEOF", "REPLICAOF", "DEBUG",
            "EVAL", "EVALSHA", "SCRIPT", "FLUSHALL",
            "FLUSHDB", "AUTH", "KEYS", "MODULE",
        }
        if cmd not in INTERESTING:
            return None  # drop PING, GET, SET, INFO, SELECT noise

    return {
        "timestamp":     raw.get("timestamp"),
        "source_ip":     raw.get("source_ip"),
        "source_port":   raw.get("source_port"),
        "event_type":    event_type,
        "sensor_id":     raw.get("sensor_id", SENSOR_ID),
        "honeypot_type": "redis",
        "severity":      _severity(event_type),
        "data": {
            "command":    raw.get("command"),
            "args":       raw.get("args", [])[:10],
            "config_set": raw.get("config_set"),
            "technique":  raw.get("technique"),
            "password":   raw.get("password"),
        },
    }

NORMALIZERS = {
    "cowrie": normalize_cowrie,
    "http":   normalize_http,
    "ftp":    normalize_ftp,
    "mysql":  normalize_mysql,
    "smtp":   normalize_smtp,
    "redis":  normalize_redis,
}

# ── OFFSET TRACKING ───────────────────────────────────────────────────────────
OFFSET_DIR.mkdir(parents=True, exist_ok=True)
DLQ_PATH.parent.mkdir(parents=True, exist_ok=True)

def _offset_file(log_path: str) -> Path:
    safe = log_path.replace("/", "_").strip("_")
    return OFFSET_DIR / f"{safe}.offset"

def read_offset(log_path: str) -> int:
    try:
        return int(_offset_file(log_path).read_text().strip())
    except Exception:
        return -1

def write_offset(log_path: str, offset: int):
    _offset_file(log_path).write_text(str(offset))

# ── DEAD-LETTER QUEUE ─────────────────────────────────────────────────────────
dlq_lock = threading.Lock()

def dlq_write(events: list):
    with dlq_lock:
        with DLQ_PATH.open("a") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

def dlq_retry_worker():
    while True:
        time.sleep(30)
        if not DLQ_PATH.exists(): continue
        with dlq_lock:
            try:
                lines = DLQ_PATH.read_text().strip().splitlines()
            except Exception:
                continue
            if not lines: continue
            DLQ_PATH.write_text("")
        pending = []
        for line in lines:
            try: pending.append(json.loads(line))
            except Exception: pass
        if not pending: continue
        still_failed = [e for e in pending if not _post_single(e, "DLQ")]
        if still_failed:
            dlq_write(still_failed)
            print(f"♻️  DLQ: {len(still_failed)}/{len(pending)} still failing")
        else:
            print(f"✅ DLQ: flushed {len(pending)} events")

# ── SENDER ────────────────────────────────────────────────────────────────────
def _post_single(event: dict, label: str = "") -> bool:
    try:
        r = requests.post(API_URL, json=event, timeout=6)
        return r.status_code < 300
    except requests.RequestException as e:
        print(f"🌐 [{label}] {e}")
        return False

def _post_batch(events: list, label: str = "") -> bool:
    try:
        r = requests.post(API_BATCH_URL, json={"events": events}, timeout=10)
        if r.status_code < 300: return True
        if r.status_code == 404:
            return all(_post_single(e, label) for e in events)
        return False
    except requests.RequestException:
        return all(_post_single(e, label) for e in events)

_send_queue: "queue.Queue[dict]" = queue.Queue(maxsize=10_000)

def sender_worker():
    while True:
        batch    = []
        deadline = time.monotonic() + BATCH_TIMEOUT
        while len(batch) < BATCH_SIZE:
            remaining = deadline - time.monotonic()
            if remaining <= 0: break
            try:
                batch.append(_send_queue.get(timeout=min(remaining, 0.5)))
            except queue.Empty:
                if batch: break
        if not batch: continue
        label = f"batch={len(batch)}"
        ok    = _post_batch(batch, label) if len(batch) > 1 else _post_single(batch[0], label)
        if ok:
            types = ", ".join(set(e.get("event_type","?") for e in batch))
            ips   = ", ".join(set(e.get("source_ip","?")   for e in batch))
            print(f"✅ [{label}] {types} | {ips}")
        else:
            print(f"❌ [{label}] failed — writing to DLQ")
            dlq_write(batch)

# ── TAILER ────────────────────────────────────────────────────────────────────
def tail_file(log_path: str, source_type: str):
    path  = Path(log_path)
    norm  = NORMALIZERS[source_type]
    label = source_type.upper()

    while not path.exists():
        print(f"⏳ [{label}] Waiting for {path} ...")
        time.sleep(5)

    saved = read_offset(log_path)
    with path.open("r") as f:
        if saved == -1:
            f.seek(0, 2)
            write_offset(log_path, f.tell())
            print(f"📂 [{label}] First run — tailing from end of {path}")
        else:
            f.seek(saved)
            print(f"📂 [{label}] Resuming from offset {saved}")

        while True:
            line = f.readline()
            if not line:
                time.sleep(POLL_INTERVAL)
                try:
                    if path.stat().st_size < f.tell():
                        print(f"🔄 [{label}] Log rotated — resetting")
                        f.seek(0); write_offset(log_path, 0)
                except OSError:
                    pass
                continue
            line = line.strip()
            if not line: continue
            write_offset(log_path, f.tell())
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            event = norm(raw)
            if event is None: continue
            if not event.get("timestamp") or not event.get("source_ip"): continue
            _send_queue.put(event)

# ── HEARTBEAT ─────────────────────────────────────────────────────────────────
def heartbeat_worker():
    while True:
        time.sleep(HEARTBEAT_INT)
        payload = {
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "event_type":    "forwarder.heartbeat",
            "sensor_id":     SENSOR_ID,
            "honeypot_type": "forwarder",
            "severity":      "low",
            "source_ip":     "127.0.0.1",
            "data": {"queue_depth": _send_queue.qsize()},
        }
        try:
            requests.post(API_URL, json=payload, timeout=5)
            print(f"💓 Heartbeat | queue={_send_queue.qsize()}")
        except Exception as e:
            print(f"💔 Heartbeat failed: {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  SentinelGrid Log Forwarder  v4.0 — ClarityMed")
    print(f"  API     : {API_URL}")
    print(f"  Sensor  : {SENSOR_ID}")
    print(f"  Sources : {len(LOG_SOURCES)}")
    print(f"  Offsets : {OFFSET_DIR}")
    print(f"  DLQ     : {DLQ_PATH}")
    print("=" * 60)

    threading.Thread(target=sender_worker,    name="sender",    daemon=True).start()
    threading.Thread(target=dlq_retry_worker, name="dlq-retry", daemon=True).start()
    threading.Thread(target=heartbeat_worker, name="heartbeat", daemon=True).start()

    tailers = []
    for log_path, source_type in LOG_SOURCES.items():
        t = threading.Thread(
            target=tail_file, args=(log_path, source_type),
            name=f"tailer-{source_type}", daemon=True,
        )
        t.start()
        tailers.append(t)

    while True:
        time.sleep(15)
        for i, t in enumerate(tailers):
            if not t.is_alive():
                log_path, source_type = list(LOG_SOURCES.items())[i]
                print(f"⚠️  Tailer {t.name} died — restarting")
                new_t = threading.Thread(
                    target=tail_file, args=(log_path, source_type),
                    name=f"tailer-{source_type}", daemon=True,
                )
                new_t.start()
                tailers[i] = new_t
        alive    = sum(1 for t in tailers if t.is_alive())
        dlq_size = "yes" if DLQ_PATH.exists() and DLQ_PATH.stat().st_size > 0 else "empty"
        print(f"💓 Watchdog: {alive}/{len(tailers)} alive | queue={_send_queue.qsize()} | dlq={dlq_size}")

if __name__ == "__main__":
    main()
