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
