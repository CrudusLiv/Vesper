"""Tests for the headless cache-only discord_bot."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace


def _bot():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude"))
    sys.path.insert(0, str(repo_root / ".claude" / "scripts"))
    from chat import discord_bot
    return discord_bot


def test_on_message_calls_store_message(monkeypatch):
    """on_message must call _store_message with the message and the cached self-id."""
    db = _bot()
    stored = []
    monkeypatch.setattr(db.discord_int, "_store_message",
                        lambda m, s: stored.append((m, s)))
    db._self_id["id"] = "bot123"
    msg = SimpleNamespace(guild=None, author=SimpleNamespace(id="111"), content="hi")
    asyncio.run(db.on_message(msg))
    assert len(stored) == 1
    assert stored[0] == (msg, "bot123")


def test_on_message_swallows_store_exception(monkeypatch):
    """A _store_message failure must not propagate — the bot must not crash."""
    db = _bot()

    def _boom(m, s):
        raise RuntimeError("db locked")

    monkeypatch.setattr(db.discord_int, "_store_message", _boom)
    msg = SimpleNamespace(guild=None, author=SimpleNamespace(id="111"), content="x")
    asyncio.run(db.on_message(msg))  # must not raise
