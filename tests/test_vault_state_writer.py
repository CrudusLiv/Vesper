"""Tests for heartbeat vault state writer."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest

# Add .claude/scripts/ to path (same pattern as other tests in this repo)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))

# Snapshot fixtures reused across tests
SNAP_FULL = {
    "timestamp": 1747656000.0,
    "discord": {
        "new_count": 2,
        "items": [
            {"id": "1", "is_dm": True, "author": "TestUser", "channel": "DM", "content": "hello"},
            {"id": "2", "is_dm": False, "author": "Other", "channel": "general", "content": "server"},
        ],
    },
    "github": {"push_count": 3, "items": []},
    "inbox": {"count": 0, "files": []},
}

SNAP_ERROR = {
    "timestamp": 1747656000.0,
    "discord": {"error": "no token"},
    "github": {"error": "no token"},
}


def test_write_discord_dm_only(tmp_vault):
    from heartbeat import vault_state_writer
    vault_state_writer.write_discord(SNAP_FULL)

    out = tmp_vault / "state" / "discord-recent.md"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "unread_dms: 1" in text
    assert "TestUser" in text
    assert "Other" not in text   # server message must be excluded


def test_write_discord_skips_on_error(tmp_vault):
    from heartbeat import vault_state_writer
    vault_state_writer.write_discord(SNAP_ERROR)

    assert not (tmp_vault / "state" / "discord-recent.md").exists()


def test_write_github_counts(tmp_vault):
    from heartbeat import vault_state_writer
    vault_state_writer.write_github(SNAP_FULL)

    out = tmp_vault / "state" / "github-counts.md"
    assert out.exists()
    assert "prs_open: 3" in out.read_text(encoding="utf-8")


def test_write_github_skips_on_error(tmp_vault):
    from heartbeat import vault_state_writer
    vault_state_writer.write_github(SNAP_ERROR)

    assert not (tmp_vault / "state" / "github-counts.md").exists()


def test_write_heartbeat_state_always_writes(tmp_vault):
    from heartbeat import vault_state_writer
    vault_state_writer.write_heartbeat_state(SNAP_ERROR)

    out = tmp_vault / "state" / "heartbeat-state.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["timestamp"] == SNAP_ERROR["timestamp"]


def test_write_all_creates_all_files(tmp_vault):
    from heartbeat import vault_state_writer
    vault_state_writer.write_all(SNAP_FULL)

    state = tmp_vault / "state"
    assert (state / "discord-recent.md").exists()
    assert (state / "github-counts.md").exists()
    assert (state / "heartbeat-state.json").exists()
