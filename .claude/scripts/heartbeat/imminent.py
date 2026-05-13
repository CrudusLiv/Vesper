"""Deterministic scan of MEMORY.md `## Deadlines`.

Per HEARTBEAT.md: items due within 48h get a high-priority notification,
items within 24h get an urgent one. Runs every tick before the LLM call,
so deadline alerts don't depend on Claude reasoning."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
MEMORY = PROJECT_DIR / "Dynamous" / "Memory" / "MEMORY.md"
KL = timezone(timedelta(hours=8))

SECTION = "## Deadlines"
# Matches: `- 2026-05-10 — CS101 — Assignment 1  <!-- src:gmail:abc -->`
LINE_RE = re.compile(
    r"^-\s*(\d{4}-\d{2}-\d{2})\s+—\s+(.+?)\s+—\s+(.+?)(?:\s+<!--.*-->)?\s*$",
    re.MULTILINE,
)


def _section_text() -> str:
    if not MEMORY.exists():
        return ""
    text = MEMORY.read_text(encoding="utf-8")
    if SECTION not in text:
        return ""
    start = text.index(SECTION) + len(SECTION)
    next_section = text.find("\n## ", start)
    end = next_section if next_section != -1 else len(text)
    return text[start:end]


def scan(now: datetime | None = None) -> tuple[list[dict], list[dict]]:
    """Return (urgent_le_24h, soon_le_48h). Past-due items are skipped."""
    now = now or datetime.now(KL)
    today = now.date()
    urgent: list[dict] = []
    soon: list[dict] = []
    for due_s, course, title in LINE_RE.findall(_section_text()):
        try:
            due = date.fromisoformat(due_s)
        except ValueError:
            continue
        days = (due - today).days
        if days < 0:
            continue
        item = {"due": due_s, "course": course.strip(), "title": title.strip(), "days": days}
        if days <= 1:
            urgent.append(item)
        elif days <= 2:
            soon.append(item)
    return urgent, soon


def format_body(items: list[dict]) -> str:
    return "; ".join(f"{i['title']} ({i['course']}, due {i['due']})" for i in items)
