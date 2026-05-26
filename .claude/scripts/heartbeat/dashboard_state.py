"""Idempotency state for the Discord dashboard layer.

Sidecar JSON at .claude/data/discord_dashboard_state.json. Each top-level
key is a namespace owned by one slice:

  heartbeat   -- Slice 1 (#heartbeat throttle bookkeeping)
  deadlines   -- Slice 3 (per-row threshold tracking + forum thread ids)
  next3       -- Slice 3 ("Next 3 deadlines" edited-in-place forum thread)
  lectures    -- Slice 4 (per-note thread ids)
  pr_activity -- Slice 5 (per-PR last-event-id)

Each slice should only read/write its own namespace. load() seeds missing
keys from DEFAULT_STATE so forward-compatible adds don't break old state
files."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
STATE_FILE = PROJECT_DIR / ".claude" / "data" / "discord_dashboard_state.json"

DEFAULT_STATE: dict[str, Any] = {
    "heartbeat": {"last_status": None, "last_tick_ts": 0},
    "deadlines": {},
    "lectures": {},
    "pr_activity": {},
    # Slice 3 "Next 3 deadlines" lives in its own forum thread because
    # #deadlines is a forum channel. Both ids are needed: thread_id to
    # target the right thread on PATCH, message_id to edit the starter
    # post in place. Forward-compat: old state files without `next3`
    # get seeded with this default; the legacy `next3_message_id` key
    # at the top level (pre-Slice-3 schema) is ignored.
    "next3": {"thread_id": None, "message_id": None},
}


def load() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return copy.deepcopy(DEFAULT_STATE)
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(DEFAULT_STATE)
    if not isinstance(state, dict):
        return copy.deepcopy(DEFAULT_STATE)
    for k, v in DEFAULT_STATE.items():
        state.setdefault(k, copy.deepcopy(v))
    return state


def save(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
