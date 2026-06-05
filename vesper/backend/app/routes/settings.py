"""GET /api/settings — read current user settings.

Merges tray_settings.json with defaults. Never raises."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends

from ..deps import require_auth

router = APIRouter()

_DEFAULTS = {
    "active_hours_start": "09:00",
    "active_hours_end": "22:00",
    "heartbeat_interval_minutes": 30,
    "auto_start_bot": True,
    "features": {
        "inbox": True,
        "reflect": True,
        "gcal_sync": True,
        "thread_chat": False,
        "toast_notifications": True,
    },
}


def _get_settings_file() -> Path:
    """Lazy resolve settings file path from env or defaults."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[4])
    return project_dir / ".claude" / "data" / "tray_settings.json"


def _load_settings() -> dict:
    """Load settings merged with defaults. Never raises."""
    settings_file = _get_settings_file()
    try:
        raw = json.loads(settings_file.read_text(encoding="utf-8"))
        merged = dict(_DEFAULTS)
        merged.update({k: v for k, v in raw.items() if k != "features"})
        merged["features"] = dict(_DEFAULTS["features"])
        merged["features"].update(raw.get("features", {}))
        return merged
    except (FileNotFoundError, json.JSONDecodeError):
        return {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DEFAULTS.items()}


def _save_settings(data: dict) -> None:
    """Save settings to tray_settings.json. Parent dirs created if missing.

    Only saves non-default values to keep the file lean and preserve
    future defaults when defaults change."""
    settings_file = _get_settings_file()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    # Only save keys that differ from defaults
    to_save = {}
    for key in ["active_hours_start", "active_hours_end", "heartbeat_interval_minutes", "auto_start_bot"]:
        if key in data and data[key] != _DEFAULTS[key]:
            to_save[key] = data[key]
    # Only save non-default features
    if "features" in data:
        features_to_save = {
            k: v for k, v in data["features"].items()
            if v != _DEFAULTS["features"].get(k)
        }
        if features_to_save:
            to_save["features"] = features_to_save
    settings_file.write_text(json.dumps(to_save, indent=2), encoding="utf-8")


@router.get("/settings")
def get_settings(_: None = Depends(require_auth)):
    """Return current settings (merged with defaults)."""
    return _load_settings()


@router.post("/settings")
def post_settings(body: dict, _: None = Depends(require_auth)):
    """Save new settings. Accepts partial updates (merges with current)."""
    current = _load_settings()
    # Only allow known keys to be updated
    for key in ["active_hours_start", "active_hours_end", "heartbeat_interval_minutes", "auto_start_bot"]:
        if key in body:
            current[key] = body[key]
    if "features" in body and isinstance(body["features"], dict):
        current["features"].update(body["features"])
    _save_settings(current)
    return current
