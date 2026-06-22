import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from kernel.web.server import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(data_dir=tmp_path, vault_dir=tmp_path, password="secret")


@pytest.fixture
def client(app):
    return TestClient(app, follow_redirects=False)


def test_root_redirects_to_login_when_unauthenticated(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/login" in r.headers["location"]


def test_login_page_returns_200(client):
    r = client.get("/login")
    assert r.status_code == 200


def test_wrong_password_returns_login_with_error(client):
    r = client.post("/login", data={"password": "wrong"}, follow_redirects=False)
    assert r.status_code == 200
    assert b"Invalid password" in r.content


def test_correct_password_redirects_to_dashboard(client):
    r = client.post("/login", data={"password": "secret"}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/"


def test_dashboard_accessible_after_login(client):
    client.post("/login", data={"password": "secret"})
    r = client.get("/")
    assert r.status_code == 200


def test_logout_clears_session(client):
    client.post("/login", data={"password": "secret"})
    client.get("/logout")
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302


def test_read_deadlines_empty(tmp_path):
    from kernel.web.server import read_deadlines
    assert read_deadlines(tmp_path) == []


def test_read_deadlines_parses_file(tmp_path):
    from kernel.web.server import read_deadlines
    (tmp_path / "DEADLINES.md").write_text(
        "# DEADLINES\n\n## Active\n\n- 2026-07-01 — CS101 — Assignment 1\n",
        encoding="utf-8",
    )
    result = read_deadlines(tmp_path)
    assert len(result) == 1
    assert result[0]["title"] == "Assignment 1"
    assert result[0]["due"] == "2026-07-01"


def test_read_heartbeat_status_missing(tmp_path):
    from kernel.web.server import read_heartbeat_status
    status = read_heartbeat_status(tmp_path)
    assert status["last_tick"] is None
    assert status["health"] == "unknown"


def test_read_heartbeat_status_green(tmp_path):
    from kernel.web.server import read_heartbeat_status
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=8)))
    data = {
        "last_tick": now.isoformat(),
        "next_tick_eta": (now + timedelta(seconds=1800)).isoformat(),
        "errors": [],
        "standby": False,
    }
    (tmp_path / "heartbeat-status.json").write_text(json.dumps(data))
    status = read_heartbeat_status(tmp_path)
    assert status["health"] == "green"
    assert status["errors"] == []
    assert status["standby"] is False


def test_read_heartbeat_status_standby(tmp_path):
    from kernel.web.server import read_heartbeat_status
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=8)))
    data = {
        "last_tick": now.isoformat(),
        "next_tick_eta": (now + timedelta(seconds=1800)).isoformat(),
        "errors": [],
        "standby": True,
    }
    (tmp_path / "heartbeat-status.json").write_text(json.dumps(data))
    status = read_heartbeat_status(tmp_path)
    assert status["health"] == "standby"
    assert status["standby"] is True
    assert status["errors"] == []


def test_web_app_skips_start_if_no_password(monkeypatch):
    from unittest.mock import MagicMock, patch
    from kernel.apps.web_app import WebApp

    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    runtime = MagicMock()
    app = WebApp(runtime)

    with patch("kernel.apps.web_app.uvicorn") as mock_uvicorn:
        app.on_start()
        mock_uvicorn.Server.assert_not_called()


def test_web_app_starts_server_with_password(monkeypatch):
    from unittest.mock import MagicMock, patch
    from kernel.apps.web_app import WebApp

    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    runtime = MagicMock()
    app = WebApp(runtime)

    started = []
    def fake_thread(**kwargs):
        t = MagicMock()
        t.start = lambda: started.append(True)
        return t

    with patch("kernel.apps.web_app.threading.Thread", side_effect=fake_thread):
        app.on_start()

    assert started
