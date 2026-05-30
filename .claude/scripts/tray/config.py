from __future__ import annotations
import json
import os
from pathlib import Path

_DEFAULT: dict = {
    "auto_start_bot": True,
    "start_with_windows": True,
    "active_hours_start": "09:00",
    "active_hours_end": "22:00",
    "features": {
        "inbox": True,
        "reflect": True,
        "gcal_sync": True,
        "thread_chat": False,
        "toast_notifications": True,
    },
}


def _path() -> Path:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
    return proj / ".claude" / "data" / "tray_settings.json"


def load() -> dict:
    """Return config merged with defaults. Never raises."""
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
        merged = dict(_DEFAULT)
        merged.update({k: v for k, v in raw.items() if k != "features"})
        merged["features"] = dict(_DEFAULT["features"])
        merged["features"].update(raw.get("features", {}))
        return merged
    except (FileNotFoundError, json.JSONDecodeError):
        return {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DEFAULT.items()}


def save(d: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=2), encoding="utf-8")
