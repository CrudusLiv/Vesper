#!/usr/bin/env python3
"""One-shot backfill: post every vault lecture to the Discord #lectures forum.

Usage:
    py .claude/scripts/heartbeat/backfill_lectures.py

Re-running is safe -- the manifest at Dynamous/Memory/state/discord-lectures-posted.json
records which lectures were posted. Already-posted lectures are skipped.
The manifest is written after each successful post so a crash mid-run
leaves state intact and re-running resumes from where it stopped."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(
    os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3]
)
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))

VAULT = PROJECT_DIR / "Dynamous" / "Memory"
LECTURES = VAULT / "lectures"
MANIFEST = VAULT / "state" / "discord-lectures-posted.json"

from heartbeat import dashboard  # noqa: E402
from heartbeat.inbox import (  # noqa: E402
    _extract_study_card_count,
    _extract_title,
    _extract_tldr,
)

SLEEP_BETWEEN_POSTS = 2  # seconds -- stays well within Discord rate limits


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse simple `key: value` YAML frontmatter delimited by `---`.

    Returns an empty dict if no opening delimiter is present or no closing
    delimiter is found. List values (e.g. tags) are kept as the raw string."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return {}


def _load_manifest() -> dict[str, str]:
    if not MANIFEST.exists():
        return {}
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(
            f"warn: manifest unreadable at {MANIFEST} ({exc}); starting fresh",
            file=sys.stderr,
        )
        return {}


def _save_manifest(manifest: dict[str, str]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    manifest = _load_manifest()
    lecture_files = sorted(LECTURES.rglob("*.md"))

    if not lecture_files:
        print(f"no lecture files found under {LECTURES}")
        return

    posted = skipped = failed = 0

    for path in lecture_files:
        rel_path = path.relative_to(VAULT).as_posix()

        if rel_path in manifest:
            print(f"skip  {rel_path}")
            skipped += 1
            continue

        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)

        course = fm.get("course", "").strip()
        source = fm.get("source_file", "").strip()
        date = fm.get("date", "").strip()
        title = _extract_title(text) or path.stem
        tldr = _extract_tldr(text)
        study_cards = _extract_study_card_count(text)

        payload = {
            "name": course,
            "title": title,
            "tldr": tldr,
            "vault_path": rel_path,
            "source": source,
            "date": date,
            "study_cards": study_cards,
        }
        thread_name = (f"[{course}] {title}" if course else title)[:100]

        result = dashboard.notify("lecture_new", payload, thread_name=thread_name)

        if result and result.get("id"):
            manifest[rel_path] = result["id"]
            _save_manifest(manifest)
            print(f"post  {rel_path}")
            posted += 1
        else:
            print(f"FAIL  {rel_path}  result={result!r}")
            failed += 1

        time.sleep(SLEEP_BETWEEN_POSTS)

    print(f"\ndone -- posted {posted}, skipped {skipped}, failed {failed}")


if __name__ == "__main__":
    main()
