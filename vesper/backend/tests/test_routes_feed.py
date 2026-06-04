from unittest.mock import patch
import app.bridge as bridge
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-secret"}

_SAMPLE = [
    {"id": "a1", "kind": "deadline_24h", "title": "[CS101] Lab", "body": "due 2026-06-05",
     "priority": "high", "read": False, "ts": None, "created_at": "2026-06-04T09:00:00+08:00"},
]


def test_get_feed_requires_auth():
    assert client.get("/api/feed").status_code == 401


def test_get_feed_returns_list(monkeypatch):
    monkeypatch.setattr(bridge, "feed_recent", lambda limit=50: _SAMPLE)
    r = client.get("/api/feed", headers=AUTH)
    assert r.status_code == 200
    assert r.json()[0]["kind"] == "deadline_24h"


def test_get_feed_limit_param(monkeypatch):
    seen = {}
    monkeypatch.setattr(bridge, "feed_recent", lambda limit=50: seen.setdefault("limit", limit) or [])
    client.get("/api/feed?limit=5", headers=AUTH)
    assert seen["limit"] == 5


def test_mark_read_returns_updated(monkeypatch):
    updated = {**_SAMPLE[0], "read": True}
    monkeypatch.setattr(bridge, "feed_mark_read", lambda item_id: updated)
    r = client.patch("/api/feed/a1/read", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["read"] is True


def test_mark_read_unknown_id_is_404(monkeypatch):
    monkeypatch.setattr(bridge, "feed_mark_read", lambda item_id: None)
    r = client.patch("/api/feed/nonexistent/read", headers=AUTH)
    assert r.status_code == 404


def test_mark_read_requires_auth():
    assert client.patch("/api/feed/a1/read").status_code == 401
