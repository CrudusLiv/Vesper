"""Append-only JSONL audit log for all voice turns and tool calls.

Written to .claude/data/voice_audit.jsonl.
Schema per line: {"ts": "<ISO8601+08:00>", "role": "user|assistant|tool", "content": "...", ["tool": "name"]}
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

_KL = timezone(timedelta(hours=8))
_ROOT = Path(__file__).resolve().parents[1]
_LOG = _ROOT / ".claude" / "data" / "voice_audit.jsonl"
_NOTICES = _ROOT / ".claude" / "data" / "voice_notices.jsonl"
_MAX_CONTENT = 500
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB cap per file
_KEEP_LINES = 1000              # lines retained after trimming
_ROTATE_EVERY = 50              # check size every N writes
_write_count = 0


def _maybe_rotate(path: Path) -> None:
    """Trim path to _KEEP_LINES newest lines when it exceeds _MAX_BYTES."""
    try:
        if path.stat().st_size < _MAX_BYTES:
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > _KEEP_LINES:
            path.write_text("\n".join(lines[-_KEEP_LINES:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def log(role: str, content: str, tool_name: str | None = None) -> None:
    """Append one audit entry (non-fatal on I/O error)."""
    global _write_count
    entry: dict = {
        "ts": datetime.now(_KL).isoformat(),
        "role": role,
        "content": content[:_MAX_CONTENT],
    }
    if tool_name:
        entry["tool"] = tool_name
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        with _LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        _write_count += 1
        if _write_count % _ROTATE_EVERY == 0:
            _maybe_rotate(_LOG)
            _maybe_rotate(_NOTICES)
    except OSError:
        pass
