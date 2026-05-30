"""Tests for schedule_parser module."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import schedule_parser

_SAMPLE_ENTRIES = [
    {"course": "CS101", "days": ["Mon", "Wed", "Fri"], "start": "08:00", "end": "09:30", "type": "class"},
    {"course": "MAT101", "days": ["Tue", "Thu"], "start": "10:00", "end": "11:30", "type": "class"},
]


def test_parse_timetable_returns_entries_and_summary():
    with patch("schedule_parser.llm.call_json", return_value=_SAMPLE_ENTRIES):
        entries, summary = schedule_parser.parse_timetable("some timetable")
    assert entries == _SAMPLE_ENTRIES
    assert "CS101" in summary
    assert "Mon/Wed/Fri" in summary
    assert "MAT101" in summary
    assert "Tue/Thu" in summary


def test_parse_timetable_raises_on_llm_none():
    with patch("schedule_parser.llm.call_json", return_value=None):
        with pytest.raises(ValueError, match="empty or malformed"):
            schedule_parser.parse_timetable("bad text")


def test_parse_timetable_raises_on_empty_list():
    with patch("schedule_parser.llm.call_json", return_value=[]):
        with pytest.raises(ValueError):
            schedule_parser.parse_timetable("empty")


def test_parse_timetable_raises_on_malformed_entries():
    with patch("schedule_parser.llm.call_json", return_value=[{}]):
        with pytest.raises(ValueError):
            schedule_parser.parse_timetable("bad entries")


def test_write_schedule_creates_file(tmp_vault):
    schedule_parser.write_schedule(_SAMPLE_ENTRIES)
    path = tmp_vault / "SCHEDULE.md"
    assert path.exists()


def test_write_schedule_fresh_uses_tbd_semester(tmp_vault):
    schedule_parser.write_schedule(_SAMPLE_ENTRIES)
    content = (tmp_vault / "SCHEDULE.md").read_text(encoding="utf-8")
    assert "semester: TBD" in content


def test_write_schedule_sets_updated_today(tmp_vault):
    from datetime import date
    schedule_parser.write_schedule(_SAMPLE_ENTRIES)
    content = (tmp_vault / "SCHEDULE.md").read_text(encoding="utf-8")
    assert f"updated: {date.today().isoformat()}" in content


def test_write_schedule_day_breakdown_has_sections(tmp_vault):
    schedule_parser.write_schedule(_SAMPLE_ENTRIES)
    content = (tmp_vault / "SCHEDULE.md").read_text(encoding="utf-8")
    assert "## Day Breakdown" in content
    assert "### Monday" in content
    assert "### Wednesday" in content
    assert "### Friday" in content
    assert "### Tuesday" in content
    assert "### Thursday" in content


def test_write_schedule_day_breakdown_has_class_lines(tmp_vault):
    schedule_parser.write_schedule(_SAMPLE_ENTRIES)
    content = (tmp_vault / "SCHEDULE.md").read_text(encoding="utf-8")
    assert "08:00–09:30 CS101 (class)" in content
    assert "10:00–11:30 MAT101 (class)" in content


_GAPPED_ENTRIES = [
    {"course": "CS101", "days": ["Mon"], "start": "08:00", "end": "09:30", "type": "class"},
    {"course": "CS102", "days": ["Mon"], "start": "11:00", "end": "12:30", "type": "class"},
]


def test_write_schedule_free_slot_between_classes(tmp_vault):
    schedule_parser.write_schedule(_GAPPED_ENTRIES)
    content = (tmp_vault / "SCHEDULE.md").read_text(encoding="utf-8")
    # 09:30–11:00 = 90 min = 1h 30m
    assert "09:30–11:00 — free (1h 30m)" in content


def test_write_schedule_preserves_semester_on_overwrite(tmp_vault):
    (tmp_vault / "SCHEDULE.md").write_text(
        "---\nsemester: 2026-S1\nupdated: 2026-01-01\n---\n\n## Day Breakdown\n\n### Monday\n- 08:00 CS50\n",
        encoding="utf-8",
    )
    schedule_parser.write_schedule(_SAMPLE_ENTRIES)
    content = (tmp_vault / "SCHEDULE.md").read_text(encoding="utf-8")
    assert "semester: 2026-S1" in content


def test_write_schedule_weekly_grid_shows_course_in_correct_cell(tmp_vault):
    schedule_parser.write_schedule(_SAMPLE_ENTRIES)
    content = (tmp_vault / "SCHEDULE.md").read_text(encoding="utf-8")
    assert "## Weekly Grid" in content
    for line in content.splitlines():
        if line.startswith("| 08:00"):
            assert line.count("CS101") == 3
            break
    else:
        pytest.fail("08:00 row not found in Weekly Grid")


def test_has_existing_schedule_false_when_file_missing(tmp_vault):
    assert schedule_parser.has_existing_schedule() is False


def test_has_existing_schedule_false_when_no_day_sections(tmp_vault):
    (tmp_vault / "SCHEDULE.md").write_text(
        "---\nsemester: TBD\n---\n\n## Day Breakdown\n\n<!-- placeholder -->\n",
        encoding="utf-8",
    )
    assert schedule_parser.has_existing_schedule() is False


def test_has_existing_schedule_true_after_write(tmp_vault):
    schedule_parser.write_schedule(_SAMPLE_ENTRIES)
    assert schedule_parser.has_existing_schedule() is True


def test_read_pending_returns_none_when_missing(tmp_vault):
    assert schedule_parser.read_pending() is None


def test_write_and_read_pending_roundtrip(tmp_vault):
    schedule_parser.write_pending(_SAMPLE_ENTRIES)
    result = schedule_parser.read_pending()
    assert result == _SAMPLE_ENTRIES


def test_clear_pending_removes_file(tmp_vault):
    schedule_parser.write_pending(_SAMPLE_ENTRIES)
    schedule_parser.clear_pending()
    assert schedule_parser.read_pending() is None


def test_read_pending_returns_none_on_malformed_json(tmp_vault):
    import os
    data_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")) / ".claude" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "schedule_pending.json").write_text("not json", encoding="utf-8")
    assert schedule_parser.read_pending() is None
