"""Speech-to-text.

Primary: faster-whisper (local, offline, no API key required).
Fallback: Deepgram REST API if faster-whisper is not installed and
          DEEPGRAM_API_KEY is set in the environment.

Config keys (voice/config.json):
  stt_model        "tiny" | "base" | "small" | "medium" | "large-v3"  (default "base")
  stt_device       "cpu" | "cuda"  (default "cpu")
  stt_compute_type "int8" | "float16" | "float32"  (default "int8")
"""
from __future__ import annotations

import io
import wave

_model = None  # lazy singleton — loaded on first transcribe() call


def _load_model():
    global _model
    if _model is not None:
        return _model

    from voice import config as cfg
    conf = cfg.load()
    model_name   = conf.get("stt_model", "base")
    device       = conf.get("stt_device", "cpu")
    compute_type = conf.get("stt_compute_type", "int8")

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(f"pip install faster-whisper  ({exc})") from exc

    print(f"[STT] loading faster-whisper '{model_name}' ({device}/{compute_type}) …", flush=True)
    try:
        _model = WhisperModel(model_name, device=device, compute_type=compute_type)
    except Exception as exc:
        if device != "cpu":
            print(f"[STT] {device} init failed ({exc}) — retrying on cpu/int8", flush=True)
            _model = WhisperModel(model_name, device="cpu", compute_type="int8")
        else:
            raise
    print("[STT] model ready.", flush=True)
    return _model


def _wav_to_float32(audio_bytes: bytes):
    """Decode 16kHz mono int16 WAV bytes to float32 numpy array."""
    import numpy as np
    buf = io.BytesIO(audio_bytes)
    with wave.open(buf) as wf:
        frames = wf.readframes(wf.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe WAV bytes; returns the recognised string (may be empty)."""
    import importlib.util

    if importlib.util.find_spec("faster_whisper") is not None:
        model = _load_model()
        audio = _wav_to_float32(audio_bytes)
        segments, _ = model.transcribe(audio, beam_size=5, language="en")
        return " ".join(seg.text for seg in segments).strip()

    # Fallback: Deepgram
    import os
    # Load .env if the key isn't already in the shell environment
    if not os.getenv("DEEPGRAM_API_KEY"):
        try:
            import integrations._env  # noqa: F401 — auto-runs load_env() on import
        except Exception:
            pass
    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "faster-whisper not installed and DEEPGRAM_API_KEY not set — "
            "run: py -m pip install faster-whisper"
        )

    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError(f"pip install httpx  ({exc})") from exc

    resp = httpx.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-2", "smart_format": "true", "punctuate": "true"},
        headers={"Authorization": f"Token {api_key}", "Content-Type": "audio/wav"},
        content=audio_bytes,
        timeout=30,
    )
    resp.raise_for_status()
    try:
        return resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"] or ""
    except (KeyError, IndexError):
        return ""
