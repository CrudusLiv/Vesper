import app.bridge as bridge


def test_get_status_shape():
    status = bridge.get_status()
    assert "integrations" in status
    assert isinstance(status["integrations"], dict)
    for name, info in status["integrations"].items():
        assert set(info.keys()) == {"ready", "missing"}
        assert isinstance(info["ready"], bool)
        assert isinstance(info["missing"], list)
    assert status["vault"]["path"]
    assert status["memory"] in ("ok", "degraded")
    assert isinstance(status["uptime"], float)


def test_search_degraded_when_db_unavailable(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no db")
    monkeypatch.setattr(bridge.memory_db, "connect", boom)
    out = bridge.search("anything", top_k=5)
    assert out == {"results": [], "warning": "memory index unavailable"}


def test_search_returns_results(monkeypatch):
    class FakeConn:
        def execute(self, *a, **k):
            class R:
                def fetchone(self_inner):
                    return {"c": 3}
            return R()
        def close(self):
            pass
    monkeypatch.setattr(bridge.memory_db, "connect", lambda *a, **k: FakeConn())
    monkeypatch.setattr(
        bridge.memory_search, "hybrid_search",
        lambda conn, q, top_k=5: [
            {"id": 1, "path": "lectures/x.md", "heading": "H", "content": "C", "score": 0.9},
        ],
    )
    out = bridge.search("query", top_k=5)
    assert out["results"][0] == {
        "path": "lectures/x.md", "heading": "H", "content": "C", "score": 0.9,
    }
    assert "warning" not in out


def test_chat_happy_path(monkeypatch):
    monkeypatch.setattr(
        bridge, "search",
        lambda message, top_k=5: {"results": [
            {"path": "p.md", "heading": "h", "content": "ctx", "score": 0.5},
        ]},
    )
    monkeypatch.setattr(bridge.llm, "call", lambda *a, **k: "a dry vesper reply")
    out = bridge.chat("hello", history=[])
    assert out["reply"] == "a dry vesper reply"
    assert out["sources"] == [{"path": "p.md", "heading": "h", "score": 0.5}]


def test_chat_raises_on_empty_llm(monkeypatch):
    monkeypatch.setattr(bridge, "search", lambda message, top_k=5: {"results": []})
    monkeypatch.setattr(bridge.llm, "call", lambda *a, **k: "")
    try:
        bridge.chat("hello", history=[])
        assert False, "expected LlmError"
    except bridge.LlmError:
        pass
