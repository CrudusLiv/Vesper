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
