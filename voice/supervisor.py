"""In-process daemon-thread supervision.

A background thread whose target raises dies silently by default -- the
process keeps running, but that feature is just gone until something else
happens to restart the whole app. supervise() wraps a thread target so a
crash gets logged, surfaced as a notice, and retried with backoff instead.

See docs/superpowers/specs/2026-09-21-thread-supervisor-design.md.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

_MIN_BACKOFF_S = 5
_MAX_BACKOFF_S = 300
_FAST_FAIL_WINDOW_S = 60

_registry: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def registry_snapshot() -> dict[str, dict[str, Any]]:
    """A copy of the current supervision registry -- safe to read from any
    thread (e.g. the boot_checks probe)."""
    with _lock:
        return {name: dict(fields) for name, fields in _registry.items()}


def _entry(name: str) -> dict[str, Any]:
    """Caller holds _lock. setdefault, not index: the registry can be reset
    (tests) while a supervised thread is still running."""
    return _registry.setdefault(
        name, {"alive": False, "restarts": 0, "last_error": None, "last_restart_ts": None}
    )


def _record_start(name: str) -> None:
    with _lock:
        entry = _entry(name)
        entry["alive"] = True
        entry["last_restart_ts"] = time.time()


def _record_crash(name: str, exc: Exception) -> None:
    with _lock:
        entry = _entry(name)
        entry["alive"] = False
        entry["last_error"] = str(exc)
        entry["restarts"] += 1


def _record_clean_exit(name: str) -> None:
    with _lock:
        _entry(name)["alive"] = False


def _notify_crash(name: str, exc: Exception) -> None:
    print(f"[supervisor] {name} crashed: {exc!r} -- restarting", flush=True)
    try:
        from voice import heartbeat
        heartbeat._post(
            f"{name} crashed and restarted: {exc}",
            level="INFO",
            meta={"thread": name},
        )
    except Exception:
        pass  # posting a notice must never itself crash the supervisor loop


def supervise(name: str, target: Callable[..., None], *args: Any, **kwargs: Any) -> threading.Thread:
    """Run target(*args, **kwargs) on a daemon thread, supervised.

    A normal (non-exception) return from target ends supervision -- that's
    a deliberate exit (a stop_event-driven shutdown, EOF, etc.), not a
    crash. An exception is logged, notified, and retried after a backoff
    that doubles on repeated fast failures and resets once target has run
    stably for more than _FAST_FAIL_WINDOW_S. If kwargs contains a
    'stop_event' and it's already set at the moment of a crash, that crash
    is treated as part of a deliberate shutdown too, and supervision ends
    without restarting.

    Returns the *supervisor* thread, which stays alive across restarts of
    target -- callers can .join()/.is_alive() it exactly like a plain
    Thread that runs target once.
    """
    stop_event = kwargs.get("stop_event")

    def _run() -> None:
        backoff = _MIN_BACKOFF_S
        while True:
            _record_start(name)
            started = time.monotonic()
            try:
                target(*args, **kwargs)
            except Exception as exc:
                _record_crash(name, exc)
                _notify_crash(name, exc)
                if stop_event is not None and stop_event.is_set():
                    return
                if time.monotonic() - started >= _FAST_FAIL_WINDOW_S:
                    backoff = _MIN_BACKOFF_S
                time.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_S)
            else:
                _record_clean_exit(name)
                return

    thread = threading.Thread(target=_run, daemon=True, name=name)
    thread.start()
    return thread
