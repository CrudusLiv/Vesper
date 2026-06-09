"""Parse timetable text via LLM into structured schedule entries."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

from heartbeat import llm

_PARSE_PROMPT = """\
Extract EVERY class/lecture/tutorial entry from this timetable as JSON.
Return ONLY a JSON array, no other text:
[{{"course": "CS101", "days": ["Mon","Wed","Fri"], "start": "08:00", "end": "09:30", "type": "lecture", "location": "Room A1"}}, ...]

Rules:
- Extract every entry. Do NOT skip, drop, summarise, or invent entries.
- Emit one object per (course, day, start time). Only combine multiple days into
  one object when the SAME course runs at the SAME start AND end time AND the
  SAME location on each.
- Days must use 3-letter abbreviations: Mon Tue Wed Thu Fri Sat Sun.
- Times must be HH:MM (24-hour); convert am/pm (e.g. 2pm -> 14:00, 2:30pm -> 14:30).
- "type" is the parenthesised kind, lowercased (e.g. lecture, tutorial); default "class".
- "location" is the room/venue (e.g. EMPH, BLH2.2, ALH2.6, Online); use "" if none.
- Include every entry from the input — do not omit any. Output the JSON array only.

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
    # Sonnet, not haiku: haiku silently drops entries from dense, run-on
    # timetable strings (observed dropping 4 of 8). Schedule parsing is rare
    # (once a semester), so the extra latency/cost is worth the reliability.
    entries = llm.call_json(_PARSE_PROMPT.format(text=text), model="sonnet")
    if not isinstance(entries, list) or not entries:
        raise ValueError("empty or malformed JSON from LLM")
    parts: list[str] = []
    try:
        for e in entries:
            days_str = "/".join(e.get("days", []))
            loc = e.get("location", "")
            suffix = f" @ {loc}" if loc else ""
            parts.append(f"{e['course']} {days_str} {e['start']}–{e['end']}{suffix}")
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


# Course colour coding. Emoji squares render identically on Obsidian desktop,
# mobile, and export, and pass through to Discord. Assigned by order of first
# appearance so any future course gets a colour automatically.
_PALETTE = ["🟦", "🟩", "🟧", "🟪", "🟥", "🟨", "🟫", "⬛"]


def _course_colors(entries: list[dict]) -> dict[str, str]:
    """Map each course code to a palette emoji, by order of first appearance."""
    colors: dict[str, str] = {}
    for e in entries:
        course = e.get("course")
        if course and course not in colors:
            colors[course] = _PALETTE[len(colors) % len(_PALETTE)]
    return colors


def _strip_color(cell: str) -> str:
    """Reduce a grid cell to bare course code for the monospace Discord grid:
    drop the palette emoji and any `<br>location` second line."""
    cell = cell.split("<br>")[0]
    for emo in _PALETTE:
        cell = cell.replace(emo, "")
    return cell.strip()


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

    colors = _course_colors(entries)
    legend = " · ".join(f"{colors[c]} **{c}**" for c in colors)

    # Weekly Grid — rows = unique start times, columns = Mon–Fri, colour-coded
    # cells. Wrapped in an open [!tip] callout so Obsidian renders it as a card.
    weekday_entries = [e for e in entries if any(d in _weekdays_abbr for d in e.get("days", []))]
    start_times = sorted(set(e["start"] for e in weekday_entries), key=_parse_time)
    grid_rows = ["| Time | Mon | Tue | Wed | Thu | Fri |", "|:----:|:---:|:---:|:---:|:---:|:---:|"]
    if start_times:
        for st in start_times:
            cells = [st]
            for abbr in _weekdays_abbr:
                match = next((e for e in entries if e["start"] == st and abbr in e.get("days", [])), None)
                if not match:
                    cells.append("")
                    continue
                cell = f"{colors.get(match['course'], '')} {match['course']}".strip()
                loc = match.get("location", "")
                cells.append(f"{cell}<br>{loc}" if loc else cell)
            grid_rows.append("| " + " | ".join(cells) + " |")
    else:
        grid_rows.append("|      |     |     |     |     |     |")
    grid_block = "\n".join(["> [!tip]+ Weekly Grid"] + [f"> {ln}" for ln in grid_rows])

    # Day Breakdown — one collapsible [!example] callout per day, class lines
    # plus free slots between them. Collapsed by default (the `-` suffix).
    breakdown_sections: list[str] = []
    for day in _weekdays_full:
        classes = day_entries[day]
        if not classes:
            continue
        lines = [f"> [!example]- {day}"]
        prev_end: int | None = None
        for cls in classes:
            start_min = _parse_time(cls["start"])
            if prev_end is not None and start_min > prev_end:
                gap = start_min - prev_end
                lines.append(
                    f"> - ⬜ {_fmt_time(prev_end)}–{cls['start']} — free ({_fmt_duration(gap)})"
                )
            emo = colors.get(cls["course"], "")
            loc = cls.get("location", "")
            loc_str = f" · 📍 {loc}" if loc else ""
            lines.append(f"> - {emo} {cls['start']}–{cls['end']} **{cls['course']}** ({cls['type']}){loc_str}")
            prev_end = _parse_time(cls["end"])
        breakdown_sections.append("\n".join(lines))

    breakdown = "\n\n".join(breakdown_sections)

    body = "\n\n".join(part for part in (legend, grid_block, breakdown) if part)
    content = f"---\nsemester: {semester}\nupdated: {today}\n---\n\n{body}\n"
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    schedule_path.write_text(content, encoding="utf-8")


