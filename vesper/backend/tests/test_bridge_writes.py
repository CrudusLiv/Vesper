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


def test_schedule_get_returns_rendered(monkeypatch):
    monkeypatch.setattr(bridge.schedule_parser, "format_for_discord", lambda: "Mon 9-10 Maths")
    assert bridge.schedule_get() == {"schedule": "Mon 9-10 Maths"}


def test_schedule_set_writes_when_none_exists(monkeypatch):
    monkeypatch.setattr(bridge.llm, "is_available", lambda: True)
    monkeypatch.setattr(bridge.schedule_parser, "parse_timetable", lambda text: ([{"day": "mon"}], "1 entry"))
    monkeypatch.setattr(bridge.schedule_parser, "has_existing_schedule", lambda: False)
    written = {}
    monkeypatch.setattr(bridge.schedule_parser, "write_schedule", lambda entries: written.update({"e": entries}))
    out = bridge.schedule_set("mon 9-10 maths", confirm=False)
    assert out == {"written": True, "summary": "1 entry"}
    assert written["e"] == [{"day": "mon"}]


def test_schedule_set_needs_confirm_when_exists(monkeypatch):
    monkeypatch.setattr(bridge.llm, "is_available", lambda: True)
    monkeypatch.setattr(bridge.schedule_parser, "parse_timetable", lambda text: ([{"day": "mon"}], "1 entry"))
    monkeypatch.setattr(bridge.schedule_parser, "has_existing_schedule", lambda: True)
    monkeypatch.setattr(bridge.schedule_parser, "write_schedule", lambda entries: pytest.fail("should not write"))
    out = bridge.schedule_set("mon 9-10 maths", confirm=False)
    assert out == {"written": False, "summary": "1 entry"}


def test_schedule_set_raises_when_llm_down(monkeypatch):
    monkeypatch.setattr(bridge.llm, "is_available", lambda: False)
    with pytest.raises(bridge.LlmError):
        bridge.schedule_set("anything", confirm=False)


def _seed_vault(tmp_path):
    notes = tmp_path / "Dynamous" / "Memory" / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    (notes / "todo.md").write_text("# todo\n", encoding="utf-8")
    (tmp_path / "Dynamous" / "Memory" / "lectures").mkdir(parents=True, exist_ok=True)


def test_vault_list_marks_dirs(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    _seed_vault(tmp_path)
    out = bridge.vault_list("")
    names = {e["name"]: e["is_dir"] for e in out["entries"]}
    assert names["notes"] is True
    assert names["lectures"] is True


def test_vault_list_files_marked_not_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    _seed_vault(tmp_path)
    out = bridge.vault_list("notes")
    assert out["entries"] == [{"name": "todo.md", "is_dir": False}]


def test_vault_delete_then_undo_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    _seed_vault(tmp_path)
    target = tmp_path / "Dynamous" / "Memory" / "notes" / "todo.md"
    deleted = bridge.vault_delete("notes/todo.md")
    assert "trash_path" in deleted
    assert not target.exists()
    msg = bridge.vault_undo()
    assert "restored" in msg["message"].lower()
    assert target.exists()


def test_vault_list_forbidden_prefix_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    _seed_vault(tmp_path)
    with pytest.raises(ValueError):
        bridge.vault_list("finance")
