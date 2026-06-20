# tests/kernel/test_dashboard_app.py
from unittest.mock import MagicMock, patch
from kernel.apps.dashboard_app import DashboardApp
from kernel.events import Notify


def _make_app():
    runtime = MagicMock()
    return DashboardApp(runtime), runtime


def test_notify_subscribed():
    app, _ = _make_app()
    assert Notify in app.subscribes


def test_on_notify_posts_to_discord(monkeypatch):
    app, _ = _make_app()
    with patch("kernel.apps.dashboard_app._post_notify") as mock_post:
        evt = Notify(text="hello world", channel="heartbeat")
        app.on_notify(evt)
        mock_post.assert_called_once_with(evt)


def test_on_notify_exception_does_not_raise(monkeypatch):
    app, _ = _make_app()
    with patch("kernel.apps.dashboard_app._post_notify", side_effect=RuntimeError("webhook down")):
        app.on_notify(Notify(text="oops"))  # should not raise