# Matches a day section header in either form: a plain `### Monday` heading
# (legacy files) or a `> [!example]- Monday` callout (current format).
_DAY_HEADER = r"(?:###\s+|\[!\w+\][+-]?\s+)(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b"
_DAY_SECTION_RE = re.compile(r"^>?\s*" + _DAY_HEADER, re.MULTILINE)


def has_existing_schedule() -> bool:
    """True iff SCHEDULE.md contains any day-section header (heading or callout)."""
    path = _vault() / "SCHEDULE.md"
    if not path.exists():
        return False
    return bool(_DAY_SECTION_RE.search(path.read_text(encoding="utf-8")))


def _align_grid(grid_lines: list[str]) -> str:
    """Turn markdown table rows into a monospace-aligned block (for a Discord
    code fence). Drops the `|---|` separator row and pads columns to width."""
    rows: list[list[str]] = []
    for ln in grid_lines:
        stripped = ln.strip()
        if stripped.startswith(">"):  # drop the callout quote marker
            stripped = stripped[1:].strip()
        if not stripped.startswith("|"):
            continue
        if set(stripped) <= set("|-: "):  # the |---|---| separator row
            continue
        rows.append([_strip_color(c) for c in stripped.strip("|").split("|")])
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    widths = [0] * ncol
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c))
    out: list[str] = []
    for idx, r in enumerate(rows):
        padded = [(r[i] if i < len(r) else "").ljust(widths[i]) for i in range(ncol)]
        out.append("  ".join(padded).rstrip())
        if idx == 0:
            out.append("  ".join("-" * widths[i] for i in range(ncol)))
    return "\n".join(out)


def schedule_view() -> dict | None:
    """Structured view of the active SCHEDULE.md for rich rendering (e.g. a
    Discord embed). Returns None when no schedule exists. Shape:

        {"semester": str, "updated": str, "grid": str,
         "days": [{"day": str, "lines": [str, ...]}, ...]}

    `grid` is the monospace-aligned weekly grid (course-only, emoji stripped);
    each day line keeps its colour emoji and room (callout/quote markup removed)."""
    path = _vault() / "SCHEDULE.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if not _DAY_SECTION_RE.search(text):
        return None

    def _unquote(line: str) -> str:
        s = line.strip()
        return s[1:].strip() if s.startswith(">") else s

    sm = re.search(r"^semester:\s*(.+)$", text, re.MULTILINE)
    um = re.search(r"^updated:\s*(.+)$", text, re.MULTILINE)
    grid = _align_grid([ln for ln in text.splitlines() if _unquote(ln).startswith("|")])

    _day_re = re.compile(_DAY_HEADER)
    days: list[dict] = []
    current: dict | None = None
    for ln in text.splitlines():
        s = _unquote(ln)
        dm = _day_re.match(s)
        if dm:
            current = {"day": dm.group(1), "lines": []}
            days.append(current)
        elif current is not None and s.startswith("-"):
            current["lines"].append(s.lstrip("-").strip())

    return {
        "semester": sm.group(1).strip() if sm else "",
        "updated": um.group(1).strip() if um else "",
        "grid": grid,
        "days": days,
    }


_ENTRY_RE = re.compile(r'(\d{1,2}:\d{2})[–\-](\d{1,2}:\d{2})\s+\*\*([^*]+)\*\*')
_LOC_RE = re.compile(r'📍\s*(.+)')
_FREE_LINE = re.compile(r'—\s*free')


def format_for_frontend() -> str | None:
    """Day-header plain-text schedule readable by the frontend scheduleParser.js.
    Returns None when no schedule exists."""
    data = schedule_view()
    if not data or not data["days"]:
        return None
    lines: list[str] = []
    for d in data["days"]:
        day_lines: list[str] = []
        for raw in d["lines"]:
            if _FREE_LINE.search(raw):
                continue
            m = _ENTRY_RE.search(raw)
            if not m:
                continue
            start, end, course = m.group(1), m.group(2), m.group(3).strip()
            loc_m = _LOC_RE.search(raw)
            loc = loc_m.group(1).strip() if loc_m else ""
            entry = f"{start}-{end} {course}"
            if loc:
                entry += f" ({loc})"
            day_lines.append(entry)
        if day_lines:
            lines.append(d["day"])
            lines.extend(day_lines)
    return "\n".join(lines) if lines else None


def format_for_discord() -> str | None:
    """Plain-text Discord rendering of the schedule (fallback for non-embed
    callers): an aligned grid code fence followed by the day breakdown. Returns
    None when no schedule exists yet."""
    data = schedule_view()
    if not data:
        return None
    parts: list[str] = []
    if data["grid"]:
        parts.append("**Weekly Grid**\n```\n" + data["grid"] + "\n```")
    if data["days"]:
        out: list[str] = []
        for d in data["days"]:
            out.append(f"**{d['day']}**")
            out.extend(f"- {ln}" for ln in d["lines"])
        parts.append("**Day Breakdown**\n" + "\n".join(out))
    return "\n\n".join(parts) if parts else None


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
