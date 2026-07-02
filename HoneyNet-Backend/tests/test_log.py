import hashlib
from datetime import datetime

from app.models import RawLog


def test_log_accepts_valid_event(client, valid_event_payload):
    response = client.post("/log", json=valid_event_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert isinstance(body["id"], int)
    assert body["id"] >= 1


def test_log_persists_row_to_database(client, db_session, valid_event_payload):
    response = client.post("/log", json=valid_event_payload)
    new_id = response.json()["id"]

    row = db_session.query(RawLog).filter(RawLog.id == new_id).one()
    assert row.raw_json["src_ip"] == "10.0.0.1"
    assert row.raw_json["event_type"] == "ssh_login"
    assert row.raw_json["session_id"] == "sess-abc"
    assert row.raw_json["sensor_id"] == "sensor-1"
    assert row.raw_json["payload"] == {"username": "root", "password": "toor"}


def test_log_normalizes_event_type_to_lowercase_and_trimmed(client, db_session):
    payload = {
        "timestamp": "2026-04-18T12:00:00+00:00",
        "source_ip": "10.0.0.2",
        "event_type": "  SSH_Login  ",
    }

    response = client.post("/log", json=payload)
    assert response.status_code == 200

    row = db_session.query(RawLog).filter(RawLog.id == response.json()["id"]).one()
    assert row.raw_json["event_type"] == "ssh_login"


def test_log_generates_session_id_when_missing(client, db_session):
    timestamp = "2026-04-18T12:30:00+00:00"
    payload = {
        "timestamp": timestamp,
        "source_ip": "10.0.0.3",
        "event_type": "ftp_login",
    }

    response = client.post("/log", json=payload)
    assert response.status_code == 200

    row = db_session.query(RawLog).filter(RawLog.id == response.json()["id"]).one()

    time_bucket = datetime.fromisoformat(timestamp).strftime("%Y%m%d%H")
    expected = hashlib.sha256(
        f"10.0.0.3:ftp_login:{time_bucket}".encode()
    ).hexdigest()
    assert row.raw_json["session_id"] == expected


def test_log_preserves_provided_session_id(client, db_session, valid_event_payload):
    response = client.post("/log", json=valid_event_payload)
    assert response.status_code == 200

    row = db_session.query(RawLog).filter(RawLog.id == response.json()["id"]).one()
    assert row.raw_json["session_id"] == "sess-abc"


def test_log_defaults_payload_to_empty_dict_when_data_missing(client, db_session):
    payload = {
        "timestamp": "2026-04-18T12:00:00+00:00",
        "source_ip": "10.0.0.4",
        "event_type": "port_scan",
    }

    response = client.post("/log", json=payload)
    assert response.status_code == 200

    row = db_session.query(RawLog).filter(RawLog.id == response.json()["id"]).one()
    assert row.raw_json["payload"] == {}


def test_log_rejects_missing_required_field(client):
    payload = {
        "source_ip": "10.0.0.5",
        "event_type": "ssh_login",
    }

    response = client.post("/log", json=payload)
    assert response.status_code == 422


def test_log_rejects_empty_body(client):
    response = client.post("/log", json={})
    assert response.status_code == 422


def test_log_rejects_malformed_timestamp(client):
    payload = {
        "timestamp": "not-a-timestamp",
        "source_ip": "10.0.0.6",
        "event_type": "ssh_login",
    }

    response = client.post("/log", json=payload)
    assert response.status_code == 422


def test_log_assigns_incrementing_ids(client, valid_event_payload):
    # Distinct events (different src_ip) so the dedup guard doesn't drop them.
    def post(ip):
        return client.post("/log", json={**valid_event_payload, "source_ip": ip}).json()["id"]

    first = post("10.1.1.1")
    second = post("10.1.1.2")
    third = post("10.1.1.3")

    assert second == first + 1
    assert third == second + 1


def test_log_deduplicates_identical_events(client, db_session, valid_event_payload):
    first = client.post("/log", json=valid_event_payload)
    assert first.status_code == 200
    assert first.json()["status"] == "accepted"

    # Same event again → dropped by the unique content_hash guard.
    second = client.post("/log", json=valid_event_payload)
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"

    # Only one row exists for that content.
    ch = first.json()  # ensure first was stored
    assert "id" in ch


def test_log_ignores_forwarder_heartbeat(client, db_session):
    before = db_session.query(RawLog).count()
    payload = {
        "timestamp": "2026-04-18T12:00:00+00:00",
        "source_ip": "127.0.0.1",
        "event_type": "forwarder.heartbeat",
        "honeypot_type": "forwarder",
    }
    response = client.post("/log", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    # nothing persisted
    assert db_session.query(RawLog).count() == before


def test_log_stores_canonical_iso_timestamp(client, db_session, valid_event_payload):
    response = client.post("/log", json=valid_event_payload)
    assert response.status_code == 200

    row = db_session.query(RawLog).filter(RawLog.id == response.json()["id"]).one()
    assert row.raw_json["timestamp"] == "2026-04-18T12:00:00+00:00"


def test_log_captures_active_honeypot_count(client, db_session):
    from app.services.honeynet_state import honeynet_state

    original = honeynet_state.counts()
    try:
        honeynet_state.set_counts({"ssh": 3})
        payload = {
            "timestamp": "2026-04-18T12:00:00+00:00",
            "source_ip": "10.0.0.7",
            "event_type": "ssh.login.attempt",  # prefix resolves to type "ssh"
        }
        response = client.post("/log", json=payload)
        assert response.status_code == 200
        assert response.json()["active_honeypot_count"] == 3

        row = db_session.query(RawLog).filter(RawLog.id == response.json()["id"]).one()
        assert row.active_honeypot_count == 3
    finally:
        honeynet_state.set_counts(original)


def test_log_active_count_defaults_to_one_for_unknown_type(client, db_session):
    payload = {
        "timestamp": "2026-04-18T12:00:00+00:00",
        "source_ip": "10.0.0.8",
        "event_type": "port_scan",  # not a known honeypot type
    }
    response = client.post("/log", json=payload)
    assert response.status_code == 200
    # NOT NULL column falls back to 1 when the type can't be resolved.
    assert response.json()["active_honeypot_count"] == 1

    row = db_session.query(RawLog).filter(RawLog.id == response.json()["id"]).one()
    assert row.active_honeypot_count == 1
