"""Embed builder used by heartbeat.notify for bot DMs."""
from __future__ import annotations

import sys
from pathlib import Path


def _import_notify():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude" / "scripts"))
    from heartbeat import notify  # type: ignore
    return notify


FIXED_TS = 1779_858_000.0
FIXED_WHEN = "13:00 KL"


def test_build_dm_embed_high_priority_orange_with_warn():
    n = _import_notify()
    em = n._build_dm_embed(
        title="Discord ping from alice",
        body="#general: hey",
        priority="high",
        ts=FIXED_TS,
    )
    assert em["color"] == 0xE67E22
    assert em["title"] == "⚠ Discord ping from alice"
    assert em["description"] == "#general: hey"
    assert em["author"] == {"name": "Vesper"}
    assert em["footer"]["text"] == f"{FIXED_WHEN}  ·  high"


def test_build_dm_embed_urgent_red_with_siren():
    n = _import_notify()
    em = n._build_dm_embed("t", "b", "urgent", ts=FIXED_TS)
    assert em["color"] == 0xE74C3C
    assert em["title"].startswith("\U0001F6A8 ")


def test_build_dm_embed_normal_blue_no_emoji():
    n = _import_notify()
    em = n._build_dm_embed("t", "b", "normal", ts=FIXED_TS)
    assert em["color"] == 0x3498DB
    assert em["title"] == "t"


def test_build_dm_embed_low_slate_no_emoji():
    n = _import_notify()
    em = n._build_dm_embed("t", "b", "low", ts=FIXED_TS)
    assert em["color"] == 0x95A5A6
    assert em["title"] == "t"


def test_build_dm_embed_unknown_priority_falls_back_to_normal():
    n = _import_notify()
    em = n._build_dm_embed("t", "b", "weird", ts=FIXED_TS)
    assert em["color"] == 0x3498DB


def test_build_dm_embed_empty_body_omits_description():
    n = _import_notify()
    em = n._build_dm_embed("t", "", "normal", ts=FIXED_TS)
    # Description is None or absent so Discord renders only the title.
    assert em.get("description") in (None, "")
