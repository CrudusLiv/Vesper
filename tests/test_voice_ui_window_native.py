"""Tests for voice/ui_window.py's testable surface -- the show()/is_available()
state and the closing-handler/init-failure/success branches of start(), all
exercised via monkeypatched _create_window() so no real WebView2 runtime is
needed. Actual webview.start()/window creation is excluded from CI, same
posture as voice/screen_overlay.py's real Tk window."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from voice import ui_window


def _reset_mini_timer():
    if ui_window._mini_hide_timer is not None:
        ui_window._mini_hide_timer.cancel()
        ui_window._mini_hide_timer = None


@pytest.fixture(autouse=True)
def _reset_module_state():
    ui_window._window = None
    ui_window._available = False
    ui_window._main_visible = True
    ui_window._mini_window = None
    ui_window._mini_available = False
    ui_window._mini_visible = False
    _reset_mini_timer()
    yield
    ui_window._window = None
    ui_window._available = False
    ui_window._main_visible = True
    ui_window._mini_window = None
    ui_window._mini_available = False
    ui_window._mini_visible = False
    _reset_mini_timer()


def test_is_available_false_initially():
    assert ui_window.is_available() is False


def test_show_noop_when_no_window():
    ui_window.show()  # must not raise


def test_show_calls_window_show():
    calls = []
    ui_window._window = SimpleNamespace(show=lambda: calls.append(True))
    ui_window.show()
    assert calls == [True]


def test_on_closing_hides_and_cancels_close():
    calls = []
    fake_window = SimpleNamespace(hide=lambda: calls.append(True))
    result = ui_window._on_closing(fake_window)
    assert calls == [True]
    assert result is False


def test_start_marks_unavailable_on_create_failure(monkeypatch):
    def _raise(port, token):
        raise RuntimeError("no WebView2 runtime")

    monkeypatch.setattr(ui_window, "_create_window", _raise)
    ui_window.start(7070, "tok")
    assert ui_window.is_available() is False
    assert ui_window._window is None


def test_start_marks_available_and_starts_webview_on_success(monkeypatch):
    # window.show() must NOT be called here -- pywebview's real Window API
    # blocks on a readiness event that's only set once webview.start() has
    # initialized the GUI loop; calling show() before start() times out
    # with WebViewException('Main window failed to start') (see start()'s
    # docstring). The window is shown automatically by start() instead,
    # since _create_window() no longer passes hidden=True.
    start_calls = []
    fake_window = SimpleNamespace()
    fake_webview = SimpleNamespace(start=lambda **kw: start_calls.append(kw))

    monkeypatch.setattr(
        ui_window, "_create_window", lambda port, token: (fake_window, fake_webview)
    )
    ui_window.start(7070, "tok")
    assert ui_window.is_available() is True
    assert ui_window._window is fake_window
    assert len(start_calls) == 1
    # persistent WebView2 profile, not the default throwaway one
    assert start_calls[0]["private_mode"] is False
    assert start_calls[0]["storage_path"]


# ── Mini speaking-popup window ──────────────────────────────────────────────

def test_on_closing_marks_main_not_visible():
    fake_window = SimpleNamespace(hide=lambda: None)
    ui_window._main_visible = True
    ui_window._on_closing(fake_window)
    assert ui_window._main_visible is False


def test_show_marks_main_visible_again():
    ui_window._window = SimpleNamespace(show=lambda: None)
    ui_window._main_visible = False
    ui_window.show()
    assert ui_window._main_visible is True


class _ImmediateTimer:
    """Stand-in for threading.Timer that fires synchronously on start(),
    so tests don't sleep 400ms to observe the delayed hide()."""
    def __init__(self, interval, function):
        self.interval = interval
        self.function = function
        self.daemon = False
        self.cancelled = False

    def start(self):
        if not self.cancelled:
            self.function()

    def cancel(self):
        self.cancelled = True


@pytest.fixture
def immediate_timer(monkeypatch):
    import threading
    monkeypatch.setattr(threading, "Timer", _ImmediateTimer)


def test_set_conversation_state_noop_when_unavailable():
    ui_window._mini_available = False
    ui_window._main_visible = False
    ui_window._mini_window = SimpleNamespace(show=lambda: (_ for _ in ()).throw(AssertionError))
    ui_window.set_conversation_state("listening")  # must not raise / must not call show()


def test_set_conversation_state_noop_when_main_window_visible():
    calls = []
    ui_window._mini_available = True
    ui_window._main_visible = True
    ui_window._mini_window = SimpleNamespace(show=lambda: calls.append(True))
    ui_window.set_conversation_state("listening")
    assert calls == []


def test_set_conversation_state_noop_when_disabled_in_config(monkeypatch):
    from voice import config as cfg
    monkeypatch.setattr(cfg, "load", lambda: {"speaking_popup_enabled": False})
    calls = []
    ui_window._mini_available = True
    ui_window._main_visible = False
    ui_window._mini_window = SimpleNamespace(show=lambda: calls.append(True))
    ui_window.set_conversation_state("listening")
    assert calls == []


def test_set_conversation_state_shows_and_resyncs_for_active_state(monkeypatch):
    from voice import config as cfg
    monkeypatch.setattr(cfg, "load", lambda: {"speaking_popup_enabled": True})
    show_calls = []
    js_calls = []
    ui_window._mini_available = True
    ui_window._main_visible = False
    ui_window._mini_window = SimpleNamespace(
        show=lambda: show_calls.append(True),
        evaluate_js=lambda js: js_calls.append(js),
    )
    ui_window.set_conversation_state("listening")
    assert show_calls == [True]
    assert ui_window._mini_visible is True
    assert len(js_calls) == 1
    assert "'listening'" in js_calls[0]
    assert "mini-show" in js_calls[0]


