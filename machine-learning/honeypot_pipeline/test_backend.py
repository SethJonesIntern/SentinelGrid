import requests
import pandas as pd
API_URL= "http://localhost:8000/sessions?limit=1000"

try:
    response= requests.get(API_URL)
    response.raise_for_status()
    data= response.json()

    print("=" * 60)
    print("BACKEND CONNECTION SUCCESS")
    print("=" * 60)

    print(f"Total logs returned: {data['count']}")
    if not data["logs"]:
        print("\nNo logs found.")
        exit()

    print("\nFirst raw event:")
    print(data["logs"][0]["raw_json"])

    records= []

    for row in data["logs"]:
        event = row["raw_json"]
        payload = event.get("payload", {})
        record = {
            "timestamp": event.get("timestamp"),
            "src_ip": event.get("src_ip"),
            "event_type": event.get("event_type"),
            "session_id": event.get("session_id"),
            "sensor_id": event.get("sensor_id"),
        }
        # flatten payload
        for key, value in payload.items():
            record[key] = value
        records.append(record)

    df= pd.DataFrame(records)

    print("\nColumns found:")
    print(df.columns.tolist())

    print("\nEvent Type Counts:")
    print(df["event_type"].value_counts())

    print("\nDataFrame Shape:")
    print(df.shape)

    print("\nFirst 5 rows:")
    print(df.head())

    print("\n" + "=" * 60)
    print("SESSION STATISTICS")
    print("=" * 60)

    #how many sessions
    unique_sessions = df["session_id"].nunique()
    print(f"\nUnique Sessions: {unique_sessions}")

    #cmds per session
    command_events = df[
        df["event_type"] == "cowrie.command.input"
    ]

    commands_per_session= (
        command_events.groupby("session_id")
        .size()
        .sort_values(ascending=False)
    )

    print("\nCommands Per Session:")
    print(commands_per_session)

    login_successes = len(
        df[df["event_type"] == "cowrie.login.success"]
    )

    print(f"\nTotal Login Successes: {login_successes}")
    login_failures = len(
        df[df["event_type"] == "cowrie.login.failed"]
    )

    print(f"Total Login Failures: {login_failures}")

    # Session summary table
    session_summary = pd.DataFrame({
        "commands": (
            df[df["event_type"] == "cowrie.command.input"]
            .groupby("session_id")
            .size()
        ),
        "login_successes": (
            df[df["event_type"] == "cowrie.login.success"]
            .groupby("session_id")
            .size()
        ),
        "login_failures": (
            df[df["event_type"] == "cowrie.login.failed"]
            .groupby("session_id")
            .size()
        )
    }).fillna(0)

    print("\nSession Summary:")
    print(session_summary)

except Exception as e:
    print("ERROR:")
    print(e)