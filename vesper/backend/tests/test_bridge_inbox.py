import pytest

import app.bridge as bridge


def test_inbox_save_writes_into_inbox(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    p = bridge.inbox_save("CS101.pptx", b"binary-bytes")
    assert p.exists()
    assert p.parent == tmp_path / "Dynamous" / "Memory" / "inbox"
    assert p.read_bytes() == b"binary-bytes"


def test_inbox_save_resolves_collisions(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    a = bridge.inbox_save("x.pdf", b"1")
    b = bridge.inbox_save("x.pdf", b"2")
    assert a.name == "x.pdf"
    assert b.name == "x_1.pdf"


def test_inbox_save_rejects_bad_extension(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        bridge.inbox_save("notes.txt", b"1")


def test_inbox_save_rejects_blank_filename(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        bridge.inbox_save("   ", b"1")


def test_inbox_save_rejects_too_large(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(bridge, "MAX_UPLOAD_BYTES", 3)
    with pytest.raises(ValueError):
        bridge.inbox_save("x.pdf", b"too-long")


def test_inbox_save_strips_path_components(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    p = bridge.inbox_save("../../evil.pptx", b"1")
    assert p.parent == tmp_path / "Dynamous" / "Memory" / "inbox"
    assert p.name == "evil.pptx"


def test_inbox_save_strips_backslash_path_components(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    p = bridge.inbox_save("..\\..\\evil.pptx", b"1")
    assert p.parent == tmp_path / "Dynamous" / "Memory" / "inbox"
    assert p.name == "evil.pptx"


def test_inbox_enqueue_and_recent(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    rec = bridge.inbox_enqueue("a.pptx")
    assert rec["status"] == "queued"
    assert rec["filename"] == "a.pptx"
    assert bridge.inbox_recent()[0]["id"] == rec["id"]


def test_inbox_trigger_heartbeat_drops_sentinel(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    bridge.inbox_trigger_heartbeat()
    sentinel = tmp_path / ".claude" / "data" / "state" / "heartbeat-trigger"
    assert sentinel.exists()
    assert sentinel.read_text(encoding="utf-8")


def test_inbox_deps_available_returns_bool():
    assert isinstance(bridge.inbox_deps_available(), bool)
