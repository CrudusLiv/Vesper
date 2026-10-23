"""Rollup fixes: only the target day's turns are distilled (brain.history
spans days), and a missed rollup is caught up into the missed day's note."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from voice import config as cfg
from voice import heartbeat as hb_mod
from voice.heartbeat import Heartbeat

KL = timezone(timedelta(hours=8))
CONF = {"timezone_offset_hours": 8, "vault_rollup_enabled": True, "vault_rollup_time": "23:30"}


def _env(tmp_path, monkeypatch, hour, minute):
    monkeypatch.setattr(cfg, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(cfg, "load", lambda: dict(CONF))
    fixed_now = datetime(2026, 7, 7, hour, minute, tzinfo=KL)
    monkeypatch.setattr(hb_mod, "datetime", type("F", (), {"now": staticmethod(lambda tz=None: fixed_now)}))
    blocks = []
    monkeypatch.setattr(
        hb_mod.vault_daily, "append_block",
        lambda label, content, day=None: blocks.append((label, content, day)),
    )
    monkeypatch.setattr(hb_mod.finance_tracker, "day_summary", lambda when=None: "")
    monkeypatch.setattr(hb_mod.core_llm, "is_available", lambda: True)
    return blocks


def _ts(y, m, d, h):
    return datetime(y, m, d, h, 0, tzinfo=KL).timestamp()


def test_distill_only_includes_the_target_days_turns(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, 23, 35)
    seen = {}
    monkeypatch.setattr(hb_mod.core_llm, "call", lambda transcript, **kw: seen.update(t=transcript) or "### Facts\n- x")

    class _Brain:
        history = [
            {"role": "user", "content": "OLD-DAY-MESSAGE", "ts": _ts(2026, 7, 6, 10)},
            {"role": "user", "content": "TODAY-MESSAGE", "ts": _ts(2026, 7, 7, 10)},
            {"role": "user", "content": "UNSTAMPED-MESSAGE"},
        ]

    hb = Heartbeat(interval_minutes=30, idle_fn=lambda: None, brain=_Brain())
    hb._check_vault_daily_rollup()
    assert "TODAY-MESSAGE" in seen["t"]
    assert "UNSTAMPED-MESSAGE" in seen["t"]
    assert "OLD-DAY-MESSAGE" not in seen["t"]


def test_distill_returns_empty_when_nothing_from_that_day(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, 23, 35)
    monkeypatch.setattr(hb_mod.core_llm, "call", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no call expected")))

    class _Brain:
        history = [{"role": "user", "content": "old", "ts": _ts(2026, 7, 5, 10)}]

    hb = Heartbeat(interval_minutes=30, idle_fn=lambda: None, brain=_Brain())
    assert hb._distill_voice_history(date(2026, 7, 7)) == ""


def test_missed_rollup_is_caught_up_into_yesterdays_note(tmp_path, monkeypatch):
    blocks = _env(tmp_path, monkeypatch, 9, 5)  # app started next morning
    (tmp_path / "voice_notices.jsonl").write_text(
        '{"ts": "2026-07-06T10:15:00+08:00", "text": "missed day notice"}\n', encoding="utf-8")
    hb = Heartbeat(interval_minutes=30, idle_fn=lambda: None)
    hb._vault_rollup_done_date = date(2026, 7, 4)  # last rollup two nights ago
    hb._check_vault_daily_rollup()
    assert blocks == [("Heartbeat digest", "- [10:15] missed day notice", "2026-07-06")]
    assert hb._vault_rollup_done_date == date(2026, 7, 6)


def test_no_catchup_on_first_ever_run(tmp_path, monkeypatch):
    blocks = _env(tmp_path, monkeypatch, 9, 5)
    hb = Heartbeat(interval_minutes=30, idle_fn=lambda: None)
    hb._check_vault_daily_rollup()
    assert blocks == []
    assert hb._vault_rollup_done_date is None


def test_normal_rollup_still_targets_today_without_day_kwarg(tmp_path, monkeypatch):
    blocks = _env(tmp_path, monkeypatch, 23, 35)
    (tmp_path / "voice_notices.jsonl").write_text(
        '{"ts": "2026-07-07T10:15:00+08:00", "text": "today notice"}\n', encoding="utf-8")
    hb = Heartbeat(interval_minutes=30, idle_fn=lambda: None)
    hb._vault_rollup_done_date = date(2026, 7, 6)
    hb._check_vault_daily_rollup()
    assert blocks == [("Heartbeat digest", "- [10:15] today notice", None)]
