"""Per-upload status store for the document-upload pipeline.

A tiny JSON file at .claude/data/state/inbox-uploads.json holding the last N
upload records, newest first. The path is resolved lazily from
CLAUDE_PROJECT_DIR on every call so tests that monkeypatch the env var isolate
to a tmp dir (a module-level constant would bake the real path). A module lock
serialises read-modify-write so two concurrent uploads can't clobber the file."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_KL = timezone(timedelta(hours=8))
_LOCK = threading.Lock()
MAX_RECORDS = 10


def _store_path() -> Path:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
    return proj / ".claude" / "data" / "state" / "inbox-uploads.json"


def _read() -> list[dict]:
    path = _store_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def _write(records: list[dict]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def add(filename: str) -> dict:
    now = datetime.now(_KL).isoformat()
    record = {
        "id": uuid.uuid4().hex,
        "filename": filename,
        "status": "queued",
        "type": None,
        "category": None,
        "title": None,
        "note_path": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    with _LOCK:
        records = _read()
        records.insert(0, record)
        _write(records[:MAX_RECORDS])
    return record


def update(upload_id: str, **fields) -> dict | None:
    with _LOCK:
        records = _read()
        for rec in records:
            if rec["id"] == upload_id:
                rec.update(fields)
                rec["updated_at"] = datetime.now(_KL).isoformat()
                _write(records)
                return rec
    return None


def recent(limit: int = MAX_RECORDS) -> list[dict]:
    with _LOCK:
        return _read()[:limit]
