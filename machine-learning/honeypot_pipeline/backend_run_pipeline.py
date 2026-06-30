import json
import subprocess
import sys
from pathlib import Path
from decision_rules import build_deployment_plan, load_labeled_sessions

SCRIPTS= [
    "data_loader.py",
    "feature_engineering.py",
    "behavioral_analysis.py",
    "heuristic_labeling.py",
    "decision_rules.py",
]
LABELED_PATH= Path("../data/outputs/json/backend_logs_labeled.json")

def main():
    for script in SCRIPTS:
        subprocess.run(
            ["python", script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    df= load_labeled_sessions(LABELED_PATH)
    plan= build_deployment_plan(df)
    print(json.dumps({"recommended_honeypot_distribution": plan["recommended_honeypot_distribution"]}, indent=4))

if __name__ == "__main__":
    main()
