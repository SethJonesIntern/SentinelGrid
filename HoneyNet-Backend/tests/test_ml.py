from app.services.ml_model import HONEYPOT_TYPES, predict_distribution


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
