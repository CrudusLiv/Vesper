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
    try:
        for e in entries:
            days_str = "/".join(e.get("days", []))
            parts.append(f"{e['course']} {days_str} {e['start']}–{e['end']}")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"empty or malformed JSON from LLM: {exc}") from exc
    return entries, ", ".join(parts)


def _parse_time(t: str) -> int:
    """HH:MM → minutes since midnight."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _fmt_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _fmt_duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def write_schedule(entries: list[dict]) -> None:
    """Write or overwrite SCHEDULE.md from parsed entries.
    Preserves existing semester: frontmatter on overwrite; uses TBD on fresh write."""
    schedule_path = _vault() / "SCHEDULE.md"

    semester = "TBD"
    if schedule_path.exists():
        existing = schedule_path.read_text(encoding="utf-8")
        m = re.search(r"^semester:\s*(.+)$", existing, re.MULTILINE)
        if m:
            semester = m.group(1).strip()

    today = date.today().isoformat()

    # Group entries by full day name, sorted by start time
    _weekdays_full = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    _weekdays_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    day_entries: dict[str, list[dict]] = {d: [] for d in _weekdays_full}
    for e in entries:
        for abbr in e.get("days", []):
            full = _ABBR_TO_FULL.get(abbr)
            if full and full in day_entries:
                day_entries[full].append(e)
    for day in day_entries:
        day_entries[day].sort(key=lambda e: _parse_time(e["start"]))

    # Weekly Grid — rows = unique start times, columns = Mon–Fri
    weekday_entries = [e for e in entries if any(d in _weekdays_abbr for d in e.get("days", []))]
    start_times = sorted(set(e["start"] for e in weekday_entries), key=_parse_time)
    grid_rows = ["| Time | Mon | Tue | Wed | Thu | Fri |", "|------|-----|-----|-----|-----|-----|"]
    if start_times:
        for st in start_times:
            cells = [st]
            for abbr in _weekdays_abbr:
                match = next((e for e in entries if e["start"] == st and abbr in e.get("days", [])), None)
                cells.append(match["course"] if match else "")
            grid_rows.append("| " + " | ".join(cells) + " |")
    else:
        grid_rows.append("|      |     |     |     |     |     |")
    grid = "\n".join(grid_rows)

    # Day Breakdown — class lines + free slots between them
    breakdown_sections: list[str] = []
    for day in _weekdays_full:
        classes = day_entries[day]
        if not classes:
            continue
        lines = [f"### {day}"]
        prev_end: int | None = None
        for cls in classes:
            start_min = _parse_time(cls["start"])
            if prev_end is not None and start_min > prev_end:
                gap = start_min - prev_end
                lines.append(
                    f"- {_fmt_time(prev_end)}–{cls['start']} — free ({_fmt_duration(gap)})"
                )
            lines.append(f"- {cls['start']}–{cls['end']} {cls['course']} ({cls['type']})")
            prev_end = _parse_time(cls["end"])
        breakdown_sections.append("\n".join(lines))

    breakdown = "\n\n".join(breakdown_sections)

    content = (
        f"---\nsemester: {semester}\nupdated: {today}\n---\n\n"
        f"## Weekly Grid\n\n{grid}\n\n"
        f"## Day Breakdown\n\n{breakdown}\n"
    )
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    schedule_path.write_text(content, encoding="utf-8")


_DAY_SECTION_RE = re.compile(
    r"^### (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
    re.MULTILINE,
)


def has_existing_schedule() -> bool:
    """True iff SCHEDULE.md contains any ### DayName sections."""
    path = _vault() / "SCHEDULE.md"
    if not path.exists():
        return False
    return bool(_DAY_SECTION_RE.search(path.read_text(encoding="utf-8")))


def read_pending() -> list[dict] | None:
    """Return pending entries from schedule_pending.json, or None if missing/malformed."""
    try:
        data = json.loads(_pending_path().read_text(encoding="utf-8"))
        return data.get("entries")
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None


def write_pending(entries: list[dict]) -> None:
    """Persist parsed entries to schedule_pending.json to await confirmation."""
    path = _pending_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "parsed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "entries": entries,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clear_pending() -> None:
    """Delete schedule_pending.json (no-ops silently if already gone)."""
    try:
        _pending_path().unlink()
    except FileNotFoundError:
        pass
