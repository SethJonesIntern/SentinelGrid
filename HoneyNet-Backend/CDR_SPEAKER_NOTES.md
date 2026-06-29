# HoneyNet Backend — CDR Speaker Script (3 Slides)

> This is the **backend portion** of the full-project CDR. Three slides:
> Backend Technology Decisions, API, Testing. Notes below are what to *say*.
> Aim ~1.5–2 min per slide. "If asked" blocks are Q&A ammo.

---

## 0 — One-line handoff (say before slide 1)

"That's the architecture — now I'll cover the backend: the service that ingests
attack events from our honeypot sensors, normalizes them, and stores them for the
dashboard. Three things: the technology decisions, the API, and how we tested it."

---

## Slide 1 — Backend Technology Decisions

**Headline to land:** every piece of the stack was chosen to solve a specific
problem — validation, flexible storage, or reproducible deployment.

- **FastAPI (Python web framework)** — picked for two reasons: it validates
  incoming requests automatically against a declared schema, and it auto-generates
  live API docs at `/docs` that the frontend team developed against as a contract.
  No hand-written validation, no separate API spec to maintain.
- **Pydantic (validation)** — we declare the event shape once (`HoneypotEvent`),
  and bad data is rejected before it reaches our code. This is what makes the API
  reliable: malformed events can't get into the database.
- **PostgreSQL + JSONB** — this is the key data decision. We use a relational DB
  for reliability, but store each event in a **JSONB** column instead of one column
  per field. Why: our sensors send different fields, and JSONB lets us absorb that
  variation without a schema migration every time — while still being queryable,
  unlike plain text.
- **SQLAlchemy ORM** — database-agnostic access layer. It's why we can run
  PostgreSQL in production but swap to in-memory SQLite for tests with zero changes
  to our route code. Also gives us parameterized queries — no SQL injection surface.
- **Docker / Docker Compose** — the whole stack (API + frontend) comes up with one
  command, so deployment is reproducible on any machine.

- **Design highlight to call out if you have time — stateless session grouping:**
  "One decision I'm proud of: when a sensor doesn't supply a session ID, we *derive*
  one by hashing `src_ip + event_type + the hour`. Same attacker, same hour →
  same ID, computed independently with no server-side state or lookup table. It
  groups a sustained attack together for free."

- *If asked "why not Flask/Django?":* FastAPI gives built-in validation, async
  support, and the auto-generated docs out of the box — less boilerplate for an
  API-only service.
- *If asked "why one table / JSONB instead of normalized columns?":* Sensor schemas
  vary and will grow; JSONB avoids a migration per sensor type while staying
  indexable. We also keep the full original payload, so no forensic detail is lost.

---

## Slide 2 — API

**Headline to land:** a small, focused surface — three endpoints — with the
contract enforced automatically.

- **`POST /log` — ingest one event.**
  - Body is validated against the `HoneypotEvent` schema: `timestamp`,
    `source_ip`, `event_type` are required; `session_id`, `sensor_id`, `data` are
    optional.
  - Behind it, a normalization step canonicalizes the record: timestamps become
    ISO-8601, `event_type` is trimmed and lowercased so `" SSH_Login "` and
    `"ssh_login"` collapse together, payload defaults to `{}` so consumers never
    null-check, and a session ID is generated if one wasn't provided.
  - Returns `{ "status": "accepted", "id": <int> }` — the echoed ID confirms the
    row was actually persisted.
- **`GET /logs?limit=200` — read events back for the dashboard.**
  - Returns `{ "count": N, "logs": [...] }`, ordered newest-first by ID, with a
    default cap of 200 rows so responses stay bounded.
- **`GET /health`** — returns `{ "ok": true }`; used as a liveness probe for Docker
  and monitoring.
- **Validation is automatic, not hand-written:** missing required field, malformed
  timestamp, or empty body all return **422** before any of our logic runs. That's
  the reliability guarantee — the database only ever sees well-formed events.
- Mention the contract: "Because it's FastAPI, this entire API is self-documenting
  at `/docs`, which is what the frontend developed against."

- *If asked about auth/CORS:* "Right now `/log` is open and CORS is permissive for
  the demo — locking ingestion behind a sensor API key and restricting CORS to the
  frontend origin is our next hardening step." *(Say this proactively if you can —
  it's the obvious question.)*

---

## Slide 3 — Testing

**Headline to land:** 19 automated tests prove every claim on the previous two
slides, and they run anywhere with no infrastructure.

- **No live database needed.** The suite runs `/log` and `/logs` against an
  **in-memory SQLite** DB. A compiler hook renders the Postgres-only JSONB column
  as plain JSON under SQLite, so the *same* models and routes run in both
  environments. Every test gets a fresh table set up and torn down — full isolation.
- **What `POST /log` tests cover:** accepts valid events, persists them correctly,
  normalizes `event_type` to lowercase/trimmed, generates a session ID when missing
  *and* preserves a provided one, defaults payload to `{}`, assigns incrementing
  IDs, and rejects missing / empty / malformed input with 422.
- **What `GET /logs` tests cover:** empty-table case, returns inserted rows,
  newest-first ordering, exact response schema, the `limit` parameter, the default
  limit of 200, and a full **end-to-end** test — post through `/log`, read it back
  through `/logs`, confirm it matches.
- Land the close: "Every design decision I described — the normalization, the
  session logic, the ordering, the validation — has a test backing it. This isn't
  a prototype we hope works; it's verified behavior."

- *If asked "why SQLite for tests if prod is Postgres?":* The ORM abstracts the
  database, so tests stay fast and dependency-free while exercising the real
  application code; the JSONB-to-JSON hook keeps the schema honest across both.

---

## Closing handoff (say after slide 3)

"So the backend is a complete, tested ingestion pipeline — validated API in,
normalized JSONB storage, queryable out. [Hand to next presenter / next section]."

---

### Pre-demo cleanup (optional — only if a reviewer might read the code)

- `app/db/database.py` has a leftover `"UNCOMMENT WHEN THE DATABASE WORKS"` comment
  — reads as unfinished; safe to delete (table creation happens in `main.py`).
- `.env.example` says `DATABASE_URL=placeholder` (not a real URL) — have a real
  example connection string handy if asked to run it live.
- `main.py` uses the deprecated `@app.on_event("startup")` — mention proactively if
  the topic of FastAPI versions comes up.
