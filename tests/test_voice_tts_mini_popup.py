"""Tests for tts.py's audio-lifecycle hooks driving the mini
conversation-presence capsule (voice/ui_window.py::set_conversation_state).

Root cause this guards against: voice/main.py::_start_proactive_speaker
(heartbeat/power-trigger speech) calls tts.speak() directly and never
emits a `state` WS event -- so if the popup depends ONLY on state events
(voice/ui_server.py::post_event), it never shows for proactive speech.
_on_speak_start/_on_speak_end must also drive it directly, since those
fire for audio playback regardless of source."""
from __future__ import annotations

from voice import tts


def test_on_speak_start_sets_conversation_state_speaking(monkeypatch):
    calls = []
    monkeypatch.setattr("voice.ui_window.set_conversation_state", lambda v: calls.append(v))
    monkeypatch.setattr("voice.audio_duck.duck", lambda: None)
    tts._on_speak_start()
    assert calls == ["speaking"]


def test_on_speak_end_sets_conversation_state_idle(monkeypatch):
    calls = []
    monkeypatch.setattr("voice.ui_window.set_conversation_state", lambda v: calls.append(v))
    monkeypatch.setattr("voice.audio_duck.restore", lambda: None)
    tts._on_speak_end()
    assert calls == ["idle"]


def test_on_speak_start_survives_ui_window_failure(monkeypatch):
    """A broken/unavailable mini window must never block audio ducking."""
    duck_calls = []
    monkeypatch.setattr("voice.audio_duck.duck", lambda: duck_calls.append(1))

    def _boom(v):
        raise RuntimeError("no window")
    monkeypatch.setattr("voice.ui_window.set_conversation_state", _boom)
    tts._on_speak_start()  # must not raise
    assert duck_calls == [1]
