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


def test_routing_note_appends_to_daily(tmp_vault):
    m = _import_module()
    msg = {"id": "2", "content": "note: try FastEmbed", "created_at": 1700000000.0}
    m.route(msg, label="note")
    expected = tmp_vault / "daily" / "2023-11-15.md"
    assert expected.exists()
    body = expected.read_text(encoding="utf-8")
    assert "## Captured" in body
    assert "note: try FastEmbed" in body


def test_routing_chitchat_discards(tmp_vault):
    m = _import_module()
    msg = {"id": "3", "content": "lol", "created_at": 1700000000.0}
    m.route(msg, label="chit-chat")
    # No daily file should have been written for this label.
    expected = tmp_vault / "daily" / "2023-11-15.md"
    assert not expected.exists()
