# SentinelGrid

SentinelGrid is a cybersecurity analytics platform designed to capture, analyze, and visualize attacker behavior using honeypots, data pipelines, and machine learning based threat analysis. It provides real time monitoring, intelligent insights, and structured reporting to understand malicious activity.

## Project Overview

- **Honeypot Network:** Emulates SSH, HTTP, and IoT services to attract and capture attacker activity.
- **Data Pipelines:** Logs and processes attack data for ML analysis and frontend visualization.
- **ML & Threat Analysis:** Extracts features, performs clustering and anomaly detection to identify malicious attack patterns.
- **Visualization Dashboard:** Offers analytics, filtering, and session inspection views.

## Team Roles
- **Zach – Project Owner, Security Architect & Honeypot Lead**  
  Builds and maintains realistic honeypots, implements attack containment and sandboxing, and defines data for analysis.

- **Seth – Backend Systems Engineer & Technical Lead**  
  Coordinates APIs, async services, authentication, and system integration. Ensures smooth communication between all subsystems.

- **Raiden – Database & Data Engineering Lead**  
  Designs database schemas, SQL queries, and pipelines. Optimizes storage and retrieval of attack logs for ML and visualization.

- **Anup – Frontend & Visualization Engineer**  
  Develops the visual dashboard, implements live attack feeds, charts, and user friendly analytics views.

- **Yama – ML & Threat Analysis Engineer**  
  Designs feature extraction pipelines, implements clustering and anomaly detection models, behavioral analysis, heuristic labeling, and honeypot decision rules.

## File Structure
### File Structure 
```
SENTINELGRID/
│
├── documentation/
├── HoneyNet-Backend/
├── HoneyNet-Frontend/
├── machine-learning/
│
├── .gitignore
└──README.md

```

## Documentation
- `documentation/minutes.tex` : All Scrum and meeting minutes are updated and stored here. This file is updated on Overleaf throughout the semesters and tracks the team's Scrum activities such as sprint planning and reviews. 
You can view it here: [Project Meeting Minutes (PDF)](documentation/minutes.pdf).

- `local_testing.txt`: This is where you can find instructions for local testing on the Sentinel Grid Cowrie honeypot. 
