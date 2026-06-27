"""Text-to-speech via Microsoft Edge TTS + Windows MCI (winmm.dll).

Free, no API key, no compilation required. Python 3.14 compatible.

Synthesis: edge-tts (neural voices, MP3 output)
Playback:  ctypes → winmm.dll MCI (Windows built-in, handles MP3 natively)

Voice: voice/config.json `tts_voice` (default: en-GB-SoniaNeural)
"""
from __future__ import annotations

import asyncio
import ctypes
import random
import tempfile
import threading
from pathlib import Path

_alias_lock = threading.Lock()
_current_alias: str | None = None


def speak(text: str) -> None:
    """Synthesise text and play it in a daemon thread (non-blocking)."""
    try:
        import edge_tts  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(f"pip install edge-tts  ({exc})") from exc

    from voice import config as cfg
    voice = cfg.load().get("tts_voice", "en-GB-SoniaNeural")
    threading.Thread(target=_play, args=(text, voice), daemon=True).start()


def stop_speaking() -> None:
    """Interrupt current playback (best-effort)."""
    with _alias_lock:
        alias = _current_alias
    if alias:
        try:
            _mci(f"stop {alias}")
        except Exception:
            pass


def _play(text: str, voice: str) -> None:
    global _current_alias

    import edge_tts

    mp3 = asyncio.run(_fetch(text, voice))
    if not mp3:
        return

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fh:
        fh.write(mp3)
        tmp_path = fh.name

    alias = f"vesper_{random.randint(0, 999_999)}"
    try:
        _mci(f'open "{tmp_path}" type mpegvideo alias {alias}')
        with _alias_lock:
            _current_alias = alias
        _mci(f"play {alias} wait")   # blocks until done or stopped
    finally:
        with _alias_lock:
            _current_alias = None
        try:
            _mci(f"close {alias}")
        except Exception:
            pass
        Path(tmp_path).unlink(missing_ok=True)


async def _fetch(text: str, voice: str) -> bytes:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


def _mci(cmd: str) -> None:
    ctypes.WinDLL("winmm.dll").mciSendStringW(cmd, None, 0, None)