def test_set_conversation_state_resyncs_without_reshowing_when_already_visible(monkeypatch):
    from voice import config as cfg
    monkeypatch.setattr(cfg, "load", lambda: {"speaking_popup_enabled": True})
    show_calls = []
    js_calls = []
    ui_window._mini_available = True
    ui_window._main_visible = False
    ui_window._mini_visible = True
    ui_window._mini_window = SimpleNamespace(
        show=lambda: show_calls.append(True),
        evaluate_js=lambda js: js_calls.append(js),
    )
    ui_window.set_conversation_state("speaking")
    assert show_calls == []  # already visible -- no redundant show()
    assert "'speaking'" in js_calls[0]


def test_set_conversation_state_hides_for_idle_when_visible(monkeypatch, immediate_timer):
    from voice import config as cfg
    monkeypatch.setattr(cfg, "load", lambda: {"speaking_popup_enabled": True})
    hide_calls = []
    js_calls = []
    ui_window._mini_available = True
    ui_window._main_visible = False
    ui_window._mini_visible = True
    ui_window._mini_window = SimpleNamespace(
        hide=lambda: hide_calls.append(True),
        evaluate_js=lambda js: js_calls.append(js),
    )
    ui_window.set_conversation_state("idle")
    assert "mini-show" in js_calls[0]
    assert hide_calls == [True]  # fired by the (monkeypatched immediate) timer
    assert ui_window._mini_visible is False


def test_set_conversation_state_idle_noop_when_not_visible(monkeypatch):
    from voice import config as cfg
    monkeypatch.setattr(cfg, "load", lambda: {"speaking_popup_enabled": True})
    ui_window._mini_available = True
    ui_window._main_visible = False
    ui_window._mini_visible = False
    ui_window._mini_window = SimpleNamespace(
        hide=lambda: (_ for _ in ()).throw(AssertionError),
        evaluate_js=lambda js: (_ for _ in ()).throw(AssertionError),
    )
    ui_window.set_conversation_state("idle")  # must not raise / must not touch the window


def test_mini_position_corners():
    import sys as _sys
    fake_win32con = SimpleNamespace(SM_CXSCREEN=0, SM_CYSCREEN=1)
    fake_win32api = SimpleNamespace(GetSystemMetrics=lambda m: 1000 if m == 0 else 800)
    _sys.modules["win32con"] = fake_win32con
    _sys.modules["win32api"] = fake_win32api
    try:
        assert ui_window._mini_position(200, 200, "top-left") == (24, 24)
        assert ui_window._mini_position(200, 200, "top-right") == (1000 - 200 - 24, 24)
        assert ui_window._mini_position(200, 200, "bottom-left") == (24, 800 - 200 - 24)
        assert ui_window._mini_position(200, 200, "bottom-right") == (1000 - 200 - 24, 800 - 200 - 24)
        assert ui_window._mini_position(200, 200, "middle-right") == (1000 - 200 - 24, (800 - 200) // 2)
        assert ui_window._mini_position(200, 200, "middle-left") == (24, (800 - 200) // 2)
    finally:
        del _sys.modules["win32con"]
        del _sys.modules["win32api"]


def test_start_creates_mini_window_and_survives_its_failure(monkeypatch):
    """If the mini window fails to create, the main window + webview loop
    must still start normally (best-effort, matches start()'s own
    docstring posture for native-window failures)."""
    fake_window = SimpleNamespace()
    start_calls = []
    fake_webview = SimpleNamespace(start=lambda **kw: start_calls.append(kw))
    monkeypatch.setattr(ui_window, "_create_window", lambda port, token: (fake_window, fake_webview))
    monkeypatch.setattr(
        ui_window, "_create_mini_window",
        lambda webview_mod, port, token: (_ for _ in ()).throw(RuntimeError("no mini")),
    )

    ui_window.start(7070, "tok")

    assert ui_window.is_available() is True
    assert ui_window._mini_available is False
    assert len(start_calls) == 1


def test_start_creates_mini_window_on_success(monkeypatch):
    fake_window = SimpleNamespace()
    fake_mini = SimpleNamespace()
    fake_webview = SimpleNamespace(start=lambda **kw: None)
    monkeypatch.setattr(ui_window, "_create_window", lambda port, token: (fake_window, fake_webview))
    monkeypatch.setattr(ui_window, "_create_mini_window", lambda webview_mod, port, token: fake_mini)

    ui_window.start(7070, "tok")

    assert ui_window._mini_available is True
    assert ui_window._mini_window is fake_mini


# ── Reload ───────────────────────────────────────────────────────────────────

def test_reload_noop_when_no_window():
    ui_window.reload()  # must not raise


def test_reload_calls_evaluate_js_on_main_window():
    calls = []
    ui_window._window = SimpleNamespace(evaluate_js=lambda js: calls.append(js))
    ui_window.reload()
    assert calls == ["location.reload()"]


def test_reload_also_reloads_mini_window_if_created():
    main_calls = []
    mini_calls = []
    ui_window._window = SimpleNamespace(evaluate_js=lambda js: main_calls.append(js))
    ui_window._mini_window = SimpleNamespace(evaluate_js=lambda js: mini_calls.append(js))
    ui_window.reload()
    assert main_calls == ["location.reload()"]
    assert mini_calls == ["location.reload()"]


def test_reload_swallows_evaluate_js_errors():
    def _raise(js):
        raise RuntimeError("window destroyed")

    ui_window._window = SimpleNamespace(evaluate_js=_raise)
    ui_window.reload()  # must not raise
