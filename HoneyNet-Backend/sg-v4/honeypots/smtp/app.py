#!/usr/bin/env python3
"""
SentinelGrid SMTP Honeypot  v4 — ClarityMed Health Systems
mail.claritymed.com — Full SMTP wire protocol.
AUTH LOGIN/PLAIN capture, relay detection, binary filter.
"""
import asyncio, base64, json, os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH  = Path("/var/log/honeypot/smtp.json")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
SENSOR_ID = os.getenv("SENSOR_ID", "sg-smtp-01")

SEVERITY = {
    "smtp.login.attempt":      "high",
    "smtp.message.received":   "high",
    "smtp.relay.attempt":      "medium",
    "smtp.session.connect":    "low",
    "smtp.session.disconnect": "low",
    "smtp.ehlo":               "low",
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

def is_printable(s, threshold=0.15):
    if not s: return True
    bad = sum(1 for c in s if ord(c) < 32 and c not in "\t\n\r")
    return (bad / len(s)) < threshold

class SMTPSession(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport   = transport
        peer             = transport.get_extra_info("peername")
        self.source_ip   = peer[0] if peer else "unknown"
        self.source_port = peer[1] if peer else 0
        self.buf         = ""
        self.auth_state  = None
        self.auth_user   = ""
        self.mail_from   = ""
        self.rcpt_to     = []
        self.ehlo_host   = ""
        self.body_lines  = []
        self.in_data     = False
        log_event("smtp.session.connect", {"source_ip": self.source_ip, "source_port": self.source_port})
        self._send("220 mail.claritymed.com ESMTP Postfix (Ubuntu) ClarityMed-2.11.3")

    def _send(self, line):
        self.transport.write((line + "\r\n").encode())

    def data_received(self, data):
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            return
        if not is_printable(text):
            return
        self.buf += text
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            line = line.rstrip("\r")
            if self.in_data:
                self._handle_data_line(line)
            else:
                self._handle_command(line)

    def _handle_command(self, line):
        if not line.strip(): return
        upper = line.upper()

        if self.auth_state == "login_user":
            try: self.auth_user = base64.b64decode(line.strip()).decode("utf-8","replace")
            except Exception: self.auth_user = line.strip()
            self.auth_state = "login_pass"
            self._send("334 UGFzc3dvcmQ6")
            return

        if self.auth_state == "login_pass":
            try: password = base64.b64decode(line.strip()).decode("utf-8","replace")
            except Exception: password = line.strip()
            log_event("smtp.login.attempt", {"source_ip": self.source_ip,
                "credentials": {"username": self.auth_user, "password": password},
                "method": "AUTH LOGIN"})
            self.auth_state = None
            self._send("235 2.7.0 Authentication successful")
            return

        if self.auth_state == "plain":
            try:
                decoded = base64.b64decode(line.strip()).decode("utf-8","replace")
                parts   = decoded.split("\x00")
                user    = parts[1] if len(parts) > 1 else ""
                passwd  = parts[2] if len(parts) > 2 else ""
            except Exception:
                user, passwd = line.strip(), ""
            log_event("smtp.login.attempt", {"source_ip": self.source_ip,
                "credentials": {"username": user, "password": passwd},
                "method": "AUTH PLAIN"})
            self.auth_state = None
            self._send("235 2.7.0 Authentication successful")
            return

        if upper.startswith("EHLO") or upper.startswith("HELO"):
            self.ehlo_host = line.split(None,1)[1].strip() if " " in line else ""
            log_event("smtp.ehlo", {"source_ip": self.source_ip, "ehlo_host": self.ehlo_host})
            if upper.startswith("EHLO"):
                self._send(f"250-mail.claritymed.com Hello {self.ehlo_host}")
                self._send("250-SIZE 52428800")
                self._send("250-ENHANCEDSTATUSCODES")
                self._send("250-8BITMIME")
                self._send("250-AUTH LOGIN PLAIN")
                self._send("250 STARTTLS")
            else:
                self._send(f"250 mail.claritymed.com Hello {self.ehlo_host}")

        elif upper.startswith("AUTH LOGIN"):
            self.auth_state = "login_user"
            self._send("334 VXNlcm5hbWU6")

        elif upper.startswith("AUTH PLAIN"):
            parts = line.split(None, 2)
            if len(parts) == 3:
                try:
                    decoded = base64.b64decode(parts[2]).decode("utf-8","replace")
                    p = decoded.split("\x00")
                    user   = p[1] if len(p) > 1 else ""
                    passwd = p[2] if len(p) > 2 else ""
                except Exception:
                    user, passwd = parts[2], ""
                log_event("smtp.login.attempt", {"source_ip": self.source_ip,
                    "credentials": {"username": user, "password": passwd},
                    "method": "AUTH PLAIN inline"})
                self._send("235 2.7.0 Authentication successful")
            else:
                self.auth_state = "plain"
                self._send("334 ")

        elif upper.startswith("MAIL FROM"):
            self.mail_from = line[10:].strip().strip("<>")
            self._send("250 2.1.0 Ok")

        elif upper.startswith("RCPT TO"):
            rcpt = line[8:].strip().strip("<>")
            self.rcpt_to.append(rcpt)
            if self.mail_from and "@claritymed.com" not in self.mail_from:
                log_event("smtp.relay.attempt", {"source_ip": self.source_ip,
                    "mail_from": self.mail_from, "rcpt_to": rcpt})
            self._send("250 2.1.5 Ok")

        elif upper == "DATA":
            self.in_data    = True
            self.body_lines = []
            self._send("354 End data with <CR><LF>.<CR><LF>")

        elif upper == "STARTTLS":
            self._send("220 2.0.0 Ready to start TLS")

        elif upper in ("VRFY","EXPN"):
            self._send("252 Cannot VRFY user")

        elif upper == "RSET":
            self.mail_from = ""; self.rcpt_to = []; self.body_lines = []
            self._send("250 2.0.0 Ok")

        elif upper == "NOOP":
            self._send("250 2.0.0 Ok")

        elif upper == "QUIT":
            log_event("smtp.session.disconnect", {"source_ip": self.source_ip})
            self._send("221 2.0.0 Bye")
            self.transport.close()

        else:
            self._send("502 5.5.2 Error: command not recognized")

    def _handle_data_line(self, line):
        if line == ".":
            self.in_data = False
            body = "\n".join(self.body_lines)
            log_event("smtp.message.received", {"source_ip": self.source_ip,
                "mail_from": self.mail_from, "rcpt_to": self.rcpt_to,
                "ehlo_host": self.ehlo_host, "body_preview": body[:500], "body_size": len(body)})
            self.mail_from = ""; self.rcpt_to = []; self.body_lines = []
            self._send("250 2.0.0 Ok: queued as CM" + os.urandom(4).hex().upper())
        else:
            if len(self.body_lines) < 100:
                self.body_lines.append(line)

    def connection_lost(self, exc):
        log_event("smtp.session.disconnect", {"source_ip": self.source_ip})

async def main():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(SMTPSession, "0.0.0.0", 25)
    log_event("smtp.server.start", {"port": 25})
    print("🪤  ClarityMed SMTP Honeypot running on :25")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
