# Handoff — Honeynet state & redistribution

_Last worked: 2026-06-28. Branch: `hostedBack`._

## What this is

We need to turn the ML model's output (a probability **distribution** over honeypot
types) into a concrete **redistribution plan** — how many of each honeypot to run, and
what to start/stop. The model doesn't know how many containers exist, so we track that
ourselves in a state object.

## The composition model (the important part)

- **6 honeypot types:** `ssh, http, redis, mysql, ftp, smtp`
  (note: the old `sql` was renamed to `mysql`).
- **12 total honeypots** running at once.
- **1 of each type is always on** ("base") → 6 fixed honeypots.
- The ML distribution only places the **remaining 6** ("distributable" pool).

So `allocate()` = base (1 per type) + largest-remainder split of the 6 distributable
slots according to the distribution. Result always sums to 12 and every type keeps ≥ 1.

Constants live at the top of `app/services/honeynet_state.py`:
`BASE_PER_TYPE = 1`, `TOTAL_HONEYPOTS = 12`.

## Files

| File | What's in it |
|------|--------------|
| `app/services/ml_model.py` | `HONEYPOT_TYPES` (the 6 types) + placeholder `predict_distribution()` (uniform until the real model lands). |
| `app/services/honeynet_state.py` | `HoneynetState` (per-type counts, in-memory singleton `honeynet_state`), `allocate()`, `plan_redistribution()`. Now takes an optional `store` for persistence. |
| `app/services/honeynet_store.py` | **Persistence skeleton.** `HoneynetStateStore` ABC + `InMemoryHoneynetStore` (default) + `DbHoneynetStore` (DB-backed, opt-in). |
| `app/models/honeynet_state.py` | `HoneypotCount` model → `honeynet_state` table (one row per type). NOT registered in `models/__init__.py` yet (so it won't auto-create in the shared DB). |
| `app/routes/ml.py` | `GET /distribution`, `GET/PUT /honeynet/state`, `GET /redistribution`. |
| `tests/test_honeynet_state.py` | 15 tests — allocation, base guarantee, state validation, store hydrate/persist, endpoints. |

## Endpoints

- `GET /distribution` → model's distribution.
- `GET /honeynet/state` → `{counts, total}` currently running.
- `PUT /honeynet/state` → sync counts from the orchestrator (body: `{type: count}`).
- `GET /redistribution` → `{current, target, delta}` (delta: + = start, − = stop).

## Status

- All 16 new tests pass (`./venv/Scripts/python.exe -m pytest tests/test_honeynet_state.py tests/test_ml.py`).
- Pre-existing unrelated failure: `tests/test_logs.py::test_logs_default_limit_is_200`
  (205 vs 200) — part of the in-progress `logs.py` work, NOT this change.
- Nothing committed yet; all changes are in the working tree.

## Open questions / next steps

1. **Confirm the redistribution policy.** Right now `/redistribution` always targets a
   fixed total of 12 (current state only affects the deltas). That matches "1 base each +
   distribute 6." Confirm this is what you want vs. the model ever changing the total.
2. **Persistence — skeleton done, not enabled.** `honeynet_store.py` has the pluggable
   store; `HoneynetState(store=...)` hydrates on init and saves on every `set_counts`.
   The live singleton still defaults to in-memory. To turn on DB persistence (needed
   because App Runner wipes in-memory state on each deploy):
     a. Register `HoneypotCount` in `app/models/__init__.py` OR create the `honeynet_state`
        table manually — it's the shared hosted DB, so coordinate with the team first.
     b. Change the singleton to `honeynet_state = HoneynetState(store=DbHoneynetStore())`.
     c. Confirm write ownership: `PUT /honeynet/state` and the redistribution loop both
        go through `set_counts`, which will then persist.
3. **Who calls PUT /honeynet/state?** Need the orchestrator to report what's actually
   deployed so our view stays in sync with reality.
4. **Real model.** Swap the placeholder `predict_distribution()` body when the model
   arrives — signature/return shape are the contract.
5. Decide whether to wire `/redistribution` to actually trigger start/stop, or leave it
   as a plan the orchestrator polls.
