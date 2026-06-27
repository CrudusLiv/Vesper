"""Background heartbeat — posts notices to .claude/data/voice_notices.jsonl.

Three checks per tick:
  1. Upcoming calendar events (today via gcal_int)
  2. Unread email count (gmail_int)
  3. Upcoming deadlines (Dynamous/Memory/DEADLINES.md, next 7 days)

Notices are consumed by voice/main.py at startup via _show_notices().
"""
from __future__ import annotations

import contextlib
import io
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

_KL = timezone(timedelta(hours=8))
_ROOT = Path(__file__).resolve().parents[1]
_NOTICES = _ROOT / ".claude" / "data" / "voice_notices.jsonl"


def _post(text: str, level: str = "INFO") -> None:
    entry = {
        "ts": datetime.now(_KL).isoformat(),
        "text": text,
        "level": level,
        "read": False,
    }
    _NOTICES.parent.mkdir(parents=True, exist_ok=True)
    with _NOTICES.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # Toast notification via tray (no-op when tray not running)
    try:
        from voice import tray
        title = "Vesper [!]" if level == "URGENT" else "Vesper"
        tray.notify(title, text)
    except Exception:
        pass


def _check_calendar() -> list[str]:
    try:
        import sys
        sys.path.insert(0, str(_ROOT / ".claude" / "scripts"))
        from integrations import gcal_int  # type: ignore
        events = gcal_int.upcoming(days=1, max_results=10)
        if not events:
            return []
        lines = [f"{e['start'][:16]}  {e['summary']}" for e in events[:3]]
        return [f"Calendar: {'; '.join(lines)}"[:120]]
    except Exception:
        return []


def _check_email() -> list[str]:
    _sink = io.StringIO()
    try:
        from integrations import gmail_int  # type: ignore
        with contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):
            msgs = gmail_int.list_recent(days=1, max_results=5)
        if msgs:
            return [f"Email: {len(msgs)} new message(s) in the last 24h"]
    except Exception:
        pass
    return []


def _check_deadlines() -> list[str]:
    try:
        deadlines_path = _ROOT / "Dynamous" / "Memory" / "DEADLINES.md"
        if not deadlines_path.exists():
            return []
        lines = [
            ln.strip()
            for ln in deadlines_path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith(("#", ">", "`"))
        ]
        if lines:
            snippet = "; ".join(lines[:2])
            return [f"Deadlines: {snippet[:120]}"]
    except Exception:
        pass
    return []


def _tick() -> None:
    notices: list[str] = []
    notices.extend(_check_calendar())
    notices.extend(_check_email())
    notices.extend(_check_deadlines())
    for text in notices:
        _post(text)


class Heartbeat:
    """Background daemon thread that calls _tick() every `interval_minutes`."""

    def __init__(self, interval_minutes: int = 30) -> None:
        self._interval = interval_minutes * 60
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="vesper-heartbeat"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        # Immediate check on startup so the first tick doesn't wait 30 min
        try:
            if not self._is_quiet():
                _tick()
        except Exception:
            pass

        while not self._stop.wait(self._interval):
            try:
                if not self._is_quiet():
                    _tick()
            except Exception:
                pass

    @staticmethod
    def _is_quiet() -> bool:
        try:
            from voice import config as cfg
            return cfg.is_quiet_hours()
        except Exception:
            return False
