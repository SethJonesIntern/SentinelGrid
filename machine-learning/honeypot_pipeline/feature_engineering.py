#convert colums to numeric, compute dervived features and fill missing vals
from collections import Counter
from typing import Dict, Tuple
import numpy as np
import pandas as pd

#weighted behavioral system
RISK_WEIGHTS= {
    "install_cmds": 2.0,
    "recon_cmds": 1.0,
    "failed_cmd_rate": 1.0,
    "commands_per_min": 0.25,
    "night_activity": 0.5,
}



def password_metrics(s:str) ->Dict[str,float]:
    #handles missing values or nons trings
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return {
            "entropy_per_char": 0.0,
            "entropy_total": 0.0,
            "normalized_entropy": 0.0,
            "length": 0.0,
            "unique_chars": 0.0,
            "total_strength": 0.0,
        }

    s=str(s).strip()
    if len(s) == 0:
        return {
            "entropy_per_char": 0.0,
            "entropy_total": 0.0,
            "normalized_entropy": 0.0,
            "length": 0.0,
            "unique_chars": 0.0,
            "total_strength": 0.0,
        }
    
    #counts how many times each character appears
    #stored in dict - ex: "aab1"-> {'a':2, 'b':1, '1':1}
    counts= Counter(s)

    #compute probability by dividing count by total length of string
    #ex: [2,1,1]/4 -> [0.5, 0.25, 0.25]
    probs= np.array(list(counts.values()), dtype=float)/ len(s)
    #apply shannon entropy formula 
    #measures how unpredictable the character distribution is
    entropy_per_char= float(-(probs*np.log2(probs)).sum())
    length= float(len(s))
    unique_chars= float(len(counts))
    entropy_total= float(entropy_per_char * length)
    max_entropy= np.log2(unique_chars) if unique_chars>1 else 0.0
    normalized_entropy= float(entropy_per_char/max_entropy) if max_entropy>0 else 0.0
    total_strength= float(entropy_total+unique_chars+0.5 * length)
    #low values -> low entropy 
    #high values -> high entropy 
    return{
        "entropy_per_char": entropy_per_char,
        "entropy_total": entropy_total,
        "normalized_entropy": normalized_entropy,
        "length": length,
        "unique_chars": unique_chars,
        "total_strength": total_strength,
    }

#compute pass metrics for  session level 
def compute_session_password_features(session_df: pd.DataFrame,events_df: pd.DataFrame) -> pd.DataFrame:
    session_df= session_df.copy()
    if "session" not in session_df.columns:
        raise ValueError("session_df must contain 'session' column")

    if "session" not in events_df.columns or "password" not in events_df.columns:
        raise ValueError("events_df must contain 'session' and 'password'")

    # group passwords by session
    pw_by_session =(events_df.dropna(subset=["password"]).groupby("session")["password"].apply(list).to_dict())

    def session_pass_metrics(session: str) -> Tuple[float, float, float, float, float, float]:
        pws= pw_by_session.get(session, [])
        if not pws:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        metrics = [password_metrics(pw) for pw in pws if pd.notna(pw)]
        if not metrics:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        metrics_df = pd.DataFrame(metrics)

        return (
            float(metrics_df["entropy_per_char"].mean()),
            float(metrics_df["entropy_total"].mean()),
            float(metrics_df["normalized_entropy"].mean()),
            float(metrics_df["length"].mean()),
            float(metrics_df["unique_chars"].mean()),
            float(metrics_df["total_strength"].mean()),
        )

    pw_stats= session_df["session"].apply(session_pass_metrics)
    session_df["pw_entropy_per_char"] = [t[0] for t in pw_stats]
    session_df["pw_entropy_total"] = [t[1] for t in pw_stats]
    session_df["pw_normalized_entropy"] = [t[2] for t in pw_stats]
    session_df["pw_length_mean"] = [t[3] for t in pw_stats]
    session_df["pw_unique_chars_mean"] = [t[4] for t in pw_stats]
    session_df["pw_total_strength"] = [t[5] for t in pw_stats]
    session_df["password_count"] = session_df["session"].map( 
        lambda s: len(pw_by_session.get(s, [])))

    return session_df

def classify_risk(score):
    if score< 2:
        return "low"
    elif score< 5:
        return "medium"
    return "high"


def preprocess_features(df: pd.DataFrame) ->pd.DataFrame:
    df= df.copy()
    numeric_cols= [
        "duration",
        "reported_session_duration",
        "cmd_count",
        "unique_cmds",
        "cmd_failed_count",
        "file_download_count",
        "file_upload_count"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col]= pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    #boolean indicators
    bool_cols=[
        "contains_recon_cmds",
        "contains_install_cmds",
        "contains_nav_cmds",
        "contains_exit_cmd"
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col]= (
                df[col]
                .fillna(False)
                .astype(str)
                .str.lower()
                .isin(["true", "1", "yes"])
            )

    df["failed_cmd_rate"] = df["cmd_failed_count"] / df["cmd_count"].replace(0, 1)
    df["total_file_activity"] = df["file_download_count"] + df["file_upload_count"]
    df["cmd_diversity"]= (
        df["unique_cmds"]/
        df["cmd_count"].replace(0, 1)
    )
    df["commands_per_min"]= (
        df["cmd_count"]/
        (df["duration"]/ 60).replace(0, 1)
    )
    df["failed_commands_per_min"]= (
        df["cmd_failed_count"]/
        (df["duration"]/ 60).replace(0, 1)
    )

    if "hour" in df.columns:
        df["is_night_activity"] = df["hour"].isin([0,1,2,3,4,5])
    else:
        df["is_night_activity"] = False

    df["session_risk_score"]= (
        df["contains_install_cmds"].astype(int)
            * RISK_WEIGHTS["install_cmds"]
        + df["contains_recon_cmds"].astype(int)
            * RISK_WEIGHTS["recon_cmds"]
        + df["failed_cmd_rate"]
            * RISK_WEIGHTS["failed_cmd_rate"]
        + df["commands_per_min"]
            * RISK_WEIGHTS["commands_per_min"]
        + df["is_night_activity"].astype(int)
            * RISK_WEIGHTS["night_activity"]
    )
    df["download_ratio"]= (
        df["file_download_count"]/
        df["cmd_count"].replace(0,1)
        )

    df["upload_ratio"]= (
        df["file_upload_count"]/
        df["cmd_count"].replace(0,1)
    )
    
    df["attacker_complexity_score"]= (
        df["cmd_diversity"] +
        df["pw_entropy_per_char"] +
        df["contains_install_cmds"].astype(int)
    )

    df["risk_level"] = df["session_risk_score"].apply(classify_risk)
    return df