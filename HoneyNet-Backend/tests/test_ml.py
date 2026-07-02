import json

import pytest

from app.services import ml_model
from app.services.ml_model import HONEYPOT_TYPES, adapt_distribution, predict_distribution


def test_distribution_endpoint_returns_200(client):
    response = client.get("/distribution")
    assert response.status_code == 200


def test_distribution_endpoint_returns_distribution_over_honeypot_types(client):
    response = client.get("/distribution")

    distribution = response.json()["distribution"]
    assert set(distribution.keys()) == set(HONEYPOT_TYPES)


def test_distribution_weights_are_a_probability_distribution(client):
    response = client.get("/distribution")

    weights = response.json()["distribution"].values()
    assert all(0.0 <= w <= 1.0 for w in weights)
    assert sum(weights) == 1.0


def test_predict_distribution_takes_no_arguments():
    # The ML model's contract: no parameters, it sources data itself.
    result = predict_distribution()
    assert set(result.keys()) == set(HONEYPOT_TYPES)


def test_adapt_distribution_strips_suffix_and_zeros_ftp():
    raw = {
        "ssh_honeypot": 0.041,
        "http_honeypot": 0.0,
        "mysql_honeypot": 0.061,
        "redis_honeypot": 0.082,
        "ftp_honeypot": 0.286,
        "smtp_honeypot": 0.531,
    }
    dist = adapt_distribution(raw)

    # keys mapped to bare types, ftp gets no distributable weight
    assert set(dist.keys()) == set(HONEYPOT_TYPES)
    assert dist["ftp"] == 0.0
    # a proper probability distribution over the scalable types
    assert sum(dist.values()) == pytest.approx(1.0)
    # ftp's 0.286 spread as 0.286/5 to each of the other five (pre-normalisation)
    assert dist["http"] == pytest.approx((0.0 + 0.286 / 5) / 1.001, rel=1e-3)
    # smtp had the most demand, so it stays the largest share
    assert max(dist, key=dist.get) == "smtp"


def test_refresh_requires_token(client):
    assert client.post("/distribution/refresh").status_code == 401


def test_refresh_runs_pipeline_and_returns_distribution(client, agent_headers, monkeypatch):
    from app.routes import ml as ml_route

    monkeypatch.setattr(ml_route, "run_pipeline_once", lambda: True)
    response = client.post("/distribution/refresh", headers=agent_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["refreshed"] is True
    assert set(body["distribution"].keys()) == set(HONEYPOT_TYPES)


def test_refresh_returns_502_when_pipeline_fails(client, agent_headers, monkeypatch):
    from app.routes import ml as ml_route

    monkeypatch.setattr(ml_route, "run_pipeline_once", lambda: False)
    response = client.post("/distribution/refresh", headers=agent_headers)
    assert response.status_code == 502


def test_override_requires_token(client):
    assert client.post("/distribution/override", json={"smtp": 1.0}).status_code == 401


def test_override_sets_and_serves_distribution(client, agent_headers):
    from app.services import ml_model

    try:
        r = client.post("/distribution/override", json={"smtp": 1.0}, headers=agent_headers)
        assert r.status_code == 200
        d = r.json()["distribution"]
        assert d["smtp"] == pytest.approx(1.0)
        assert d["ftp"] == 0.0
        # /distribution now serves the override
        served = client.get("/distribution").json()["distribution"]
        assert served["smtp"] == pytest.approx(1.0)
        assert ml_model.override_active() is True
    finally:
        ml_model.clear_override()


def test_override_rejects_unknown_type(client, agent_headers):
    r = client.post("/distribution/override", json={"telnet": 1.0}, headers=agent_headers)
    assert r.status_code == 400


def test_clear_override(client, agent_headers):
    from app.services import ml_model

    client.post("/distribution/override", json={"smtp": 1.0}, headers=agent_headers)
    r = client.delete("/distribution/override", headers=agent_headers)
    assert r.status_code == 200
    assert ml_model.override_active() is False


def test_set_counts_requires_token(client):
    assert client.post("/distribution/set-counts", json={"ssh": 6}).status_code == 401


def test_set_counts_sets_target(client, agent_headers):
    from app.services import ml_model

    try:
        r = client.post(
            "/distribution/set-counts",
            json={"ssh": 2, "http": 1, "smtp": 3},
            headers=agent_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 12
        # base 1 each + the distributable counts
        assert body["target_counts"] == {
            "ssh": 3, "http": 2, "smtp": 4, "redis": 1, "mysql": 1, "ftp": 1,
        }
    finally:
        ml_model.clear_override()


def test_set_counts_rejects_wrong_sum(client, agent_headers):
    r = client.post("/distribution/set-counts", json={"ssh": 3, "http": 1}, headers=agent_headers)
    assert r.status_code == 400


def test_set_counts_rejects_ftp(client, agent_headers):
    r = client.post(
        "/distribution/set-counts",
        json={"ftp": 2, "ssh": 2, "http": 2},
        headers=agent_headers,
    )
    assert r.status_code == 400


def test_predict_distribution_reads_plan(monkeypatch, tmp_path):
    plan = {
        "recommended_honeypot_distribution": {
            "ssh_honeypot": 0.0,
            "http_honeypot": 0.0,
            "mysql_honeypot": 0.0,
            "redis_honeypot": 0.0,
            "ftp_honeypot": 0.0,
            "smtp_honeypot": 1.0,
        }
    }
    plan_file = tmp_path / "honeypot_deployment.json"
    plan_file.write_text(json.dumps(plan))

    monkeypatch.setenv("ML_PLAN_PATH", str(plan_file))
    ml_model._cache.clear()  # avoid a stale cache from another test

    dist = predict_distribution()
    # smtp had all the demand and ftp is zeroed, so smtp takes the whole weight
    assert dist["smtp"] == pytest.approx(1.0)
    assert dist["ftp"] == 0.0
