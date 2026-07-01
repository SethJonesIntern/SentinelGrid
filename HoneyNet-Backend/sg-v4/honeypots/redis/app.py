#!/usr/bin/env python3
"""
SentinelGrid Redis Honeypot  v4
Identity: ClarityMed Health Systems — claritymed-cache-01
Full RESP protocol. Logs all commands, detects RCE attempts.
Returns realistic ClarityMed-themed fake data.
"""
import asyncio, json, os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH  = Path("/var/log/honeypot/redis.json")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
SENSOR_ID = os.getenv("SENSOR_ID", "sg-redis-01")

SEVERITY = {
    "redis.rce.attempt":       "high",
    "redis.slaveof.attempt":   "high",
    "redis.replicaof.attempt": "high",
    "redis.auth.attempt":      "medium",
    "redis.flush.attempt":     "medium",
    "redis.debug.attempt":     "medium",
    "redis.command":           "low",
    "redis.session.connect":   "low",
}

def log_event(event_type: str, extra: dict = None):
    entry = {
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "sensor_id":  SENSOR_ID,
        "event_type": event_type,
        "severity":   SEVERITY.get(event_type, "low"),
        **(extra or {})
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{event_type}] {extra}")

def bulk(s)    -> bytes: return f"${len(s)}\r\n{s}\r\n".encode()
def simple(s)  -> bytes: return f"+{s}\r\n".encode()
def integer(n) -> bytes: return f":{n}\r\n".encode()
def null_bulk()-> bytes: return b"$-1\r\n"
def array(items)->bytes:
    out = f"*{len(items)}\r\n".encode()
    for it in items: out += bulk(str(it))
    return out

FAKE_INFO = """\
# Server
redis_version:6.2.14
redis_mode:standalone
os:Linux 5.4.0-1074-aws x86_64
tcp_port:6379
uptime_in_seconds:2764800
uptime_in_days:32
# Clients
connected_clients:4
# Memory
used_memory_human:4.00M
maxmemory:0
# Stats
total_connections_received:28491
total_commands_processed:184723
# Replication
role:master
connected_slaves:0
# Keyspace
db0:keys=11,expires=3,avg_ttl=86400000
"""

FAKE_KV = {
    "session:admin":       '{"user_id":1,"role":"admin","token":"eyJhbGciOiJIUzI1NiJ9.claritymed_fake"}',
    "session:jsmith":      '{"user_id":2,"role":"physician","token":"eyJhbGciOiJIUzI1NiJ9.jsmith_fake"}',
    "config:db":           '{"host":"claritymed-db-01.internal","user":"claritymed_app","pass":"ClarityDB_Pr0d_2024!"}',
    "config:aws":          '{"key":"AKIAIOSFODNN7EXAMPLE","secret":"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY","bucket":"claritymed-patient-data"}',
    "config:smtp":         '{"host":"smtp.claritymed.com","user":"noreply@claritymed.com","pass":"SMTP_P@ssw0rd_2024"}',
    "api_key:ehr-service": "ehr_sk_live_Cl4r1tyM3d2024XXXXX",
    "api_key:billing":     "bill_sk_live_B1ll1ngSvc2024XXXX",
    "rate_limit:global":   "127",
    "cache:app_config":    '{"version":"3.1.4","env":"production","debug":false}',
    "lock:deploy":         "0",
}

class RESPProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        self.transport   = transport
        peer             = transport.get_extra_info("peername")
        self.source_ip   = peer[0] if peer else "unknown"
        self.source_port = peer[1] if peer else 0
        self.buf         = b""
        self.config_dir  = "/var/lib/redis"
        self.config_file = "dump.rdb"
        log_event("redis.session.connect", {
            "source_ip": self.source_ip, "source_port": self.source_port
        })

    def data_received(self, data):
        self.buf += data
        while True:
            cmd, self.buf = self._parse(self.buf)
            if cmd is None: break
            self._dispatch(cmd)

    def _parse(self, buf):
        if not buf: return None, buf
        if buf[0:1] == b"*":
            try:
                eol = buf.index(b"\r\n")
                count = int(buf[1:eol])
                pos = eol + 2
                args = []
                for _ in range(count):
                    if buf[pos:pos+1] != b"$": return None, buf
                    eol2 = buf.index(b"\r\n", pos)
                    length = int(buf[pos+1:eol2])
                    start = eol2 + 2; end = start + length
                    if end + 2 > len(buf): return None, buf
                    args.append(buf[start:end].decode("utf-8", errors="replace"))
                    pos = end + 2
                return args, buf[pos:]
            except (ValueError, IndexError):
                return None, buf
        else:
            if b"\r\n" not in buf and b"\n" not in buf: return None, buf
            line, rest = buf.split(b"\n", 1)
            return line.decode("utf-8", errors="replace").strip().split(), rest

    def _dispatch(self, args):
        if not args: return
        cmd = args[0].upper()
        rest = args[1:]

        # Log all commands — filter noisy ones from forwarding in the forwarder
        log_event("redis.command", {
            "source_ip": self.source_ip, "command": cmd, "args": rest[:8]
        })

        if cmd == "PING":
            self.transport.write(simple("PONG") if not rest else bulk(rest[0]))
        elif cmd == "INFO":
            self.transport.write(bulk(FAKE_INFO))
        elif cmd == "CONFIG":
            sub = rest[0].upper() if rest else ""
            if sub == "GET":
                key = rest[1] if len(rest) > 1 else "*"
                if key == "dir":
                    self.transport.write(array(["dir", self.config_dir]))
                elif key == "dbfilename":
                    self.transport.write(array(["dbfilename", self.config_file]))
                else:
                    self.transport.write(array(["dir", self.config_dir, "dbfilename", self.config_file, "bind", "0.0.0.0", "requirepass", ""]))
            elif sub == "SET":
                log_event("redis.rce.attempt", {"source_ip": self.source_ip, "config_set": rest, "technique": "CONFIG SET file write"})
                if len(rest) >= 3:
                    if rest[1].lower() == "dir": self.config_dir = rest[2]
                    elif rest[1].lower() == "dbfilename": self.config_file = rest[2]
                self.transport.write(simple("OK"))
            else:
                self.transport.write(simple("OK"))
        elif cmd in ("SLAVEOF", "REPLICAOF"):
            log_event(f"redis.{cmd.lower()}.attempt", {"source_ip": self.source_ip, "master_host": rest[0] if rest else "", "master_port": rest[1] if len(rest) > 1 else "", "technique": "Replication-based RCE"})
            self.transport.write(simple("OK"))
        elif cmd == "DEBUG":
            log_event("redis.debug.attempt", {"source_ip": self.source_ip, "args": rest})
            self.transport.write(simple("OK"))
        elif cmd in ("EVAL", "EVALSHA", "SCRIPT"):
            log_event("redis.rce.attempt", {"source_ip": self.source_ip, "technique": f"{cmd} Lua RCE", "args": rest[:3]})
            self.transport.write(simple("OK"))
        elif cmd in ("SET","SETEX","PSETEX","MSET","SETNX"):
            if len(rest) >= 2: FAKE_KV[rest[0]] = rest[1]
            self.transport.write(simple("OK"))
        elif cmd == "GET":
            v = FAKE_KV.get(rest[0] if rest else "")
            self.transport.write(bulk(v) if v else null_bulk())
        elif cmd == "KEYS":
            pat = rest[0] if rest else "*"
            keys = list(FAKE_KV.keys()) if pat == "*" else [k for k in FAKE_KV if pat.strip("*") in k]
            self.transport.write(array(keys))
        elif cmd == "DBSIZE":
            self.transport.write(integer(len(FAKE_KV)))
        elif cmd in ("FLUSHALL","FLUSHDB"):
            log_event("redis.flush.attempt", {"source_ip": self.source_ip, "command": cmd})
            self.transport.write(simple("OK"))
        elif cmd == "AUTH":
            log_event("redis.auth.attempt", {"source_ip": self.source_ip, "password": rest[0] if rest else ""})
            self.transport.write(simple("OK"))
        elif cmd in ("SELECT","SAVE","NOOP"):
            self.transport.write(simple("OK"))
        elif cmd == "BGSAVE":
            self.transport.write(simple("Background saving started"))
        elif cmd == "LASTSAVE":
            self.transport.write(integer(1704067200))
        elif cmd == "COMMAND":
            self.transport.write(integer(246))
        elif cmd == "QUIT":
            self.transport.write(simple("OK"))
            self.transport.close()
        else:
            self.transport.write(simple("OK"))

    def connection_lost(self, exc):
        log_event("redis.session.disconnect", {"source_ip": self.source_ip})

async def main():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(RESPProtocol, "0.0.0.0", 6379)
    log_event("redis.server.start", {"port": 6379})
    print("🪤  ClarityMed Redis Honeypot running on :6379")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
