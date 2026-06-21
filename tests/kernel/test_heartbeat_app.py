# tests/kernel/test_heartbeat_app.py
from unittest.mock import MagicMock, patch
from kernel.apps.heartbeat_app import HeartbeatApp
from kernel.events import Tick


def _make_app():
    runtime = MagicMock()
    return HeartbeatApp(runtime), runtime


def test_tick_is_subscribed():
    app, _ = _make_app()
    assert Tick in app.subscribes


def test_on_tick_calls_heartbeat_run(monkeypatch):
    app, runtime = _make_app()
    with patch("kernel.apps.heartbeat_app._run_heartbeat_tick") as mock_run:
        mock_run.return_value = None
        app.on_tick(Tick(interval=1800))
        mock_run.assert_called_once()


def test_on_tick_outside_active_hours_skips(monkeypatch):
    app, runtime = _make_app()
    with patch("kernel.apps.heartbeat_app._run_heartbeat_tick") as mock_run, \
         patch("kernel.apps.heartbeat_app.in_active_hours", return_value=False):
        app.on_tick(Tick(interval=1800))
        mock_run.assert_not_called()


def test_on_tick_writes_status_file(tmp_path, monkeypatch):
    import json
    from kernel.apps.heartbeat_app import HeartbeatApp
    from kernel.events import Tick
    from unittest.mock import MagicMock, patch

    runtime = MagicMock()
    app = HeartbeatApp(runtime)
    # Monkeypatch the data property by patching the instance method
    monkeypatch.setattr(type(app), "data", property(lambda self: tmp_path))

    with patch("kernel.apps.heartbeat_app.in_active_hours", return_value=True), \
         patch("kernel.apps.heartbeat_app._run_heartbeat_tick"):
        app.on_tick(Tick(interval=1800))

    status_file = tmp_path / "heartbeat-status.json"
    assert status_file.exists()
    data = json.loads(status_file.read_text())
    assert "last_tick" in data
    assert "next_tick_eta" in data
    assert data["errors"] == []
