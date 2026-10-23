"""Size-budgeted vault context shared by the voice brain and the Claude Code
SessionStart hook. Both used to inject whole files (or cut the tail off the
concatenation, which dropped the newest memory first); these helpers keep
the newest material and say what was left out."""
from __future__ import annotations

import re
from pathlib import Path

_DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
_TIMELINE_RE = re.compile(r"<!-- timeline:begin -->.*?<!-- timeline:end -->\n?", re.DOTALL)


def trim_memory(text: str, max_chars: int) -> str:
    """Fit MEMORY.md-style text into max_chars by dropping its oldest bullet
    lines (bullets are appended chronologically). Headings and prose stay."""
    if len(text) <= max_chars:
        return text
    lines = text.split("\n")
    note_room = 80
    size = len(text)
    drop: set[int] = set()
    for i, line in enumerate(lines):
        if size <= max_chars - note_room:
            break
        if line.startswith("- "):
            drop.add(i)
            size -= len(line) + 1
    kept = "\n".join(line for i, line in enumerate(lines) if i not in drop)
    return f"{kept}\n\n[{len(drop)} older entries omitted -- search the vault for them]"


def recent_daily(daily_dir: Path, n: int, max_chars_each: int) -> str:
    """The n newest existing daily notes, each cut to its last max_chars_each
    characters (the end of a day is what matters tomorrow)."""
    if not daily_dir.is_dir():
        return ""
    files = sorted(p for p in daily_dir.iterdir() if _DATE_FILE_RE.match(p.name))[-n:]
    blocks: list[str] = []
    for path in reversed(files):
        try:
            body = _TIMELINE_RE.sub("", path.read_text(encoding="utf-8")).strip()
        except OSError:
            continue
        body = re.sub(r"^# \d{4}-\d{2}-\d{2}\s*", "", body).strip()
        if not body:
            continue
        if len(body) > max_chars_each:
            body = "[earlier part omitted]\n" + body[-max_chars_each:]
        blocks.append(f"### {path.stem}\n\n{body}")
    return "\n\n".join(blocks)
