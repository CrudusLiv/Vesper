"""Native window for the orb UI -- pywebview (WebView2), given the real
process main thread by voice/main.py::run() (pywebview's webview.start()
hard-requires it; there is no bypass for running it off-thread).

The window is created once, shown automatically when webview.start()
initializes the GUI loop, and kept alive for the process lifetime: the
native close button hides it instead of destroying it (see _on_closing),
so voice/ui_server.py's open_window()/ensure_window_open() can just call
show() again rather than recreating a window or a browser subprocess.
(window.show() must never be called before webview.start() has run --
pywebview's Window API methods block on a readiness event that only gets
set once the real GUI loop is initialized, and time out with
WebViewException('Main window failed to start') otherwise.)

If pywebview/WebView2 aren't available, start() returns without blocking,
is_available() stays False forever, and voice/ui_server.py falls back to
its Edge/Chrome subprocess launch.

A second, small always-on-top window (the "mini" popup) is created
alongside the main one -- pywebview runs one GUI loop per process, so
every window has to exist before webview.start() is called. It points at
`/?mini=1`, a stripped-down view of the same orb.html (see that file's
`body.mini` CSS and `#mini-capsule`), and is shown/resynced/hidden by
set_conversation_state() below for every listening/thinking/speaking/idle
state change -- but only when the main window isn't already visible
(tracked via _main_visible below), since the full window already shows
the same state and a second indicator would be redundant.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_window = None
_available = False
_main_visible = True  # the main window is shown by default once created

_mini_window = None
_mini_available = False
_mini_visible = False
_mini_hide_timer: threading.Timer | None = None

# The mini window shows a compact conversation-presence capsule (CSS, not the
# Three.js orb -- see voice/static/orb.html's #mini-capsule) docked to a
# screen edge. The window is sized to exactly the pill, and the pill fills it
# edge to edge, so there is no leftover window background left to paint:
# pywebview's default min_size of (200, 100) silently inflated this window
# past the size we asked for, and that oversized near-black window *was* the
# black box showing behind the pill. min_size below is what keeps it honest.
# Transparent WebView2 windows are not an alternative -- they clip/offset
# their content inside the WinForms host -- so the window's own corners are
# rounded to match the pill's instead; see _round_mini_window().
_MINI_WIDTH = 172
_MINI_HEIGHT = 54
_MINI_MARGIN = 24

# DWM corner rounding for the mini window (Windows 11+); see
# _round_mini_window(). DWM picks the radius (~8px) and it can't be set, so
# .mc-pill's border-radius in orb.html is matched to it rather than the
# other way round.
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_ROUND = 2

# States that keep the mini capsule on screen -- everything else (idle,
# error) slides it away. Mirrors the values voice/main.py and voice/brain.py
# emit via {"type": "state", "value": ...}.
_MINI_ACTIVE_STATES = {"listening", "thinking", "speaking"}
_MINI_SLIDE_MS = 400


def is_available() -> bool:
    """True once the native window has been created successfully."""
    return _available


def show() -> None:
    """Bring the native window to front. No-op if it was never created."""
    global _main_visible
    if _window is not None:
        _window.show()
        _main_visible = True


def start(port: int, token: str) -> None:
    """Create the native window(s) and run pywebview's GUI loop on the
    calling thread -- must be called from the process's real main thread.
    Blocks for the rest of the process's life on success. Returns (without
    blocking) if window creation fails, e.g. no WebView2 runtime -- the
    caller is expected to fall back to voice/ui_server.py's Edge/Chrome
    subprocess launch in that case."""
    global _window, _available, _mini_window, _mini_available
    try:
        window, webview_mod = _create_window(port, token)
    except Exception:
        logger.exception("[ui_window] native window unavailable, falling back to browser launch")
        return
    _window = window
    _available = True

    try:
        _mini_window = _create_mini_window(webview_mod, port, token)
        _mini_available = True
    except Exception:
        logger.exception("[ui_window] mini speaking-popup window unavailable")

    # private_mode defaults to True, which hands WebView2 a throwaway
    # user-data folder every launch -- so the orb's microphone permission
    # grant is wiped and re-prompted on each start. Pin a persistent
    # profile dir so the grant sticks.
    from voice import config as cfg
    storage_path = cfg.get_data_dir() / "webview2"
    storage_path.mkdir(parents=True, exist_ok=True)
    webview_mod.start(private_mode=False, storage_path=str(storage_path))


def set_conversation_state(value: str) -> None:
    """Show, resync, or hide the mini conversation-presence capsule for a
    new state value. Called from two places: voice/ui_server.py::
    post_event() on every `state` broadcast (listening/thinking/speaking/
    idle/error) for conversational turns, AND voice/tts.py's
    _on_speak_start/_on_speak_end directly, since proactive/heartbeat
    speech (voice/main.py::_start_proactive_speaker) calls speak() without
    ever emitting a `state` event -- audio playback is the only signal
    available for that path. The two calls overlap harmlessly for a normal
    conversational turn (redundant resync, not a conflict).

    No-op unless the mini window exists, the main window is hidden, and
    speaking_popup_enabled is on (config re-read every call so a live
    Settings toggle applies without a restart).

    The capsule's visuals are pure CSS keyed off body[data-state] (set
    synchronously by orb.html's setState(), independent of any render
    loop) rather than the Three.js orb canvas -- a hidden WebView2 window
    throttles requestAnimationFrame, which is why the old shrunk-orb mini
    popup could surface stuck on a stale frame. Setting body[data-state]
    right before the slide-in class guarantees the very first visible
    frame is already correct."""
    global _mini_visible, _mini_hide_timer
    if not _mini_available or _main_visible:
        return
    from voice import config as cfg
    if not cfg.load().get("speaking_popup_enabled", True):
        return

    if _mini_hide_timer is not None:
        _mini_hide_timer.cancel()
        _mini_hide_timer = None

    active = value in _MINI_ACTIVE_STATES
    try:
        if active:
            if not _mini_visible:
                _mini_window.show()
                _round_mini_window(_mini_window)
                _mini_visible = True
            _mini_window.evaluate_js(
                f"document.body.dataset.state = {value!r};"
                "requestAnimationFrame(() => document.body.classList.add('mini-show'));"
            )
        elif _mini_visible:
            _mini_window.evaluate_js("document.body.classList.remove('mini-show')")

            def _finish_hide() -> None:
                global _mini_visible
                try:
                    _mini_window.hide()
                finally:
                    _mini_visible = False

            _mini_hide_timer = threading.Timer(_MINI_SLIDE_MS / 1000, _finish_hide)
            _mini_hide_timer.daemon = True
            _mini_hide_timer.start()
    except Exception:
        logger.exception("[ui_window] set_conversation_state failed")


def reload() -> None:
    """Reload the served page in place -- for settings baked into the HTML
    at request time (e.g. ui_render_mode) that a live WS push can't apply.
    Uses the page's own JS rather than window.load_url() so it doesn't need
    to reconstruct the URL/token. Safe no-op for any window never created."""
    for win in (_window, _mini_window):
        if win is None:
            continue
        try:
            win.evaluate_js("location.reload()")
        except Exception:
            logger.exception("[ui_window] reload failed")


def _on_closing(window) -> bool:
    """Wired to window.events.closing: hide instead of destroy, and cancel
    the actual close (pywebview treats a False return as 'don't close')."""
    global _main_visible
    _main_visible = False
    window.hide()
    return False


def _create_window(port: int, token: str):
    """Import pywebview and create the main window (shown by default once
    the GUI loop starts -- see start()). Split out from start() so tests
    can monkeypatch this one call to simulate success/failure without a
    real WebView2 runtime."""
    import webview

    url = f"http://127.0.0.1:{port}?t={token}"
    window = webview.create_window("Vesper", url, width=900, height=700)
    window.events.closing += lambda: _on_closing(window)
    return window, webview


def _mini_position(width: int, height: int, corner: str) -> tuple[int, int]:
    """Screen-corner coordinates for the mini window, from the Windows
    desktop resolution (win32api -- pywebview's own screen query is only
    populated once the GUI loop is already running, too late for
    create_window()'s x/y arguments)."""
    import win32api
    import win32con
    sw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    sh = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    x = sw - width - _MINI_MARGIN if "right" in corner else _MINI_MARGIN
    if "middle" in corner:
        y = (sh - height) // 2
    else:
        y = sh - height - _MINI_MARGIN if "bottom" in corner else _MINI_MARGIN
    return x, y


def _round_mini_window(window) -> None:
    """Ask DWM to round the mini window's corners, so the pill's rounded
    edge isn't squared off by the native window behind it.

    SetWindowRgn does not work here: WebView2 renders through
    DirectComposition, whose visuals ignore a classic HWND region, so the
    square corners paint straight back over the clip on the next repaint
    (any state change or running bar animation). DWM's own corner
    preference is applied by the compositor itself, so it survives.

    Windows 10 has no such attribute and the call simply fails -- corners
    stay square there, which is cosmetic only: the window is sized to the
    pill either way, so no backdrop is exposed.

    Re-applied on every show() because pywebview creates hidden windows by
    toggling WinForms' Opacity (winforms.py::create_window), which can
    recreate the handle and drop attributes set earlier."""
    try:
        import ctypes
        hwnd = window.native.Handle.ToInt32()
        preference = ctypes.c_int(_DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(preference), ctypes.sizeof(preference),
        )
    except Exception:
        logger.exception("[ui_window] failed to round mini window corners")


def _create_mini_window(webview_mod, port: int, token: str):
    """Create the small always-on-top conversation-presence popup window,
    hidden until set_conversation_state() shows it."""
    from voice import config as cfg
    corner = cfg.load().get("speaking_popup_corner", "middle-right")
    x, y = _mini_position(_MINI_WIDTH, _MINI_HEIGHT, corner)
    url = f"http://127.0.0.1:{port}/?mini=1&t={token}"
    return webview_mod.create_window(
        "Vesper — speaking", url,
        width=_MINI_WIDTH, height=_MINI_HEIGHT, x=x, y=y,
        min_size=(_MINI_WIDTH, _MINI_HEIGHT),
        frameless=True, on_top=True, hidden=True, easy_drag=False,
        resizable=False, shadow=False, background_color="#100e16",
    )
