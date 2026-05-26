from app.models import RawLog


def _insert_raw_log(db, src_ip: str, event_type: str = "ssh_login"):
    row = RawLog(
        raw_json={
            "timestamp": "2026-04-18T12:00:00+00:00",
            "src_ip": src_ip,
            "event_type": event_type,
            "sensor_id": None,
            "session_id": "sess",
            "payload": {},
        }
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_logs_returns_empty_when_no_rows(client):
    response = client.get("/logs")
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == 0
    assert body["logs"] == []


def test_logs_returns_inserted_rows(client, db_session):
    _insert_raw_log(db_session, "10.0.0.1")
    _insert_raw_log(db_session, "10.0.0.2")

    response = client.get("/logs")
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == 2
    assert len(body["logs"]) == 2


def test_logs_returns_rows_in_descending_id_order(client, db_session):
    first = _insert_raw_log(db_session, "10.0.0.1")
    second = _insert_raw_log(db_session, "10.0.0.2")
    third = _insert_raw_log(db_session, "10.0.0.3")

    response = client.get("/logs")
    assert response.status_code == 200

    ids = [entry["id"] for entry in response.json()["logs"]]
    assert ids == [third.id, second.id, first.id]


def test_logs_response_schema(client, db_session):
    inserted = _insert_raw_log(db_session, "10.0.0.9", event_type="port_scan")

    response = client.get("/logs")
    assert response.status_code == 200

    entry = response.json()["logs"][0]
    assert set(entry.keys()) == {"id", "raw_json", "created_at"}
    assert entry["id"] == inserted.id
    assert entry["raw_json"]["src_ip"] == "10.0.0.9"
    assert entry["raw_json"]["event_type"] == "port_scan"
    assert entry["created_at"] is not None


def test_logs_respects_limit_parameter(client, db_session):
    for i in range(5):
        _insert_raw_log(db_session, f"10.0.0.{i}")

    response = client.get("/logs", params={"limit": 2})
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == 2
    assert len(body["logs"]) == 2


def test_logs_limit_larger_than_total_returns_all(client, db_session):
    for i in range(3):
        _insert_raw_log(db_session, f"10.0.0.{i}")

    response = client.get("/logs", params={"limit": 500})
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == 3
    assert len(body["logs"]) == 3


def test_logs_default_limit_is_200(client, db_session):
    for i in range(205):
        _insert_raw_log(db_session, f"10.1.{i // 256}.{i % 256}")

    response = client.get("/logs")
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == 200
    assert len(body["logs"]) == 200


def test_logs_returns_rows_created_via_log_endpoint(client, valid_event_payload):
    post = client.post("/log", json=valid_event_payload)
    assert post.status_code == 200

    response = client.get("/logs")
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == 1

    entry = body["logs"][0]
    assert entry["id"] == post.json()["id"]
    assert entry["raw_json"]["src_ip"] == "10.0.0.1"
    assert entry["raw_json"]["event_type"] == "ssh_login"
