import pytest

from app.services.ml_model import HONEYPOT_TYPES
from app.services.honeynet_state import (
    BASE_PER_TYPE,
    TOTAL_HONEYPOTS,
    HoneynetState,
    allocate,
    plan_redistribution,
    honeynet_state,
)
from app.services.honeynet_store import InMemoryHoneynetStore


@pytest.fixture(autouse=True)
def _reset_state():
    # honeynet_state is a process-wide singleton; reset it so the endpoint
    # tests don't leak counts into each other.
    honeynet_state.set_counts({hp: 0 for hp in HONEYPOT_TYPES})
    yield
    honeynet_state.set_counts({hp: 0 for hp in HONEYPOT_TYPES})


def test_new_state_starts_empty():
    state = HoneynetState()
    assert state.total == 0
    assert state.counts() == {hp: 0 for hp in HONEYPOT_TYPES}


def test_set_counts_updates_total():
    state = HoneynetState()
    state.set_counts({"http": 3, "ssh": 1})
    assert state.counts()["http"] == 3
    assert state.counts()["ssh"] == 1
    assert state.total == 4


def test_counts_returns_a_copy():
    state = HoneynetState({"http": 2})
    state.counts()["http"] = 99
    assert state.counts()["http"] == 2


def test_unknown_honeypot_type_is_rejected():
    state = HoneynetState()
    with pytest.raises(ValueError):
        state.set_counts({"telnet": 1})


def test_negative_count_is_rejected():
    state = HoneynetState()
    with pytest.raises(ValueError):
        state.set_counts({"http": -1})


def test_allocate_sums_to_total_and_respects_base():
    distribution = {hp: 1 / len(HONEYPOT_TYPES) for hp in HONEYPOT_TYPES}
    counts = allocate(distribution)
    assert sum(counts.values()) == TOTAL_HONEYPOTS
    # every type gets at least its always-on base
    assert all(count >= BASE_PER_TYPE for count in counts.values())


def test_allocate_uniform_gives_each_type_base_plus_even_share():
    # 6 types, base 1 each = 6 fixed; uniform spreads the remaining 6 evenly,
    # so every type ends up with 1 base + 1 distributed = 2.
    distribution = {hp: 1 / len(HONEYPOT_TYPES) for hp in HONEYPOT_TYPES}
    counts = allocate(distribution)
    assert counts == {hp: 2 for hp in HONEYPOT_TYPES}


def test_allocate_all_weight_on_one_type_still_keeps_base_elsewhere():
    # All distributable slots go to ssh, but every other type keeps its base.
    distribution = {hp: 0.0 for hp in HONEYPOT_TYPES}
    distribution["ssh"] = 1.0
    counts = allocate(distribution)

    assert sum(counts.values()) == TOTAL_HONEYPOTS
    distributable = TOTAL_HONEYPOTS - BASE_PER_TYPE * len(HONEYPOT_TYPES)
    assert counts["ssh"] == BASE_PER_TYPE + distributable
    assert all(counts[hp] == BASE_PER_TYPE for hp in HONEYPOT_TYPES if hp != "ssh")


def test_allocate_rejects_total_smaller_than_base():
    distribution = {hp: 1 / len(HONEYPOT_TYPES) for hp in HONEYPOT_TYPES}
    with pytest.raises(ValueError):
        allocate(distribution, total=len(HONEYPOT_TYPES) - 1)


def test_plan_redistribution_targets_total_and_reports_deltas():
    # Honeynet currently lopsided: everything piled onto ssh.
    state = HoneynetState({"ssh": TOTAL_HONEYPOTS})
    distribution = {hp: 1 / len(HONEYPOT_TYPES) for hp in HONEYPOT_TYPES}
    plan = plan_redistribution(distribution, state)

    assert sum(plan["target"].values()) == TOTAL_HONEYPOTS
    # ssh is over-provisioned, so it should be scaled down; others scaled up
    assert plan["delta"]["ssh"] < 0
    # net change brings current total (12) to target total (12)
    assert sum(plan["delta"].values()) == TOTAL_HONEYPOTS - state.total


def test_state_persists_to_store_on_set():
    store = InMemoryHoneynetStore()
    state = HoneynetState(store=store)
    state.set_counts({"ssh": 5})
    # the store should have captured the change
    assert store.load()["ssh"] == 5


def test_state_hydrates_from_store_on_init():
    store = InMemoryHoneynetStore({"http": 4, "ssh": 2})
    state = HoneynetState(store=store)
    assert state.counts()["http"] == 4
    assert state.counts()["ssh"] == 2


def test_state_without_store_does_not_persist():
    # default singleton-style usage: no store, pure in-memory, no errors
    state = HoneynetState()
    state.set_counts({"ftp": 3})
    assert state.counts()["ftp"] == 3


def test_state_endpoints_round_trip(client, agent_headers):
    put = client.put("/honeynet/state", json={"http": 2, "ssh": 1}, headers=agent_headers)
    assert put.status_code == 200
    assert put.json()["total"] == 3

    get = client.get("/honeynet/state", headers=agent_headers)
    assert get.json()["counts"]["http"] == 2
    assert get.json()["total"] == 3


def test_redistribution_endpoint(client, agent_headers):
    client.put("/honeynet/state", json={"ssh": 8}, headers=agent_headers)
    plan = client.get("/redistribution", headers=agent_headers).json()
    assert sum(plan["target"].values()) == TOTAL_HONEYPOTS
    assert set(plan["delta"].keys()) == set(HONEYPOT_TYPES)


def test_protected_endpoints_reject_without_token(client):
    # GET /honeynet/state is public (read-only display data for the frontend).
    assert client.get("/honeynet/state").status_code == 200
    assert client.get("/redistribution").status_code == 401
    assert client.put("/honeynet/state", json={"ssh": 1}).status_code == 401


def test_protected_endpoints_reject_wrong_token(client):
    bad = {"Authorization": "Bearer wrong-token"}
    # GET is public, so a bad token is simply ignored (still 200).
    assert client.get("/honeynet/state", headers=bad).status_code == 200
    assert client.get("/redistribution", headers=bad).status_code == 401
    assert client.put("/honeynet/state", json={"ssh": 1}, headers=bad).status_code == 401
