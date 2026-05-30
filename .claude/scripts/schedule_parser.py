"""Parse timetable text via LLM into structured schedule entries."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

from heartbeat import llm

_PARSE_PROMPT = """\
Extract all class/lecture entries from this timetable as JSON.
Return ONLY a JSON array, no other text:
[{{"course": "CS101", "days": ["Mon","Wed","Fri"], "start": "08:00", "end": "09:30", "type": "class"}}, ...]

Days must use 3-letter abbreviations: Mon Tue Wed Thu Fri Sat Sun.
Times must be HH:MM (24-hour).

Timetable:
{text}"""

_ABBR_TO_FULL = {
    "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
    "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday",
}


def _proj() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])


def _vault() -> Path:
    return _proj() / "Dynamous" / "Memory"


def _data_dir() -> Path:
    return _proj() / ".claude" / "data"


def _pending_path() -> Path:
    return _data_dir() / "schedule_pending.json"


def parse_timetable(text: str) -> tuple[list[dict], str]:
    """Parse raw timetable text via LLM. Returns (entries, human_summary).
    Raises ValueError if LLM returns empty or malformed JSON."""
    entries = llm.call_json(_PARSE_PROMPT.format(text=text), model="haiku")
    if not isinstance(entries, list) or not entries:
        raise ValueError("empty or malformed JSON from LLM")
    parts: list[str] = []
    for e in entries:
        days_str = "/".join(e.get("days", []))
        parts.append(f"{e['course']} {days_str} {e['start']}–{e['end']}")
    return entries, ", ".join(parts)
