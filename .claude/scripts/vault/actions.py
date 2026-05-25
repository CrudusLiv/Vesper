"""Vault action verbs. Each function:

  1. Calls paths.validate() before touching disk.
  2. Performs exactly one filesystem operation.
  3. Appends a transaction-log entry (with undo_state) on success.
  4. Raises a stdlib exception on failure (no logging on failure).

Caller (chat handler) translates exceptions into user-facing replies.
"""
from __future__ import annotations

from pathlib import Path

from vault import paths, transactions


def append(path: str, text: str) -> dict:
    """Append `text` to existing `path`. Raises FileNotFoundError if missing."""
    target = paths.validate(path)
    if not target.exists():
        raise FileNotFoundError(path)
    original_length = target.stat().st_size
    with target.open("a", encoding="utf-8") as f:
        f.write(text)
    transactions.append({
        "action": "append",
        "args": {"path": path, "text": text},
        "undo_state": {"original_length": original_length},
    })
    return {"path": path, "appended_chars": len(text)}


def create(path: str, content: str) -> dict:
    """Create new file at `path`. Raises FileExistsError if path exists."""
    target = paths.validate(path)
    if target.exists():
        raise FileExistsError(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    transactions.append({
        "action": "create",
        "args": {"path": path, "content": content},
        "undo_state": {},
    })
    return {"path": path, "bytes": len(content.encode("utf-8"))}
