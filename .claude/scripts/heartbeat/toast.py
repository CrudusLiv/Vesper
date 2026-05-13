"""Windows toast notifications via winotify. Used for Discord pings only
(see Section 2 of the 2026-05-12 restructure design). Other heartbeat
notifications still go through notify.py → Discord DM.

This module degrades cleanly on non-Windows platforms or if winotify
isn't installed: callers get a logged warning and no exception."""
from __future__ import annotations

import sys

_AVAILABLE: bool | None = None
_ICON_PATH: str | None = None


def _check_available() -> bool:
    global _AVAILABLE
    if _AVAILABLE is not None:
        return _AVAILABLE
    if not sys.platform.startswith("win"):
        _AVAILABLE = False
        return False
    try:
        import winotify  # noqa: F401
    except ImportError:
        _AVAILABLE = False
        return False
    _AVAILABLE = True
    return True


def show(title: str, body: str) -> bool:
    """Fire a Windows toast. Returns True if delivered, False if skipped
    (non-Windows, winotify missing, or the call raised)."""
    if not _check_available():
        print(f"[toast] skipped (winotify unavailable): {title}", file=sys.stderr)
        return False
    try:
        from winotify import Notification
        n = Notification(
            app_id="Second Brain",
            title=title[:64],
            msg=body[:200],
        )
        n.show()
        return True
    except Exception as exc:
        print(f"[toast] failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False
