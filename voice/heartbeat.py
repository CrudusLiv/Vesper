"""Background heartbeat — posts notices and queues proactive spoken text.

Per-tick (every heartbeat_interval_minutes, default 30):
  1. Upcoming calendar events (today via gcal_int)
  2. Unread email count (gmail_int)
  3. Upcoming deadlines (Dynamous/Memory/DEADLINES.md)

When speak_queue is provided and proactive_tts is true:
  4. Morning briefing (once per day at briefing_time)
  5. Evening wrap-up (once per day at wrap_time)
  6. Pre-event nudge (nudge_minutes before each calendar event)

Notices are written to .claude/data/voice_notices.jsonl.
Spoken text is pushed to speak_queue as plain str items.
"""
from __future__ import annotations

import contextlib
import io
import json
import queue as _queue_mod
import threading
from datetime import date, datetime, timedelta, timezone
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
    try:
        from voice import tray
        title = "Vesper [!]" if level == "URGENT" else "Vesper"
        tray.notify(title, text)
    except Exception:
        pass


def _fetch_events(days: int = 1, max_results: int = 10) -> list[dict]:
    """Fetch calendar events; returns [] on any error."""
    try:
        import sys
        sys.path.insert(0, str(_ROOT / ".claude" / "scripts"))
        from integrations import gcal_int  # type: ignore
        return gcal_int.upcoming(days=days, max_results=max_results) or []
    except Exception:
        return []


def _fetch_deadlines() -> list[str]:
    """Return non-header deadline lines from DEADLINES.md."""
    try:
        p = _ROOT / "Dynamous" / "Memory" / "DEADLINES.md"
        if not p.exists():
            return []
        return [
            ln.strip()
            for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith(("#", ">", "`"))
        ]
    except Exception:
        return []


def _check_calendar() -> list[str]:
    try:
        events = _fetch_events(days=1, max_results=10)
        if not events:
            return []
        lines = [f"{e.get('start', '')[:16]}  {e.get('summary', '(no title)')}" for e in events[:3]]
        return [f"Calendar: {'; '.join(lines)}"[:120]]
    except Exception:
        return []


def _check_email() -> list[str]:
    _sink = io.StringIO()
    try:
        import sys
        sys.path.insert(0, str(_ROOT / ".claude" / "scripts"))
        from integrations import gmail_int  # type: ignore
        with contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):
            msgs = gmail_int.list_recent(days=1, max_results=5)
        if msgs:
            return [f"Email: {len(msgs)} new message(s) in the last 24h"]
    except Exception:
        pass
    return []


def _check_deadlines() -> list[str]:
    lines = _fetch_deadlines()
    if lines:
        snippet = "; ".join(lines[:2])
        return [f"Deadlines: {snippet[:120]}"]
    return []


def _tick() -> None:
    notices: list[str] = []
    notices.extend(_check_calendar())
    notices.extend(_check_email())
    notices.extend(_check_deadlines())
    for text in notices:
        _post(text)


