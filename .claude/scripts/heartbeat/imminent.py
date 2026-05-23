"""Deterministic scan of DEADLINES.md `## Active`.

Per HEARTBEAT.md: items due within 48h get a high-priority notification,
items within 24h get an urgent one. Runs every tick before the LLM call,
so deadline alerts don't depend on Claude reasoning."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
DEADLINES = PROJECT_DIR / "Dynamous" / "Memory" / "DEADLINES.md"
KL = timezone(timedelta(hours=8))

SECTION = "## Active"
# Matches: `- 2026-05-10 — CS101 — Assignment 1` and `- 2026-05-10 — title`.
# An optional `nogcal:` prefix (used to opt the row out of GCal sync) is
# tolerated so imminent alerts still fire for manually-scheduled items.
LINE_RE = re.compile(
    r"^-\s*(?:nogcal:\s*)?(\d{4}-\d{2}-\d{2})\s+—\s+(.+?)(?:\s+<!--.*-->)?\s*$",
    re.MULTILINE,
)


def _section_text() -> str:
    if not DEADLINES.exists():
        return ""
    text = DEADLINES.read_text(encoding="utf-8")
    if SECTION not in text:
        return ""
    start = text.index(SECTION) + len(SECTION)
    next_section = text.find("\n## ", start)
    end = next_section if next_section != -1 else len(text)
    return text[start:end]


def _split_course_title(rest: str) -> tuple[str, str]:
    """Split `<course> — <title>` into (course, title). If no em-dash
    separator, the whole string is the title and course is empty."""
    if " — " in rest:
        course, _, title = rest.partition(" — ")
        return course.strip(), title.strip()
    return "", rest.strip()


def scan(now: datetime | None = None) -> tuple[list[dict], list[dict]]:
    """Return (urgent_le_24h, soon_le_48h). Past-due items are skipped."""
    now = now or datetime.now(KL)
    today = now.date()
    urgent: list[dict] = []
    soon: list[dict] = []
    for due_s, rest in LINE_RE.findall(_section_text()):
        try:
            due = date.fromisoformat(due_s)
        except ValueError:
            continue
        days = (due - today).days
        if days < 0:
            continue
        course, title = _split_course_title(rest)
        item = {"due": due_s, "course": course, "title": title, "days": days}
        if days <= 1:
            urgent.append(item)
        elif days <= 2:
            soon.append(item)
    return urgent, soon


def format_body(items: list[dict]) -> str:
    def _one(i: dict) -> str:
        if i["course"]:
            return f"{i['title']} ({i['course']}, due {i['due']})"
        return f"{i['title']} (due {i['due']})"
    return "; ".join(_one(i) for i in items)
