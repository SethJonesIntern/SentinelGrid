from app.routes import geo


def test_get_coords_returns_coordinates(client, monkeypatch):
    def fake_geolocate(ip):
        return {
            "ip": ip,
            "latitude": 37.751,
            "longitude": -97.822,
            "city": "Wichita",
            "country": "United States",
        }

    monkeypatch.setattr(geo, "geolocate_ip", fake_geolocate)

    response = client.get("/get_coords", params={"ip": "8.8.8.8"})
    assert response.status_code == 200
    body = response.json()
    assert body["ip"] == "8.8.8.8"
    assert body["latitude"] == 37.751
    assert body["longitude"] == -97.822


def test_get_coords_rejects_invalid_ip(client):
    response = client.get("/get_coords", params={"ip": "not-an-ip"})
    assert response.status_code == 400


def test_get_coords_requires_ip_param(client):
    response = client.get("/get_coords")
    assert response.status_code == 422


def test_get_coords_accepts_ipv6(client, monkeypatch):
    monkeypatch.setattr(
        geo, "geolocate_ip", lambda ip: {"ip": ip, "latitude": 0.0, "longitude": 0.0}
    )
    response = client.get("/get_coords", params={"ip": "2001:4860:4860::8888"})
    assert response.status_code == 200


def test_geolocate_caches_successful_lookups(monkeypatch):
    geo.clear_cache()
    calls = {"n": 0}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": "success",
                "lat": 1.0,
                "lon": 2.0,
                "city": "X",
                "country": "Y",
                "query": "1.2.3.4",
            }

    def fake_get(url, params=None, timeout=None):
        calls["n"] += 1
        return FakeResp()

    monkeypatch.setattr(geo.httpx, "get", fake_get)

    first = geo.geolocate_ip("1.2.3.4")
    second = geo.geolocate_ip("1.2.3.4")

    assert first == second
    assert calls["n"] == 1  # second lookup served from cache, no upstream call
    geo.clear_cache()
