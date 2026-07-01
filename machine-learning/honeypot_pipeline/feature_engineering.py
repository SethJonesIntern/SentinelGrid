#01_honeypot pipeline notebook transformed into script
import pandas as pd
import numpy as np
from collections import Counter
from typing import Dict, List, Tuple
from pathlib import Path

#core columns expected from the dataset 
CORECOLS= [
    "eventid",      #type of event (command input, login success, etc.)
    "timestamp",    #time the event occurred
    "session_id",      #unique session identifier
    "src_ip",       #attacker/source IP
    "dst_ip",       #destination IP (honeypot server)
    "dst_port",     #destination port used
    "protocol",     #network protocol
    "sensor",       #sensor that captured the event
    "uuid",         #uunique identifier for the event
    "message",      #raw log message
    "input",        #command entered by attacker
    "username",     #username attempted/used
    "password",     #password attempted
    "duration",     #session duration
    "ttylog",       #terminal log reference
    "size",         #file size (for file transfers)
    "shasum",       #file hash if malware was downloaded
    "duplicate",    #flag if event is duplicated
    "url",          #url accessed or downloaded
    "outfile",      #stored file name of downloaded file
    "filename",     #uploaded file name
    "destfile",     #uploaded file destination
]

#helpers
#returns existing column or a default filled series if missing
def ensure_col(df: pd.DataFrame, col: str, default=None) -> pd.Series:
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)

def first_nonnull(series: pd.Series):
    s= series.dropna()
    return s.iloc[0] if len(s) else None

def last_nonnull(series: pd.Series):
    s= series.dropna()
    return s.iloc[-1] if len(s) else None