class Heartbeat:
    """Background daemon thread. Calls _tick() each interval and schedules
    proactive spoken briefings when speak_queue is provided."""

    def __init__(
        self,
        interval_minutes: int = 30,
        speak_queue: "_queue_mod.Queue[str] | None" = None,
        proactive_tts: bool = True,
    ) -> None:
        self._interval = interval_minutes * 60
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._speak_queue = speak_queue
        self._proactive_tts = proactive_tts

        # Once-per-day guards — pre-mark as done if we're past the window,
        # so a mid-day restart doesn't re-speak an already-delivered briefing.
        _now = datetime.now(_KL)
        _today = _now.date()
        try:
            from voice import config as _cfg
            _conf = _cfg.load()
            _bh, _bm = (int(x) for x in _conf.get("briefing_time", "09:00").split(":"))
            _wh, _wm = (int(x) for x in _conf.get("wrap_time", "21:00").split(":"))
        except Exception:
            _bh, _bm, _wh, _wm = 9, 0, 21, 0
        _past_briefing = _now.hour > _bh or (_now.hour == _bh and _now.minute >= _bm)
        _past_wrap     = _now.hour > _wh or (_now.hour == _wh and _now.minute >= _wm)
        self._briefing_done_date: date | None = _today if _past_briefing else None
        self._wrap_done_date:     date | None = _today if _past_wrap     else None

        # Nudge deduplication (reset each day)
        self._nudged_events: set[str] = set()
        self._nudge_reset_date: date | None = None

    def _speak(self, text: str) -> None:
        if self._speak_queue is not None and self._proactive_tts:
            try:
                self._speak_queue.put_nowait(text)
            except Exception:
                pass

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
        try:
            if not self._is_quiet():
                _tick()
                self._run_scheduled()
        except Exception as _e:
            print(f"[heartbeat] tick error: {_e}", flush=True)

        while not self._stop.wait(self._interval):
            try:
                if not self._is_quiet():
                    _tick()
                    self._run_scheduled()
            except Exception as _e:
                print(f"[heartbeat] tick error: {_e}", flush=True)

    def _run_scheduled(self) -> None:
        for task in (self._morning_briefing, self._evening_wrap, self._check_nudges):
            try:
                task()
            except Exception as _e:
                print(f"[heartbeat] {task.__name__} error: {_e}", flush=True)

    def _morning_briefing(self) -> None:
        from voice import config as cfg
        conf = cfg.load()
        if not conf.get("briefing_enabled", True):
            return

        now = datetime.now(_KL)
        today = now.date()
        if self._briefing_done_date == today:
            return

        bh, bm = (int(x) for x in conf.get("briefing_time", "09:00").split(":"))
        if now.hour < bh or (now.hour == bh and now.minute < bm):
            return

        self._briefing_done_date = today

        parts: list[str] = ["Good morning."]
        events = _fetch_events(days=1, max_results=5)
        if events:
            strs = []
            for e in events[:3]:
                t = e.get("start", "")[11:16] if "T" in e.get("start", "") else "all day"
                strs.append(f"{e.get('summary', '(no title)')} at {t}")
            parts.append(f"Today: {', '.join(strs)}.")
        else:
            parts.append("No events today.")

        deadlines = _fetch_deadlines()
        if deadlines:
            parts.append(f"Upcoming: {'; '.join(deadlines[:2])}.")

        text = " ".join(parts)
        self._speak(text)
        _post(text)

    def _evening_wrap(self) -> None:
        from voice import config as cfg
        conf = cfg.load()
        if not conf.get("briefing_enabled", True):
            return

        now = datetime.now(_KL)
        today = now.date()
        if self._wrap_done_date == today:
            return

        wh, wm = (int(x) for x in conf.get("wrap_time", "21:00").split(":"))
        if now.hour < wh or (now.hour == wh and now.minute < wm):
            return

        self._wrap_done_date = today

        parts: list[str] = ["Evening check-in."]
        tomorrow = today + timedelta(days=1)
        events = _fetch_events(days=2, max_results=10)
        tmr = [e for e in events if e.get("start", "")[:10] == str(tomorrow)]
        if tmr:
            t = tmr[0].get("start", "")[11:16] if "T" in tmr[0].get("start", "") else "all day"
            parts.append(f"Tomorrow starts with {tmr[0].get('summary', '(no title)')} at {t}.")
        else:
            parts.append("Nothing scheduled for tomorrow.")

        deadlines = _fetch_deadlines()
        if deadlines:
            parts.append(f"Don't forget: {deadlines[0]}.")

        text = " ".join(parts)
        self._speak(text)
        _post(text)

    def _check_nudges(self) -> None:
        from voice import config as cfg
        conf = cfg.load()
        if not conf.get("nudge_enabled", True):
            return

        nudge_min = int(conf.get("nudge_minutes", 15))
        now = datetime.now(_KL)
        today = now.date()

        if self._nudge_reset_date != today:
            self._nudged_events.clear()
            self._nudge_reset_date = today

        for event in _fetch_events(days=1, max_results=10):
            key = f"{event.get('start', '')}|{event.get('summary', '')}"
            if key in self._nudged_events:
                continue
            start_str = event.get("start", "")
            if "T" not in start_str:
                continue  # all-day event — no time-based nudge
            try:
                event_dt = datetime.fromisoformat(start_str)
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=_KL)
                delta = (event_dt - now).total_seconds() / 60
                if 0 < delta <= nudge_min:
                    self._nudged_events.add(key)
                    mins = int(delta)
                    text = (
                        f"Heads up — {event.get('summary', 'an event')} starts in "
                        f"{mins} minute{'s' if mins != 1 else ''}."
                    )
                    self._speak(text)
                    _post(text, level="URGENT")
            except Exception:
                continue

    @staticmethod
    def _is_quiet() -> bool:
        try:
            from voice import config as cfg
            return cfg.is_quiet_hours()
        except Exception:
            return False
