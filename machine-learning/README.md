# Sentinel Grid — Machine Learning

This folder contains the machine learning and threat analysis module for Sentinel Grid. It ingests raw honeypot logs from the backend, runs a multi-stage analysis pipeline, and produces labeled attack sessions with a recommended honeypot deployment plan that is returned to the backend.

---

## Components
### `honeypot_pipeline/`
The core production pipeline. Each script represents one stage and they are orchestrated in order by `run_pipeline.py` (locally) or `backend_run_pipeline.py` (backend integrated).

| Script | Purpose |
|---|---|
| `data_loader.py` | Loads and normalizes raw honeypot JSON logs from the backend |
| `feature_engineering.py` | Extracts session-level features (timing, command patterns, auth behavior, etc.) |
| `behavioral_analysis.py` | Performs clustering and anomaly detection on extracted features |
| `heuristic_labeling.py` | Assigns attacker behavior profiles with a confidence score |
| `decision_rules.py` | Applies deployment logic to recommend honeypot distribution |
| `run_pipeline.py` | Runs all 5 stages sequentially this is used for local development/testing |
| `backend_run_pipeline.py` | Same pipeline but called by the backend and returns JSON deployment redistribution plan |
| `test_backend.py` | Integration tests for the pipeline |

#### Attacker Behavior Profiles
The heuristic labeling stage classifies sessions into one of 14 profiles:

`Brute Force Attack`, `Credential Stuffing`, `Interactive Attacker`, `Recon Scanner`, `Web Scanner`, `Malware Downloader`, `File Exfiltration`, `FTP Abuse`, `Email Abuse`, `Database Recon`, `Database Attack`, `Redis Attack`, `Automated Bot`, `Low-Interaction SSH Probe`

**How confidence is calculated:**  
Each session is scored against every profile independently. For a given profile, individual behavioral signals (ex: many failed logins, high command count, file download observed) each contribute a capped, weighted amount to that profile's score. The final confidence is:

$$\text{confidence} = \frac{\sum \text{signals earned}}{\sum \text{max signals applicable}}$$

This gives a value between 0 and 1 per profile. The profile with the highest score is assigned as the session's label.

**Why confidence might be low (below 0.30):**
- **Too few events** — very short or minimal sessions don't produce enough signals to score strongly against any profile
- **Ambiguous behavior** — the attacker's activity matches multiple profiles equally (ex: both recon and brute force signals present but neither dominant)
- **Missing features** — the session lacks key fields (ex: no command data, no HTTP events) that certain profiles rely on heavily
- **Passive/silent sessions** — connections that opened but produced little or no activity

**Effect on honeypot redistribution:**  
Low-confidence sessions (below `0.30`) are excluded from the deployment calculation entirely. Only trusted, high confidence sessions are used to determine where attack demand is highest. This prevents ambiguous or noisy data from skewing the honeypot distribution. If *all* sessions in the current window fall below the threshold, the system returns a `"hold"` action and makes no redistribution recommendation until more reliable data is available.

#### Honeypot Deployment Output
`decision_rules.py` uses the most recent 100 labeled sessions to recommend how to distribute a fixed pool of 12 honeypots across 6 service types (SSH, HTTP, MySQL, Redis, FTP, SMTP). Each service is guaranteed a baseline of 1 honeypot, with the remaining 6 flexible slots allocated proportionally based on normalized attack demand. Raw session counts are divided by how many honeypots of that type were already deployed when those sessions were captured. This normalization prevents services with more honeypots from appearing artificially more popular.

If fewer than 100 sessions are available, or all sessions are low-confidence, the system returns `"action": "hold"` and does not recommend any changes.

---

### `notebooks/`
Jupyter notebooks used for exploratory data analysis, model prototyping, and validation. These were used to develop and validate the pipeline logic before our actual pipeline was built.

| Notebook | Description |
|---|---|
| `01_honeypot_pipeline.ipynb` | End-to-end pipeline walkthrough on Cowrie honeypot data |
| `02_behavior_model.ipynb` | Behavior clustering and anomaly detection exploration |
| `cic-ids_analysis.ipynb` | Analysis of the CIC-IDS-2017 dataset |
| `cic-ids_classification.ipynb` | Classification experiments on CIC-IDS-2017 |
| `zenodo_analysis.ipynb` | Analysis of the Zenodo honeypot dataset |

Install notebook dependencies:
```bash
cd notebooks/
python -m venv .venv && source .venv/bin/activate  
pip install -r requirements.txt
```

---

### `data/`
Contains all datasets, raw logs, and pipeline outputs. See [`data/README.md`](data/README.md) for full details.

| Folder | Contents |
|---|---|
| `Zenodo Honeypot Data/` | Public honeypot dataset used for training and validation |
| `cyberlab_features/` & `cyberlab_outputs/` | Feature/output data from the CyberLab environment |
| `features/` & `outputs/` | Production feature CSVs and labeled JSON outputs |
| `processed/` | Intermediate processed data |

---

## Running the Pipeline Locally

```bash
cd honeypot_pipeline/
python run_pipeline.py
```

This runs all 5 stages in order and prints timing for each step. Output files are written to `data/outputs/`.

**Requirements:** Install dependencies from `honeypot_pipeline/requirements.txt`

---

## File Structure
```
machine-learning/
│
├── honeypot_pipeline/
│   ├── data_loader.py
│   ├── feature_engineering.py
│   ├── behavioral_analysis.py
│   ├── heuristic_labeling.py
│   ├── decision_rules.py
│   ├── run_pipeline.py
│   ├── backend_run_pipeline.py
│   └── test_backend.py
│
├── notebooks/
│   ├── 01_honeypot_pipeline.ipynb
│   ├── 02_behavior_model.ipynb
│   ├── cic-ids_analysis.ipynb
│   ├── cic-ids_classification.ipynb
│   ├── zenodo_analysis.ipynb
│   └── requirements.txt
│
└── data/
    ├── Zenodo Honeypot Data/
    ├── cyberlab_features/
    ├── cyberlab_outputs/
    ├── features/
    ├── outputs/
    ├── processed/
    └── README.md
```