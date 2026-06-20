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
