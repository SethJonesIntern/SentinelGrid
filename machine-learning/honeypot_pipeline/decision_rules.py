import json
from pathlib import Path
import pandas as pd

INPUT_PATH= Path("../data/outputs/json/backend_logs_labeled.json")
OUTPUT_PATH= Path("../data/outputs/json/honeypot_deployment.json")

MIN_SESSIONS = 100
SESSION_WINDOW = 100
MIN_CONFIDENCE = 0.30

#limits
TOTAL_HONEYPOTS = 12
# guaranteed 1 minimum of each type
BASELINE_PER_SERVICE = 1  
#6 baseline+6 flexible to adjust
FLEXIBLE_SLOTS= TOTAL_HONEYPOTS- 6        

#map each service to the backend provided count column in the log data
#backend stamps how many honeypots of each type were active when the
# session was captured so normalization uses the same window as the data 
SERVICE_COUNT_COLUMNS= {
    "ssh_honeypot": "ssh_honeypot_count",
    "http_honeypot":"http_honeypot_count",
    "mysql_honeypot": "mysql_honeypot_count",
    "redis_honeypot":"redis_honeypot_count",
    "ftp_honeypot":"ftp_honeypot_count",
    "smtp_honeypot": "smtp_honeypot_count",
}

PROFILE_TO_HONEYPOT={
    #ssh
    "Brute Force Attack": "ssh_honeypot",
    "Credential Stuffing": "ssh_honeypot",
    "Low-Interaction SSH Probe": "ssh_honeypot",
    "Interactive Attacker": "ssh_honeypot",
    "Recon Scanner": "ssh_honeypot",
    "Malware Downloader": "ssh_honeypot",
    "File Exfiltration": "ssh_honeypot",
    "Automated Bot": "ssh_honeypot",
    #http
    "Web Scanner": "http_honeypot",
    #ftp
    "FTP Abuse": "ftp_honeypot",
    #smtp
    "Email Abuse": "smtp_honeypot",
    #sql
    "Database Recon": "mysql_honeypot",
    "Database Attack": "mysql_honeypot",
    #redis 
    "Redis Attack": "redis_honeypot",
}

HONEYPOT_SERVICES= [
    "ssh_honeypot",
    "http_honeypot",
    "mysql_honeypot",
    "redis_honeypot",
    "ftp_honeypot",
    "smtp_honeypot",
]

def load_labeled_sessions(input_path: Path)-> pd.DataFrame:
    df= pd.read_json(input_path)
    if "session_start" in df.columns:
        df["session_start"]= pd.to_datetime(df["session_start"], errors="coerce", utc=True)
    return df

#derive perservice honeypot counts from  session 
#takes the mean of the backend-provided *honeypotcount columns 
def extract_current_counts(selected_df: pd.DataFrame) -> dict:
    counts= {}
    for service, col in SERVICE_COUNT_COLUMNS.items():
        if col in selected_df.columns:
            counts[service]= max(round(selected_df[col].mean()), 1)
        else:
            counts[service] = 1
    return counts

#divide raw session counts by currently deployed honeypot count per service
def normalize_session_counts(raw_counts: dict, current_counts: dict) -> dict:
    return{
        service: raw_counts[service]/ max(current_counts.get(service, 1), 1)
        for service in HONEYPOT_SERVICES
    }

#distributes the 6 other honeypots porportionally
def allocate_flexible_slots(normalized_demand: dict) -> dict:
    total_demand = sum(normalized_demand.values())
    if total_demand== 0:
        base= FLEXIBLE_SLOTS//len(HONEYPOT_SERVICES)
        remainder = FLEXIBLE_SLOTS % len(HONEYPOT_SERVICES)
        floors= {s: base for s in HONEYPOT_SERVICES}
        for s in list(HONEYPOT_SERVICES)[:remainder]:
            floors[s]+= 1
        return floors
    raw= {
        service: (normalized_demand[service]/total_demand)* FLEXIBLE_SLOTS
        for service in HONEYPOT_SERVICES
    }
    floors = {s: int(v) for s, v in raw.items()}
    remainders = {s: raw[s] - floors[s] for s in HONEYPOT_SERVICES}
    leftover = FLEXIBLE_SLOTS - sum(floors.values())
    for s in sorted(remainders, key=remainders.get, reverse=True)[:leftover]:
        floors[s]+= 1
    return floors

#takes the most recent 100 sessions
def select_latest_sessions(df: pd.DataFrame, session_limit: int = SESSION_WINDOW)-> pd.DataFrame:
    if "session_start" not in df.columns or df["session_start"].isna().all():
        return df.tail(session_limit).copy()
    return(df.sort_values("session_start").tail(session_limit).copy())

