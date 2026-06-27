"""Load and save voice/config.json. Merges with defaults so new keys added
to DEFAULTS are available even in older config files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULTS: dict[str, Any] = {
    "model": "claude-sonnet-4-6",
    "fast_model": "claude-haiku-4-5-20251001",
    "voice_id": "",
    "tts_voice": "en-GB-SoniaNeural",
    "ptt_key": "space",
    "max_history_turns": 40,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "09:00",
    "heartbeat_enabled": True,
    "heartbeat_interval_minutes": 30,
    "ui_enabled": False,
    "ui_port": 7070,
    "requires_confirmation": ["create_note", "append_note", "forget_fact"],
    "wakeword_model": "",        # path to .onnx or openwakeword model name; "" = demo (alexa)
    "wakeword_threshold": 0.5,
}


def load() -> dict[str, Any]:
    """Return config merged with defaults (file values win)."""
    if not _CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        on_disk = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    return {**DEFAULTS, **on_disk}


def save(updates: dict[str, Any]) -> None:
    """Merge `updates` into the config file."""
    current = load()
    current.update(updates)
    _CONFIG_PATH.write_text(
        json.dumps(current, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def is_quiet_hours() -> bool:
    """Return True if current KL time falls within quiet_hours_start–quiet_hours_end."""
    from datetime import datetime, timezone, timedelta

    conf = load()
    start_str = conf.get("quiet_hours_start", "22:00")
    end_str = conf.get("quiet_hours_end", "09:00")
    _KL = timezone(timedelta(hours=8))
    now = datetime.now(_KL)
    now_min = now.hour * 60 + now.minute
    sh, sm = (int(x) for x in start_str.split(":"))
    eh, em = (int(x) for x in end_str.split(":"))
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    if start_min > end_min:  # window crosses midnight (e.g. 22:00–09:00)
        return now_min >= start_min or now_min < end_min
    return start_min <= now_min < end_min