#standardizes columns and creates helper flags
def normalize_events(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    #ensure all expected columns exist
    for col in CORECOLS:
        out[col]= ensure_col(out, col, default=None)
    out["timestamp"]= pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out["dst_port"]= pd.to_numeric(out["dst_port"], errors="coerce")
    out["duration"]= pd.to_numeric(out["duration"], errors="coerce")
    out["size"]= pd.to_numeric(out["size"], errors="coerce")

    if out["protocol"].isna().all():
        out["protocol"]= ensure_col(out, "system.transport", default=None)
    out["command"]= out["input"]
    
    #binary flags
    out["is_command_input"]= out["eventid"].astype(str).eq("cowrie.command.input").astype(int)
    out["is_command_failed"]= out["eventid"].astype(str).eq("cowrie.command.failed").astype(int)
    out["is_login_success"]= out["eventid"].astype(str).eq("cowrie.login.success").astype(int)
    out["is_login_failed"]= out["eventid"].astype(str).eq("cowrie.login.failed").astype(int)
    out["is_session_closed"]= out["eventid"].astype(str).eq("cowrie.session.closed").astype(int)
    out["is_log_closed"]= out["eventid"].astype(str).eq("cowrie.log.closed").astype(int)
    out["is_file_download"]= out["eventid"].astype(str).eq("cowrie.session.file_download").astype(int)
    out["is_file_upload"]= out["eventid"].astype(str).eq("cowrie.session.file_upload").astype(int)

    # service type flags
    out["is_ssh"] = out["eventid"].astype(str).str.startswith("cowrie.").astype(int)
    out["is_http"] = out["eventid"].astype(str).str.startswith("http.").astype(int)
    out["is_mysql"] = out["eventid"].astype(str).str.startswith("mysql.").astype(int)
    out["is_redis"] = out["eventid"].astype(str).str.startswith("redis.").astype(int)
    out["is_http_login_attempt"]= (out["eventid"].astype(str).eq("http.login.attempt")).astype(int)
    out["is_http_page_visit"] = (out["eventid"].astype(str).eq("http.page.visit")).astype(int)
    out["is_mysql_query"] = (out["eventid"].astype(str).eq("mysql.query")).astype(int)
    out["is_redis_command"] = (out["eventid"].astype(str).eq("redis.command")).astype(int)
    out["is_ftp"]= out["eventid"].astype(str).str.startswith("ftp.").astype(int)
    out["is_smtp"] = out["eventid"].astype(str).str.startswith("smtp.").astype(int)
    out["is_ftp_connect"] = (out["eventid"].astype(str).eq("ftp.session.connect")).astype(int)
    out["is_ftp_disconnect"] = (out["eventid"].astype(str).eq("ftp.session.disconnect")).astype(int)
    out["is_smtp_ehlo"] = (out["eventid"].astype(str).eq("smtp.ehlo")).astype(int)
    out["is_smtp_connect"] = (out["eventid"].astype(str).eq("smtp.session.connect")).astype(int)
    out["is_client_version"] = (out["eventid"].astype(str).eq("cowrie.client.version")).astype(int)
    out["is_client_kex"] = (out["eventid"].astype(str).eq("cowrie.client.kex")).astype(int)

    return out

#groups events by session id and computes durations
def compute_session_boundaries(events_df: pd.DataFrame) -> pd.DataFrame:
    sess_events= events_df.dropna(subset=["session_id"]).copy()
    session_times= (sess_events.groupby("session_id")["timestamp"].agg(session_start="min", session_end="max").reset_index())
    session_times["duration"]= (session_times["session_end"] - session_times["session_start"]).dt.total_seconds()
    session_times["duration"]= session_times["duration"].clip(lower=0)
    return session_times, sess_events

#aggregates all network, login, and command data to the session level
def aggregate_session_data(session_times: pd.DataFrame, sess_events: pd.DataFrame) -> pd.DataFrame:
    #network info
    session_net = sess_events.groupby("session_id").agg(
        src_ip=("src_ip", first_nonnull),
        dst_ip=("dst_ip", first_nonnull),
        dst_port=("dst_port", first_nonnull),
        protocol=("protocol", first_nonnull),
        user_first=("username", first_nonnull),
        sensor=("sensor", first_nonnull),
        uuid=("uuid", first_nonnull),
    ).reset_index()

    login_agg= sess_events.groupby("session_id").agg(
        login_success=("is_login_success", "sum"),
        login_fail=("is_login_failed", "sum"),
        unique_users=("username", pd.Series.nunique),
        unique_pass=("password", pd.Series.nunique),
    ).reset_index()

    event_agg= sess_events.groupby("session_id").agg(
        event_count=("eventid", "count"),
        unique_event_types=("eventid", pd.Series.nunique),

        ssh_events=("is_ssh", "sum"),
        http_events=("is_http", "sum"),
        mysql_events=("is_mysql", "sum"),
        redis_events=("is_redis", "sum"),

        http_login_attempts=("is_http_login_attempt", "sum"),
        http_page_visits=("is_http_page_visit", "sum"),

        mysql_queries=("is_mysql_query", "sum"),
        redis_commands=("is_redis_command", "sum"),
        downloads=("is_file_download", "sum"),
        uploads=("is_file_upload", "sum"),
        ftp_events=("is_ftp", "sum"),
        smtp_events=("is_smtp", "sum"),
        ftp_connects=("is_ftp_connect", "sum"),
        ftp_disconnects=("is_ftp_disconnect", "sum"),
        smtp_ehlo_count=("is_smtp_ehlo", "sum"),
        smtp_connects=("is_smtp_connect", "sum"),
    ).reset_index()
    

    #comands

    cmd_df = sess_events[sess_events["eventid"].astype(str).str.contains(
        "command|query",case=False,na=False)].copy()
    cmd_agg= cmd_df.groupby("session_id").agg(
        cmd_count=("command", "count"),
        unique_cmds=("command", pd.Series.nunique),
        first_cmd=("command", first_nonnull),
        last_cmd=("command", last_nonnull),
    ).reset_index()

    #failed cmds
    failed_cmd_df= sess_events[sess_events["eventid"].astype(str).eq("cowrie.command.failed")& sess_events["command"].notna()].copy()
    failed_cmd_agg= failed_cmd_df.groupby("session_id").agg(
        cmd_failed_count=("command", "count"),
        unique_failed_cmds=("command", pd.Series.nunique),
        first_failed_cmd=("command", first_nonnull),
        last_failed_cmd=("command", last_nonnull),
    ).reset_index()

    #take last known value per session for honeypot count cols 
    honeypot_count_cols= [
        "ssh_honeypot_count", "http_honeypot_count", "mysql_honeypot_count",
        "redis_honeypot_count", "ftp_honeypot_count", "smtp_honeypot_count",
    ]
    available_count_cols= [c for c in honeypot_count_cols if c in sess_events.columns]
    if available_count_cols:
        count_agg= sess_events.groupby("session_id")[available_count_cols].last().reset_index()
    else:
        count_agg= None

    session_df=(
        session_times
        .merge(session_net, on="session_id", how="left")
        .merge(login_agg, on="session_id", how="left")
        .merge(cmd_agg, on="session_id", how="left")
        .merge(failed_cmd_agg, on="session_id", how="left")
        .merge(event_agg, on="session_id", how="left")
    )
    if count_agg is not None:
        session_df= session_df.merge(count_agg, on="session_id", how="left")
        for c in available_count_cols:
            session_df[c] = session_df[c].fillna(0).astype(int)
    
    #fill nas with 0
    count_cols= ["login_success", "login_fail", "unique_users", "unique_pass", "cmd_count", "unique_cmds", "cmd_failed_count", "unique_failed_cmds"]
    for c in count_cols:
        if c in session_df.columns:
            session_df[c]= session_df[c].fillna(0).astype(int)
            
    return session_df

#calculates shanon entropy for pass string
def password_metrics(s: str) -> Dict[str, float]:
    if not isinstance(s, str) or not str(s).strip():
        return {"entropy_per_char": 0.0, "entropy_total": 0.0, "normalized_entropy": 0.0, "length": 0.0, "unique_chars": 0.0, "total_strength": 0.0}

    s= str(s).strip()
    counts= Counter(s)
    probs= np.array(list(counts.values()), dtype=float)/ len(s)

    entropy_per_char= float(-(probs* np.log2(probs)).sum())
    length= float(len(s))
    unique_chars= float(len(counts))
    entropy_total= float(entropy_per_char* length)
    max_entropy= np.log2(unique_chars) if unique_chars> 1 else 0.0
    normalized_entropy= float(entropy_per_char/ max_entropy) if max_entropy> 0 else 0.0
    total_strength= float(entropy_total+ unique_chars+ 0.5* length)
    
    return{
        "entropy_per_char": entropy_per_char, "entropy_total": entropy_total, 
        "normalized_entropy": normalized_entropy, "length": length, 
        "unique_chars": unique_chars, "total_strength": total_strength
    }

def add_password_entropy(session_df: pd.DataFrame, sess_events: pd.DataFrame) -> pd.DataFrame:
    pw_by_session= sess_events.dropna(subset=["password"]).groupby("session_id")["password"].apply(list).to_dict()
    
    def session_pass_metrics(session: str):
        pws= pw_by_session.get(session, [])
        if not pws: return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        metrics= [password_metrics(pw) for pw in pws if pd.notna(pw)]
        if not metrics: return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        return(
            float(np.mean([m["entropy_per_char"] for m in metrics])),
            float(np.mean([m["entropy_total"] for m in metrics])),
            float(np.mean([m["normalized_entropy"] for m in metrics])),
            float(np.mean([m["length"] for m in metrics])),
            float(np.mean([m["unique_chars"] for m in metrics])),
            float(np.mean([m["total_strength"] for m in metrics]))
        )

    pw_stats= session_df["session_id"].apply(session_pass_metrics)
    session_df["pw_entropy_per_char"]= [t[0] for t in pw_stats]
    session_df["pw_entropy_total"]= [t[1] for t in pw_stats]
    session_df["pw_normalized_entropy"]= [t[2] for t in pw_stats]
    session_df["pw_length_mean"]= [t[3] for t in pw_stats]
    session_df["pw_unique_chars_mean"]= [t[4] for t in pw_stats]
    session_df["pw_total_strength"]= [t[5] for t in pw_stats]
    
    return session_df

#create rates and command flags
def add_behavioral_features(session_df: pd.DataFrame, sess_events: pd.DataFrame) -> pd.DataFrame:
    session_df["cmds_per_min"]= session_df["cmd_count"]/(session_df["duration"]/ 60.0 + 1e-9)
    session_df["fails_per_min"] = session_df["login_fail"]/ (session_df["duration"]/60.0+1e-9)
    session_df["cmd_failed_per_min"]= session_df["cmd_failed_count"]/ (session_df["duration"]/ 60.0+ 1e-9)
    session_df["cmd_failed_ratio"]= session_df["cmd_failed_count"]/(session_df["cmd_count"]+ 1e-9)

    session_df["has_successful_login"]= (session_df["login_success"]> 0).astype(int)
    session_df["has_any_commands"]= (session_df["cmd_count"]> 0).astype(int)
    session_df["has_failed_commands"]= (session_df["cmd_failed_count"]> 0).astype(int)
    session_df["is_local_src"]= session_df["src_ip"].isin(["127.0.0.1", "::1"]).astype(int)

    # service ratios
    session_df["ssh_ratio"] = (session_df["ssh_events"] /(session_df["event_count"] + 1e-9))
    session_df["http_ratio"] = (session_df["http_events"] /(session_df["event_count"] + 1e-9))
    session_df["mysql_ratio"]= (session_df["mysql_events"]/(session_df["event_count"] + 1e-9))
    session_df["redis_ratio"]= (session_df["redis_events"] /(session_df["event_count"] + 1e-9))
    session_df["ftp_ratio"] = (session_df["ftp_events"] /(session_df["event_count"] + 1e-9))
    session_df["smtp_ratio"] = (session_df["smtp_events"]/(session_df["event_count"] + 1e-9))
    session_df["download_ratio"] = (session_df["downloads"]/(session_df["event_count"] + 1e-9))
    session_df["upload_ratio"] = (session_df["uploads"]/(session_df["event_count"] + 1e-9))
    session_df["file_transfer_ratio"] = (
        (session_df["downloads"] + session_df["uploads"]) /
        (session_df["event_count"] + 1e-9)
    )
    duration_mins = (
        session_df["duration"]
        .clip(lower=1)
        / 60
    )
    session_df["events_per_min"] = (
        session_df["event_count"] /
        duration_mins
    )
    session_df["services_touched"] = (
    (session_df["ssh_events"] > 0).astype(int)
    + (session_df["http_events"] > 0).astype(int)
    + (session_df["ftp_events"] > 0).astype(int)
    + (session_df["smtp_events"] > 0).astype(int)
    + (session_df["mysql_events"] > 0).astype(int)
    + (session_df["redis_events"] > 0).astype(int))


    # protocol flags
    session_df["is_ssh_protocol"]= (
        session_df["protocol"].astype(str)
        .str.contains("ssh", case=False, na=False) .astype(int))
    
    session_df["is_http_protocol"]= (
        session_df["protocol"].astype(str)
        .str.contains("http", case=False, na=False) .astype(int))

    session_df["is_ftp_protocol"]= (
        session_df["protocol"] .astype(str)
        .str.contains("ftp", case=False, na=False).astype(int))

    session_df["is_smtp_protocol"]= (
        session_df["protocol"].astype(str)
        .str.contains("smtp", case=False, na=False).astype(int))

    session_df["is_mysql_protocol"] = (
        session_df["protocol"].astype(str)
        .str.contains("mysql", case=False, na=False).astype(int))

    session_df["is_redis_protocol"] = (
        session_df["protocol"].astype(str)
        .str.contains("redis", case=False, na=False).astype(int))

    session_df["has_http_activity"] = (
    session_df["http_events"] > 0 ).astype(int)
    session_df["has_ftp_activity"] = (session_df["ftp_events"] > 0).astype(int)
    session_df["has_smtp_activity"] = (session_df["smtp_events"] > 0).astype(int)
    session_df["has_mysql_activity"] = (session_df["mysql_events"] > 0).astype(int)
    session_df["has_redis_activity"] = (session_df["redis_events"] > 0).astype(int)

    def determine_service(row):
        counts = {
        "ssh": row["ssh_events"],
        "http": row["http_events"],
        "ftp": row["ftp_events"],
        "smtp": row["smtp_events"],
        "mysql": row["mysql_events"],
        "redis": row["redis_events"],
    }
        return max(counts, key=counts.get)

    session_df["primary_service"] = session_df.apply(
        determine_service,
        axis=1
    )
    
    cmd_df= sess_events[sess_events["eventid"].astype(str).eq("cowrie.command.input")].copy()
    cmd_df["command_text"]= cmd_df["command"].combine_first(cmd_df["input"])
    cmds_per_session= cmd_df.dropna(subset=["command_text"]).groupby("session_id")["command_text"].apply(list).to_dict()


    def session_cmd_flags(commands: List[str]) -> Dict[str, int]:
        if not commands:
            return {k: 0 for k in ["contains_recon_cmds", "contains_install_cmds", "contains_nav_cmds", "contains_exit_cmd", "contains_persist_terms", "contains_exec_terms", "contains_kill_terms", "contains_network_terms"]}
        
        joined= ";".join(str(c).lower() for c in commands)
        return {
            "contains_recon_cmds": int(any(t in joined for t in ["ls", "pwd", "whoami", "uname", "id", "ifconfig"])),
            "contains_install_cmds": int(any(t in joined for t in ["wget", "curl", "apt", "yum", "pip", "scp"])),
            "contains_nav_cmds": int(any(t in joined for t in ["cd", "mkdir", "rm", "mv", "cp", "touch"])),
            "contains_exit_cmd": int(any(t in joined for t in ["exit", "logout", "quit"])),
            "contains_persist_terms": int(any(t in joined for t in ["crontab", "systemctl", "nohup"])),
            "contains_exec_terms": int(any(t in joined for t in ["./", "sh", "bash", "python"])),
            "contains_kill_terms": int(any(t in joined for t in ["kill", "killall", "pkill"])),
            "contains_network_terms": int(any(t in joined for t in ["ssh", "telnet", "nc", "nmap", "ping"])),
        }

    cmd_flags= session_df["session_id"].apply(lambda s: session_cmd_flags(cmds_per_session.get(s, [])))
    cmd_flags_df= pd.DataFrame(list(cmd_flags))
    session_df= pd.concat([session_df, cmd_flags_df], axis=1)
    return session_df

def extract_ml_features(session_df: pd.DataFrame) -> pd.DataFrame:
    feature_cols=[
        "duration", "cmd_count", "unique_cmds", "cmd_failed_count", "unique_failed_cmds",
        "cmds_per_min", "cmd_failed_per_min", "cmd_failed_ratio", "login_success",
        "login_fail", "fails_per_min", "unique_users", "unique_pass",
        "pw_entropy_per_char", "pw_entropy_total", "pw_normalized_entropy",
        "pw_length_mean", "pw_unique_chars_mean", "pw_total_strength",
        "has_successful_login", "has_any_commands", "has_failed_commands", "is_local_src",
        "contains_recon_cmds", "contains_install_cmds", "contains_nav_cmds", "contains_exit_cmd",
        "contains_persist_terms", "contains_exec_terms", "contains_kill_terms", "contains_network_terms",
        "event_count","unique_event_types","services_touched","events_per_min",
        "ssh_events","http_events", "mysql_events", "redis_events", "http_login_attempts", "http_page_visits",
        "mysql_queries", "redis_commands", "downloads", "uploads", "ftp_events", "smtp_events",
        "ssh_ratio", "http_ratio", "mysql_ratio", "redis_ratio",
        "ftp_ratio", "smtp_ratio", "download_ratio", "upload_ratio", "file_transfer_ratio",
        "is_ssh_protocol","is_http_protocol", "is_ftp_protocol",
        "is_smtp_protocol", "is_mysql_protocol", "is_redis_protocol",
    ]
    
    # include GeoIP features if added
    geo_cols= [col for col in session_df.columns if col.startswith('geo_')]
    feature_cols.extend(geo_cols)
    # include honeypot count cols as pass-through metadata (not ML features)
    count_cols = [c for c in session_df.columns if c.endswith('_honeypot_count')]
    valid_cols= ["session_id", "src_ip", "session_start", "session_end"]+[c for c in feature_cols if c in session_df.columns]+count_cols
    
    features_df= session_df[valid_cols].copy()
    features_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    features_df.fillna(0, inplace=True)
    return features_df

#feature engineering process pipeline
def process_pipeline(input_csv_path: str, output_dir: str):
    input_path= Path(input_csv_path)
    #extracts filename
    dataset_name = input_path.stem 
    print(f"Processing Dataset: {dataset_name}")
    print(f"Loading data from {input_path}...")
    events_df= pd.read_csv(input_path, low_memory=False)
    
    if events_df.empty:
        print(f"Skipping {dataset_name}: File is empty")
        return

    events_df= normalize_events(events_df)
    #print(events_df["protocol"].value_counts(dropna=False))
    print("\nService Counts")
    print("SSH Events:", events_df["is_ssh"].sum())
    print("HTTP Events:", events_df["is_http"].sum())
    print("FTP Events:", events_df["is_ftp"].sum())
    print("SMTP Events:", events_df["is_smtp"].sum())
    print("MySQL Events:", events_df["is_mysql"].sum())
    print("Redis Events:", events_df["is_redis"].sum())

    session_times, sess_events= compute_session_boundaries(events_df)
    session_df= aggregate_session_data(session_times, sess_events)
    session_df= add_password_entropy(session_df, sess_events)
    session_df = add_behavioral_features(session_df, sess_events)
    features_df= extract_ml_features(session_df)
    
    out_path= Path(output_dir)
    csv_dir= out_path/"csv"
    json_dir= out_path/"json"
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    events_csv= csv_dir/ f"{dataset_name}_normalized_events.csv"
    sessions_csv= csv_dir/ f"{dataset_name}_aggregated_sessions.csv"
    features_csv= csv_dir/ f"{dataset_name}_ml_features.csv"
    events_json= json_dir/f"{dataset_name}_normalized_events.json"
    sessions_json= json_dir/ f"{dataset_name}_aggregated_sessions.json"
    features_json= json_dir/ f"{dataset_name}_ml_features.json"

    events_df.to_csv(events_csv, index=False)
    session_df.to_csv(sessions_csv, index=False)
    features_df.to_csv(features_csv, index=False)
    events_df.to_json(events_json, orient="records", indent=4, date_format="iso")
    session_df.to_json(sessions_json, orient="records", indent=4, date_format="iso")
    features_df.to_json(features_json, orient="records", indent=4, date_format="iso")

    print(f"\nSaved {dataset_name} files:")
    print(f"CSV files saved to: {csv_dir}")
    print(f"JSON files saved to: {json_dir}")



if __name__ == "__main__":
    INPUT_DIR = Path("../data/processed/csv/") 
    OUTPUT_DIR = Path("../data/features/")
    
    if not INPUT_DIR.exists():
        print(f"Error: Input directory '{INPUT_DIR}' does not exist")
    else:
        #find all csvs
        csv_files= list(INPUT_DIR.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in '{INPUT_DIR}'.")
        else:
            print(f"Found {len(csv_files)} CSV file(s) to process.")
            #loop through and process each file
            for csv_file in csv_files:
                #process just backends
                if csv_file.stem != "backend_logs":
                    continue
                process_pipeline(str(csv_file), str(OUTPUT_DIR))
            print("\nAll datasets processed successfully!")
