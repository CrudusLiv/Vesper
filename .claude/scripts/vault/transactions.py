"""Append-only JSONL log of every vault action.

Every action emits one entry. `undo` reads the last entry, executes the
inverse, and appends the inverse as a new entry — so undo-undo works.

The log is never auto-pruned. Disk cost is negligible (a few KB / day).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
LOG_PATH = PROJECT_DIR / ".claude" / "data" / "vault_transactions.jsonl"

KL = timezone(timedelta(hours=8))


def append(entry: dict) -> None:
    """Append one entry to the JSONL log. Auto-stamps `ts` if missing."""
    if "ts" not in entry:
        entry = {**entry, "ts": datetime.now(KL).isoformat()}
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_last() -> Optional[dict]:
    """Return the most recent entry, or None if the log is empty/missing."""
    if not LOG_PATH.exists():
        return None
    last_line = ""
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line:
                last_line = line
    if not last_line:
        return None
    try:
        return json.loads(last_line)
    except json.JSONDecodeError:
        return None
