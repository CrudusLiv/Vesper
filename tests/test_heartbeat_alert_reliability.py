"""Alert-reliability fixes: honest briefings when the calendar is unreachable,
nudges that survive quiet hours and a missed window."""
from __future__ import annotations

import queue
from datetime import datetime, timedelta, timezone

from voice import config as cfg
from voice import heartbeat as hb_mod
from voice.heartbeat import Heartbeat

UTC = timezone.utc


def _fixed_datetime(fixed):
    class _F(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed
    return _F


def _env(tmp_path, monkeypatch, conf):
    monkeypatch.setattr(cfg, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(cfg, "load", lambda: dict(conf))
    monkeypatch.setattr(cfg, "get_vault_dir", lambda: None)
    posts = []
    monkeypatch.setattr(hb_mod, "_post", lambda text, level="INFO": posts.append((text, level)))
    monkeypatch.setattr(hb_mod, "_fetch_reminders", lambda *a, **k: [])
    return posts


def _hb():
    q: "queue.Queue[str]" = queue.Queue()
    return Heartbeat(interval_minutes=30, speak_queue=q, proactive_tts=True, idle_fn=lambda: None), q


def _trigger_conf(now):
    t = (now - timedelta(minutes=2)).strftime("%H:%M")
    return {"timezone_offset_hours": 0, "briefing_enabled": True, "briefing_time": t, "wrap_time": t}


def _boom(*a, **k):
    raise RuntimeError("google auth dead")


def test_morning_briefing_admits_calendar_failure(tmp_path, monkeypatch):
    now = datetime.now(UTC)
    _env(tmp_path, monkeypatch, _trigger_conf(now))
    monkeypatch.setattr(hb_mod, "_fetch_events", _boom)
    hb, q = _hb()
    hb._morning_briefing()
    text = q.get_nowait()
    assert "Couldn't reach your calendar" in text
    assert "No events today" not in text


def test_morning_briefing_still_says_no_events_when_calendar_ok(tmp_path, monkeypatch):
    now = datetime.now(UTC)
    _env(tmp_path, monkeypatch, _trigger_conf(now))
    monkeypatch.setattr(hb_mod, "_fetch_events", lambda *a, **k: [])
    hb, q = _hb()
    hb._morning_briefing()
    assert "No events today" in q.get_nowait()


def test_evening_wrap_admits_calendar_failure(tmp_path, monkeypatch):
    now = datetime.now(UTC)
    _env(tmp_path, monkeypatch, _trigger_conf(now))
    monkeypatch.setattr(hb_mod, "_fetch_events", _boom)
    hb, q = _hb()
    hb._evening_wrap()
    text = q.get_nowait()
    assert "Couldn't reach your calendar" in text
    assert "Nothing scheduled" not in text


def test_fetch_events_strict_reraises_nonstrict_swallows(monkeypatch):
    import integrations.gcal_int as gcal_int
    monkeypatch.setattr(gcal_int, "upcoming", _boom)
    assert hb_mod._fetch_events() == []
    try:
        hb_mod._fetch_events(strict=True)
    except RuntimeError:
        return
    raise AssertionError("strict=True should re-raise")


def test_missed_nudge_window_gets_a_late_heads_up(tmp_path, monkeypatch):
    now = datetime(2026, 7, 7, 8, 4, tzinfo=UTC)
    posts = _env(tmp_path, monkeypatch, {"timezone_offset_hours": 0, "nudge_enabled": True, "nudge_minutes": 15})
    monkeypatch.setattr(hb_mod, "datetime", _fixed_datetime(now))
    start = datetime(2026, 7, 7, 8, 0, tzinfo=UTC).isoformat()
    monkeypatch.setattr(hb_mod, "_fetch_events", lambda *a, **k: [{"start": start, "summary": "Lecture"}])
    hb, q = _hb()
    hb._check_nudges()
    assert [t for t, _ in posts] == ["Lecture already started 4 minutes ago."]
    assert q.get_nowait() == "Lecture already started 4 minutes ago."
    hb._check_nudges()  # deduped
    assert len(posts) == 1


def test_event_started_long_ago_gets_no_nudge(tmp_path, monkeypatch):
    now = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
    posts = _env(tmp_path, monkeypatch, {"timezone_offset_hours": 0, "nudge_enabled": True, "nudge_minutes": 15})
    monkeypatch.setattr(hb_mod, "datetime", _fixed_datetime(now))
    start = datetime(2026, 7, 7, 8, 0, tzinfo=UTC).isoformat()
    monkeypatch.setattr(hb_mod, "_fetch_events", lambda *a, **k: [{"start": start, "summary": "Lecture"}])
    hb, _ = _hb()
    hb._check_nudges()
    assert posts == []


def test_run_scheduled_only_runs_named_tasks(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(cfg, "load", lambda: {"timezone_offset_hours": 0})
    hb, _ = _hb()
    calls = []
    for _n, method_name, _m, _k in Heartbeat._SCHEDULE:
        monkeypatch.setattr(hb, method_name, (lambda mn: lambda: calls.append(mn))(method_name))
    hb._run_scheduled(only=("nudges",))
    assert calls == ["_check_nudges"]


def _quiet_env(tmp_path, monkeypatch, hour, minute):
    monkeypatch.setattr(cfg, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(cfg, "load", lambda: {"timezone_offset_hours": 0, "nudge_quiet_floor": "07:00"})
    monkeypatch.setattr(hb_mod, "datetime", _fixed_datetime(datetime(2026, 7, 7, hour, minute, tzinfo=UTC)))
    hb, _ = _hb()
    ran = []
    monkeypatch.setattr(hb, "_run_scheduled", lambda only=None: ran.append(only))
    return hb, ran


def test_quiet_hours_nudges_run_after_floor(tmp_path, monkeypatch):
    hb, ran = _quiet_env(tmp_path, monkeypatch, 7, 30)
    hb._nudge_in_quiet_hours()
    assert ran == [("nudges",)]


def test_quiet_hours_nudges_silent_before_floor(tmp_path, monkeypatch):
    hb, ran = _quiet_env(tmp_path, monkeypatch, 3, 0)
    hb._nudge_in_quiet_hours()
    assert ran == []


def test_poll_once_in_quiet_hours_only_nudges(tmp_path, monkeypatch):
    hb, ran = _quiet_env(tmp_path, monkeypatch, 7, 30)
    monkeypatch.setattr(Heartbeat, "_is_quiet", staticmethod(lambda: True))
    monkeypatch.setattr(hb, "_check_activity", lambda: None)
    monkeypatch.setattr(hb, "_check_idle_return", lambda gap: (_ for _ in ()).throw(AssertionError("must not run in quiet hours")))
    hb._poll_once()
    assert ran == [("nudges",)]
