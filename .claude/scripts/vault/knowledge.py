"""Concept/research note writer -- the daily-reflection job's third
curation lane, alongside MEMORY.md decisions/lessons and ABOUT.md facts.
See .claude/scripts/memory_reflect.py::curate_knowledge().

concepts/<slug>.md is a discrete idea/term/technique CrudusLiv learned or
worked through; research/<slug>.md is a broader topic worth an evolving
note. Both are append-only: a first hit creates the note with frontmatter
+ summary, a later hit on the same title appends a dated section instead
of overwriting.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
VAULT = PROJECT_DIR / "Dynamous" / "Memory"
CONCEPTS_DIR = VAULT / "concepts"
RESEARCH_DIR = VAULT / "research"


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return slug or "untitled"


def existing_titles(kind: str) -> list[str]:
    """Titles (filenames without .md) of existing concept or research
    notes -- fed into the reflection prompt so the model can match an
    existing note instead of creating a near-duplicate."""
    d = CONCEPTS_DIR if kind == "concepts" else RESEARCH_DIR
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.md"))


def _upsert(
    dir_path: Path, title: str, entry: str, date: str,
    tags: list[str] | None = None, source_date: str | None = None,
) -> bool:
    entry = entry.strip()
    title = title.strip()
    if not entry or not title:
        return False
    path = dir_path / f"{_slugify(title)}.md"
    link = f" (from [[{source_date}]])" if source_date else ""
    section = f"\n## {date}\n{entry}{link}\n"

    if not path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        tag_line = f"tags: [{', '.join(tags)}]\n" if tags else ""
        frontmatter = f"---\ntitle: {title}\ncreated: {date}\n{tag_line}---\n"
        path.write_text(f"{frontmatter}\n# {title}\n{section}", encoding="utf-8")
        return True

    existing = path.read_text(encoding="utf-8")
    if f"## {date}\n{entry}" in existing:
        return False  # same entry already captured today
    suffix = "" if existing.endswith("\n") else "\n"
    path.write_text(existing + suffix + section, encoding="utf-8")
    return True


def upsert_concept(
    title: str, entry: str, date: str,
    tags: list[str] | None = None, source_date: str | None = None,
) -> bool:
    """Create or append to concepts/<slug>.md. Returns True if written."""
    return _upsert(CONCEPTS_DIR, title, entry, date, tags, source_date)


def upsert_research(title: str, entry: str, date: str, source_date: str | None = None) -> bool:
    """Create or append to research/<slug>.md. Returns True if written."""
    return _upsert(RESEARCH_DIR, title, entry, date, None, source_date)
