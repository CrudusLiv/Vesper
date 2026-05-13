"""Discord ping scanner. Reads the discord_cache.db (populated by the
long-running Phase 4 bot) and returns new pings since the last tick.

A "ping" is:
- A message in any channel where content contains <@USER_ID>, OR
- A DM from a user other than CrudusLiv.

State file (.claude/data/discord_last_tick.json) tracks:
- last_tick: ISO timestamp of last successful scan
- seen_message_ids: list of {id, t} (t = created_at) so we don't re-ping on overlap.
  Trimmed to last 24h on every call.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

KL = timezone(timedelta(hours=8))
SEEN_TTL_SEC = 24 * 3600


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {"last_tick": None, "seen_message_ids": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"last_tick": None, "seen_message_ids": []}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _trim_seen(seen: list[dict], now: float) -> list[dict]:
    return [s for s in seen if s.get("t", 0) >= now - SEEN_TTL_SEC]


def scan_pings(
    db_path: Path,
    *,
    user_id: str,
    state_path: Path,
    now: Optional[float] = None,
) -> list[dict]:
    """Return list of new ping rows since last tick, mark them seen, persist state."""
    if now is None:
        now = time.time()
    state = _load_state(state_path)
    state["seen_message_ids"] = _trim_seen(state.get("seen_message_ids") or [], now)
    seen_ids = {s["id"] for s in state["seen_message_ids"]}

    if not db_path.exists():
        _save_state(state_path, state)
        return []

    mention_token = f"<@{user_id}>"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cutoff = now - SEEN_TTL_SEC
    try:
        cursor = conn.execute(
            """
            SELECT id, channel_name, is_dm, author_id, author_name, content, created_at
            FROM messages
            WHERE created_at >= ?
              AND (
                (is_dm = 1 AND is_self = 0)
                OR (is_dm = 0 AND content LIKE ?)
            )
            ORDER BY created_at ASC
            """,
            (cutoff, f"%{mention_token}%"),
        )
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    new_pings: list[dict] = []
    for r in rows:
        if r["id"] in seen_ids:
            continue
        new_pings.append(r)
        state["seen_message_ids"].append({"id": r["id"], "t": r["created_at"]})

    state["last_tick"] = datetime.fromtimestamp(now, tz=KL).isoformat()
    _save_state(state_path, state)
    return new_pings


def format_toast(ping: dict) -> tuple[str, str]:
    """Render (title, body) for winotify."""
    sender = ping.get("author_name") or "unknown"
    channel = "DM" if ping.get("is_dm") else (ping.get("channel_name") or "channel")
    title = f"Discord ping from {sender}"
    content = (ping.get("content") or "").strip().replace("\n", " ")
    body = f"{channel}: {content[:120]}"
    return title, body
