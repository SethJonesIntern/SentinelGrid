import os
import json

# Hardcoded Cowrie log path for WSL
cowrie_log_path = "/home/zachary/cowrie/var/log/cowrie/cowrie.json"

if not os.path.exists(cowrie_log_path):
    print(f"Log file {cowrie_log_path} not found!")
    exit(1)

# Read and process Cowrie JSON logs
with open(cowrie_log_path, "r") as f:
    try:
        logs = [json.loads(line) for line in f if line.strip()]
    except json.JSONDecodeError as e:
        print(f"Error reading JSON: {e}")
        exit(1)

# Example: extract only timestamp, source_ip, and event_type
processed_logs = []
for log in logs:
    processed_logs.append({
        "timestamp": log.get("timestamp"),
        "source_ip": log.get("src_ip", "unknown"),
        "event_type": log.get("eventid", "unknown")
    })

print(f"Processed {len(processed_logs)} log entries.")

# Optionally save processed logs
with open("processed_logs.json", "w") as out_file:
    json.dump(processed_logs, out_file, indent=2)