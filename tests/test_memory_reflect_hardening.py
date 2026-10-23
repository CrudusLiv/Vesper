"""Reflection hardening: catch-up over missed days, code-level dedupe, source
links, mistakes lane, archive instead of unbounded growth, raw-signal
grounding, status file, and the heartbeat's health check on it."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import memory_reflect as mr  # noqa: E402
from voice import agent_tools  # noqa: E402
from voice import heartbeat as hb_mod  # noqa: E402
from voice.heartbeat import Heartbeat  # noqa: E402

KL = timezone(timedelta(hours=8))


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "STATUS", tmp_path / "state" / "reflect_status.json")
    monkeypatch.setattr(mr, "MEMORY", tmp_path / "MEMORY.md")
    monkeypatch.setattr(mr, "ARCHIVE", tmp_path / "MEMORY-archive.md")
    monkeypatch.setattr(mr, "DAILY", tmp_path / "daily")
    (tmp_path / "daily").mkdir(exist_ok=True)
    monkeypatch.setattr(mr, "curate_about", lambda: 0)


def _days_ago(n: int) -> str:
    return (datetime.now(KL) - timedelta(days=n)).strftime("%Y-%m-%d")


# ---- catch-up ---------------------------------------------------------------

def test_pending_days_first_run_is_yesterday_only(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert mr.pending_days() == [_days_ago(1)]


def test_pending_days_catches_up_after_gap(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    mr.write_status(_days_ago(4), None)
    assert mr.pending_days() == [_days_ago(3), _days_ago(2), _days_ago(1)]


def test_pending_days_caps_at_a_week_and_is_empty_when_current(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    mr.write_status(_days_ago(30), None)
    assert len(mr.pending_days()) == mr.MAX_CATCHUP_DAYS
    mr.write_status(_days_ago(1), None)
    assert mr.pending_days() == []


# ---- dedupe, source links, mistakes ----------------------------------------

def test_insert_dedupes_against_existing_text_and_within_batch():
    text = "## Lessons\n- 2026-01-01 — Atomic JSON writes prevent partial reads\n"
    out, n = mr._insert_into_section(
        text, "Lessons",
        ["atomic json writes prevent partial reads!", "New thing", "new thing", 42, "  "],
        "2026-02-02", source="2026-02-01",
    )
    assert n == 1
    assert out.count("New thing") == 1
    assert "([[2026-02-01]])" in out


def test_append_to_memory_adds_source_link_mistake_prefix_and_is_idempotent(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    mr.MEMORY.write_text("## Decisions\n\n## Lessons\n\n## Stances\n\n## Open questions\n", encoding="utf-8")
    items = {"new_decisions": ["Use X"], "new_mistakes": ["Said No events today while calendar was down"],
             "new_facts": ["Y is Z"]}
    assert mr.append_to_memory(items, source="2026-03-03") == 3
    text = mr.MEMORY.read_text(encoding="utf-8")
    assert "- 2026-03-03 — Use X ([[2026-03-03]])" in text
    assert "(mistake) Said No events today" in text and "(fact) Y is Z" in text
    assert mr.append_to_memory(items, source="2026-03-04") == 0
    assert not list(tmp_path.glob("*.tmp"))


# ---- archive ----------------------------------------------------------------

def test_archive_moves_oldest_bullets_and_loses_nothing(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    decisions = [f"- 2026-01-{i:02d} — decision {i:02d} " + "d" * 50 for i in range(1, 21)]
    lessons = [f"- 2025-12-{i:02d} — lesson {i:02d} " + "l" * 50 for i in range(1, 11)]
    original = "## Decisions\n" + "\n".join(decisions) + "\n\n## Lessons\n" + "\n".join(lessons) + "\n\n## Stances\n- keep me\n"
    mr.MEMORY.write_text(original, encoding="utf-8")
    moved = mr.archive_old_memory(max_chars=1000, target_chars=700)
    kept = mr.MEMORY.read_text(encoding="utf-8")
    archived = mr.ARCHIVE.read_text(encoding="utf-8")
    assert moved > 0 and len(kept) <= 700
    assert "keep me" in kept and "## Decisions" in kept
    assert "lesson 01" in archived          # oldest by date goes first, across sections
    assert "decision 20" in kept            # newest stays
    for line in decisions + lessons:        # every bullet is in exactly one of the two files
        assert (line in kept) != (line in archived)


def test_archive_noop_under_budget(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    mr.MEMORY.write_text("## Decisions\n- 2026-01-01 — a\n", encoding="utf-8")
    assert mr.archive_old_memory() == 0
    assert not mr.ARCHIVE.exists()


# ---- raw signals ------------------------------------------------------------

def test_gather_signals_summarizes_outcomes_denials_injections(tmp_path, monkeypatch):
    monkeypatch.setattr("voice.config.get_data_dir", lambda: tmp_path)
    rows = [
        {"ts": "2026-05-05T10:00:00+08:00", "role": "outcome", "content": "notice deleted after 3m [URGENT]: Deadline (24h): X"},
        {"ts": "2026-05-05T11:00:00+08:00", "role": "tool", "tool": "create_note", "outcome": "cancelled", "content": "[cancelled by user]"},
        {"ts": "2026-05-05T11:05:00+08:00", "role": "tool", "tool": "create_note", "outcome": "cancelled", "content": "[cancelled by user]"},
        {"ts": "2026-05-05T12:00:00+08:00", "role": "tool", "tool": "triage_inbox_tool", "outcome": "injection", "content": "injection markers: ignore_instructions"},
        {"ts": "2026-05-04T12:00:00+08:00", "role": "outcome", "content": "other day"},
    ]
    (tmp_path / "voice_audit.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out = mr.gather_signals("2026-05-05")
    assert "notice deleted after 3m" in out
    assert "create_note cancelled x2" in out
    assert "triage_inbox_tool" in out and "ignore_instructions" in out
    assert "other day" not in out


def test_gather_signals_empty_when_no_audit_log(tmp_path, monkeypatch):
    monkeypatch.setattr("voice.config.get_data_dir", lambda: tmp_path)
    assert mr.gather_signals("2026-05-05") == ""


# ---- reflect / main ---------------------------------------------------------

def test_reflect_returns_none_when_cli_unavailable(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    (mr.DAILY / "2026-05-05.md").write_text("# log", encoding="utf-8")
    monkeypatch.setattr(mr.llm, "is_available", lambda: False)
    assert mr.reflect("2026-05-05") is None


def test_reflect_empty_dict_when_no_log(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert mr.reflect("2026-05-05") == {}


def test_reflect_prompt_includes_raw_signals(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    (mr.DAILY / "2026-05-05.md").write_text("# log body", encoding="utf-8")
    monkeypatch.setattr(mr.llm, "is_available", lambda: True)
    monkeypatch.setattr(mr, "gather_signals", lambda day: "SIGNAL-TEXT")
    seen = {}
    monkeypatch.setattr(mr.llm, "call_json", lambda prompt, **kw: seen.update(p=prompt) or {})
    assert mr.reflect("2026-05-05") == {}
    assert "SIGNAL-TEXT" in seen["p"] and "log body" in seen["p"]


def test_main_failure_keeps_day_pending_and_records_error(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    mr.MEMORY.write_text("## Decisions\n", encoding="utf-8")
    mr.write_status(_days_ago(3), None)
    monkeypatch.setattr(mr, "reflect", lambda day: None)
    assert mr.main([]) == 1
    st = mr.read_status()
    assert st["ok"] is False and st["last_reflected_date"] == _days_ago(3)


def test_main_success_advances_through_every_missed_day(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    mr.MEMORY.write_text("## Decisions\n", encoding="utf-8")
    mr.write_status(_days_ago(3), None)
    seen = []
    monkeypatch.setattr(mr, "reflect", lambda day: seen.append(day) or {"new_decisions": [f"decided on {day}"]})
    monkeypatch.setattr(mr, "curate_knowledge", lambda items, source_date=None: 0)
    assert mr.main([]) == 0
    assert seen == [_days_ago(2), _days_ago(1)]
    st = mr.read_status()
    assert st["ok"] is True and st["last_reflected_date"] == _days_ago(1)
    text = mr.MEMORY.read_text(encoding="utf-8")
    assert f"decided on {_days_ago(2)}" in text and f"decided on {_days_ago(1)}" in text


# ---- heartbeat health check -------------------------------------------------

def _hb(tmp_path, monkeypatch, status):
    monkeypatch.setattr("voice.config.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("voice.config.load", lambda: {"timezone_offset_hours": 8})
    root = tmp_path / "repo"
    (root / ".claude" / "data" / "state").mkdir(parents=True)
    if status is not None:
        (root / ".claude" / "data" / "state" / "reflect_status.json").write_text(json.dumps(status), encoding="utf-8")
    monkeypatch.setattr(hb_mod, "_ROOT", root)
    posts = []
    monkeypatch.setattr(hb_mod, "_post", lambda text, level="INFO", meta=None: posts.append((text, level)))
    return Heartbeat(interval_minutes=30, idle_fn=lambda: None), posts


def _today_kl():
    return datetime.now(KL).date()


def test_health_silent_without_status_file(tmp_path, monkeypatch):
    hb, posts = _hb(tmp_path, monkeypatch, None)
    hb._check_reflection_health()
    assert posts == []


def test_health_silent_when_recent_and_ok(tmp_path, monkeypatch):
    hb, posts = _hb(tmp_path, monkeypatch, {"ok": True, "last_reflected_date": str(_today_kl() - timedelta(days=1))})
    hb._check_reflection_health()
    assert posts == []


def test_health_notifies_once_a_day_on_failure(tmp_path, monkeypatch):
    hb, posts = _hb(tmp_path, monkeypatch, {"ok": False, "error": "reflection failed for X",
                                            "last_reflected_date": str(_today_kl() - timedelta(days=1))})
    hb._check_reflection_health()
    hb._check_reflection_health()
    assert len(posts) == 1
    assert "reflection failed for X" in posts[0][0] and posts[0][1] == "URGENT"
    assert hb._reflect_health_notified == _today_kl()


def test_health_notifies_when_stale(tmp_path, monkeypatch):
    hb, posts = _hb(tmp_path, monkeypatch, {"ok": True, "last_reflected_date": str(_today_kl() - timedelta(days=5))})
    hb._check_reflection_health()
    assert len(posts) == 1 and "last success was" in posts[0][0]


# ---- outcome logging --------------------------------------------------------

def test_complete_deadline_and_reminder_log_outcomes(monkeypatch):
    logged = []
    monkeypatch.setattr(agent_tools.audit, "log", lambda role, content, **kw: logged.append((role, content, kw)))
    monkeypatch.setattr(agent_tools, "requires_confirmation", lambda name: False)
    monkeypatch.setattr(agent_tools, "complete_deadline", lambda query: "Marked done")
    monkeypatch.setattr(agent_tools, "complete_reminder", lambda title: "Marked done")
    agent_tools.complete_deadline_tool(query="passport")
    agent_tools.complete_reminder_tool(title="call mum")
    roles = [(r, kw.get("outcome")) for r, _, kw in logged]
    assert roles == [("outcome", "completed"), ("outcome", "completed")]
    assert "passport" in logged[0][1] and "call mum" in logged[1][1]


def test_notice_outcome_is_logged_with_age(monkeypatch):
    from voice import ui_server
    logged = []
    monkeypatch.setattr("voice.audit.log", lambda role, content, **kw: logged.append((role, content, kw)))
    posted = (datetime.now(KL) - timedelta(minutes=7)).isoformat()
    ui_server._log_notice_outcome({"id": "abc", "ts": posted, "level": "URGENT", "text": "Deadline (24h): X"}, "deleted")
    role, content, kw = logged[0]
    assert role == "outcome" and kw["outcome"] == "deleted"
    assert "after 7m" in content and "[URGENT]" in content and "Deadline (24h): X" in content
