# SentinelGrid – Student Frontend

This is the React + TypeScript frontend for the SentinelGrid honeypot telemetry dashboard.

It connects to the FastAPI backend and displays:

- Student login (mock authentication)
- Dashboard with live event feed
- Sessions table grouped by session_id
- Filtering controls for session data

---

## Tech Stack

- React
- TypeScript
- Vite
- Docker (served via Nginx in production)

---

## Running Locally (Without Docker)

From inside `HoneyNet-Frontend`:

```bash
npm install
npm run dev
