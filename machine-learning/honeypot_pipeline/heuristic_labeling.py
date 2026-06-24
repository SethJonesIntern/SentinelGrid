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
    "Automated Bot",
    "Multi-Service Recon",
    "Low-Interaction SSH Probe",
    "Unknown",
]

PROFILE_MAX_SCORES= {
    "Brute Force Attack": 3.0,
    "Credential Stuffing": 3.0,
    "Interactive Attacker": 4.25,
    "Recon Scanner": 3.25,
    "Web Scanner": 3.0,
    "Malware Downloader": 3.0,
    "File Exfiltration": 2.5,
    "FTP Abuse": 2.0,
    "Email Abuse": 2.0,
    "Database Recon": 2.0,
    "Database Attack": 2.5,
    "Automated Bot": 2.0,
    "Multi-Service Recon": 2.0,
    "Low-Interaction SSH Probe": 2.5,
}

MIN_PROFILE_SCORE= 0.75
MIN_PROFILE_CONFIDENCE= 0.30
MIN_CONFIDENCE_MARGIN= 0.05


def capped(value, denominator=1.0, weight=1.0):
    if denominator<= 0:
        return 0.0
    return min(float(value)/denominator, 1.0) *weight


def add_score(scores, reasons, profile, amount, reason=None):
    if amount<= 0:
        return
    scores[profile] += amount
    if reason:
        reasons[profile].append(reason)


