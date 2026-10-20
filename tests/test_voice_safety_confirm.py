"""Tests for voice.safety.confirm_with_reason's HTTP-first, then-fallback
behavior once tool dispatch can happen in a separate process from ui_server."""
from __future__ import annotations

import json
import os
from urllib.error import URLError

import pytest

from voice import safety


@pytest.fixture(autouse=True)
def _not_paused(monkeypatch):
    monkeypatch.setattr("voice.killswitch.is_paused", lambda: False)


@pytest.fixture(autouse=True)
def _fixed_port(monkeypatch):
    monkeypatch.setattr(
        "voice.config.load",
        lambda: {"confirm_timeout_seconds": 30, "ui_port": 7070},
    )


def test_paused_short_circuits_before_any_http_call(monkeypatch):
    monkeypatch.setattr("voice.killswitch.is_paused", lambda: True)
    called = []
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: called.append(1))
    approved, reason = safety.confirm_with_reason("create_note", {"path": "x.md"})
    assert (approved, reason) == (False, "paused")
    assert called == []


def test_http_bridge_success_returns_server_decision(monkeypatch):
    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"approved": True, "reason": "user"}).encode()

    monkeypatch.setenv("VESPER_UI_TOKEN", "test-token")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _FakeResp())
    approved, reason = safety.confirm_with_reason("create_note", {"path": "x.md"})
    assert (approved, reason) == (True, "user")


def test_http_bridge_explicit_deny_normalizes_reason_to_cancelled(monkeypatch):
    """The orb UI reports raw reason='user' for both approve and explicit
    deny votes (voice/confirm.py's resolve() always sets pending.reason =
    'user'). confirm_with_reason's contract says 'user' only ever
    accompanies approved=True, so an explicit deny must be translated to
    'cancelled', never passed through verbatim."""
    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"approved": False, "reason": "user"}).encode()

    monkeypatch.setenv("VESPER_UI_TOKEN", "test-token")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _FakeResp())
    approved, reason = safety.confirm_with_reason("create_note", {"path": "x.md"})
    assert (approved, reason) == (False, "cancelled")


def test_http_bridge_unreachable_falls_back_to_console(monkeypatch):
    def _raise(*a, **k):
        raise URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    monkeypatch.setattr(
        "voice.safety._console_confirm", lambda *a, **k: (True, "user")
    )
    approved, reason = safety.confirm_with_reason("create_note", {"path": "x.md"})
    assert (approved, reason) == (True, "user")


def test_voice_confirm_skipped_when_source_is_text(monkeypatch):
    """Default get_current_source() is 'text' -- voice must be a no-op so
    every existing HTTP-path test above keeps passing unmodified."""
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "text")
    called = []
    monkeypatch.setattr("voice.tts.speak", lambda *a, **k: called.append(1))
    class _FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"approved": True, "reason": "user"}).encode()
    monkeypatch.setenv("VESPER_UI_TOKEN", "test-token")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _FakeResp())
    approved, reason = safety.confirm_with_reason("create_note", {"path": "x.md"})
    assert (approved, reason) == (True, "user")
    assert called == []  # never spoke -- voice path wasn't attempted


def test_voice_confirm_skipped_during_quiet_hours(monkeypatch):
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "voice")
    monkeypatch.setattr("voice.config.is_quiet_hours", lambda: True)
    called = []
    monkeypatch.setattr("voice.tts.speak", lambda *a, **k: called.append(1))
    class _FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"approved": True, "reason": "user"}).encode()
    monkeypatch.setenv("VESPER_UI_TOKEN", "test-token")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _FakeResp())
    approved, reason = safety.confirm_with_reason("create_note", {"path": "x.md"})
    assert (approved, reason) == (True, "user")
    assert called == []


def test_voice_confirm_yes_approves(monkeypatch):
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "voice")
    monkeypatch.setattr("voice.config.is_quiet_hours", lambda: False)
    monkeypatch.setattr("voice.tts.speak", lambda *a, **k: None)
    monkeypatch.setattr("voice.tts.stop_speaking", lambda: None)
    monkeypatch.setattr("voice.audio.is_ptt_down", lambda key: True)
    monkeypatch.setattr("voice.audio.record_while_held", lambda key, on_press=None: b"WAV")
    monkeypatch.setattr("voice.stt.transcribe", lambda audio: "Yeah.")
    approved, reason = safety.confirm_with_reason("create_calendar_event", {"title": "x"})
    assert (approved, reason) == (True, "user")


