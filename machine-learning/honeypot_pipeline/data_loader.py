
#loads honeypot dataset and adds source column if there are multiple sourses
# useful when we have two or more honeypots 

import pandas as pd 
from pathlib import Path 
import json
import requests


#loads logs from the backend 
def load_backend_logs(api_url="http://localhost:8000/sessions?limit=5000") -> pd.DataFrame:
    response = requests.get(api_url)
    response.raise_for_status()
    data= response.json()

    print("\n" + "=" * 60)
    print("BACKEND DATA")
    print("=" * 60)
    print(f"Raw logs returned by API: {data['count']}")

    records= []

    for row in data["logs"]:
        event= row["raw_json"]
        payload= event.get("payload", {})

        record= {
            "timestamp": event.get("timestamp"),
            "src_ip": event.get("src_ip"),
            "session_id": event.get("session_id"),
            "sensor": event.get("sensor_id"),
            "eventid": event.get("event_type"),
        }

        record.update(payload)
        record["session_id"] = event.get("session_id")
        record["eventid"] = event.get("event_type")
        record["src_ip"] = event.get("src_ip")
        records.append(record)

    df= pd.DataFrame(records)
    df["source"] = "backend"
 
    return df


#load cowrie JSON honeypot logs into dataframe
def load_cowrie_json(path:str)-> pd.DataFrame:
    with open(path, "r") as f:
        raw_data= json.load(f)
    all_events= []
    for session in raw_data:
        for session_id, events in session.items():
            for event in events:
                geo= event.get("geolocation_data", {})
                event["geo_country"] = geo.get("country_name")
                event["geo_city"] = geo.get("city_name")
                event["geo_region"] = geo.get("region_name")
                event["geo_latitude"] = geo.get("latitude")
                event["geo_longitude"] = geo.get("longitude")
                event["geo_timezone"] = geo.get("timezone")

                location = geo.get("location", {})
                event["geo_loc_lat"] = location.get("lat")
                event["geo_loc_lon"] = location.get("lon")
                event.pop("geolocation_data", None)
                all_events.append(event)

    df= pd.DataFrame(all_events)
    df["source"]= "cowrie"

    return df

#load other honeypot datasets if we have
def load_other_honeypot(path: str, source_name: str) -> pd.DataFrame:
    df= pd.read_json(path)
    df["source"]= source_name

    return df

#save outputs of csv and json
def save_outputs(df: pd.DataFrame, output_dir: str, base_filename: str):
    output_dir= Path(output_dir)
    # create output folders
    csv_dir= output_dir/ "csv"
    json_dir= output_dir/ "json"
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    csv_path= csv_dir/ f"{base_filename}.csv"
    df.to_csv(csv_path, index=False)

    json_path= json_dir/ f"{base_filename}.json"
    df.to_json(json_path, orient="records",indent=4)

    print(f"CSV saved to: {csv_path}")
    print(f"JSON saved to: {json_path}")


#loads all data
def load_all_data(data_dir: str) -> dict:
    data_dir= Path(data_dir)
    datasets= {}
    json_files = data_dir.glob("*.json")

    for json_file in json_files:
        print(f"\nLoading: {json_file.name}")

        try:
            # load cowrie dataset
            df= load_cowrie_json(json_file)
            # filename without .json
            dataset_name= json_file.stem
            datasets[dataset_name]= df

        except Exception as e:
            print(f"Failed to load {json_file.name}")
            print(e)
    #if there are  another honeypot load example:
    #other_path= data_dir/ "other_honeypot.json"
    #if other_path.exists():
    #     other_df= load_other_honeypot(other_path, "other_honeypot")
    #     datasets["other_data"]= other_df

    if not datasets:
        raise ValueError("No honeypot datasets loaded")

    return datasets



if __name__ == "__main__":
    #log reading from backend 
    OUTPUT_DIR = "../data/processed/"
    df= load_backend_logs()

    print("\nLoaded backend logs")
    print(f"Rows: {len(df)}")

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head())

    save_outputs(df,OUTPUT_DIR,"backend_logs")


    # test pipeline
    #INPUT_DIR = "../data/Zenodo Honeypot Data/"
    #OUTPUT_DIR = "../data/processed/"
    #datasets = load_all_data(INPUT_DIR)

    #for dataset_name, df in datasets.items():
    #    print(f"\nLoaded dataset: {dataset_name}")
    #    print(f"Rows: {len(df)}")
    #
    #    print("\nColumns:")
    #    print(df.columns.tolist())
    #    print("\nFirst 5 rows:")
    #    print(df.head())

        # save outputs
    #    save_outputs(df,OUTPUT_DIR,dataset_name)