def assign_profile(row):
    scores= {profile: 0.0 for profile in PROFILE_MAX_SCORES}
    reasons= {profile: [] for profile in PROFILE_MAX_SCORES}

    login_fail = row.get("login_fail", 0)
    unique_users = row.get("unique_users", 0)
    unique_pass = row.get("unique_pass", 0)
    event_count = row.get("event_count", 0)
    cmd_count = row.get("cmd_count", 0)
    unique_cmds = row.get("unique_cmds", 0)

    add_score(scores,reasons,"Brute Force Attack",
        capped(login_fail, 20),"Many failed logins",)
    
    add_score(scores, reasons,"Brute Force Attack", 
        capped(unique_pass, 20),"Many unique passwords",)
    
    add_score(scores,reasons, "Brute Force Attack",
        capped(row.get("fails_per_min", 0), 20),"High failed-login rate",)

    add_score(scores, reasons, "Credential Stuffing",
        capped(unique_users, 10), "Many unique usernames",)
    
    add_score(scores,reasons,"Credential Stuffing",
        capped(unique_pass, 10),"Many unique passwords",)
    
    add_score(scores, reasons,"Credential Stuffing",
        capped(login_fail, 20), "Repeated failed logins",)

    add_score(scores, reasons,"Interactive Attacker",
        capped(cmd_count, 10),"High command activity",)
    
    add_score(scores,reasons, "Interactive Attacker",
        capped(unique_cmds, 5), "Multiple unique commands",)
    
    add_score(scores, reasons, "Interactive Attacker",
        capped(row.get("duration", 0), 300), "Longer session duration",)
    
    add_score(scores,reasons, "Interactive Attacker",
        capped(row.get("login_success", 0)), "Successful authentication",)
    

    if row.get("is_anomaly", False) and (cmd_count > 0 or row.get("login_success", 0)>0):
        add_score(scores, reasons, "Interactive Attacker",
            0.25, "Anomalous interactive session",)

    add_score(scores,reasons, "Recon Scanner",
        capped(row.get("services_touched", 0), 4), "Multiple services touched",)
    add_score(scores, reasons,"Recon Scanner",
        capped(event_count, 20),"Elevated event count",)
    
    if row.get("contains_recon_cmds", 0):
        add_score(scores, reasons, "Recon Scanner", 1.0, "Recon command observed")
    if row.get("contains_network_terms", 0):
        add_score(scores, reasons, "Recon Scanner", 0.5, "Network probing command observed")
    if row.get("contains_nav_cmds", 0):
        add_score(scores, reasons, "Recon Scanner", 0.25, "Filesystem navigation command observed")

    add_score(scores, reasons,"Web Scanner",
        capped(row.get("http_events", 0), 10), "HTTP activity",)
    
    add_score(scores, reasons,"Web Scanner",
        capped(row.get("http_page_visits", 0), 10),"HTTP page visits",)
    
    add_score(scores,reasons, "Web Scanner",
        capped(row.get("http_login_attempts", 0), 10),"HTTP login attempts",)

    add_score(scores, reasons, "Malware Downloader",
        capped(row.get("downloads", 0)),"File download observed",)
    
    add_score(scores, reasons, "Malware Downloader",
        capped(row.get("download_ratio", 0)), "Download-heavy session",)
    
    if row.get("contains_install_cmds", 0):
        add_score(scores, reasons, "Malware Downloader", 1.0, "Install/download command observed")
    if row.get("contains_exec_terms", 0) and row.get("downloads", 0) > 0:
        add_score(scores, reasons, "Malware Downloader", 0.5, "Downloaded file may have been executed")

    add_score(scores, reasons,"File Exfiltration",
        capped(row.get("uploads", 0)),"File upload observed",)
    
    add_score(scores, reasons,"File Exfiltration",
        capped(row.get("upload_ratio", 0)), "Upload-heavy session",)
    
    add_score(scores,reasons,"File Exfiltration",
        capped(row.get("file_transfer_ratio", 0), 0.5, 0.5),"High file-transfer share",  )

    add_score(scores,reasons,"FTP Abuse",
        capped(row.get("ftp_events", 0), 5),"FTP activity",)
    
    add_score(scores, reasons, "FTP Abuse",
        capped(row.get("ftp_ratio", 0)),"FTP-dominant session",)

    add_score(scores, reasons,"Email Abuse",
        capped(row.get("smtp_events", 0), 5),"SMTP activity",)
    
    add_score(scores,reasons, "Email Abuse",
        capped(row.get("smtp_ratio", 0)),"SMTP-dominant session",)

    add_score(scores, reasons,"Database Recon",
        capped(row.get("mysql_events", 0), 5),"MySQL activity",)
    
    add_score(scores, reasons, "Database Recon",
        capped(row.get("redis_events", 0), 5), "Redis activity",)

    add_score(scores, reasons, "Database Attack",
        capped(row.get("mysql_queries", 0), 10),"MySQL queries",)
    
    add_score(scores,reasons, "Database Attack",
        capped(row.get("redis_commands", 0), 10),"Redis commands",)
    
    if row.get("is_anomaly", False) and (row.get("mysql_queries", 0)>0 or row.get("redis_commands", 0) > 0):
        add_score(scores, reasons, "Database Attack", 0.5, "Anomalous database activity")

    if event_count>= 10:
        add_score(scores,reasons, "Automated Bot",
            capped(row.get("events_per_min", 0), 100), "High event rate",)
        
    if cmd_count>= 5:
        add_score(scores,reasons, "Automated Bot",
            capped(row.get("cmds_per_min", 0), 20),"High command rate",)

    add_score(scores, reasons,"Multi-Service Recon",
        capped(row.get("services_touched", 0), 4), "Multiple services touched",)
    
    add_score(scores, reasons, "Multi-Service Recon",
        capped(row.get("unique_event_types", 0), 10),"Many event types",)

    if row.get("ssh_events", 0) > 0:
        add_score(scores, reasons, "Low-Interaction SSH Probe",
            capped(row.get("ssh_ratio", 0)), "SSH-dominant session",)

    if row.get("login_success", 0) > 0 and cmd_count == 0:
        add_score(scores, reasons, "Low-Interaction SSH Probe",
            0.75, "Successful login without commands",)

    if event_count <= 5 and cmd_count == 0:
        add_score(scores, reasons, "Low-Interaction SSH Probe",
            0.5, "Short low-activity session",)

    if row.get("unique_event_types", 0) <= 4 and cmd_count == 0:
        add_score(scores, reasons, "Low-Interaction SSH Probe",
            0.25, "Few event types",)

    profile_scores={
        profile: round(scores[profile]/ PROFILE_MAX_SCORES[profile], 3)
        for profile in scores
    }

    ranked= sorted(profile_scores.items(), key=lambda item: item[1], reverse=True)
    top_profile, top_confidence = ranked[0]
    second_confidence = ranked[1][1] if len(ranked)> 1 else 0.0
    top_raw_score = scores[top_profile]

    if top_raw_score< MIN_PROFILE_SCORE or top_confidence < MIN_PROFILE_CONFIDENCE:
        return(
            "Unknown",
            round(top_confidence, 3),
            {**profile_scores, "Unknown": round(1.0- top_confidence, 3)},
            ["Low-confidence evidence"],
        )

    if top_confidence- second_confidence <MIN_CONFIDENCE_MARGIN:
        return(
            "Unknown",
            round(top_confidence, 3),
            {**profile_scores, "Unknown": round(1.0 - top_confidence, 3)},
            ["Ambiguous evidence between multiple profiles"],
        )

    return(
        top_profile,
        round(top_confidence, 3),
        {**profile_scores, "Unknown": round(1.0 - top_confidence, 3)},
        reasons[top_profile][:3],
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
