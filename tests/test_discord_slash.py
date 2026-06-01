"""Unit tests for discord_bot module-level helpers (no live Discord)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


def _bot():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude"))
    sys.path.insert(0, str(repo_root / ".claude" / "scripts"))
    from chat import discord_bot
    return discord_bot


def test_build_help_text_lists_every_command():
    db = _bot()
    text = db.build_help_text()
    assert text.startswith(db.HELP_TITLE)
    for name in ("/schedule", "/note", "/finance", "/totals", "/list", "/delete", "/undo", "/help"):
        assert name in text


def test_slash_text_prefers_explicit_text():
    db = _bot()
    assert db._slash_text("✅", "logged RM5.00") == "logged RM5.00"


def test_slash_text_falls_back_to_reaction():
    db = _bot()
    assert db._slash_text("✅", None) == "Done."
    assert db._slash_text("❌", None) == "Failed."
    assert db._slash_text("❓", None) == "Unrecognized."
    assert db._slash_text(None, None) == "Done."


class _FakeSchedule:
    """Stand-in for the schedule_parser module."""
    def __init__(self, existing=False, pending=None):
        self._existing = existing
        self._pending = pending
        self.written = None
        self.pending_written = None
        self.cleared = False

    def parse_timetable(self, raw):
        if raw == "BOOM":
            raise ValueError("bad")
        return ([{"day": "Mon"}], f"parsed: {raw}")

    def has_existing_schedule(self):
        return self._existing

    def write_schedule(self, entries):
        self.written = entries

    def write_pending(self, entries):
        self.pending_written = entries

    def read_pending(self):
        return self._pending

    def clear_pending(self):
        self.cleared = True


def test_run_schedule_fresh_write(monkeypatch):
    db = _bot()
    fake = _FakeSchedule(existing=False)
    monkeypatch.setattr(db, "schedule_parser", fake)
    reaction, text = db.run_schedule("Mon 9am Math", confirm=False)
    assert reaction == "✅"
    assert text == "parsed: Mon 9am Math"
    assert fake.written == [{"day": "Mon"}]


def test_run_schedule_existing_asks_confirm(monkeypatch):
    db = _bot()
    fake = _FakeSchedule(existing=True)
    monkeypatch.setattr(db, "schedule_parser", fake)
    reaction, text = db.run_schedule("Mon 9am Math", confirm=False)
    assert reaction == "❓"
    assert "confirm" in text.lower()
    assert fake.pending_written == [{"day": "Mon"}]
    assert fake.written is None  # not written yet


def test_run_schedule_confirm_writes_pending(monkeypatch):
    db = _bot()
    fake = _FakeSchedule(pending=[{"day": "Tue"}])
    monkeypatch.setattr(db, "schedule_parser", fake)
    reaction, text = db.run_schedule("", confirm=True)
    assert reaction == "✅"
    assert "updated" in text.lower()
    assert fake.written == [{"day": "Tue"}]
    assert fake.cleared is True


def test_run_schedule_confirm_nothing_pending(monkeypatch):
    db = _bot()
    fake = _FakeSchedule(pending=None)
    monkeypatch.setattr(db, "schedule_parser", fake)
    reaction, text = db.run_schedule("", confirm=True)
    assert reaction == "❓"
    assert "nothing pending" in text.lower()


def test_run_schedule_parse_error(monkeypatch):
    db = _bot()
    fake = _FakeSchedule(existing=False)
    monkeypatch.setattr(db, "schedule_parser", fake)
    reaction, text = db.run_schedule("BOOM", confirm=False)
    assert reaction == "❌"
    assert "failed to parse" in text.lower()


def test_run_note_not_a_note(monkeypatch):
    db = _bot()
    monkeypatch.setattr(db.discord_dm_capture, "classify", lambda c: "chit-chat")
    reaction, text = db.run_note("just chatting")
    assert reaction is None
    assert text is None


def test_run_note_success(monkeypatch):
    db = _bot()
    monkeypatch.setattr(db.discord_dm_capture, "classify", lambda c: "note")
    monkeypatch.setattr(db.discord_dm_capture, "_append_note", lambda target, dt, raw: "the body")
    reaction, text = db.run_note("note: the body")
    assert reaction == "✅"
    assert text is None


def test_run_note_empty_after_strip(monkeypatch):
    db = _bot()
    monkeypatch.setattr(db.discord_dm_capture, "classify", lambda c: "note")
    monkeypatch.setattr(db.discord_dm_capture, "_append_note", lambda target, dt, raw: "")
    reaction, text = db.run_note("note:")
    assert reaction == "❌"
    assert "empty" in text.lower()


def test_run_note_error(monkeypatch):
    db = _bot()
    monkeypatch.setattr(db.discord_dm_capture, "classify", lambda c: "note")

    def _boom(target, dt, raw):
        raise OSError("disk")

    monkeypatch.setattr(db.discord_dm_capture, "_append_note", _boom)
    reaction, text = db.run_note("note: x")
    assert reaction == "❌"
    assert "error" in text.lower()
