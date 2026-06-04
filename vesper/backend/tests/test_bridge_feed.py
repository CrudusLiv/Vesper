"""Bridge wrapper tests for the feed store functions."""
from unittest.mock import patch
import app.bridge as bridge


def test_feed_recent_delegates_to_feed_module():
    with patch("heartbeat.feed.recent", return_value=[{"id": "x", "kind": "error", "read": False}]) as mock:
        result = bridge.feed_recent(limit=10)
    mock.assert_called_once_with(10)
    assert isinstance(result, list)
    assert result[0]["id"] == "x"


def test_feed_recent_caps_limit_at_50():
    with patch("heartbeat.feed.recent", return_value=[]) as mock:
        bridge.feed_recent(limit=99)
    mock.assert_called_once_with(50)


def test_feed_mark_read_delegates_to_feed_module():
    updated = {"id": "abc", "read": True}
    with patch("heartbeat.feed.mark_read", return_value=updated) as mock:
        result = bridge.feed_mark_read("abc")
    mock.assert_called_once_with("abc")
    assert result == updated


def test_feed_mark_read_none_for_missing_id():
    with patch("heartbeat.feed.mark_read", return_value=None):
        result = bridge.feed_mark_read("nonexistent")
    assert result is None
