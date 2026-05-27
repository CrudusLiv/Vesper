"""Discord ping scanner. Reads the discord_cache.db (populated by the
long-running Phase 4 bot) and returns new pings since the last tick.

A "ping" is a server-channel message authored by someone other than the user
where any of the following holds:
- content contains <@USER_ID> (explicit mention)
- referenced_author_id == USER_ID (someone replied to one of the user's messages,
  even with the "ping on reply" toggle disabled)

State file (.claude/data/discord_last_tick.json) tracks:
- last_tick: ISO timestamp of last successful scan
- seen_message_ids: list of {id, t} (t = created_at) so we don't re-ping on overlap.
  Trimmed to last 24h on every call.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

KL = timezone(timedelta(hours=8))
SEEN_TTL_SEC = 24 * 3600
_MENTION_RE = re.compile(r"<@!?(\d+)>")


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
        # Tolerate older caches that haven't been migrated yet — if the reply
        # columns are missing, fall back to the mention-only scan.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
        has_reply_cols = "referenced_author_id" in cols
        if has_reply_cols:
            cursor = conn.execute(
                """
                SELECT id, channel_name, is_dm, author_id, author_name, content,
                       created_at, referenced_author_id
                FROM messages
                WHERE created_at >= ?
                  AND is_bot = 0
                  AND is_dm = 0
                  AND author_id != ?
                  AND (content LIKE ? OR referenced_author_id = ?)
                ORDER BY created_at ASC
                """,
                (cutoff, user_id, f"%{mention_token}%", user_id),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, channel_name, is_dm, author_id, author_name, content, created_at
                FROM messages
                WHERE created_at >= ?
                  AND is_bot = 0
                  AND is_dm = 0
                  AND content LIKE ?
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


def _humanize_mentions(content: str, user_id: Optional[str]) -> str:
    """Replace `<@id>` tokens with readable text — the recipient becomes `@you`,
    other IDs collapse to `@user` since we don't have a name mapping here."""
    def repl(m: re.Match) -> str:
        return "@you" if user_id and m.group(1) == user_id else "@user"
    return _MENTION_RE.sub(repl, content)


def format_toast(ping: dict, *, user_id: Optional[str] = None) -> tuple[str, str]:
    """Render (title, body) for winotify."""
    sender = ping.get("author_name") or "unknown"
    channel = "DM" if ping.get("is_dm") else (ping.get("channel_name") or "channel")
    content = (ping.get("content") or "").strip().replace("\n", " ")
    has_mention = bool(user_id) and (
        f"<@{user_id}>" in content or f"<@!{user_id}>" in content
    )
    is_reply_to_user = bool(user_id) and ping.get("referenced_author_id") == user_id
    if has_mention:
        title = f"Discord ping from {sender}"
        fallback = "(mention)"
    elif is_reply_to_user:
        title = f"Discord reply from {sender}"
        fallback = "(reply)"
    else:
        title = f"Discord message from {sender}"
        fallback = ""
    cleaned = _humanize_mentions(content, user_id).strip()
    body = f"{channel}: {cleaned[:120]}" if cleaned else f"{channel}: {fallback}".rstrip(": ")
    return title, body