def test_voice_confirm_no_denies(monkeypatch):
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "voice")
    monkeypatch.setattr("voice.config.is_quiet_hours", lambda: False)
    monkeypatch.setattr("voice.tts.speak", lambda *a, **k: None)
    monkeypatch.setattr("voice.tts.stop_speaking", lambda: None)
    monkeypatch.setattr("voice.audio.is_ptt_down", lambda key: True)
    monkeypatch.setattr("voice.audio.record_while_held", lambda key, on_press=None: b"WAV")
    monkeypatch.setattr("voice.stt.transcribe", lambda audio: "no")
    approved, reason = safety.confirm_with_reason("create_calendar_event", {"title": "x"})
    assert (approved, reason) == (False, "cancelled")


def test_voice_confirm_unrecognized_answer_denies(monkeypatch):
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "voice")
    monkeypatch.setattr("voice.config.is_quiet_hours", lambda: False)
    monkeypatch.setattr("voice.tts.speak", lambda *a, **k: None)
    monkeypatch.setattr("voice.tts.stop_speaking", lambda: None)
    monkeypatch.setattr("voice.audio.is_ptt_down", lambda key: True)
    monkeypatch.setattr("voice.audio.record_while_held", lambda key, on_press=None: b"WAV")
    monkeypatch.setattr("voice.stt.transcribe", lambda audio: "maybe later")
    approved, reason = safety.confirm_with_reason("create_calendar_event", {"title": "x"})
    assert (approved, reason) == (False, "cancelled")


def test_voice_confirm_no_ptt_press_times_out(monkeypatch):
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "voice")
    monkeypatch.setattr("voice.config.is_quiet_hours", lambda: False)
    monkeypatch.setattr("voice.config.load", lambda: {"confirm_timeout_seconds": 0.05, "ptt_key": "`"})
    monkeypatch.setattr("voice.tts.speak", lambda *a, **k: None)
    monkeypatch.setattr("voice.tts.stop_speaking", lambda: None)
    monkeypatch.setattr("voice.audio.is_ptt_down", lambda key: False)
    approved, reason = safety.confirm_with_reason("create_calendar_event", {"title": "x"})
    assert (approved, reason) == (False, "timeout")


def test_voice_confirm_empty_recording_times_out(monkeypatch):
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "voice")
    monkeypatch.setattr("voice.config.is_quiet_hours", lambda: False)
    monkeypatch.setattr("voice.tts.speak", lambda *a, **k: None)
    monkeypatch.setattr("voice.tts.stop_speaking", lambda: None)
    monkeypatch.setattr("voice.audio.is_ptt_down", lambda key: True)
    monkeypatch.setattr("voice.audio.record_while_held", lambda key, on_press=None: None)
    approved, reason = safety.confirm_with_reason("create_calendar_event", {"title": "x"})
    assert (approved, reason) == (False, "timeout")


def test_voice_confirm_stt_failure_falls_through_to_http(monkeypatch):
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "voice")
    monkeypatch.setattr("voice.config.is_quiet_hours", lambda: False)
    monkeypatch.setattr("voice.tts.speak", lambda *a, **k: None)
    monkeypatch.setattr("voice.tts.stop_speaking", lambda: None)
    monkeypatch.setattr("voice.audio.is_ptt_down", lambda key: True)
    monkeypatch.setattr("voice.audio.record_while_held", lambda key, on_press=None: b"WAV")

    def _boom(audio):
        raise RuntimeError("stt down")
    monkeypatch.setattr("voice.stt.transcribe", _boom)

    class _FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"approved": True, "reason": "user"}).encode()
    monkeypatch.setenv("VESPER_UI_TOKEN", "test-token")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _FakeResp())
    approved, reason = safety.confirm_with_reason("create_calendar_event", {"title": "x"})
    assert (approved, reason) == (True, "user")  # fell through to HTTP bridge


def test_http_bridge_sends_token_header(monkeypatch):
    seen = {}

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"approved": False, "reason": "user"}).encode()

    def _fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["headers"] = dict(req.header_items())
        return _FakeResp()

    monkeypatch.setenv("VESPER_UI_TOKEN", "test-token-123")
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    safety.confirm_with_reason("forget_fact", {"key": "x"})
    assert seen["url"] == "http://127.0.0.1:7070/internal/confirm"
    assert seen["headers"].get("X-vesper-token") == "test-token-123"


# ── Retry, answer normalization, and UI state during a voice confirm ───────

