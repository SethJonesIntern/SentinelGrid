import json
from pathlib import Path
import pandas as pd

PROFILES= [
    "Brute Force Attack",
    "Credential Stuffing",
    "Interactive Attacker",
    "Recon Scanner",
    "Web Scanner",
    "Malware Downloader",
    "File Exfiltration",
    "FTP Abuse",
    "Email Abuse",
    "Database Recon",
    "Database Attack",
    "Redis Attack",
    "Automated Bot",
    "Low-Interaction SSH Probe",
]

#min confidence for low confidence
LOW_CONFIDENCE_THRESHOLD = 0.30
def capped(value, denominator=1.0, weight=1.0):
    if denominator<= 0:
        return 0.0
    return min(float(value)/denominator, 1.0) *weight

#confidence is calculated per session
# #confidence = sum(amounts earned) /sum(max_amounts applicable)
def add_score(scores, max_scores, reasons, profile, amount, max_amount, reason=None):
    max_scores[profile]+= max_amount
    if amount> 0:
        scores[profile]+= amount
        if reason:
            reasons[profile].append(reason)


def assign_profile(row):
    scores = {p: 0.0 for p in PROFILES if p != "Unknown"}
    max_scores = {p: 0.0 for p in scores}
    reasons = {p: [] for p in scores}

    login_fail= row.get("login_fail", 0)
    unique_users = row.get("unique_users", 0)
    unique_pass = row.get("unique_pass", 0)
    event_count= row.get("event_count", 0)
    cmd_count = row.get("cmd_count", 0)
    unique_cmds = row.get("unique_cmds", 0)

    # brute force attack 
    add_score(scores, max_scores, reasons, "Brute Force Attack",
        capped(login_fail, 20), 1.0, "Many failed logins")
    add_score(scores, max_scores, reasons, "Brute Force Attack",
        capped(unique_pass, 20), 1.0, "Many unique passwords")
    add_score(scores, max_scores, reasons, "Brute Force Attack",
        capped(row.get("fails_per_min", 0), 20), 1.0, "High failed-login rate")

    # credential stuffing
    add_score(scores, max_scores, reasons, "Credential Stuffing",
        capped(unique_users, 10), 1.0, "Many unique usernames")
    add_score(scores, max_scores, reasons, "Credential Stuffing",
        capped(unique_pass, 10), 1.0, "Many unique passwords")
    add_score(scores, max_scores, reasons, "Credential Stuffing",
        capped(login_fail, 20), 1.0, "Repeated failed logins")

    #interactive attacker 
    add_score(scores, max_scores, reasons, "Interactive Attacker",
        capped(cmd_count, 10), 1.0, "High command activity")
    add_score(scores, max_scores, reasons, "Interactive Attacker",
        capped(unique_cmds, 5), 1.0, "Multiple unique commands")
    add_score(scores, max_scores, reasons, "Interactive Attacker",
        capped(row.get("duration", 0), 300), 1.0, "Longer session duration")
    add_score(scores, max_scores, reasons, "Interactive Attacker",
        capped(row.get("login_success", 0)), 1.0, "Successful authentication")
    # Conditional: only applicable for anomalous interactive sessions
    if row.get("is_anomaly", False) and (cmd_count > 0 or row.get("login_success", 0) > 0):
        add_score(scores, max_scores, reasons, "Interactive Attacker",
            0.25, 0.25, "Anomalous interactive session")

    #recon scanner
    add_score(scores, max_scores, reasons, "Recon Scanner",
        capped(row.get("services_touched", 0), 4), 1.0, "Multiple services touched")
    add_score(scores, max_scores, reasons, "Recon Scanner",
        capped(event_count, 20), 1.0, "Elevated event count")
    if row.get("contains_recon_cmds", 0):
        add_score(scores, max_scores, reasons, "Recon Scanner", 1.0, 1.0, "Recon command observed")
    if row.get("contains_network_terms", 0):
        add_score(scores, max_scores, reasons, "Recon Scanner", 0.5, 0.5, "Network probing command observed")
    if row.get("contains_nav_cmds", 0):
        add_score(scores, max_scores, reasons, "Recon Scanner", 0.25, 0.25, "Filesystem navigation command observed")

    # web scanner 
    add_score(scores, max_scores, reasons, "Web Scanner",
        capped(row.get("http_events", 0), 10), 1.0, "HTTP activity")
    add_score(scores, max_scores, reasons, "Web Scanner",
        capped(row.get("http_page_visits", 0), 10), 1.0, "HTTP page visits")
    add_score(scores, max_scores, reasons, "Web Scanner",
        capped(row.get("http_login_attempts", 0), 10), 1.0, "HTTP login attempts")

    #malware downloader
    add_score(scores, max_scores, reasons, "Malware Downloader",
        capped(row.get("downloads", 0)), 1.0, "File download observed")
    add_score(scores, max_scores, reasons, "Malware Downloader",
        capped(row.get("download_ratio", 0)), 1.0, "Download-heavy session")
    if row.get("contains_install_cmds", 0):
        add_score(scores, max_scores, reasons, "Malware Downloader", 1.0, 1.0, "Install/download command observed")
    if row.get("contains_exec_terms", 0) and row.get("downloads", 0) > 0:
        add_score(scores, max_scores, reasons, "Malware Downloader", 0.5, 0.5, "Downloaded file may have been executed")

    # file xxfiltration
    add_score(scores, max_scores, reasons, "File Exfiltration",
        capped(row.get("uploads", 0)), 1.0, "File upload observed")
    add_score(scores, max_scores, reasons, "File Exfiltration",
        capped(row.get("upload_ratio", 0)), 1.0, "Upload-heavy session")
    add_score(scores, max_scores, reasons, "File Exfiltration",
        capped(row.get("file_transfer_ratio", 0), 0.5, 0.5), 0.5, "High file-transfer share")

    #ftp abuse 
    add_score(scores, max_scores, reasons, "FTP Abuse",
        capped(row.get("ftp_events", 0), 5), 1.0, "FTP activity")
    add_score(scores, max_scores, reasons, "FTP Abuse",
        capped(row.get("ftp_ratio", 0)), 1.0, "FTP-dominant session")
    add_score(scores, max_scores, reasons, "FTP Abuse",
        capped(row.get("ftp_connects", 0), 5), 1.0, "FTP connection attempts")
    if row.get("ftp_connects", 0) > 0 and row.get("ftp_disconnects", 0) > 0:
        churn = row.get("ftp_connects", 0) / max(row.get("ftp_disconnects", 1), 1)
        add_score(scores, max_scores, reasons, "FTP Abuse",
            min(churn / 5.0, 1.0) * 0.5, 0.5, "High FTP connection churn")

    #email abuse 
    add_score(scores, max_scores, reasons, "Email Abuse",
        capped(row.get("smtp_events", 0), 5), 1.0, "SMTP activity")
    add_score(scores, max_scores, reasons, "Email Abuse",
        capped(row.get("smtp_ratio", 0)), 1.0, "SMTP-dominant session")
    add_score(scores, max_scores, reasons, "Email Abuse",
        capped(row.get("smtp_connects", 0), 5), 1.0, "SMTP connection attempts")
    add_score(scores, max_scores, reasons, "Email Abuse",
        capped(row.get("smtp_ehlo_count", 0), 5), 1.0, "SMTP EHLO probing")

    # database recon 
    add_score(scores, max_scores, reasons, "Database Recon",
        capped(row.get("mysql_events", 0), 5), 1.0, "MySQL activity")

    #database attack 
    add_score(scores, max_scores, reasons, "Database Attack",
        capped(row.get("mysql_queries", 0), 10), 1.0, "MySQL queries")
    if row.get("is_anomaly", False) and row.get("mysql_queries", 0) > 0:
        add_score(scores, max_scores, reasons, "Database Attack", 0.5, 0.5, "Anomalous MySQL activity")

    # redis attack 
    add_score(scores, max_scores, reasons, "Redis Attack",
        capped(row.get("redis_events", 0), 5), 1.0, "Redis activity")
    add_score(scores, max_scores, reasons, "Redis Attack",
        capped(row.get("redis_commands", 0), 10), 1.0, "Redis commands")
    add_score(scores, max_scores, reasons, "Redis Attack",
        capped(row.get("redis_ratio", 0)), 1.0, "Redis-dominant session")
    if row.get("is_anomaly", False) and row.get("redis_commands", 0) > 0:
        add_score(scores, max_scores, reasons, "Redis Attack", 0.5, 0.5, "Anomalous Redis activity")

    #automated bot
    if event_count>= 10:
        add_score(scores, max_scores, reasons, "Automated Bot",
            capped(row.get("events_per_min", 0), 100), 1.0, "High event rate")
    if cmd_count >= 5:
        add_score(scores, max_scores, reasons, "Automated Bot",
            capped(row.get("cmds_per_min", 0), 20), 1.0, "High command rate")

    # low interaction ssh 
    if row.get("ssh_events", 0)> 0:
        add_score(scores, max_scores, reasons, "Low-Interaction SSH Probe",
            capped(row.get("ssh_ratio", 0)), 1.0, "SSH-dominant session")
        if row.get("login_success", 0) > 0 and cmd_count == 0:
            add_score(scores, max_scores, reasons, "Low-Interaction SSH Probe",
                0.75, 0.75, "Successful login without commands")
        if event_count<= 5 and cmd_count == 0:
            add_score(scores, max_scores, reasons, "Low-Interaction SSH Probe",
                0.5, 0.5, "Short low-activity session")
        if row.get("unique_event_types", 0)<= 4 and cmd_count == 0:
            add_score(scores, max_scores, reasons, "Low-Interaction SSH Probe",
                0.25, 0.25, "Few event types")

    #normalization confidence = score / session_max
    profile_scores= {p: round(scores[p] / max_scores[p], 3) if max_scores[p] > 0 else 0.0
        for p in scores}

    ranked= sorted(profile_scores.items(), key=lambda item: item[1], reverse=True)
    top_profile, top_confidence = ranked[0]
    top_reasons = reasons[top_profile][:3] if reasons[top_profile] else ["Low-confidence evidence"]

    return(
        top_profile,
        round(top_confidence, 3),
        {**profile_scores, "Unknown": round(1.0 - top_confidence, 3)},
        top_reasons,
    )


def main():
    input_path= Path("../data/outputs/csv/backend_logs_modeled.csv")
    csv_output_path = Path("../data/outputs/csv/backend_logs_labeled.csv")
    json_output_path = Path("../data/outputs/json/backend_logs_labeled.json")

    df= pd.read_csv(input_path)
    results= df.apply(
        lambda row: assign_profile(row),
        axis=1
    )

    df["profile"]= results.apply(lambda x: x[0])
    df["profile_confidence"] = results.apply(lambda x: x[1])
    df["profile_reasons"] = results.apply(lambda x: json.dumps(x[3]))
    df["profile_scores"] = results.apply(lambda x: json.dumps(x[2]))

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(csv_output_path, index=False)
    df.to_json(
        json_output_path,
        orient="records",
        indent=4,
        date_format="iso",
    )

    print("\nProfile Distribution")
    print(df["profile"].value_counts())
    print("\nAverage Confidence")
    print(df.groupby("profile")["profile_confidence"].mean())

if __name__ == "__main__":
    main()
