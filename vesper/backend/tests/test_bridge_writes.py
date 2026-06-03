import pytest

import app.bridge as bridge


def test_finance_log_writes_under_project_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    out = bridge.finance_log(12.5, "food", "lunch")
    assert out["currency"] == "RM"
    assert out["month_total"] >= 12.5
    assert out["category_total"] >= 12.5
    # Isolation regression: the write must land under tmp_path, not the real vault.
    finance_dir = tmp_path / "Dynamous" / "Memory" / "finance"
    assert finance_dir.exists()
    assert list(finance_dir.glob("*.md"))


def test_finance_summary_returns_string(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    bridge.finance_log(5, "transport", "")
    out = bridge.finance_summary()
    assert isinstance(out["summary"], str)
    assert "transport" in out["summary"]


def test_note_append_writes_notes_file(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    out = bridge.note_append("remember to email the lecturer")
    assert out["ok"] is True
    assert out["appended_chars"] > 0
    notes = tmp_path / "Dynamous" / "Memory" / "notes" / "NOTES.md"
    assert notes.exists()
    assert "email the lecturer" in notes.read_text(encoding="utf-8")


def test_note_append_empty_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        bridge.note_append("   ")
