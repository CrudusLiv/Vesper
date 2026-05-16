"""Section 2: Discord ping scanner."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


def _import_module():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude" / "scripts"))
    from heartbeat import discord_ping  # type: ignore
    return discord_ping


def _seed_cache(db_path: Path, rows: list[dict]) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY, channel_id TEXT, channel_name TEXT,
            guild_id TEXT, guild_name TEXT, is_dm INTEGER, author_id TEXT,
            author_name TEXT, is_self INTEGER, is_bot INTEGER,
            content TEXT, created_at REAL, fetched_at REAL
        )
    """)
    for r in rows:
        conn.execute(
            "INSERT INTO messages VALUES (:id, :channel_id, :channel_name, :guild_id, "
            ":guild_name, :is_dm, :author_id, :author_name, :is_self, :is_bot, "
            ":content, :created_at, :fetched_at)",
            r,
        )
    conn.commit()
    conn.close()


def _row(id_, content, *, is_dm=0, is_self=0, is_bot=0, author_name="alice", created_at=100.0):
    return {
        "id": id_, "channel_id": "ch", "channel_name": "general",
        "guild_id": "g", "guild_name": "Server", "is_dm": is_dm,
        "author_id": "111" if not is_self else "999",
        "author_name": author_name, "is_self": is_self, "is_bot": is_bot,
        "content": content, "created_at": created_at, "fetched_at": created_at + 1,
    }


def test_server_mention_detected(tmp_path):
    dp = _import_module()
    db = tmp_path / "cache.db"
    _seed_cache(db, [_row("1", "hey <@999> look at this", created_at=200.0)])
    state_path = tmp_path / "state.json"
    pings = dp.scan_pings(db, user_id="999", state_path=state_path, now=300.0)
    assert len(pings) == 1
    assert pings[0]["content"] == "hey <@999> look at this"


def test_dm_from_other_detected(tmp_path):
    dp = _import_module()
    db = tmp_path / "cache.db"
    _seed_cache(db, [_row("2", "hi", is_dm=1, created_at=200.0)])
    state_path = tmp_path / "state.json"
    pings = dp.scan_pings(db, user_id="999", state_path=state_path, now=300.0)
    assert len(pings) == 1


def test_self_dm_not_a_ping(tmp_path):
    dp = _import_module()
    db = tmp_path / "cache.db"
    _seed_cache(db, [_row("3", "note to self", is_dm=1, is_self=1, created_at=200.0)])
    state_path = tmp_path / "state.json"
    pings = dp.scan_pings(db, user_id="999", state_path=state_path, now=300.0)
    assert pings == []


def test_seen_messages_not_re_pinged(tmp_path):
    dp = _import_module()
    db = tmp_path / "cache.db"
    _seed_cache(db, [_row("4", "<@999>", created_at=200.0)])
    state_path = tmp_path / "state.json"
    first = dp.scan_pings(db, user_id="999", state_path=state_path, now=300.0)
    assert len(first) == 1
    second = dp.scan_pings(db, user_id="999", state_path=state_path, now=400.0)
    assert second == []


def test_state_file_trims_old_ids(tmp_path):
    """seen_message_ids older than 24h are dropped."""
    dp = _import_module()
    db = tmp_path / "cache.db"
    _seed_cache(db, [_row("5", "<@999>", created_at=1000.0)])
    state_path = tmp_path / "state.json"
    # First scan at t=1100 marks id "5" as seen.
    dp.scan_pings(db, user_id="999", state_path=state_path, now=1100.0)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "5" in [s["id"] for s in state["seen_message_ids"]]
    # Now advance more than 24h. The entry should be trimmed.
    dp.scan_pings(db, user_id="999", state_path=state_path, now=1100.0 + 25 * 3600)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["seen_message_ids"] == []


def test_format_toast_humanizes_self_mention():
    """Body should replace `<@self_id>` with `@you`, not show the raw ID."""
    dp = _import_module()
    ping = {
        "author_name": "alice", "is_dm": 0, "channel_name": "general",
        "content": "<@999> look at this",
    }
    title, body = dp.format_toast(ping, user_id="999")
    assert title == "Discord ping from alice"
    assert "<@999>" not in body
    assert "@you" in body
    assert "look at this" in body


def test_format_toast_handles_bare_mention():
    """A content of only `<@self_id>` should still produce a non-empty body."""
    dp = _import_module()
    ping = {
        "author_name": "bob", "is_dm": 0, "channel_name": "dev",
        "content": "<@999>",
    }
    _, body = dp.format_toast(ping, user_id="999")
    assert "999" not in body
    assert body.startswith("dev:")


def test_format_toast_other_mentions_become_user():
    """Mentions for other IDs collapse to `@user`."""
    dp = _import_module()
    ping = {
        "author_name": "alice", "is_dm": 0, "channel_name": "general",
        "content": "<@111> and <@999> see this",
    }
    _, body = dp.format_toast(ping, user_id="999")
    assert "<@111>" not in body
    assert "@user" in body
    assert "@you" in body
