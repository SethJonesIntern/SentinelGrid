#!/usr/bin/env python3
"""
SentinelGrid HTTP Honeypot  v4 — ClarityMed Health Systems
Multi-page fake healthcare web platform.
"""
import json, os, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, redirect, make_response

app = Flask(__name__)
LOG_PATH  = Path("/var/log/honeypot/http.json")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
SENSOR_ID = os.getenv("SENSOR_ID", "sg-http-01")

SEVERITY = {
    "http.login.attempt": "high",
    "http.admin.probe":   "medium",
    "http.file.probe":    "medium",
    "http.api.probe":     "low",
    "http.scan.probe":    "low",
    "http.page.visit":    "low",
}

def log_event(event_type, extra=None):
    entry = {
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "sensor_id":   SENSOR_ID,
        "event_type":  event_type,
        "severity":    SEVERITY.get(event_type, "low"),
        "source_ip":   request.headers.get("X-Forwarded-For", request.remote_addr),
        "source_port": request.environ.get("REMOTE_PORT"),
        "method":      request.method,
        "path":        request.path,
        "user_agent":  request.headers.get("User-Agent"),
        "session_id":  request.cookies.get("PHPSESSID", str(uuid.uuid4())[:8]),
        **(extra or {})
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")

@app.after_request
def bait_headers(r):
    r.headers["Server"]       = "Apache/2.4.54 (Ubuntu)"
    r.headers["X-Powered-By"] = "PHP/8.1.12"
    r.headers["X-Application"]= "ClarityMed-Portal/3.1"
    return r

PORTAL = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>ClarityMed Health Systems — Patient Portal</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:linear-gradient(135deg,#0a2540,#1a6b9a);font-family:'Segoe UI',sans-serif;
     display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh}
.logo{text-align:center;margin-bottom:20px;color:#fff}
.logo h1{font-size:1.8rem;font-weight:700}.logo h1 span{color:#4fc3f7}
.logo p{font-size:.85rem;color:#90caf9;margin-top:4px}
.card{background:#fff;border-radius:12px;padding:40px;width:400px;box-shadow:0 30px 80px rgba(0,0,0,.4)}
.badge{background:#f0f9ff;border:1px solid #bae6fd;border-radius:4px;padding:6px 10px;
       font-size:11px;color:#0369a1;margin-bottom:16px;text-align:center}
h2{font-size:1.1rem;color:#1e293b;margin-bottom:4px}
.sub{font-size:.8rem;color:#64748b;margin-bottom:20px}
label{display:block;font-size:12px;font-weight:600;color:#475569;margin-bottom:3px;margin-top:10px}
input{width:100%;padding:10px 14px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px}
input:focus{outline:none;border-color:#1a6b9a}
button{width:100%;padding:12px;background:#1a6b9a;color:#fff;border:none;border-radius:6px;
       font-size:15px;cursor:pointer;margin-top:16px;font-weight:600}
.error{color:#dc2626;font-size:12px;margin-top:8px;text-align:center}
.links{display:flex;justify-content:space-between;margin-top:14px;font-size:11px}
.links a{color:#1a6b9a;text-decoration:none}
.footer{margin-top:18px;font-size:10px;color:#94a3b8;text-align:center}
</style></head><body>
<div class="logo"><h1><span>Clarity</span>Med Health Systems</h1>
<p>Secure Patient &amp; Staff Portal</p></div>
<div class="card">
  <div class="badge">🔒 HIPAA Compliant — All access monitored and logged</div>
  <h2>Sign In</h2>
  <p class="sub">Use your ClarityMed credentials or Patient ID</p>
  <form method="POST" action="/login">
    <label>Email or Staff ID</label>
    <input type="text" name="username" placeholder="name@claritymed.com" autocomplete="off">
    <label>Password</label>
    <input type="password" name="password" placeholder="Password">
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <button type="submit">Sign In</button>
  </form>
  <div class="links">
    <a href="/forgot-password">Forgot password?</a>
    <a href="/ehr">EHR System</a>
    <a href="/admin">Staff Admin</a>
  </div>
  <div class="footer">ClarityMed Portal v3.1.4 &nbsp;|&nbsp;
    <a href="/api/v1/status">API</a> &nbsp;|&nbsp; <a href="/wiki">Staff Wiki</a>
  </div>
</div></body></html>"""

EHR = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>ClarityMed EHR — Clinical Workstation</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#1e1e2e;font-family:'Courier New',monospace;display:flex;
     justify-content:center;align-items:center;min-height:100vh;color:#cdd6f4}
.t{background:#181825;border:1px solid #313244;border-radius:8px;padding:32px;width:480px}
.h{color:#89b4fa;font-size:1rem;margin-bottom:4px}
.s{color:#6c7086;font-size:.75rem;margin-bottom:24px}
.p{color:#a6e3a1;margin-bottom:6px;font-size:.85rem}
input{background:#11111b;border:1px solid #313244;color:#cdd6f4;width:100%;
      padding:8px 12px;font-family:'Courier New',monospace;font-size:14px;
      border-radius:4px;margin-bottom:10px}
button{background:#89b4fa;color:#1e1e2e;border:none;padding:10px;width:100%;
       font-family:'Courier New',monospace;font-size:14px;cursor:pointer;font-weight:700}
.w{color:#f38ba8;font-size:.75rem;margin-top:14px;text-align:center}
.i{color:#6c7086;font-size:.7rem;margin-top:8px}
</style></head><body>
<div class="t">
  <div class="h">ClarityMed EHR System v8.4.2</div>
  <div class="s">Clinical Workstation — Authorized Personnel Only</div>
  <form method="POST" action="/ehr/login">
    <div class="p">login: </div>
    <input type="text" name="username" autocomplete="off">
    <div class="p">password: </div>
    <input type="password" name="password">
    <button type="submit">[AUTHENTICATE]</button>
  </form>
  <div class="w">⚠ Unauthorized access is a federal offense (HIPAA §164.306)</div>
  <div class="i">Host: claritymed-ehr-01.internal | Build: 20240115-prod</div>
</div></body></html>"""

ADMIN = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>ClarityMed — System Administration</title>
<style>
body{background:#111;font-family:'Segoe UI',sans-serif;display:flex;
     justify-content:center;align-items:center;min-height:100vh;color:#fff}
.c{background:#1e1e1e;border:1px solid #333;border-radius:8px;padding:36px;width:380px}
h2{color:#f59e0b;margin-bottom:6px}.s{color:#6b7280;font-size:.8rem;margin-bottom:20px}
input{width:100%;background:#2a2a2a;border:1px solid #444;color:#fff;
      padding:10px;border-radius:4px;font-size:14px;margin-bottom:10px}
button{width:100%;background:#f59e0b;color:#000;border:none;padding:10px;
       border-radius:4px;font-size:14px;cursor:pointer;font-weight:700}
.w{color:#ef4444;font-size:11px;margin-top:12px;text-align:center}
</style></head><body>
<div class="c">
  <h2>⚙ System Administration</h2>
  <p class="s">ClarityMed IT Operations Console</p>
  <form method="POST" action="/admin/auth">
    <input type="text" name="username" placeholder="Admin Username" autocomplete="off">
    <input type="password" name="password" placeholder="Password">
    <button type="submit">Login</button>
  </form>
  <p class="w">All admin actions are logged and audited</p>
</div></body></html>"""

WIKI_HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>ClarityMed Staff Wiki</title>
<style>
body{font-family:'Segoe UI',sans-serif;max-width:860px;margin:0 auto;padding:30px;color:#1e293b}
.hdr{border-bottom:3px solid #1a6b9a;padding-bottom:12px;margin-bottom:24px}
h1{color:#1a6b9a;font-size:1.4rem}.sub{color:#64748b;font-size:.85rem;margin-top:4px}
.sec{margin-bottom:28px}
h2{font-size:1rem;color:#334155;margin-bottom:10px;border-left:3px solid #1a6b9a;padding-left:8px}
ul{list-style:none;padding:0}
li{padding:7px 0;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;gap:8px}
li a{color:#1a6b9a;text-decoration:none;font-size:.9rem}
.r{font-size:10px;padding:2px 6px;border-radius:3px}
.red{background:#fee2e2;color:#dc2626}.yel{background:#fef3c7;color:#d97706}
.grn{background:#dcfce7;color:#16a34a}
</style></head><body>
<div class="hdr"><h1>ClarityMed Health Systems — Staff Wiki</h1>
<div class="sub">Internal knowledge base</div></div>
<div class="sec"><h2>IT & Infrastructure</h2><ul>
<li><a href="/wiki/vpn-setup">VPN Setup Guide</a> <span class="r grn">public</span></li>
<li><a href="/wiki/server-inventory">Server Inventory</a> <span class="r red">restricted</span></li>
<li><a href="/wiki/db-credentials">Database Credentials</a> <span class="r red">restricted</span></li>
<li><a href="/wiki/aws-keys">AWS Access Keys</a> <span class="r red">restricted</span></li>
<li><a href="/wiki/deployment-runbook">Deployment Runbook</a> <span class="r yel">internal</span></li>
</ul></div>
<div class="sec"><h2>Clinical Operations</h2><ul>
<li><a href="/wiki/ehr-access">EHR Access Procedures</a> <span class="r yel">internal</span></li>
<li><a href="/wiki/hipaa-policy">HIPAA Compliance Policy</a> <span class="r grn">public</span></li>
<li><a href="/wiki/incident-response">Incident Response Plan</a> <span class="r red">restricted</span></li>
</ul></div>
<div class="sec"><h2>HR & Onboarding</h2><ul>
<li><a href="/wiki/onboarding">Employee Onboarding Guide</a> <span class="r grn">public</span></li>
<li><a href="/wiki/directory">Staff Directory</a> <span class="r yel">internal</span></li>
</ul></div></body></html>"""

RESTRICTED = """<!DOCTYPE html><html><head><title>ClarityMed Wiki — Restricted</title>
<style>body{font-family:'Segoe UI',sans-serif;padding:60px;max-width:500px;margin:0 auto}
.b{background:#fff5f5;border:1px solid #fca5a5;border-radius:8px;padding:24px}
h2{color:#dc2626;margin-bottom:8px}p{color:#6b7280;font-size:.9rem;margin-bottom:16px}
input{width:100%;padding:8px;border:1px solid #e5e7eb;border-radius:4px;
      margin-bottom:10px;font-size:14px}
button{background:#dc2626;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer}
</style></head><body><div class="b">
<h2>🔒 Restricted Access</h2>
<p>This page requires elevated IT credentials. Contact helpdesk@claritymed.com</p>
<form method="POST">
  <input type="text" name="username" placeholder="IT Admin Username" autocomplete="off">
  <input type="password" name="password" placeholder="Password">
  <button type="submit">Authenticate</button>
</form></div></body></html>"""

# Routes
@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET"])
@app.route("/patient-portal", methods=["GET"])
def portal():
    log_event("http.page.visit", {"page": "patient-portal"})
    r = make_response(render_template_string(PORTAL, error=None))
    r.set_cookie("PHPSESSID", str(uuid.uuid4()).replace("-","")[:26], httponly=True)
    return r

@app.route("/login", methods=["POST"])
def login_post():
    u = request.form.get("username","")
    p = request.form.get("password","")
    log_event("http.login.attempt", {"page":"patient-portal","credentials":{"username":u,"password":p}})
    time.sleep(1.2)
    return render_template_string(PORTAL, error="Invalid credentials. Please try again."), 200

@app.route("/ehr", methods=["GET"])
@app.route("/ehr/", methods=["GET"])
def ehr():
    log_event("http.admin.probe", {"page":"ehr-login"})
    return render_template_string(EHR)

@app.route("/ehr/login", methods=["POST"])
def ehr_login():
    u = request.form.get("username","")
    p = request.form.get("password","")
    log_event("http.login.attempt", {"page":"ehr-system","credentials":{"username":u,"password":p}})
    time.sleep(1.5)
    return render_template_string(EHR), 200

@app.route("/admin", methods=["GET","POST"])
@app.route("/admin/", methods=["GET","POST"])
@app.route("/admin/auth", methods=["POST"])
def admin():
    log_event("http.admin.probe", {"page":"admin"})
    if request.method == "POST":
        log_event("http.login.attempt", {"page":"admin","credentials":{
            "username":request.form.get("username",""),
            "password":request.form.get("password","")}})
    return render_template_string(ADMIN)

@app.route("/phpmyadmin", methods=["GET","POST"])
@app.route("/phpmyadmin/", methods=["GET","POST"])
@app.route("/phpmyadmin/index.php", methods=["GET","POST"])
def phpmyadmin():
    log_event("http.admin.probe", {"page":"phpmyadmin"})
    if request.method == "POST":
        log_event("http.login.attempt", {"page":"phpmyadmin","credentials":{
            "username":request.form.get("pma_username",""),
            "password":request.form.get("pma_password","")}})
    return ('<html><body style="font-family:Arial;padding:40px">'
            '<h2>phpMyAdmin 5.2.1</h2>'
            '<form method="POST"><label>User: <input name="pma_username" value="root"></label><br><br>'
            '<label>Pass: <input type="password" name="pma_password"></label><br><br>'
            '<button>Go</button></form>'
            '<p style="color:#888;font-size:12px">MySQL 8.0.35 / claritymed-db-01</p>'
            '</body></html>')

@app.route("/wp-admin", methods=["GET","POST"])
@app.route("/wp-login.php", methods=["GET","POST"])
def wp_admin():
    log_event("http.admin.probe", {"page":"wp-admin"})
    if request.method == "POST":
        log_event("http.login.attempt", {"page":"wordpress","credentials":{
            "username":request.form.get("log",""),
            "password":request.form.get("pwd","")}})
    return render_template_string(ADMIN)

@app.route("/wiki")
def wiki():
    log_event("http.page.visit", {"page":"wiki"})
    return render_template_string(WIKI_HTML)

@app.route("/wiki/<page>", methods=["GET","POST"])
def wiki_page(page):
    RESTRICTED_PAGES = ["db-credentials","aws-keys","server-inventory","incident-response"]
    log_event("http.admin.probe", {"page":f"wiki/{page}"})
    if page in RESTRICTED_PAGES:
        if request.method == "POST":
            log_event("http.login.attempt", {"page":f"wiki/{page}","credentials":{
                "username":request.form.get("username",""),
                "password":request.form.get("password","")}})
        return render_template_string(RESTRICTED)
    return f"<html><body style='font-family:sans-serif;padding:30px'><h2>ClarityMed Wiki — {page.replace('-',' ').title()}</h2><p>Loading...</p></body></html>"

@app.route("/forgot-password")
def forgot():
    log_event("http.page.visit", {"page":"forgot-password"})
    return "<html><body style='font-family:sans-serif;padding:40px'><h3>Password Reset</h3><form method='POST'><input type='email' name='email' placeholder='ClarityMed email' style='padding:8px;width:280px'> <button style='padding:8px 16px;background:#1a6b9a;color:#fff;border:none'>Reset</button></form></body></html>"

@app.route("/api/v1/status")
def api_status():
    log_event("http.api.probe", {"endpoint":"/api/v1/status"})
    return jsonify({"status":"ok","version":"3.1.4","env":"production","host":"claritymed-app01","uptime":1728432})

@app.route("/api/v1/patients")
def api_patients():
    log_event("http.api.probe", {"endpoint":"/api/v1/patients"})
    return jsonify({"error":"Unauthorized","code":401}), 401

@app.route("/api/v1/health")
def api_health():
    log_event("http.api.probe", {"endpoint":"/api/v1/health"})
    return jsonify({"healthy":True,"checks":{"db":"ok","cache":"ok","ehr":"ok","billing":"ok"}})

@app.route("/.env")
def env_file():
    log_event("http.file.probe", {"file":"/.env"})
    return ("APP_ENV=production\nDB_HOST=claritymed-db-01.internal\nDB_PORT=3306\n"
            "DB_DATABASE=claritymed_production\nDB_USERNAME=claritymed_app\n"
            "DB_PASSWORD=ClarityDB_Pr0d_2024!\n"
            "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n"
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n"
            "REDIS_HOST=claritymed-cache-01.internal\nREDIS_PASSWORD=Redis_S3cr3t!\n"
            "JWT_SECRET=claritymed_jwt_s3cr3t_k3y_2024\n"), 200, {"Content-Type":"text/plain"}

@app.route("/.git/config")
def git_config():
    log_event("http.file.probe", {"file":"/.git/config"})
    return ("[core]\n\trepositoryformatversion = 0\n"
            "[remote \"origin\"]\n\turl = git@github.com:claritymed/patient-portal.git\n"), 200, {"Content-Type":"text/plain"}

@app.route("/config.php")
@app.route("/wp-config.php")
def wp_config():
    log_event("http.file.probe", {"file":request.path})
    return ("<?php\ndefine('DB_NAME','claritymed_production');\n"
            "define('DB_USER','claritymed_app');\ndefine('DB_PASSWORD','ClarityDB_Pr0d_2024!');\n"
            "define('DB_HOST','claritymed-db-01.internal');\n"), 200, {"Content-Type":"text/plain"}

@app.route("/server-status")
@app.route("/nginx_status")
def server_status():
    log_event("http.scan.probe", {"probe_path":request.path})
    return "Active connections: 31\nserver accepts handled requests\n4821 4821 52341\n", 200

@app.route("/<path:path>", methods=["GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS"])
def catch_all(path):
    log_event("http.scan.probe", {"probe_path":f"/{path}","body":request.get_data(as_text=True)[:512]})
    return "Not Found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
