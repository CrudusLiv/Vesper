import json

import app.inbox_status as store


def test_add_creates_queued_record(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    rec = store.add("CS101.pptx")
    assert rec["filename"] == "CS101.pptx"
    assert rec["status"] == "queued"
    assert rec["id"]
    assert rec["type"] is None and rec["note_path"] is None and rec["error"] is None
    # Persisted to the lazy path under tmp_path.
    db = tmp_path / ".claude" / "data" / "state" / "inbox-uploads.json"
    assert db.exists()
    assert json.loads(db.read_text(encoding="utf-8"))[0]["id"] == rec["id"]


def test_recent_is_newest_first_and_capped(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    ids = [store.add(f"f{i}.pdf")["id"] for i in range(12)]
    recent = store.recent()
    assert len(recent) == 10            # capped
    assert recent[0]["id"] == ids[-1]   # newest first


def test_update_sets_fields_by_id(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    rec = store.add("x.pptx")
    out = store.update(rec["id"], status="done", title="Sorting", note_path="lectures/CS101/x.md")
    assert out["status"] == "done"
    assert out["title"] == "Sorting"
    assert store.recent()[0]["note_path"] == "lectures/CS101/x.md"
    assert store.recent()[0]["updated_at"] >= store.recent()[0]["created_at"]


def test_update_unknown_id_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert store.update("nope", status="done") is None


def test_corrupt_store_is_treated_as_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    db = tmp_path / ".claude" / "data" / "state" / "inbox-uploads.json"
    db.parent.mkdir(parents=True, exist_ok=True)
    db.write_text("{ not json", encoding="utf-8")
    assert store.recent() == []
    rec = store.add("a.pdf")
    assert store.recent()[0]["id"] == rec["id"]
