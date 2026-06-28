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
    # TTS engine: "edge" (online, free) or "kokoro" (offline, local, ~300 MB download on first run)
    "tts_engine": "edge",
    "tts_voice": "en-GB-SoniaNeural",       # used when tts_engine = "edge"
    "tts_kokoro_voice": "bf_isabella",       # used when tts_engine = "kokoro"
    "ptt_key": "space",
    "max_history_turns": 40,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "09:00",
    "heartbeat_enabled": True,
    "heartbeat_interval_minutes": 30,
    "ui_enabled": False,
    "ui_port": 7070,
    "requires_confirmation": ["create_note", "append_note", "forget_fact"],
    # STT (speech-to-text)
    "stt_model": "base",        # faster-whisper model: tiny/base/small/medium/large-v3
    "stt_device": "cpu",        # "cpu" or "cuda"
    "stt_compute_type": "int8", # int8 (fastest CPU), float16 (GPU), float32
    # Wake word
    "wakeword_engine": "vosk",       # "vosk" (recommended) or "openwakeword"
    "wakeword_keyword": "vesper",    # keyword for vosk engine
    "wakeword_model": "",            # vosk: model name or dir path; openwakeword: .onnx name
    "wakeword_threshold": 0.5,       # openwakeword only
    # Proactive TTS
    "proactive_tts": True,
    "briefing_enabled": True,
    "briefing_time": "09:00",
    "wrap_time": "21:00",
    "nudge_enabled": True,
    "nudge_minutes": 15,
    # App launcher shortcuts: {"name": "cmd"} or {"name": ["cmd1", "cmd2"]}
    "app_shortcuts": {},
    # Double-clap one-shot launch (fires once on startup, then disables itself)
    "clap_enabled": False,
    "clap_threshold": 0.7,
    "clap_window_s": 0.8,
    # VAD tuning
    "vad_silence_s": 0.6,           # seconds of silence before recording stops
    "vad_max_s": 8.0,               # hard cap on recording length
    "vad_silence_threshold": 0.01,  # RMS amplitude below which counts as silence
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
