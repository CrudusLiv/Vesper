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
