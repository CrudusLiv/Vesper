"""Discord embed formatters in heartbeat.dashboard.

All tests pass an explicit `ts` into payloads so the footer time is
deterministic. Discord rate-limited paths are not exercised; we only
assert on the dict shape returned by format_embed."""
from __future__ import annotations

import sys
from pathlib import Path


def _import_dashboard():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude" / "scripts"))
    from heartbeat import dashboard  # type: ignore
    return dashboard


# A fixed unix timestamp inside KL (2026-05-27 13:00 KL == 05:00 UTC).
FIXED_TS = 1779_858_000.0
FIXED_WHEN = "13:00 KL"


def test_obsidian_url_plain_path():
    d = _import_dashboard()
    assert d._obsidian_url("DEADLINES.md") == (
        "obsidian://open?vault=Memory&file=DEADLINES.md"
    )


def test_obsidian_url_nested_path_keeps_slashes():
    d = _import_dashboard()
    assert d._obsidian_url("daily/2026-05-27.md") == (
        "obsidian://open?vault=Memory&file=daily/2026-05-27.md"
    )


def test_obsidian_url_encodes_spaces_and_specials():
    d = _import_dashboard()
    # Spaces -> %20, ampersand -> %26; slashes stay literal.
    result = d._obsidian_url("lectures/CS 101/Intro & basics.md")
    assert result == (
        "obsidian://open?vault=Memory&file=lectures/CS%20101/Intro%20%26%20basics.md"
    )


def test_vesper_embed_minimal():
    d = _import_dashboard()
    em = d._vesper_embed(
        title="hello",
        description="world",
        color=0x123456,
        channel_label="Heartbeat",
        ts=FIXED_TS,
    )
    assert em["author"] == {"name": "Vesper · Heartbeat"}
    assert em["title"] == "hello"
    assert em["description"] == "world"
    assert em["color"] == 0x123456
    assert em["fields"] == []
    assert em["footer"] == {"text": FIXED_WHEN}
    assert "url" not in em  # No vault_path / url -> no clickable title.


def test_vesper_embed_with_vault_path():
    d = _import_dashboard()
    em = d._vesper_embed(
        title="t",
        description="d",
        color=0,
        channel_label="Deadlines",
        vault_path="DEADLINES.md",
        ts=FIXED_TS,
    )
    assert em["url"] == "obsidian://open?vault=Memory&file=DEADLINES.md"
    assert em["footer"]["text"] == f"{FIXED_WHEN}  ·  \U0001F4C2 DEADLINES.md"


def test_vesper_embed_explicit_url_overrides_vault_path():
    d = _import_dashboard()
    em = d._vesper_embed(
        title="t", description="", color=0, channel_label="PRs",
        vault_path="ignored.md",
        url="https://github.com/o/r/pull/42",
        ts=FIXED_TS,
    )
    # Explicit url wins; footer falls back to bare time (no vault link).
    assert em["url"] == "https://github.com/o/r/pull/42"
    assert em["footer"]["text"] == FIXED_WHEN


def test_vesper_embed_fields_preserved():
    d = _import_dashboard()
    fields = [{"name": "Status", "value": "OK", "inline": True}]
    em = d._vesper_embed(
        title="t", description="", color=0, channel_label="X",
        fields=fields, ts=FIXED_TS,
    )
    assert em["fields"] == fields


def test_vesper_embed_defaults_ts_to_now(monkeypatch):
    """When ts is None, _vesper_embed uses datetime.now(KL)."""
    d = _import_dashboard()
    em = d._vesper_embed(title="t", description="", color=0, channel_label="X")
    # Just assert the footer has the KL suffix; exact minute is racy.
    assert em["footer"]["text"].endswith(" KL")


def test_heartbeat_tick_green_when_no_failing():
    d = _import_dashboard()
    body = d.format_embed("heartbeat_tick", {
        "status": "ok", "failing": [], "tick_ts": FIXED_TS,
    })
    assert "content" not in body
    em = body["embeds"][0]
    assert em["title"] == "All systems green"
    assert em["description"] == "all integrations ok"
    assert em["color"] == 0x2ECC71
    assert em["author"]["name"] == "Vesper · Heartbeat"
    assert em["footer"]["text"] == FIXED_WHEN


def test_heartbeat_tick_degraded_yellow():
    d = _import_dashboard()
    body = d.format_embed("heartbeat_tick", {
        "status": "degraded", "failing": ["gmail"], "tick_ts": FIXED_TS,
    })
    em = body["embeds"][0]
    assert em["color"] == 0xF1C40F
    assert em["title"] == "\U0001F534 Degraded — gmail"
    assert em["description"] == "1 check(s) failed · other integrations ok"


def test_heartbeat_tick_red_with_multiple_failing():
    d = _import_dashboard()
    body = d.format_embed("heartbeat_tick", {
        "status": "red", "failing": ["gmail", "gcal"], "tick_ts": FIXED_TS,
    })
    em = body["embeds"][0]
    assert em["color"] == 0xE74C3C
    assert em["title"] == "\U0001F534 Degraded — gmail, gcal"
    assert em["description"] == "2 check(s) failed · other integrations ok"
