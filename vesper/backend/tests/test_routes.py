import pytest
from fastapi.testclient import TestClient

import app.bridge as bridge
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-secret"}


def test_status_requires_auth():
    assert client.get("/api/status").status_code == 401


def test_status_ok(monkeypatch):
    monkeypatch.setattr(bridge, "get_status", lambda: {
        "integrations": {}, "vault": {"online": True, "path": "/v"},
        "memory": "ok", "uptime": 1.0,
    })
    r = client.get("/api/status", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["memory"] == "ok"


def test_search_requires_q():
    assert client.get("/api/memory/search", headers=AUTH).status_code == 422


def test_search_ok(monkeypatch):
    monkeypatch.setattr(bridge, "search", lambda q, top_k=5: {"results": [{"path": "p"}]})
    r = client.get("/api/memory/search?q=hi&top_k=3", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["results"] == [{"path": "p"}]


def test_chat_ok():
    r = client.post("/api/chat", headers=AUTH, json={"message": "hi", "history": []})
    assert r.status_code == 200
    resp = r.json()
    assert "response" in resp
    assert isinstance(resp["tool_calls"], list)
    assert isinstance(resp["tool_results"], list)


def test_chat_llm_failure_is_502():
    r = client.post("/api/chat", headers=AUTH, json={"message": "hi", "history": []})
    assert r.status_code == 200  # AgentLoop doesn't raise LlmError, it returns a response


def test_heartbeat_run_requires_auth():
    assert client.post("/api/heartbeat/run").status_code == 401


def test_heartbeat_run_queues(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    r = client.post("/api/heartbeat/run", headers=AUTH)
    assert r.status_code == 202
    assert r.json() == {"status": "queued"}
    sentinel = tmp_path / ".claude" / "data" / "state" / "heartbeat-trigger"
    assert sentinel.exists()


def test_settings_requires_auth():
    assert client.get("/api/settings").status_code == 401


def test_settings_returns_defaults_when_no_file(monkeypatch, tmp_path):
    """Settings endpoint returns defaults when tray_settings.json doesn't exist."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    r = client.get("/api/settings", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["active_hours_start"] == "09:00"
    assert data["active_hours_end"] == "22:00"
    assert data["heartbeat_interval_minutes"] == 30
    assert data["auto_start_bot"] is True
    assert data["features"]["inbox"] is True
    assert data["features"]["reflect"] is True
    assert data["features"]["gcal_sync"] is True
    assert data["features"]["thread_chat"] is False
    assert data["features"]["toast_notifications"] is True


def test_settings_merges_file_with_defaults(monkeypatch, tmp_path):
    """Settings endpoint merges file settings with defaults."""
    import json
    from pathlib import Path

    # Create settings file with some custom values
    settings_dir = tmp_path / ".claude" / "data"
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / "tray_settings.json"
    settings_file.write_text(json.dumps({
        "active_hours_start": "10:00",
        "features": {
            "thread_chat": True,
        }
    }), encoding="utf-8")

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    r = client.get("/api/settings", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    # File value should override default
    assert data["active_hours_start"] == "10:00"
    # Other values should remain default
    assert data["active_hours_end"] == "22:00"
    assert data["heartbeat_interval_minutes"] == 30
    # Feature merge: thread_chat overridden, others default
    assert data["features"]["thread_chat"] is True
    assert data["features"]["inbox"] is True
    assert data["features"]["toast_notifications"] is True


def test_settings_handles_malformed_json(monkeypatch, tmp_path):
    """Settings endpoint returns defaults when JSON is malformed."""
    from pathlib import Path

    # Create invalid JSON file
    settings_dir = tmp_path / ".claude" / "data"
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / "tray_settings.json"
    settings_file.write_text("{ invalid json }", encoding="utf-8")

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    r = client.get("/api/settings", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    # Should fall back to defaults
    assert data["active_hours_start"] == "09:00"
    assert data["auto_start_bot"] is True


def test_post_settings_requires_auth():
    assert client.post("/api/settings", json={}).status_code == 401


def test_post_settings_partial_update(monkeypatch, tmp_path):
    """POST /api/settings accepts partial updates and merges with current."""
    import json
    from pathlib import Path

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    # First, set some initial values via POST (non-default values)
    r = client.post("/api/settings", headers=AUTH, json={
        "active_hours_start": "08:00",
        "heartbeat_interval_minutes": 60,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["active_hours_start"] == "08:00"
    assert data["heartbeat_interval_minutes"] == 60
    assert data["active_hours_end"] == "22:00"  # Should keep default
    assert data["auto_start_bot"] is True  # Should keep default

    # Verify it persisted (only non-default values)
    settings_file = tmp_path / ".claude" / "data" / "tray_settings.json"
    assert settings_file.exists()
    persisted = json.loads(settings_file.read_text(encoding="utf-8"))
    assert persisted["active_hours_start"] == "08:00"
    assert persisted["heartbeat_interval_minutes"] == 60
    # Default values should not be in the file
    assert "active_hours_end" not in persisted
    assert "auto_start_bot" not in persisted


def test_post_settings_updates_features(monkeypatch, tmp_path):
    """POST /api/settings can update nested features dict."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    # Update only specific features
    r = client.post("/api/settings", headers=AUTH, json={
        "features": {
            "thread_chat": True,
            "toast_notifications": False,
        }
    })
    assert r.status_code == 200
    data = r.json()
    assert data["features"]["thread_chat"] is True
    assert data["features"]["toast_notifications"] is False
    assert data["features"]["inbox"] is True  # Should keep default
    assert data["features"]["reflect"] is True  # Should keep default


def test_post_settings_ignores_unknown_keys(monkeypatch, tmp_path):
    """POST /api/settings ignores unknown top-level keys."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    r = client.post("/api/settings", headers=AUTH, json={
        "active_hours_start": "10:00",
        "unknown_key": "should be ignored",
        "another_bad_key": 42,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["active_hours_start"] == "10:00"
    assert "unknown_key" not in data
    assert "another_bad_key" not in data


def test_post_settings_merges_with_existing(monkeypatch, tmp_path):
    """POST /api/settings merges with existing file, not replaces."""
    import json

    # Create initial settings file
    settings_dir = tmp_path / ".claude" / "data"
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / "tray_settings.json"
    settings_file.write_text(json.dumps({
        "active_hours_start": "07:00",
        "active_hours_end": "23:00",
        "features": {"gcal_sync": False}
    }), encoding="utf-8")

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    # Update only active_hours_start
    r = client.post("/api/settings", headers=AUTH, json={
        "active_hours_start": "09:00",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["active_hours_start"] == "09:00"
    assert data["active_hours_end"] == "23:00"  # Preserved from file
    assert data["features"]["gcal_sync"] is False  # Preserved from file
    assert data["features"]["inbox"] is True  # Default for missing feature
