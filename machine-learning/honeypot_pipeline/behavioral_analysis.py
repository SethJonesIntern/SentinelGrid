import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from pathlib import Path
from sklearn.ensemble import IsolationForest
import json
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA


sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (8, 5)
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*matmul.*")

#isolation forest for anomly detection 
def run_isolation_forest(df, X_scaled):
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )

    predictions= iso_forest.fit_predict(X_scaled)

    #higher= more normal
    anomaly_scores= iso_forest.decision_function(X_scaled)
    df["is_anomaly"]= predictions == -1
    df["anomaly_score"]= anomaly_scores
    anomaly_count= df["is_anomaly"].sum()
    print("anomaly percentage")
    print(
        df["is_anomaly"]
        .value_counts(normalize=True) * 100
    )

    print(f"Detected {anomaly_count} anomalies ({anomaly_count/len(df)*100:.2f}%)")
    return df, iso_forest


#kmeans for behavioral clustering
def run_kmeans_and_iso(input_csv_path: str, output_dir: str):
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
    exclude_cols = [
        'session',
        'session_id',
        'src_ip',
        'session_start',
        'session_end',
        'source',
        'attack_cluster',
        'pca1',
        'pca2',
        'is_anomaly',
        'anomaly_score'
    ]
    numeric_cols= [col for col in df.columns if col not in exclude_cols and df[col].dtype in ['float64', 'int64']]
    X_raw= df[numeric_cols].copy()

    # clean nans infinit and negatives 
    #prevents log1p crashing
    X_raw.replace([np.inf, -np.inf], np.nan, inplace=True)
    X_raw.fillna(0, inplace=True)
    X_raw = X_raw.clip(lower=0)
    
    model_features = X_raw.copy()
    constant_cols = model_features.columns[
        model_features.nunique() <= 1
    ]
    low_var_cols= model_features.columns[model_features.std() < 1e-6]
    cols_to_drop= constant_cols.union(low_var_cols)

    if len(cols_to_drop)> 0:
        print("\nRemoving constant/near-zero variance columns:")
        print(list(cols_to_drop))

    model_features = model_features.drop(
        columns=cols_to_drop
    )

    print("\nLargest feature values:")
    print(model_features.max().sort_values(ascending=False).head(20))

    print("\nColumns containing inf:")
    print(model_features.columns[np.isinf(model_features).any()])
    print("\nColumns containing NaN:")
    print(model_features.columns[model_features.isna().any()])

    #transformation and standardization
    #cap outliers at 99th percentile per column before log transform
    upper = model_features.quantile(0.99)
    model_features = model_features.clip(upper=upper, axis=1)

    X_log = np.log1p(model_features)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_log)
    X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
    X_scaled = np.clip(X_scaled, -5, 5)

    pca_model = PCA(n_components=0.95, svd_solver='full', random_state=42)
    X_reduced = pca_model.fit_transform(X_scaled)
    X_reduced = np.nan_to_num(X_reduced, nan=0.0, posinf=0.0, neginf=0.0)

    print(
        f"\nFeature reduction: "
        f"{X_scaled.shape[1]} -> "
        f"{X_reduced.shape[1]}"
    )
        
    # find optimal k with silhouette score
    sil_scores= []
    max_k = min(6, len(df) - 1)
    k_range = range(2, max_k + 1)
    for k in k_range:
        km= KMeans(n_clusters=k, random_state= 42, n_init=10)
        labels= km.fit_predict(X_reduced)
        score= silhouette_score(X_reduced, labels)
        sil_scores.append(score)
        
    best_k= k_range[np.argmax(sil_scores)]
    print(f"Best K found: {best_k} (Score: {max(sil_scores):.4f})")

    #fit kmeans
    kmeans_final= KMeans(n_clusters= best_k, random_state=42, n_init=10)
    df["attack_cluster"]= kmeans_final.fit_predict(X_reduced)
    cluster_profiles = (
        df.groupby("attack_cluster")[model_features.columns]
        .mean()
    )

    print("\nCluster Profiles:")
    print(cluster_profiles.round(2))
    # pca dimensionality reduction
    viz_pca = PCA(n_components=2, svd_solver='full', random_state=42)
    X_pca = viz_pca.fit_transform(X_scaled)
    df["pca1"]= X_pca[:, 0]
    df["pca2"]= X_pca[:, 1]

    #isolation forest
    df, iso_model= run_isolation_forest(df, X_reduced)

    #top contributing features for anomalies
    scaled_df = pd.DataFrame(
        X_scaled,
        columns= model_features.columns
    )

    feature_means= X_raw.mean()

    anomaly_explanations= []

    for idx in df[df["is_anomaly"]].index:
        feature_scores= (
            scaled_df.iloc[idx]
            .abs()
            .sort_values(ascending=False)
            .head(3)
        )

        reasons= []
        for feature in feature_scores.index:
            z_score= scaled_df.loc[idx, feature]
            reasons.append({
                "feature": feature,
                "direction": (
                    "high"
                    if z_score > 0
                    else "low"
                ),
                "z_score": round(abs(z_score), 2),
                "value": round(
                    float(X_raw.loc[idx, feature]),
                    2
                ),
                "average": round(
                    float(feature_means[feature]),
                    2
                )
            })

        anomaly_explanations.append({
            "row_index": int(idx),
            "anomaly_score": round(
                float(df.loc[idx, "anomaly_score"]),
                4
            ),
            "attack_cluster": int(
                df.loc[idx, "attack_cluster"]
            ),
            "reasons": reasons
        })
        
    #outputs
    out_path= Path(output_dir)
    csv_dir= out_path/"csv"
    json_dir= out_path/"json"
    plot_dir= out_path/"plots"
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)
    cluster_profiles.to_csv(
        csv_dir / f"{dataset_name}_cluster_profiles.csv"
    )


    
    #kmeans clusters
    plt.figure(figsize= (8, 6))
    sns.scatterplot(data=df, x="pca1", y="pca2", hue="attack_cluster", palette="tab10", s=15, alpha=0.8)
    plt.title(f"Attacker Behavior Clusters (PCA): {dataset_name}")
    plt.legend(title="Cluster", bbox_to_anchor=(1.05, 1), loc= 'upper left')
    plt.savefig(plot_dir/ f"{dataset_name}_kmeans_pca.png", bbox_inches='tight')
    plt.close()
    
    #pca anomaly plot
    plt.figure(figsize=(8, 6))
    sns.scatterplot(
        data=df[~df["is_anomaly"]],
        x="pca1",
        y="pca2",
        color="blue",
        s=15,
        alpha=0.5,
        label="Normal"
    )
    sns.scatterplot(
        data=df[df["is_anomaly"]],
        x="pca1",
        y="pca2",
        color="red",
        s=40,
        label="Anomaly"
    )
    plt.title(f"Isolation Forest Anomalies (PCA): {dataset_name}")
    plt.savefig(
        plot_dir/ f"{dataset_name}_isolation_forest_pca.png",
        bbox_inches="tight"
    )
    plt.close()

    #anomaly score histogram 
    plt.figure(figsize=(8, 5))
    sns.histplot(
        data=df,
        x="anomaly_score",
        bins=40,
        kde=True
    )
    plt.title(f"Anomaly Score Distribution: {dataset_name}")
    plt.savefig(
        plot_dir/f"{dataset_name}_anomaly_scores.png",
        bbox_inches="tight"
    )
    plt.close()

    output_csv= csv_dir/f"{dataset_name}_modeled.csv"
    df.to_csv(output_csv, index=False)

    anomaly_csv= csv_dir / f"{dataset_name}_anomalies.csv"
    df[df["is_anomaly"]].to_csv(
        anomaly_csv,
        index=False
    )
    #detailed anomaly explanations
    json_path = (
        json_dir /
        f"{dataset_name}_anomaly_explanations.json"
    )

    with open(json_path, "w") as f:
        json.dump(
            anomaly_explanations,
            f,
            indent=4
        )
    
    print("\nReached summary section")

    #summaries
    print("\nCluster counts:")
    print(df["attack_cluster"].value_counts().sort_index().to_string())
    print("\nCluster vs Anomaly Summary:")
    print(
        pd.crosstab(
            df["attack_cluster"],
            df["is_anomaly"]
        )
    )

if __name__ == "__main__":
    INPUT_DIR= Path("../data/features/csv/") 
    OUTPUT_DIR= Path("../data/outputs/")
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
                run_kmeans_and_iso(str(csv_file), str(OUTPUT_DIR))
            print("\nKMeans modeling and isolation forest complete")
