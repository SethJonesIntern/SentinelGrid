#!/usr/bin/env python3
"""
SentinelGrid MySQL Honeypot  v4 — ClarityMed Health Systems
Wire-level MySQL 8.0 protocol with realistic ClarityMed DB responses.
"""
import asyncio, json, os, struct
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH  = Path("/var/log/honeypot/mysql.json")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
SENSOR_ID = os.getenv("SENSOR_ID", "sg-mysql-01")

SEVERITY = {
    "mysql.login.success":   "high",
    "mysql.login.attempt":   "medium",
    "mysql.query":           "high",
    "mysql.session.connect": "low",
}

def log_event(event_type, extra=None):
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

def pkt(payload, seq):
    return struct.pack("<I", len(payload))[:3] + bytes([seq]) + payload

def ok_pkt(seq=2):
    return pkt(b"\x00\x00\x00\x02\x00\x00\x00", seq)

def err_pkt(code, msg, seq=2):
    return pkt(b"\xff" + struct.pack("<H", code) + b"#28000" + msg.encode(), seq)

def handshake():
    auth_data = os.urandom(20)
    p = (b"\x0a" + b"8.0.35\x00" + struct.pack("<I", 1) +
         auth_data[:8] + b"\x00" + struct.pack("<H", 0xffff) + b"\x21" +
         struct.pack("<H", 0x0002) + struct.pack("<H", 0xffff) +
         bytes([len(auth_data)+1]) + b"\x00"*10 + auth_data[8:] + b"\x00" +
         b"mysql_native_password\x00")
    return pkt(p, seq=0)

def lenenc(n):
    if n < 251: return bytes([n])
    return b"\xfc" + struct.pack("<H", n)

def lcs(s):
    b = s.encode()
    return lenenc(len(b)) + b

def result_set(columns, rows, seq_start=1):
    out = b""
    seq = seq_start
    out += pkt(lenenc(len(columns)), seq); seq += 1
    for col in columns:
        p = (lcs("def") + lcs("claritymed_production") + lcs(col[0]) +
             lcs(col[0]) + lcs(col[0]) + lcs(col[0]) +
             b"\x0c\x21\x00" + struct.pack("<I", 255) +
             bytes([col[1]]) + struct.pack("<H", 0) + b"\x00\x00")
        out += pkt(p, seq); seq += 1
    out += pkt(b"\xfe\x00\x00\x02\x00", seq); seq += 1
    for row in rows:
        p = b"".join(lcs(str(v)) if v is not None else b"\xfb" for v in row)
        out += pkt(p, seq); seq += 1
    out += pkt(b"\xfe\x00\x00\x02\x00", seq)
    return out

