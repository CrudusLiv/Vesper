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


def test_chat_ok(monkeypatch):
    monkeypatch.setattr(bridge, "chat", lambda message, history: {"reply": "yo", "sources": []})
    r = client.post("/api/chat", headers=AUTH, json={"message": "hi", "history": []})
    assert r.status_code == 200
    assert r.json()["reply"] == "yo"


def test_chat_llm_failure_is_502(monkeypatch):
    def boom(message, history):
        raise bridge.LlmError("nope")
    monkeypatch.setattr(bridge, "chat", boom)
    r = client.post("/api/chat", headers=AUTH, json={"message": "hi", "history": []})
    assert r.status_code == 502
