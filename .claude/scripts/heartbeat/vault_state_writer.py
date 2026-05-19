"""Write heartbeat snapshots to vault-readable files in Dynamous/Memory/state/.

Dataview can only read files inside the Obsidian vault. This module bridges
the gap between .claude/data/state/ and the vault on each heartbeat tick."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


def _vault_state_dir() -> Path:
    base = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
    return base / "Dynamous" / "Memory" / "state"


def _iso(ts: float | None = None) -> str:
    if ts is None:
        ts = time.time()
    t = datetime.fromtimestamp(ts, tz=timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S")


def write_discord(snapshot: dict) -> None:
    discord = snapshot.get("discord") or {}
    if "error" in discord:
        return

    items = discord.get("items") or []
    dm_items = [i for i in items if i.get("is_dm")]
    unread = len(dm_items)

    log_lines = []
    for item in dm_items[:3]:
        author = item.get("author") or "?"
        content = (item.get("content") or "")[:200]
        log_lines.append(f"**{author}** — {content}")

    body = "\n".join(log_lines) if log_lines else "_No recent DMs_"
    content = (
        f"---\n"
        f"updated: {_iso(snapshot.get('timestamp'))}\n"
        f"unread_dms: {unread}\n"
        f"---\n"
        f"{body}\n"
    )

    d = _vault_state_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "discord-recent.md").write_text(content, encoding="utf-8")


def write_github(snapshot: dict) -> None:
    github = snapshot.get("github") or {}
    if "error" in github:
        return

    push_count = github.get("push_count", 0)
    content = (
        f"---\n"
        f"updated: {_iso(snapshot.get('timestamp'))}\n"
        f"prs_open: {push_count}\n"
        f"notifications: 0\n"
        f"---\n"
    )

    d = _vault_state_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "github-counts.md").write_text(content, encoding="utf-8")


def write_heartbeat_state(snapshot: dict) -> None:
    d = _vault_state_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "heartbeat-state.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_all(snapshot: dict) -> None:
    write_discord(snapshot)
    write_github(snapshot)
    write_heartbeat_state(snapshot)
