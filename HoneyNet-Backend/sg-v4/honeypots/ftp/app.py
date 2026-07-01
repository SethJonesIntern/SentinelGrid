#!/usr/bin/env python3
"""
SentinelGrid FTP Honeypot  v4 — ClarityMed Health Systems
Deep bait filesystem with realistic healthcare IT files.
"""
import json, os
from datetime import datetime, timezone
from pathlib import Path
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import DummyAuthorizer

LOG_PATH  = Path("/var/log/honeypot/ftp.json")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
SENSOR_ID = os.getenv("SENSOR_ID", "sg-ftp-01")

SEVERITY = {
    "ftp.login.success":      "high",
    "ftp.login.failed":       "medium",
    "ftp.file.download":      "high",
    "ftp.file.upload":        "high",
    "ftp.session.connect":    "low",
    "ftp.session.disconnect": "low",
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

BAIT_ROOT = Path("/ftp/bait")
BAIT_FILES = {
    "README.txt": "ClarityMed Health Systems — Secure FTP Server\nAuthorized personnel only.\nContact IT: helpdesk@claritymed.com\n",
    "TRANSFER_LOG.txt": "2024-03-01 09:12 jsmith uploaded employee_roster_q1.xlsx\n2024-03-05 14:33 backup uploaded db_backup_20240305.sql.gz\n2024-03-10 11:05 devops uploaded deploy_keys.zip\n",
    "credentials/server_passwords.txt": "# ClarityMed Server Credentials — CONFIDENTIAL\nclaritymed-app01  root  ClarityPr0d_2024!\nclaritymed-db-01  mysql  DBAdmin_S3cur3!\nclaritymed-cache-01  redis  Redis_S3cr3t!\nvpn.claritymed.com  vpnuser  VPN_P@ss2024\n",
    "credentials/aws_keys.csv": "environment,access_key_id,secret_access_key,region\nproduction,AKIAIOSFODNN7EXAMPLE,wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY,us-east-1\nstaging,AKIAI44QH8DHBEXAMPLE,je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY,us-west-2\n",
    "credentials/vpn_config.txt": "VPN Server: vpn.claritymed.com:1194\nUsername: claritymed_vpn\nPassword: VPN_Cl4r1ty_2024!\nMFA Seed: JBSWY3DPEHPK3PXP\n",
    "credentials/ssh_keys.tar.gz": b"\x1f\x8b\x08\x00" + b"\x00" * 120,
    "backups/db_backup_20240315.sql": "-- ClarityMed Production DB Backup\n-- Date: 2024-03-15\nCREATE DATABASE claritymed_production;\nUSE claritymed_production;\nCREATE TABLE staff (id INT, username VARCHAR(64), email VARCHAR(128), password_hash VARCHAR(255), role VARCHAR(32));\nINSERT INTO staff VALUES (1,'admin','admin@claritymed.com','$2b$12$LQv3c1yqBWVHxkd0LHAkCO','admin');\n",
    "backups/config_backup_20240315.tar.gz": b"\x1f\x8b\x08\x00" + b"\x00" * 200,
    "configs/.env.production": "APP_ENV=production\nDB_HOST=claritymed-db-01.internal\nDB_USER=claritymed_app\nDB_PASS=ClarityDB_Pr0d_2024!\nREDIS_URL=redis://:Redis_S3cr3t!@claritymed-cache-01.internal:6379\nAWS_KEY=AKIAIOSFODNN7EXAMPLE\nAWS_SECRET=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\nJWT_SECRET=claritymed_jwt_s3cr3t_k3y_2024\n",
    "configs/database.ini": "[production]\nhost=claritymed-db-01.internal\nport=3306\nuser=claritymed_app\npassword=ClarityDB_Pr0d_2024!\ndatabase=claritymed_production\n",
    "configs/nginx.conf": "server {\n  listen 443 ssl;\n  server_name portal.claritymed.com;\n  ssl_certificate /etc/ssl/claritymed/claritymed.crt;\n  location / { proxy_pass http://127.0.0.1:8080; }\n  location /ehr { proxy_pass http://claritymed-ehr-01.internal:8443; }\n}\n",
    "scripts/deploy.sh": "#!/bin/bash\nSSH_KEY=/home/deploy/.ssh/id_rsa\nfor SERVER in claritymed-app01 claritymed-app02; do\n  ssh -i $SSH_KEY deploy@$SERVER.internal 'cd /opt/claritymed && git pull && pm2 restart all'\ndone\n",
    "scripts/backup_db.sh": "#!/bin/bash\nmysqldump -h claritymed-db-01.internal -u claritymed_app -pClarityDB_Pr0d_2024! claritymed_production > /backups/db_$(date +%Y%m%d).sql\n",
    "reports/staff_roster_q1_2024.csv": "id,name,email,department,role\n1,John Smith,jsmith@claritymed.com,Clinical,Physician\n2,Maria Thompson,mthompson@claritymed.com,Operations,Analyst\n3,Admin User,admin@claritymed.com,IT,System Administrator\n",
    "reports/q1_financial_summary.csv": "department,budget,spent,remaining\nClinical Operations,4500000,3821000,679000\nIT Infrastructure,1200000,987000,213000\nBilling,890000,754000,136000\n",
}

def create_bait_files():
    for path, content in BAIT_FILES.items():
        full = BAIT_ROOT / path
        full.parent.mkdir(parents=True, exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with full.open(mode) as f:
            f.write(content)

create_bait_files()

class HoneypotFTPHandler(FTPHandler):
    def on_connect(self):
        log_event("ftp.session.connect", {"source_ip": self.remote_ip, "source_port": self.remote_port})
    def on_disconnect(self):
        log_event("ftp.session.disconnect", {"source_ip": self.remote_ip})
    def on_login_failed(self, username, password):
        log_event("ftp.login.failed", {"source_ip": self.remote_ip, "credentials": {"username": username, "password": password}})
    def on_login(self, username):
        log_event("ftp.login.success", {"source_ip": self.remote_ip, "username": username})
    def on_file_sent(self, file):
        log_event("ftp.file.download", {"source_ip": self.remote_ip, "file": str(file)})
    def on_file_received(self, file):
        log_event("ftp.file.upload", {"source_ip": self.remote_ip, "file": str(file)})

def main():
    auth = DummyAuthorizer()
    auth.add_anonymous(str(BAIT_ROOT), perm="elr")
    for user, pwd in [
        ("ftp","ftp"),("admin","admin"),("admin","admin123"),
        ("ftpuser","ftpuser"),("user","password"),("root","root"),
        ("backup","backup"),("deploy","deploy"),
        ("jsmith","jsmith"),("claritymed","claritymed"),
        ("billingsvc","billing123"),("devops","devops"),
    ]:
        try:
            auth.add_user(user, pwd, str(BAIT_ROOT), perm="elradfmwMT")
        except Exception:
            pass
    handler                    = HoneypotFTPHandler
    handler.authorizer         = auth
    handler.banner             = "220 ClarityMed Secure FTP Server (ProFTPD 1.3.8) ready."
    handler.passive_ports      = range(60000, 60100)
    handler.max_login_attempts = 999
    handler.login_timeout      = 60
    handler.timeout            = 300
    server = FTPServer(("0.0.0.0", 21), handler)
    server.max_cons = 256
    server.max_cons_per_ip = 50
    log_event("ftp.server.start", {"port": 21})
    print("🪤  ClarityMed FTP Honeypot running on :21")
    server.serve_forever()

if __name__ == "__main__":
    main()
