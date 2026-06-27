"""Speech-to-text via Deepgram REST API (nova-2).

Uses httpx directly — no deepgram-sdk version dependency.
Requires DEEPGRAM_API_KEY in .env.
"""
from __future__ import annotations

import os


def transcribe(audio_bytes: bytes) -> str:
    """POST WAV bytes to Deepgram /v1/listen; return transcript string."""
    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY not set — add it to .env")

    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError(f"pip install httpx  ({exc})") from exc

    resp = httpx.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-2", "smart_format": "true", "punctuate": "true"},
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/wav",
        },
        content=audio_bytes,
        timeout=30,
    )
    resp.raise_for_status()

    try:
        return resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"] or ""
    except (KeyError, IndexError):
        return ""
