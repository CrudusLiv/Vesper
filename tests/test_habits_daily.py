"""Tests for habits.auto_check daily-log wiring."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

from heartbeat import habits
import vault.daily as daily_mod

HABITS_TEMPLATE = (
    "- [ ] **Lecture engagement**\n"
    "- [ ] **Project progress**\n"
    "- [ ] **Research / learning**\n"
    "- [ ] **Personal goals**\n"
)


@pytest.fixture(autouse=True)
def _patch_habits_paths(tmp_vault, monkeypatch):
    """Redirect module-level path constants so tests never touch the real vault."""
    monkeypatch.setattr(habits, "HABITS", tmp_vault / "HABITS.md")
    monkeypatch.setattr(habits, "LECTURES", tmp_vault / "lectures")


def test_auto_check_writes_habit_line_for_newly_ticked(tmp_vault, monkeypatch):
    (tmp_vault / "HABITS.md").write_text(HABITS_TEMPLATE, encoding="utf-8")
    (tmp_vault / "lectures" / "CS101").mkdir(parents=True, exist_ok=True)
    (tmp_vault / "lectures" / "CS101" / "note.md").write_text("x", encoding="utf-8")

    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))

    newly = habits.auto_check({})
    assert "Lecture engagement" in newly
    assert "Habit: Lecture engagement" in written


def test_auto_check_no_write_when_nothing_ticked(tmp_vault, monkeypatch):
    (tmp_vault / "HABITS.md").write_text(HABITS_TEMPLATE, encoding="utf-8")

    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))

    newly = habits.auto_check({})
    assert newly == []
    assert written == []


def test_auto_check_no_write_when_already_checked(tmp_vault, monkeypatch):
    already = HABITS_TEMPLATE.replace(
        "- [ ] **Lecture engagement**", "- [x] **Lecture engagement**"
    )
    (tmp_vault / "HABITS.md").write_text(already, encoding="utf-8")
    (tmp_vault / "lectures" / "CS101").mkdir(parents=True, exist_ok=True)
    (tmp_vault / "lectures" / "CS101" / "note.md").write_text("x", encoding="utf-8")

    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))

    newly = habits.auto_check({})
    assert newly == []
    assert written == []
