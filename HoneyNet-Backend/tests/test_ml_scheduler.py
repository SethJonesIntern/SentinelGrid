import threading

from app.services import ml_scheduler


def _scheduler_threads():
    return [t for t in threading.enumerate() if t.name == "ml-scheduler"]


def test_start_scheduler_is_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("ML_SCHEDULER_ENABLED", raising=False)
    ml_scheduler.start_scheduler()
    assert _scheduler_threads() == []


def test_enabled_reads_env(monkeypatch):
    monkeypatch.setenv("ML_SCHEDULER_ENABLED", "true")
    assert ml_scheduler._enabled() is True
    monkeypatch.setenv("ML_SCHEDULER_ENABLED", "0")
    assert ml_scheduler._enabled() is False
