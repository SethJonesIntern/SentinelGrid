import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA


sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (8, 5)

def run_kmeans_model(input_csv_path: str, output_dir: str):
    input_path= Path(input_csv_path)
    dataset_name= input_path.stem.replace("_ml_features", "")
    
    print(f"Running KMeans Modeling on: {dataset_name}")
    
    #loads data
    print("Loading ML features...")
    df= pd.read_csv(input_path, low_memory=False)
    if df.empty or len(df)< 5:
        print(f"Skipping {dataset_name}: Not enough data")
        return

    # grabs all numeric columns while ignoring
    exclude_cols= ['session', 'session_id', 'src_ip', 'session_start', 'session_end', 'source']
    numeric_cols= [col for col in df.columns if col not in exclude_cols and df[col].dtype in ['float64', 'int64']]
    X_raw= df[numeric_cols].copy()

    # clean nans infinit and negatives 
    #prevents log1p crashing
    X_raw.replace([np.inf, -np.inf], np.nan, inplace=True)
    X_raw.fillna(0, inplace=True)
    X_raw = X_raw.clip(lower=0)
    
    #transformation and standardization
    X_log = np.log1p(X_raw)
    scaler = StandardScaler()
    X_scaled= scaler.fit_transform(X_log)
    
    # find optimal k with silhouette score
    sil_scores= []
    k_range= range(2, 10)
    for k in k_range:
        km= KMeans(n_clusters=k, random_state= 42, n_init=10)
        labels= km.fit_predict(X_scaled)
        score= silhouette_score(X_scaled, labels)
        sil_scores.append(score)
        
    best_k= k_range[np.argmax(sil_scores)]
    print(f"Best K found: {best_k} (Score: {max(sil_scores):.4f})")

    #fit kmeans
    kmeans_final= KMeans(n_clusters= best_k, random_state=42, n_init=10)
    df["attack_cluster"]= kmeans_final.fit_predict(X_scaled)
    # pca dimensionality reduction
    pca= PCA(n_components=2, random_state=42)
    X_pca= pca.fit_transform(X_scaled)
    df["pca1"]= X_pca[:, 0]
    df["pca2"]= X_pca[:, 1]

    #outputs
    out_path= Path(output_dir)
    csv_dir= out_path/"csv"
    plot_dir= out_path/"plots"
    csv_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    plt.figure()
    plt.plot(list(k_range), sil_scores, marker= "o", color='b')
    plt.xlabel("Number of Clusters (k)")
    plt.ylabel("Silhouette Score")
    plt.title(f"Silhouette Score vs K: {dataset_name}")
    plt.savefig(plot_dir/ f"{dataset_name}_silhouette_scores.png", bbox_inches= 'tight')
    plt.close()

    plt.figure(figsize= (8, 6))
    sns.scatterplot(data=df, x="pca1", y="pca2", hue="attack_cluster", palette="tab10", s=15, alpha=0.8)
    plt.title(f"Attacker Behavior Clusters (PCA): {dataset_name}")
    plt.legend(title="Cluster", bbox_to_anchor=(1.05, 1), loc= 'upper left')
    plt.savefig(plot_dir/ f"{dataset_name}_kmeans_pca.png", bbox_inches='tight')
    plt.close()

    output_csv = csv_dir/f"{dataset_name}_kmeans_clusters.csv"
    df.to_csv(output_csv, index=False)
    
    print("\nCluster counts:")
    print(df["attack_cluster"].value_counts().sort_index().to_string())
    print(f"\nSaved modeled dataset and plots to {out_path}/")

if __name__ == "__main__":
    INPUT_DIR= Path("../data/features/csv/") 
    OUTPUT_DIR= Path("../data/models/")
    if not INPUT_DIR.exists():
        print(f"Error: Directory '{INPUT_DIR}' does not exist")
    else:
        #usee ml_features files
        csv_files= list(INPUT_DIR.glob("*_ml_features.csv"))
        if not csv_files:
            print(f"No ML feature files found in '{INPUT_DIR}'")
        else:
            print(f"Found {len(csv_files)} dataset(s) for modeling")
            for csv_file in csv_files:
                run_kmeans_model(str(csv_file), str(OUTPUT_DIR))
            print("\nKMeans modeling complete")