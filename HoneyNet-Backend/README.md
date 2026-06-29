##FOR TEAMMATES



#IN APP FILE RUN COMMAND
    cp .env.example .env

#TO RUN LOCALLY

    python -m venv venv
    venv\Scripts\activate           -Creates venv

    pip install -r requirements.txt -INSTALLS Required libraries
    python run.py                   -Runs backend locally



#TO RUN ON DOCKER


    #ON FIRST BUILD:
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml up --build


    #AFTER FIRST BUILD:
        #RUN FOREGROUD:
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml up
        #RUN BACKGROUND:
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml up -d
        
        #STOP
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml down 


    #Rebuild
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml up --build --force-recreate




# TESTING

## Install test dependencies

    venv\Scripts\activate
    pip install pytest httpx

## Run the full test suite

    python -m pytest tests/ -v

## How the tests work

The suite lives in [tests/](tests/) and exercises the `/log` and `/logs`
endpoints against an in-memory SQLite database — no Postgres needed.

### [tests/conftest.py](tests/conftest.py)

Shared test scaffolding. Runs once before any test:

1. Sets `DATABASE_URL=sqlite:///:memory:` so importing `app.db.database`
   does not fail on the missing env var.
2. Registers a compiler hook that renders `JSONB` columns as `JSON` when
   the dialect is SQLite, so the Postgres-only `raw_json` column works
   against SQLite.
3. Builds a single shared SQLite engine using `StaticPool` (so every
   connection sees the same in-memory DB) and swaps it into
   `app.db.database` *before* `app.main` imports the engine.
4. Overrides the FastAPI `get_db` dependency so routes use the test
   session factory.

Fixtures provided:

- `_setup_database` (autouse) — creates all tables before each test and
  drops them after, giving every test a clean DB.
- `db_session` — a raw SQLAlchemy session for direct DB inspection or
  seeding.
- `client` — a `fastapi.testclient.TestClient` wired to the app with
  dependency overrides applied.
- `valid_event_payload` — a canonical `HoneypotEvent` JSON body reused
  across tests.

### [tests/test_log.py](tests/test_log.py) — POST `/log`

| Test | What it verifies |
| --- | --- |
| `test_log_accepts_valid_event` | A well-formed event returns `200` with `status="accepted"` and an integer `id`. |
| `test_log_persists_row_to_database` | The inserted row is queryable via SQLAlchemy and `raw_json` contains the normalized fields (`src_ip`, `event_type`, `session_id`, `sensor_id`, `payload`). |
| `test_log_normalizes_event_type_to_lowercase_and_trimmed` | `"  SSH_Login  "` is stored as `"ssh_login"` — confirms `normalize_event_dict` strips and lowercases. |
| `test_log_generates_session_id_when_missing` | When no `session_id` is provided, the stored value matches `sha256("{src_ip}:{event_type}:{YYYYMMDDHH}")` — the deterministic bucket logic in `generate_session_id`. |
| `test_log_preserves_provided_session_id` | A caller-supplied `session_id` is stored verbatim rather than being regenerated. |
| `test_log_defaults_payload_to_empty_dict_when_data_missing` | Omitting `data` yields `payload == {}` in the stored row (not `None`). |
| `test_log_rejects_missing_required_field` | Omitting `timestamp` returns `422` from Pydantic validation. |
| `test_log_rejects_empty_body` | `POST /log` with `{}` returns `422`. |
| `test_log_rejects_malformed_timestamp` | A non-ISO timestamp string returns `422`. |
| `test_log_assigns_incrementing_ids` | Three successive posts produce consecutive primary keys. |
| `test_log_stores_canonical_iso_timestamp` | The stored `timestamp` field is an ISO-8601 string matching the request. |

### [tests/test_logs.py](tests/test_logs.py) — GET `/logs`

Each test uses a local `_insert_raw_log` helper to seed `RawLog` rows
directly via `db_session`.

| Test | What it verifies |
| --- | --- |
| `test_logs_returns_empty_when_no_rows` | With an empty table the response is `{"count": 0, "logs": []}`. |
| `test_logs_returns_inserted_rows` | After inserting two rows, `count == 2` and `len(logs) == 2`. |
| `test_logs_returns_rows_in_descending_id_order` | Rows are returned newest-first, i.e. ordered by `id DESC`. |
| `test_logs_response_schema` | Each log entry has exactly the keys `{id, raw_json, created_at}`, and the values round-trip correctly. |
| `test_logs_respects_limit_parameter` | `?limit=2` caps the response at 2 rows even when more exist. |
| `test_logs_limit_larger_than_total_returns_all` | A `limit` larger than the row count still returns every row (no padding/error). |
| `test_logs_default_limit_is_200` | With 205 rows and no `limit`, exactly 200 are returned — confirms the default value in the route signature. |
| `test_logs_returns_rows_created_via_log_endpoint` | End-to-end: a row posted through `POST /log` is visible through `GET /logs` with matching `id` and normalized fields. |

