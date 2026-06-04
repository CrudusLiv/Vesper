"""Tests for the feed side-effect and toast wiring inside dashboard.notify()."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import pytest


@pytest.fixture(autouse=True)
def _no_discord(monkeypatch):
    """Stub out the actual Discord webhook so no network calls happen."""
    monkeypatch.setenv("DISCORD_HOOK_HEARTBEAT", "")
    monkeypatch.setenv("DISCORD_HOOK_DEADLINES", "")
    monkeypatch.setenv("DISCORD_HOOK_ERRORS", "")
    monkeypatch.setenv("DISCORD_HOOK_DAILY", "")


def test_ok_tick_not_appended_to_feed():
    appended = []
    with patch("heartbeat.feed.append", side_effect=lambda k, p: appended.append(k) or {}):
        with patch("heartbeat.toast.show", return_value=True):
            from heartbeat import dashboard
            import importlib; importlib.reload(dashboard)
            dashboard.notify("heartbeat_tick", {"status": "ok", "failing": []})
    assert "heartbeat_tick" not in appended


def test_degraded_tick_appended_to_feed():
    appended = []
    with patch("heartbeat.feed.append", side_effect=lambda k, p: appended.append(k) or {"title": "t", "body": "b"}):
        with patch("heartbeat.toast.show", return_value=True):
            from heartbeat import dashboard
            import importlib; importlib.reload(dashboard)
            dashboard.notify("heartbeat_tick", {"status": "degraded", "failing": ["gmail"]})
    assert "heartbeat_tick" in appended


def test_deadline_reply_not_appended_to_feed():
    appended = []
    with patch("heartbeat.feed.append", side_effect=lambda k, p: appended.append(k) or {}):
        with patch("heartbeat.toast.show", return_value=True):
            from heartbeat import dashboard
            import importlib; importlib.reload(dashboard)
            dashboard.notify("deadline_reply", {"text": "reply"})
    assert "deadline_reply" not in appended


def test_deadline_24h_appended_and_toast_fired():
    appended = []
    toasted = []
    payload = {"course": "CS101", "title": "Lab", "due": "2026-06-05", "days": 1}
    record = {"title": "[CS101] Lab", "body": "due 2026-06-05"}
    with patch("heartbeat.feed.append", side_effect=lambda k, p: appended.append(k) or record):
        with patch("heartbeat.toast.show", side_effect=lambda t, b: toasted.append(t)):
            from heartbeat import dashboard
            import importlib; importlib.reload(dashboard)
            dashboard.notify("deadline_24h", payload)
    assert "deadline_24h" in appended
    assert toasted, "toast.show was not called for deadline_24h"


def test_error_appended_and_toast_fired():
    appended = []
    toasted = []
    record = {"title": "Error in x", "body": "boom"}
    with patch("heartbeat.feed.append", side_effect=lambda k, p: appended.append(k) or record):
        with patch("heartbeat.toast.show", side_effect=lambda t, b: toasted.append(t)):
            from heartbeat import dashboard
            import importlib; importlib.reload(dashboard)
            dashboard.notify("error", {"script": "x", "trace": "boom"})
    assert "error" in appended
    assert toasted, "toast.show was not called for error"


def test_morning_digest_appended_no_toast():
    appended = []
    toasted = []
    record = {"title": "Morning — Thu", "body": "..."}
    with patch("heartbeat.feed.append", side_effect=lambda k, p: appended.append(k) or record):
        with patch("heartbeat.toast.show", side_effect=lambda t, b: toasted.append(t)):
            from heartbeat import dashboard
            import importlib; importlib.reload(dashboard)
            dashboard.notify("morning_digest", {"body": "good morning"})
    assert "morning_digest" in appended
    assert not toasted, "toast.show must NOT fire for morning_digest"


def test_feed_failure_does_not_raise():
    with patch("heartbeat.feed.append", side_effect=OSError("disk full")):
        with patch("heartbeat.toast.show", return_value=True):
            from heartbeat import dashboard
            import importlib; importlib.reload(dashboard)
            # Must not raise even if feed.append blows up
            dashboard.notify("morning_digest", {"body": "hello"})