FAKE_DBS   = ["claritymed_production","claritymed_staging","ehr_system","billing_db","analytics","audit_log"]
FAKE_TABLES = {
    "claritymed_production": ["staff","sessions","appointments","config","audit_log","api_keys"],
    "ehr_system":            ["patients","records","prescriptions","providers","facilities"],
    "billing_db":            ["invoices","payments","insurance_claims","contracts"],
}
FAKE_STAFF = [
    (1,"admin","admin@claritymed.com","$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGX2p9","admin","IT"),
    (2,"jsmith","jsmith@claritymed.com","$2b$12$abc123fakehashedpassword000000000","physician","Clinical"),
    (3,"mthompson","mthompson@claritymed.com","$2b$12$xyz789fakehashedpassword000000","analyst","Operations"),
    (4,"billingsvc","billingsvc@claritymed.com","$2b$12$billing123fakehashedpassword00","service","Billing"),
]
FAKE_CONFIG = [
    ("app_secret","claritymed_jwt_s3cr3t_k3y_2024"),
    ("smtp_password","SMTP_P@ssw0rd_2024"),
    ("aws_access_key","AKIAIOSFODNN7EXAMPLE"),
    ("aws_secret","wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
    ("ehr_api_key","EHR_API_K3Y_2024_claritymed"),
    ("encryption_key","AES256_Cl4r1tyM3d_K3y!"),
]

def handle_query(query):
    q = query.strip().upper()
    if "SHOW DATABASES" in q:
        return result_set([("Database",253)], [[d] for d in FAKE_DBS])
    if "SHOW TABLES" in q:
        tables = FAKE_TABLES.get("claritymed_production", ["staff","config"])
        return result_set([("Tables_in_claritymed_production",253)], [[t] for t in tables])
    if "INFORMATION_SCHEMA" in q and "TABLES" in q:
        rows = [[db,t,"BASE TABLE"] for db,ts in FAKE_TABLES.items() for t in ts]
        return result_set([("TABLE_SCHEMA",253),("TABLE_NAME",253),("TABLE_TYPE",253)], rows)
    if "FROM" in q and ("STAFF" in q or "USER" in q):
        return result_set(
            [("id",3),("username",253),("email",253),("password_hash",253),("role",253),("department",253)],
            [[str(r[0]),r[1],r[2],r[3],r[4],r[5]] for r in FAKE_STAFF]
        )
    if "FROM" in q and "CONFIG" in q:
        return result_set([("config_key",253),("config_value",253)], [[k,v] for k,v in FAKE_CONFIG])
    if "VERSION" in q:
        return result_set([("VERSION()",253)],[["8.0.35"]])
    if "USER()" in q:
        return result_set([("USER()",253)],[["root@localhost"]])
    if "SELECT 1" in q:
        return result_set([("1",3)],[["1"]])
    if q.startswith("USE "): return ok_pkt()
    if "CREATE" in q or "DROP" in q or "INSERT" in q or "UPDATE" in q or "DELETE" in q:
        return err_pkt(1142, "Command denied to user")
    if q.startswith("SET ") or q.startswith("SHOW "): return ok_pkt()
    return result_set([("result",253)],[])

class MySQLHoneypot(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport   = transport
        peer             = transport.get_extra_info("peername")
        self.source_ip   = peer[0] if peer else "unknown"
        self.source_port = peer[1] if peer else 0
        self.buf         = b""
        self.state       = "auth"
        self.username    = ""
        log_event("mysql.session.connect", {"source_ip": self.source_ip, "source_port": self.source_port})
        transport.write(handshake())

    def data_received(self, data):
        self.buf += data
        while len(self.buf) >= 4:
            length = struct.unpack("<I", self.buf[:3] + b"\x00")[0]
            if len(self.buf) < 4 + length: break
            seq     = self.buf[3]
            payload = self.buf[4:4+length]
            self.buf = self.buf[4+length:]
            if self.state == "auth":   self._auth(payload, seq)
            elif self.state == "cmd":  self._command(payload, seq)

    def _auth(self, payload, seq):
        try:
            offset = 36
            null   = payload.find(b"\x00", offset)
            user   = payload[offset:null].decode("utf-8", errors="replace")
            offset = null + 1
            alen   = payload[offset]; offset += 1
            phash  = payload[offset:offset+alen].hex(); offset += alen
            dend   = payload.find(b"\x00", offset)
            db     = payload[offset:dend].decode("utf-8","replace") if dend > offset else ""
            self.username = user
            log_event("mysql.login.attempt", {"source_ip": self.source_ip,
                "credentials": {"username": user, "password_hash": phash, "database": db}})
            ALLOW = {"root","admin","mysql","claritymed_app","ehr_service","billing","sa","dbadmin","user","claritymed"}
            if user.lower() in ALLOW:
                self.transport.write(ok_pkt(seq=seq+1))
                self.state = "cmd"
                log_event("mysql.login.success", {"source_ip": self.source_ip, "username": user})
            else:
                self.transport.write(err_pkt(1045, f"Access denied for user '{user}'@'{self.source_ip}'", seq=seq+1))
                self.transport.close()
        except Exception as e:
            log_event("mysql.parse.error", {"error": str(e)})
            self.transport.close()

    def _command(self, payload, seq):
        if not payload: return
        cmd  = payload[0]
        data = payload[1:].decode("utf-8", errors="replace")
        if cmd == 0x03:
            log_event("mysql.query", {"source_ip": self.source_ip, "username": self.username, "query": data[:500]})
            self.transport.write(handle_query(data))
        elif cmd == 0x02:
            self.transport.write(ok_pkt(seq=seq+1))
        elif cmd == 0x01:
            log_event("mysql.session.disconnect", {"source_ip": self.source_ip})
            self.transport.close()
        else:
            self.transport.write(ok_pkt(seq=seq+1))

    def connection_lost(self, exc):
        log_event("mysql.session.end", {"source_ip": self.source_ip})

async def main():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(MySQLHoneypot, "0.0.0.0", 3306)
    log_event("mysql.server.start", {"port": 3306})
    print("🪤  ClarityMed MySQL Honeypot running on :3306")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