def _voice_stubs(monkeypatch, answers, spoken=None, events=None):
    """Wire the voice-confirm path: PTT always down, recording always
    non-empty, and transcribe() returning `answers` in order (the last one
    repeats once exhausted, so a stub can outlive the retry budget)."""
    monkeypatch.setattr("voice.brain.get_current_source", lambda: "voice")
    monkeypatch.setattr("voice.config.is_quiet_hours", lambda: False)
    monkeypatch.setattr("voice.tts.stop_speaking", lambda: None)
    monkeypatch.setattr("voice.audio.is_ptt_down", lambda key: True)
    monkeypatch.setattr("voice.audio.record_while_held", lambda key, on_press=None: b"WAV")
    if spoken is not None:
        monkeypatch.setattr("voice.tts.speak", lambda text, **k: spoken.append(text))
    else:
        monkeypatch.setattr("voice.tts.speak", lambda *a, **k: None)
    if events is not None:
        monkeypatch.setattr("voice.ui_server.post_event", lambda ev: events.append(ev))
    queue = list(answers)
    monkeypatch.setattr(
        "voice.stt.transcribe",
        lambda audio: queue.pop(0) if len(queue) > 1 else queue[0],
    )


def test_voice_confirm_retries_once_then_accepts_yes(monkeypatch):
    """An unrecognized first answer must re-ask, not cancel outright --
    the whole request otherwise has to be restated from scratch."""
    spoken: list[str] = []
    _voice_stubs(monkeypatch, ["uhh what", "yes"], spoken=spoken)
    approved, reason = safety.confirm_with_reason("create_reminder", {"title": "x"})
    assert (approved, reason) == (True, "user")
    assert len(spoken) == 2  # original question + one re-ask


def test_voice_confirm_retries_only_once(monkeypatch):
    """Two unrecognized answers deny -- the retry budget is one, so a
    mishearing loop can't hold the brain thread open indefinitely."""
    spoken: list[str] = []
    _voice_stubs(monkeypatch, ["uhh what", "still garbled"], spoken=spoken)
    approved, reason = safety.confirm_with_reason("create_reminder", {"title": "x"})
    assert (approved, reason) == (False, "cancelled")
    assert len(spoken) == 2


def test_voice_confirm_explicit_no_never_retries(monkeypatch):
    spoken: list[str] = []
    _voice_stubs(monkeypatch, ["no", "yes"], spoken=spoken)
    approved, reason = safety.confirm_with_reason("create_reminder", {"title": "x"})
    assert (approved, reason) == (False, "cancelled")
    assert len(spoken) == 1


@pytest.mark.parametrize("answer", [
    "yes please", "Yeah, go ahead.", "yep!", "sure", "do it", "go ahead and do it",
])
def test_voice_confirm_accepts_padded_yes(monkeypatch, answer):
    """Whisper rarely returns a bare 'yes' -- trailing politeness and
    punctuation must not fall into the deny branch."""
    _voice_stubs(monkeypatch, [answer])
    assert safety.confirm_with_reason("create_reminder", {"title": "x"}) == (True, "user")


@pytest.mark.parametrize("answer", ["no thanks", "Nope.", "don't", "cancel that"])
def test_voice_confirm_rejects_padded_no(monkeypatch, answer):
    _voice_stubs(monkeypatch, [answer])
    assert safety.confirm_with_reason("create_reminder", {"title": "x"}) == (False, "cancelled")


def test_voice_confirm_question_names_the_arguments(monkeypatch):
    """Speaking only the tool name asks the user to approve blind."""
    spoken: list[str] = []
    _voice_stubs(monkeypatch, ["yes"], spoken=spoken)
    safety.confirm_with_reason(
        "create_reminder", {"title": "BDA 205 assignment", "date": "2026-09-21"}
    )
    assert "BDA 205 assignment" in spoken[0]
    assert "2026-09-21" in spoken[0]


def test_voice_confirm_emits_listening_state_while_recording(monkeypatch):
    """Without this the orb ring stays on 'thinking' and the mini capsule
    stays hidden while she is actively recording the yes/no answer."""
    events: list[dict] = []
    _voice_stubs(monkeypatch, ["yes"], events=events)
    safety.confirm_with_reason("create_reminder", {"title": "x"})
    states = [e.get("value") for e in events if e.get("type") == "state"]
    assert "listening" in states
    assert states[-1] == "thinking"  # handed back to the brain's own state


def test_voice_confirm_empty_recording_restores_thinking_state(monkeypatch):
    events: list[dict] = []
    _voice_stubs(monkeypatch, ["yes"], events=events)
    monkeypatch.setattr("voice.audio.record_while_held", lambda key, on_press=None: None)
    approved, reason = safety.confirm_with_reason("create_reminder", {"title": "x"})
    assert (approved, reason) == (False, "timeout")
    states = [e.get("value") for e in events if e.get("type") == "state"]
    assert states[-1] == "thinking"
