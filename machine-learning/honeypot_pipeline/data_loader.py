#loads honeypot dataset and adds source column if there are multiple sourses
# useful when we have two or more honeypots 

import pandas as pd 
from pathlib import Path 

def load_cowrie(path:str)-> pd.DataFrame:
    df= pd.read_csv(path)
    df['source']= 'cowrie'
    return df

def load_other_honeypot(path: str, source_name: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['source'] = source_name
    return df

def load_all_data(data_dir: str) -> pd.DataFrame:
    data_dir= Path(data_dir)
    dfs= []
    cowrie_path = data_dir / "cowrie_features.csv"
    dfs.append(load_cowrie(cowrie_path))
    
    #if there are  another honeypot CSV
    #other_path = data_dir / "other_honeypot.csv"
    #dfs.append(load_other_honeypot(other_path, "other_honeypot"))
    combined_df= pd.concat(dfs, ignore_index=True)
    return combined_df
if __name__ == "__main__":
    # test
    df = load_all_data("../data/TESToutputs/")
    print(f"Loaded {len(df)} rows from honeypots")
    print(df.head())