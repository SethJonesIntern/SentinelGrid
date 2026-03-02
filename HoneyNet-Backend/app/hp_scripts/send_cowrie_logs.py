# HoneyNet-Backend/scripts/send_cowrie_logs.py
import json
import requests
import time
from pathlib import Path

# Backend endpoint
API_URL = "http://127.0.0.1:8000/log"  # adjust if your backend is running elsewhere

# Cowrie log file
COWRIE_LOG = Path.home() / "cowrie/var/log/cowrie/cowrie.json"

def send_logs():
    if not COWRIE_LOG.exists():
        print(f"Log file {COWRIE_LOG} not found!")
        return

    total_logs = 0
    sent_logs = 0

    with open(COWRIE_LOG, "r") as f:
        for line in f:
            try:
                log_entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip invalid lines

            total_logs += 1

            # Prepare JSON to match backend /log schema
            payload = {
                "timestamp": log_entry.get("timestamp"),
                "source_ip": log_entry.get("src_ip", "unknown"),
                "event_type": log_entry.get("eventid", "unknown"),
                "data": log_entry
            }

            try:
                resp = requests.post(API_URL, json=payload)
                if resp.status_code == 200:
                    sent_logs += 1
                else:
                    print(f"Failed to send log: {resp.status_code} - {resp.text}")
            except requests.exceptions.RequestException as e:
                print(f"Error sending log: {e}")

            # Optional: delay so we don't spam our API
            time.sleep(0.05)

    print(f"Processed {total_logs} logs, successfully sent {sent_logs} logs.")

if __name__ == "__main__":
    send_logs()