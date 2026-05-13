#!/usr/bin/env python3
"""Daily reflection -- runs at 08:00 UTC+8.

Two jobs each morning:
1. Read yesterday's daily/<YYYY-MM-DD>.md, ask Claude for durable items
   (decisions, lessons, facts), append them to MEMORY.md under the matching
   sections. Ruthlessly small lists -- most days produce 0-2 items.
2. Archive yesterday's HABITS.md to goals/habits-history/, reset today's
   checkboxes for a fresh day."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])

sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
from heartbeat import llm  # noqa: E402

VAULT = PROJECT_DIR / "Dynamous" / "Memory"
DAILY = VAULT / "daily"
HABITS = VAULT / "HABITS.md"
HABITS_HISTORY = VAULT / "goals" / "habits-history"
MEMORY = VAULT / "MEMORY.md"

KL = timezone(timedelta(hours=8))

REFLECT_SYSTEM = """You curate CrudusLiv's long-term memory.

You receive yesterday's daily log and the current MEMORY.md. Output STRICT
JSON only -- no prose, no markdown fences:

{
  "new_decisions": ["one line each -- durable choices made yesterday"],
  "new_lessons":   ["one line each -- what worked, what didn't, what to do differently"],
  "new_facts":     ["one line each -- non-obvious facts about systems/people/projects"]
}

Rules:
- Be RUTHLESS. Most chatter is not durable. Empty arrays are correct most days.
- Don't duplicate items already present in MEMORY.md.
- Each item <= 100 chars. No headers, no markdown formatting in items.
- Skip small fixes, debugging steps, and in-the-moment decisions that won't matter
  next month."""


def yesterday_kl() -> str:
    return (datetime.now(KL) - timedelta(days=1)).strftime("%Y-%m-%d")


def today_kl() -> str:
    return datetime.now(KL).strftime("%Y-%m-%d")


# ---------- Reflection ----------

def reflect() -> dict:
    y_path = DAILY / f"{yesterday_kl()}.md"
    if not y_path.exists():
        print(f"No daily log at {y_path}. Skipping reflection.")
        return {}
    y_log = y_path.read_text(encoding="utf-8")
    memory = MEMORY.read_text(encoding="utf-8") if MEMORY.exists() else ""

    if not llm.is_available():
        print("`claude` CLI not available. Reflection skipped.", file=sys.stderr)
        return {}

    prompt = (
        f"YESTERDAY'S DAILY LOG ({y_path.name}):\n\n{y_log}\n\n"
        f"---\n\nCURRENT MEMORY.md:\n\n{memory}\n\n"
        f"Return JSON per the schema."
    )
    return llm.call_json(prompt, system_prompt=REFLECT_SYSTEM, model="haiku") or {}


def _insert_into_section(text: str, section_name: str, new_items: list[str], date_prefix: str) -> tuple[str, int]:
    """Append new bullets at the END of `## section_name` (before the next ## block)."""
    marker = f"## {section_name}"
    if marker not in text or not new_items:
        return text, 0
    start = text.index(marker)
    next_section = text.find("\n## ", start + 1)
    end = next_section if next_section != -1 else len(text)
    section = text[start:end].rstrip()
    additions = "".join(f"- {date_prefix} — {item.strip()}\n" for item in new_items)
    new_section = section + "\n" + additions
    return text[:start] + new_section + ("\n" + text[end:].lstrip("\n") if next_section != -1 else ""), len(new_items)


def append_to_memory(items: dict) -> int:
    if not items or not MEMORY.exists():
        return 0
    text = MEMORY.read_text(encoding="utf-8")
    today = today_kl()
    appended = 0
    for section, key in (("Decisions", "new_decisions"), ("Lessons", "new_lessons")):
        new = items.get(key) or []
        text, n = _insert_into_section(text, section, new, today)
        appended += n
    facts = items.get("new_facts") or []
    if facts:
        text, n = _insert_into_section(text, "Lessons", [f"(fact) {f}" for f in facts], today)
        appended += n
    if appended:
        MEMORY.write_text(text, encoding="utf-8")
    return appended


# ---------- Habits reset ----------

def reset_habits() -> str:
    if not HABITS.exists():
        return "no HABITS.md"
    HABITS_HISTORY.mkdir(parents=True, exist_ok=True)
    yesterday = yesterday_kl()
    today = today_kl()

    text = HABITS.read_text(encoding="utf-8")

    archive = HABITS_HISTORY / f"{yesterday}.md"
    if not archive.exists():
        archive.write_text(text, encoding="utf-8")

    text = re.sub(
        r"## Today — \d{4}-\d{2}-\d{2}",
        f"## Today — {today}",
        text,
    )
    today_marker = f"## Today — {today}"
    start = text.find(today_marker)
    if start != -1:
        next_section = text.find("\n## ", start + 1)
        end = next_section if next_section != -1 else len(text)
        before, section, after = text[:start], text[start:end], text[end:]
        section = section.replace("- [x]", "- [ ]").replace("- [X]", "- [ ]")
        text = before + section + after
        HABITS.write_text(text, encoding="utf-8")
        return f"reset (archived {yesterday})"
    return "no Today section"


def main() -> int:
    items = reflect()
    appended = append_to_memory(items)
    habits_status = reset_habits()
    print(f"Reflection: {appended} item(s) added to MEMORY.md.")
    print(f"Habits: {habits_status}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
