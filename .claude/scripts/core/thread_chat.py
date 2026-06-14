"""Slice 7: in-thread chat carve-out.

Watches discord_cache.db for messages CrudusLiv posts inside forum threads
that the agent opened (Slice 3 deadlines, Slice 4 lectures). For each new
message: pull the last N messages in the thread for context, call the LLM
with the persona+kind-specific system prompt, post the response back via
the same channel's webhook with `thread_id=...`.

Bot identity stays read-only. Outbound goes through the channel webhook,
which is the same shape used by Slice 3/4 starter posts.

State: shares `seen_message_ids` with discord_ping.py and
discord_dm_capture.py (same JSON file at .claude/data/discord_last_tick.json,
same 24h TTL) so a row routed here can't be reprocessed by another scanner."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])

sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
from core import dashboard, dashboard_state, llm, thread_chat_prompt  # noqa: E402

SEEN_TTL_SEC = 24 * 3600
CONTEXT_DEPTH = 20  # last N messages in the thread to feed the LLM


def known_threads() -> dict[str, dict]:
    """Map thread_id -> { kind, ...identifiers }.

    Read fresh each call so threads opened mid-tick by Slice 3/4 become
    chatable immediately. Returns empty when no threads are tracked."""
    state = dashboard_state.load()
    out: dict[str, dict] = {}
    for key, rec in (state.get("deadlines") or {}).items():
        tid = rec.get("thread_id")
        if tid:
            out[str(tid)] = {"kind": "deadline", "key": key}
    for path, rec in (state.get("lectures") or {}).items():
        tid = rec.get("thread_id")
        if tid:
            out[str(tid)] = {"kind": "lecture", "path": path}
    return out


def scan_and_reply(
    db_path: Path,
    *,
    user_id: str,
    state_path: Path,
    now: Optional[float] = None,
) -> int:
    """Find new owner messages in agent-owned threads, reply once each.

    Returns the number of replies actually posted. A failure in LLM or
    dashboard post still marks the source message seen so subsequent ticks
    don't loop on the same broken row.

    Idempotency: a message is seen iff its id appears in
    state['seen_message_ids']. The shared scanner state file is also used
    by discord_ping and discord_dm_capture; collisions are fine since the
    queries select disjoint subsets (server pings, self-DMs, thread chat)."""
    if now is None:
        now = time.time()

    threads = known_threads()
    if not threads or not db_path.exists():
        return 0

    state = _load_state(state_path)
    seen = {s["id"] for s in state.get("seen_message_ids") or []}

    placeholders = ",".join(["?"] * len(threads))
    cutoff = now - SEEN_TTL_SEC
    sql = f"""
        SELECT id, channel_id, content, author_id, author_name, created_at
        FROM messages
        WHERE channel_id IN ({placeholders})
          AND is_dm = 0
          AND is_self = 0
          AND is_bot = 0
          AND author_id = ?
          AND created_at >= ?
        ORDER BY created_at ASC
    """
    params: list = list(threads.keys()) + [user_id, cutoff]

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

    posted = 0
    for row in rows:
        if row["id"] in seen:
            continue
        thread_meta = threads.get(str(row["channel_id"]))
        if not thread_meta:
            # Race: the thread was forgotten between read and now. Mark
            # the row seen anyway so we don't keep scanning it.
            _mark_seen(state, row)
            continue

        reply_text = ""
        try:
            reply_text = _generate_reply(row, thread_meta, db_path)
        except Exception as exc:
            print(f"thread_chat: LLM failed for msg {row['id']}: {exc}", file=sys.stderr)

        if reply_text:
            kind = "deadline_reply" if thread_meta["kind"] == "deadline" else "lecture_reply"
            channel_id = row.get("channel_id") or ""
            if not str(channel_id).isdigit():
                print(f"thread_chat: skipping msg {row['id']} — bad channel_id {channel_id!r}", file=sys.stderr)
                _mark_seen(state, row)
                continue
            try:
                resp = dashboard.notify(
                    kind,
                    {"text": reply_text},
                    thread_id=str(channel_id),
                )
                if resp is not None:
                    posted += 1
            except Exception as exc:
                print(f"thread_chat: post failed for msg {row['id']}: {exc}", file=sys.stderr)

        _mark_seen(state, row)

    _save_state(state_path, state, now)
    return posted


def _generate_reply(msg: dict, thread_meta: dict, db_path: Path) -> str:
    """Build prompt + call LLM. Returns the response text or empty string
    on any failure (caller still marks the message seen so we don't loop)."""
    context = _thread_context(db_path, str(msg["channel_id"]))
    # Drop the row that triggered this call from context so the LLM
    # doesn't see it twice. _thread_context already orders oldest first,
    # so the latest is typically at the end -- but skip by id to be safe.
    context = [c for c in context if str(c.get("id")) != str(msg["id"])]
    system_prompt = thread_chat_prompt.system_prompt(thread_meta)
    user_prompt = thread_chat_prompt.user_prompt(msg, context)
    return (llm.call(user_prompt, system_prompt=system_prompt, model="haiku", task="thread_chat", timeout=60) or "").strip()


def _thread_context(db_path: Path, thread_id: str, limit: int = CONTEXT_DEPTH) -> list[dict]:
    """Last `limit` messages in the thread, returned oldest first."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = list(conn.execute(
            """SELECT id, author_name, content, created_at, is_self
               FROM messages
               WHERE channel_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (thread_id, limit),
        ).fetchall())
    finally:
        conn.close()
    rows.reverse()
    return [dict(r) for r in rows]


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {"last_tick": None, "seen_message_ids": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"last_tick": None, "seen_message_ids": []}


def _save_state(path: Path, state: dict, now: float) -> None:
    from datetime import datetime, timedelta, timezone
    KL = timezone(timedelta(hours=8))
    state["last_tick"] = datetime.fromtimestamp(now, tz=KL).isoformat()
    state["seen_message_ids"] = [
        s for s in (state.get("seen_message_ids") or [])
        if s.get("t", 0) >= now - SEEN_TTL_SEC
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _mark_seen(state: dict, row: dict) -> None:
    state.setdefault("seen_message_ids", []).append({
        "id": row["id"],
        "t": row.get("created_at") or time.time(),
    })
