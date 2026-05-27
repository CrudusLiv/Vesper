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
