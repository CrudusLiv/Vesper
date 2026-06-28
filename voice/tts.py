"""Text-to-speech — two backends selectable via config `tts_engine`.

edge (default): Microsoft Edge TTS — free, requires internet.
  Config: tts_voice  (e.g. "en-GB-SoniaNeural")

kokoro: Local Kokoro TTS — offline, no API key, high quality.
  Install: py -m pip install kokoro soundfile
  Config: tts_kokoro_voice  (e.g. "bf_isabella")
  First run downloads ~300 MB of model weights to ~/.cache/huggingface/.
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

# Set while audio is physically playing — wakeword/clap import this to suppress self-triggering
speaking = threading.Event()

_kokoro_pipeline = None


def speak(text: str, on_done=None) -> None:
    """Synthesise and play in a daemon thread (non-blocking).

    on_done: optional zero-arg callable fired after playback ends or fails.
             Pass _wakeword_ready.set here instead of calling it after speak().
    """
    threading.Thread(target=_play, args=(text, on_done), daemon=True).start()


def stop_speaking() -> None:
    """Interrupt current playback (best-effort)."""
    with _alias_lock:
        alias = _current_alias
    if alias:
        try:
            _mci(f"stop {alias}")
        except Exception:
            pass


# ── Backend dispatch ──────────────────────────────────────────────────────────

def _play(text: str, on_done=None) -> None:
    from voice import config as cfg
    conf = cfg.load()
    engine = conf.get("tts_engine", "edge")
    if engine == "kokoro":
        voice = conf.get("tts_kokoro_voice", "bf_isabella")
        _play_kokoro(text, voice, on_done)
    else:
        voice = conf.get("tts_voice", "en-GB-SoniaNeural")
        _play_edge(text, voice, on_done)


# ── Edge TTS backend ──────────────────────────────────────────────────────────

def _play_edge(text: str, voice: str, on_done=None) -> None:
    try:
        import edge_tts  # noqa: F401
    except ImportError as exc:
        print(f"[TTS] pip install edge-tts  ({exc})", flush=True)
        if on_done:
            on_done()
        return

    try:
        mp3 = asyncio.run(_fetch_edge(text, voice))
    except Exception as exc:
        print(f"[TTS] edge fetch failed: {exc}", flush=True)
        if on_done:
            on_done()
        return

    if not mp3:
        print("[TTS] edge returned empty audio — check tts_voice in config.json", flush=True)
        if on_done:
            on_done()
        return

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fh:
        fh.write(mp3)
        tmp_path = fh.name

    _mci_play(tmp_path, "mpegvideo", on_done)


async def _fetch_edge(text: str, voice: str) -> bytes:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


# ── Kokoro backend ────────────────────────────────────────────────────────────

def _load_kokoro(lang_code: str):
    global _kokoro_pipeline
    if _kokoro_pipeline is not None:
        return _kokoro_pipeline
    try:
        from kokoro import KPipeline
    except ImportError as exc:
        raise RuntimeError(f"pip install kokoro soundfile  ({exc})") from exc
    print(f"[TTS] loading Kokoro (lang={lang_code!r}) — first run downloads ~300 MB …", flush=True)
    _kokoro_pipeline = KPipeline(lang_code=lang_code)
    print("[TTS] Kokoro ready.", flush=True)
    return _kokoro_pipeline


def _play_kokoro(text: str, voice: str, on_done=None) -> None:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        print(f"[TTS] kokoro needs soundfile: pip install soundfile  ({exc})", flush=True)
        if on_done:
            on_done()
        return

    try:
        # 'b' = British phonemes (bf_* voices), 'a' = American (af_* voices)
        lang_code = "b" if voice.startswith("b") else "a"
        pipeline = _load_kokoro(lang_code)
        audio_chunks = [audio for _, _, audio in pipeline(text, voice=voice, speed=1.0)]
        if not audio_chunks:
            print("[TTS] Kokoro returned no audio", flush=True)
            if on_done:
                on_done()
            return
        audio = np.concatenate(audio_chunks)
    except Exception as exc:
        print(f"[TTS] Kokoro synthesis failed: {exc}", flush=True)
        if on_done:
            on_done()
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
        tmp_path = fh.name
    try:
        sf.write(tmp_path, audio, 24000)
    except Exception as exc:
        print(f"[TTS] wav write failed: {exc}", flush=True)
        Path(tmp_path).unlink(missing_ok=True)
        if on_done:
            on_done()
        return

    _mci_play(tmp_path, "waveaudio", on_done)


# ── Shared MCI playback ───────────────────────────────────────────────────────

def _mci_play(tmp_path: str, file_type: str, on_done=None) -> None:
    """Open file with MCI, play to completion, then clean up."""
    global _current_alias
    alias = f"vesper_{random.randint(0, 999_999)}"
    try:
        _mci(f'open "{tmp_path}" type {file_type} alias {alias}')
        with _alias_lock:
            _current_alias = alias
        speaking.set()
        _mci(f"play {alias} wait")
    finally:
        speaking.clear()
        with _alias_lock:
            _current_alias = None
        try:
            _mci(f"close {alias}")
        except Exception:
            pass
        Path(tmp_path).unlink(missing_ok=True)
        if on_done:
            on_done()


def _mci(cmd: str) -> None:
    ctypes.WinDLL("winmm.dll").mciSendStringW(cmd, None, 0, None)
