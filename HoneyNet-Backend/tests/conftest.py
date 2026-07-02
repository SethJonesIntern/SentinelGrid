import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AGENT_TOKEN"] = "test-agent-token"
# Point the ML plan at a path that doesn't exist so predict_distribution() uses
# its uniform fallback by default; tests that exercise the plan set this per-test.
os.environ["ML_PLAN_PATH"] = os.path.join(os.path.dirname(__file__), "_no_ml_plan.json")

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _render_jsonb_as_json_for_sqlite(type_, compiler, **kw):
    return "JSON"


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE, autoflush=False, autocommit=False, future=True
)

from app.db import database as _db_module

_db_module.engine = TEST_ENGINE
_db_module.SessionLocal = TestingSessionLocal

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.database import get_db
from app.main import app


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def agent_headers():
    """Auth header for the agent-protected honeynet endpoints."""
    return {"Authorization": f"Bearer {os.environ['AGENT_TOKEN']}"}


@pytest.fixture()
def user_headers(client):
    """Auth header for a logged-in user (frontend-driven control endpoints)."""
    res = client.post(
        "/auth/signup", json={"username": "test-operator", "password": "password123"}
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def valid_event_payload():
    return {
        "timestamp": "2026-04-18T12:00:00+00:00",
        "source_ip": "10.0.0.1",
        "event_type": "ssh_login",
        "session_id": "sess-abc",
        "sensor_id": "sensor-1",
        "data": {"username": "root", "password": "toor"},
    }
