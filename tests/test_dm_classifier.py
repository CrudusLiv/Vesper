"""Section 3: rule-based DM classifier."""
from __future__ import annotations

import sys
from pathlib import Path


def _import_module():
    import importlib
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude" / "scripts"))
    from heartbeat import discord_dm_capture  # type: ignore
    importlib.reload(discord_dm_capture)
    return discord_dm_capture


def test_currency_symbol_routes_to_finance():
    m = _import_module()
    assert m.classify_rule_based("RM 25 for lunch") == "finance"
    assert m.classify_rule_based("$12.50 coffee") == "finance"
    assert m.classify_rule_based("usd 100 received") == "finance"


def test_money_keyword_routes_to_finance():
    m = _import_module()
    assert m.classify_rule_based("spent on cab today") == "finance"
    assert m.classify_rule_based("paid the rent") == "finance"


def test_chit_chat_default():
    """Anything without an explicit marker falls through to chit-chat."""
    m = _import_module()
    assert m.classify_rule_based("lol") == "chit-chat"
    assert m.classify_rule_based("hey what's up") == "chit-chat"
    assert m.classify_rule_based("idea: try using FastEmbed") == "chit-chat"
    assert m.classify_rule_based("reminder: ask supervisor about scope") == "chit-chat"
    assert m.classify_rule_based("cost") == "chit-chat"


def test_note_prefix_routes_to_note():
    """Only messages with explicit 'note' / 'note to self' prefix are kept."""
    m = _import_module()
    assert m.classify_rule_based("note: pick up groceries") == "note"
    assert m.classify_rule_based("Note to self: revisit FastEmbed perf") == "note"
    assert m.classify_rule_based("note - swap to discord webhooks") == "note"
    assert m.classify_rule_based("NOTE try the new approach") == "note"


def test_note_prefix_requires_content():
    """The 'note' marker alone, without trailing content, is chit-chat."""
    m = _import_module()
    assert m.classify_rule_based("note") == "chit-chat"
    assert m.classify_rule_based("note:") == "chit-chat"


def test_finance_beats_note_prefix():
    """If the message has a money signal, finance wins even with 'note' prefix."""
    m = _import_module()
    assert m.classify_rule_based("note: RM 25 for lunch") == "finance"


def test_routing_finance_appends_to_monthly_file(tmp_vault):
    m = _import_module()
    msg = {"id": "1", "content": "RM 25 lunch", "created_at": 1700000000.0}
    m.route(msg, label="finance")
    # 2023-11-14 21:33 KL based on 1700000000
    expected = tmp_vault / "finance" / "2023-11.md"
    assert expected.exists()
    body = expected.read_text(encoding="utf-8")
    assert "## Captured" in body
    assert "RM 25 lunch" in body


def test_routing_note_appends_to_rolling_notes_file(tmp_vault):
    m = _import_module()
    msg = {"id": "2", "content": "note: try FastEmbed", "created_at": 1700000000.0}
    m.route(msg, label="note")
    expected = tmp_vault / "notes" / "NOTES.md"
    assert expected.exists()
    body = expected.read_text(encoding="utf-8")
    assert "try FastEmbed" in body
    assert "2023-11-15" in body  # date prefix on the bullet


def test_routing_chitchat_discards(tmp_vault):
    m = _import_module()
    msg = {"id": "3", "content": "lol", "created_at": 1700000000.0}
    m.route(msg, label="chit-chat")
    # No daily file should have been written for this label.
    expected = tmp_vault / "daily" / "2023-11-15.md"
    assert not expected.exists()


def _seed_self_dms(db_path, rows):
    import sqlite3
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
            "INSERT INTO messages VALUES (:id, :channel_id, :channel_name, "
            ":guild_id, :guild_name, :is_dm, :author_id, :author_name, "
            ":is_self, :is_bot, :content, :created_at, :fetched_at)",
            r,
        )
    conn.commit()
    conn.close()


def _self_row(id_, content, created_at):
    return {
        "id": id_, "channel_id": "ch1", "channel_name": "DM",
        "guild_id": None, "guild_name": None, "is_dm": 1,
        "author_id": "999", "author_name": "me", "is_self": 1, "is_bot": 0,
        "content": content, "created_at": created_at, "fetched_at": created_at + 1,
    }


def test_scan_and_route_ignores_messages_past_24h(tmp_vault):
    """A self-DM older than 24h must NOT be processed, even if seen-state is
    empty (this is what caused the 8x duplication: each tick reaped the seen
    entry, scan_and_route had no SQL cutoff, so it re-imported every time)."""
    m = _import_module()
    tmp_path = tmp_vault.parent.parent  # tmp_vault is tmp_path/Dynamous/Memory
    db = tmp_path / "cache.db"
    now = 1_000_000.0
    _seed_self_dms(db, [
        _self_row("old", "note: ancient idea", now - 25 * 3600),
        _self_row("new", "note: fresh idea", now - 300),
    ])
    state_path = tmp_path / "state.json"
    counts = m.scan_and_route(db, user_id="999", state_path=state_path, now=now)
    assert counts == {"note": 1, "finance": 0, "chit-chat": 0}


def test_scan_and_route_skips_already_seen(tmp_vault):
    """A self-DM already in seen_message_ids must not be re-processed even
    when it's inside the 24h window."""
    import json
    m = _import_module()
    tmp_path = tmp_vault.parent.parent
    db = tmp_path / "cache.db"
    now = 1_000_000.0
    _seed_self_dms(db, [_self_row("a", "note: dedupe me", now - 100)])
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"last_tick": None, "seen_message_ids": [{"id": "a", "t": now - 100}]}),
        encoding="utf-8",
    )
    counts = m.scan_and_route(db, user_id="999", state_path=state_path, now=now)
    assert counts == {"note": 0, "finance": 0, "chit-chat": 0}