#keeps sessions with more than set onfidence so low conf doent affect reccomndations
def confidence_filtered_sessions(df: pd.DataFrame)-> pd.DataFrame:
    if "profile_confidence" not in df.columns:
        return df.copy()
    return df[df["profile_confidence"]>=MIN_CONFIDENCE].copy()

#returns deployment plan based on most recent 100 sess and current deployed honeypot counts
def build_deployment_plan(df: pd.DataFrame, session_limit: int = SESSION_WINDOW) -> dict:
    selected_df= select_latest_sessions(df, session_limit)
    trusted_df= confidence_filtered_sessions(selected_df)
    trusted_df = trusted_df[trusted_df["profile"].isin(PROFILE_TO_HONEYPOT)].copy()
    current_counts = extract_current_counts(selected_df)
    empty_counts = {service: 0 for service in HONEYPOT_SERVICES}
    empty_recommended = {service: 0.0 for service in HONEYPOT_SERVICES}

    if len(selected_df)< MIN_SESSIONS:
        return{
            "mode": "recommendation",
            "action": "hold",
            "window_type": "latest_sessions",
            "session_limit": session_limit,
            "total_available_sessions": int(len(df)),
            "selected_sessions": int(len(selected_df)),
            "trusted_sessions": int(len(trusted_df)),
            "current_honeypot_counts": current_counts,
            "raw_session_counts": empty_counts,
            "normalized_session_counts": empty_counts,
            "recommended_honeypot_distribution": empty_recommended,
            "total_recommended": sum(empty_recommended.values()),
            "reasons":[
                f"Only {len(selected_df)} sessions selected; need at least {MIN_SESSIONS} before scaling."
            ],
        }

    if trusted_df.empty:
        return{
            "mode": "recommendation",
            "action": "hold",
            "window_type": "latest_sessions",
            "session_limit": session_limit,
            "total_available_sessions": int(len(df)),
            "selected_sessions": int(len(selected_df)),
            "trusted_sessions": 0,
            "current_honeypot_counts": current_counts,
            "raw_session_counts": empty_counts,
            "normalized_session_counts": empty_counts,
            "recommended_honeypot_distribution": empty_recommended,
            "total_recommended": sum(empty_recommended.values()),
            "reasons": [
                f"No sessions met the minimum confidence threshold of {MIN_CONFIDENCE}."
            ],
        }

    #raw session counts per service
    profile_counts= trusted_df["profile"].value_counts()
    raw_counts = {service: 0 for service in HONEYPOT_SERVICES}
    for profile, count in profile_counts.items():
        service = PROFILE_TO_HONEYPOT.get(profile)
        if service:
            raw_counts[service] += int(count)

    total_mapped= sum(raw_counts.values())

    #normalize by mean honeypot count 
    normalized = normalize_session_counts(raw_counts, current_counts)
    flexible = allocate_flexible_slots(normalized)
    recommended_counts= {
        service: BASELINE_PER_SERVICE+flexible[service]
        for service in HONEYPOT_SERVICES
    }

    recommended_distribution = {
        service: round(raw_counts[service] / total_mapped, 3) if total_mapped > 0 else 0.0
        for service in HONEYPOT_SERVICES
    }

    assert sum(recommended_counts.values()) == TOTAL_HONEYPOTS
    total_norm= sum(normalized.values())
    reasons = []
    for service in HONEYPOT_SERVICES:
        share = normalized[service]/ total_norm if total_norm > 0 else 0.0
        if share > 0:
            reasons.append(
                f"{service}: {raw_counts[service]} sessions "
                f"/ {current_counts[service]} current honeypot = "
                f"{normalized[service]:.2f} normalized demand ->"
                f"{recommended_counts[service]} honeypots"
            )

    return{
        "version": 1,
        "mode": "recommendation",
        "window_type": "latest_sessions",
        "session_limit": session_limit,
        "total_available_sessions": int(len(df)),
        "selected_sessions": int(len(selected_df)),
        "trusted_sessions": int(len(trusted_df)),
        "mapped_sessions": total_mapped,
        "policy": {
            "total_honeypots": TOTAL_HONEYPOTS,
            "baseline_per_service": BASELINE_PER_SERVICE,
            "flexible_slots": FLEXIBLE_SLOTS,
            "min_sessions": MIN_SESSIONS,
            "session_window": SESSION_WINDOW,
            "min_confidence": MIN_CONFIDENCE,
        },
        "current_honeypot_counts": current_counts,
        "recommended_honeypot_counts": recommended_counts,
        "recommended_honeypot_distribution": recommended_distribution,
        "total_recommended": TOTAL_HONEYPOTS,
        "reasons": reasons,
    }

def save_plan(plan: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(plan, f, indent=4)

def main():
    df= load_labeled_sessions(INPUT_PATH)
    plan= build_deployment_plan(df)
    save_plan(plan, OUTPUT_PATH)

    print("\nDeployment Recommendation")
    print(json.dumps(plan, indent=4))
    print(f"\nSaved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
