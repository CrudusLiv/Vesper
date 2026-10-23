#!/usr/bin/env python3
"""Daily reflection -- runs at 08:00 UTC+8.

Reads each not-yet-reflected daily/<YYYY-MM-DD>.md (catching up on days the
machine missed, up to a week), asks Claude for durable items (decisions,
lessons, mistakes, facts), and appends them to MEMORY.md under the matching
sections. Ruthlessly small lists -- most days produce 0-2 items.

Every item is tagged with a [[source-date]] link, deduplicated in code (not
just by prompt), and checked against a RAW SIGNALS block built from the
audit log so a reflection is grounded in what actually happened rather than
only in a summary of a summary. Progress is recorded in
.claude/data/state/reflect_status.json so a failing run is visible to the
heartbeat instead of silently doing nothing."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])

sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
from core import llm  # noqa: E402
from vault import context as vault_context  # noqa: E402
from vault import knowledge  # noqa: E402

VAULT = PROJECT_DIR / "Dynamous" / "Memory"
DAILY = VAULT / "daily"
MEMORY = VAULT / "MEMORY.md"
ARCHIVE = VAULT / "MEMORY-archive.md"
STATUS = PROJECT_DIR / ".claude" / "data" / "state" / "reflect_status.json"

KL = timezone(timedelta(hours=8))

MAX_CATCHUP_DAYS = 7
MEMORY_MAX_CHARS = 12000      # archive the oldest entries once MEMORY.md grows past this...
MEMORY_TARGET_CHARS = 9000    # ...down to this
PROMPT_MEMORY_CHARS = 20000   # cap on the MEMORY.md copy sent to the model
MAX_ITEM_CHARS = 200

REFLECT_SYSTEM = """You curate CrudusLiv's long-term memory.

You receive a daily log, optionally a RAW SIGNALS block (facts taken straight
from the audit log: what was approved or denied, what happened to alerts,
instruction-like text found in tool output), the current MEMORY.md, and the
titles of existing concept/research notes. Output STRICT JSON only -- no
prose, no markdown fences:

{
  "new_decisions": ["one line each -- durable choices made that day"],
  "new_lessons":   ["one line each -- what worked, what didn't, what to do differently"],
  "new_facts":     ["one line each -- non-obvious facts about systems/people/projects"],
  "new_mistakes":  ["one line each -- something Vesper got wrong or a tool that failed"],
  "new_concepts":  [{"title": "...", "note": "..."}],
  "new_research":  [{"title": "...", "note": "..."}],
  "new_stances":   ["one line each -- an opinion/reaction you (Vesper) actually expressed"]
}

Rules:
- Be RUTHLESS. Most chatter is not durable. Empty arrays are correct most days.
- Record ONLY what the log or the RAW SIGNALS block explicitly states. Never
  infer motives, preferences or facts that are not written there. If you are
  unsure, leave it out.
- Don't duplicate items already present in MEMORY.md.
- Each decision/lesson/fact/mistake item <= 100 chars. No headers, no markdown formatting.
- Skip small fixes, debugging steps, and in-the-moment decisions that won't matter
  next month.
- new_decisions/new_lessons/new_facts are about VESPER'S OWN BUILD (the voice
  app, the agent layer, this repo) -- never about CrudusLiv's coursework, life,
  or outside interests.
- new_mistakes: a concrete error Vesper made, a correction CrudusLiv gave, a
  tool call that failed or was denied, or an alert pattern CrudusLiv kept
  dismissing -- only if the log or RAW SIGNALS shows it. Most days this is empty.
- new_concepts: a discrete idea/term/technique CrudusLiv learned or worked
  through (coursework, reading, a side project) -- NOT Vesper's own build.
  If it matches an EXISTING concept title given below, reuse that exact title
  so it gets appended to instead of duplicated.
- new_research: a broader topic/thread CrudusLiv is exploring, worth an
  evolving note rather than a fixed definition. Same reuse-existing-title rule.
- Each concept/research "note" is 1-3 plain sentences: what was learned or
  explored, and why it matters. No markdown formatting.
- new_stances: an opinion, prediction, or reaction YOU (Vesper) actually
  expressed that day -- not a fact about CrudusLiv, not a project decision.
  Only include it if it's something worth bringing up again later (a real
  disagreement, a prediction, a recurring complaint) -- most days this is
  empty. Each item <= 100 chars, plain text, include enough of what it was
  about that reading it cold weeks later still makes sense."""


def yesterday_kl() -> str:
    return (datetime.now(KL) - timedelta(days=1)).strftime("%Y-%m-%d")


def today_kl() -> str:
    return datetime.now(KL).strftime("%Y-%m-%d")


# ---------- Status + catch-up ----------

def read_status() -> dict:
    try:
        return json.loads(STATUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_status(last_reflected: str | None, error: str | None) -> None:
    try:
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATUS.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({
            "last_reflected_date": last_reflected,
            "last_run": datetime.now(KL).isoformat(),
            "ok": error is None,
            "error": error,
        }), encoding="utf-8")
        tmp.replace(STATUS)
    except OSError as exc:
        print(f"status write failed: {exc}", file=sys.stderr)


def pending_days() -> list[str]:
    """Days still to reflect on: everything after the last successful one up
    to yesterday (newest MAX_CATCHUP_DAYS), or just yesterday on first run."""
    yesterday = yesterday_kl()
    last = read_status().get("last_reflected_date")
    try:
        start = date.fromisoformat(last) + timedelta(days=1)
    except (TypeError, ValueError):
        return [yesterday]
    end = date.fromisoformat(yesterday)
    days = []
    while start <= end:
        days.append(start.isoformat())
        start += timedelta(days=1)
    return days[-MAX_CATCHUP_DAYS:]


# ---------- Raw signals (grounding + outcome feedback) ----------

def gather_signals(day: str) -> str:
    """Facts for `day` straight from the voice audit log: alert outcomes
    (dismissed/deleted, deadline/reminder completions), denied or timed-out
    confirmations and injection warnings. "" when there are none or the
    audit log can't be read."""
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        from voice import config as voice_cfg
        path = voice_cfg.get_data_dir() / "voice_audit.jsonl"
        raw = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""

    outcomes: list[str] = []
    denied: dict[str, int] = {}
    injections: list[str] = []
    for line in raw:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not str(e.get("ts", "")).startswith(day):
            continue
        role, outcome = e.get("role"), e.get("outcome")
        if role == "outcome":
            outcomes.append(f"- {e.get('content', '')}")
        elif role == "tool" and outcome in ("cancelled", "timeout", "paused"):
            key = f"{e.get('tool', '?')} {outcome}"
            denied[key] = denied.get(key, 0) + 1
        elif role == "tool" and outcome == "injection":
            injections.append(f"- {e.get('tool', '?')}: {e.get('content', '')}")

    blocks: list[str] = []
    if outcomes:
        blocks.append("What happened to alerts and tasks:\n" + "\n".join(outcomes[:20]))
    if denied:
        blocks.append("Confirmations not approved:\n" + "\n".join(f"- {k} x{n}" for k, n in sorted(denied.items())))
    if injections:
        blocks.append("Instruction-like text found in tool output:\n" + "\n".join(injections[:10]))
    return "\n\n".join(blocks)[:3000]


# ---------- Reflection ----------

def reflect(day: str | None = None) -> dict | None:
    """Ask the model what from `day`'s log is durable. {} when there is
    nothing to reflect on; None when the attempt failed (so the caller does
    not mark the day done)."""
    day = day or yesterday_kl()
    y_path = DAILY / f"{day}.md"
    if not y_path.exists():
        print(f"No daily log at {y_path}. Skipping {day}.")
        return {}
    y_log = y_path.read_text(encoding="utf-8")
    memory = MEMORY.read_text(encoding="utf-8") if MEMORY.exists() else ""

    if not llm.is_available():
        print("`claude` CLI not available. Reflection skipped.", file=sys.stderr)
        return None

    existing_concepts = ", ".join(knowledge.existing_titles("concepts")) or "(none yet)"
    existing_research = ", ".join(knowledge.existing_titles("research")) or "(none yet)"
    signals = gather_signals(day)
    signals_block = f"RAW SIGNALS (from the audit log):\n\n{signals}\n\n---\n\n" if signals else ""

    prompt = (
        f"DAILY LOG ({y_path.name}):\n\n{y_log}\n\n"
        f"---\n\n{signals_block}"
        f"CURRENT MEMORY.md:\n\n{vault_context.trim_memory(memory, PROMPT_MEMORY_CHARS)}\n\n"
        f"---\n\nEXISTING CONCEPT NOTE TITLES: {existing_concepts}\n"
        f"EXISTING RESEARCH NOTE TITLES: {existing_research}\n\n"
        f"Return JSON per the schema."
    )
    result = llm.call_json(prompt, system_prompt=REFLECT_SYSTEM, model="haiku", task="memory_reflect")
    return result if isinstance(result, dict) else None


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def _insert_into_section(
    text: str, section_name: str, new_items: list[str], date_prefix: str, source: str | None = None,
) -> tuple[str, int]:
    """Append new bullets at the END of `## section_name` (before the next ## block).
    Items already present anywhere in `text` (case/punctuation-insensitive),
    non-strings and empties are skipped; `source` adds a [[date]] link."""
    marker = f"## {section_name}"
    if marker not in text or not new_items:
        return text, 0

    seen = _norm(text)
    fresh: list[str] = []
    for item in new_items:
        if not isinstance(item, str):
            continue
        item = item.strip()[:MAX_ITEM_CHARS]
        key = _norm(item)
        if not key or key in seen:
            continue
        seen += " " + key
        fresh.append(item)
    if not fresh:
        return text, 0

    start = text.index(marker)
    next_section = text.find("\n## ", start + 1)
    end = next_section if next_section != -1 else len(text)
    section = text[start:end].rstrip()
    tag = f" ([[{source}]])" if source else ""
    additions = "".join(f"- {date_prefix} — {item}{tag}\n" for item in fresh)
    new_section = section + "\n" + additions
    return text[:start] + new_section + ("\n" + text[end:].lstrip("\n") if next_section != -1 else ""), len(fresh)


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def append_to_memory(items: dict, source: str | None = None) -> int:
    """Add reflected items to MEMORY.md. `source` is the day they came from;
    it dates the bullets and links back to that day's log."""
    if not items or not MEMORY.exists():
        return 0
    text = MEMORY.read_text(encoding="utf-8")
    stamp = source or today_kl()
    appended = 0
    for section, key, prefix in (
        ("Decisions", "new_decisions", ""),
        ("Lessons", "new_lessons", ""),
        ("Stances", "new_stances", ""),
        ("Lessons", "new_facts", "(fact) "),
        ("Lessons", "new_mistakes", "(mistake) "),
    ):
        new = [f"{prefix}{item}" for item in (items.get(key) or []) if isinstance(item, str)]
        text, n = _insert_into_section(text, section, new, stamp, source)
        appended += n
    if appended:
        _write_atomic(MEMORY, text)
    return appended


def archive_old_memory(max_chars: int = MEMORY_MAX_CHARS, target_chars: int = MEMORY_TARGET_CHARS) -> int:
    """Keep MEMORY.md (loaded into every session) from growing forever: past
    max_chars, move its oldest Decisions/Lessons bullets to MEMORY-archive.md
    (indexed, so still searchable) until it is back under target_chars.
    Nothing is deleted. Returns the number of bullets moved."""
    if not MEMORY.exists():
        return 0
    text = MEMORY.read_text(encoding="utf-8")
    if len(text) <= max_chars:
        return 0

    lines = text.split("\n")
    section = None
    candidates: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("- ") and section in ("Decisions", "Lessons"):
            m = re.match(r"- (\d{4}-\d{2}-\d{2})", line)
            candidates.append((m.group(1) if m else "9999-99-99", i))
    candidates.sort()

    size, moved = len(text), []
    for _date, i in candidates:
        if size <= target_chars:
            break
        moved.append(i)
        size -= len(lines[i]) + 1
    if not moved:
        return 0

    moved_set = set(moved)
    header = "" if ARCHIVE.exists() else (
        "# MEMORY archive\n\n> Older Decisions/Lessons moved out of MEMORY.md to keep the "
        "always-loaded context small. Nothing is deleted.\n"
    )
    block = f"\n## Archived {today_kl()}\n" + "\n".join(lines[i] for i in sorted(moved_set)) + "\n"
    with ARCHIVE.open("a", encoding="utf-8") as fh:
        fh.write(header + block)
    _write_atomic(MEMORY, "\n".join(line for i, line in enumerate(lines) if i not in moved_set))
    return len(moved)


def curate_knowledge(items: dict, source_date: str | None = None) -> int:
    """Write/append concept and research notes from reflect()'s
    new_concepts/new_research arrays (see vault/knowledge.py). Returns the
    number of notes created or appended to."""
    if not items:
        return 0
    today = today_kl()
    source = source_date or yesterday_kl()
    written = 0
    for item in items.get("new_concepts") or []:
        if not isinstance(item, dict):
            continue
        title, note = item.get("title"), item.get("note")
        if title and note and knowledge.upsert_concept(title, note, today, source_date=source):
            written += 1
    for item in items.get("new_research") or []:
        if not isinstance(item, dict):
            continue
        title, note = item.get("title"), item.get("note")
        if title and note and knowledge.upsert_research(title, note, today, source_date=source):
            written += 1
    return written


ABOUT_SYSTEM = """You curate ABOUT.md — durable facts about CrudusLiv himself
(preferences, working style, recurring patterns), not project state.

You receive yesterday's chat-session messages (in #vesper) and the current
ABOUT.md. Output STRICT JSON only:

{"new_bullets": ["one line each, <= 100 chars, no markdown"]}

Rules:
- Be RUTHLESS. Most exchanges produce nothing. Empty arrays are correct most days.
- Only include facts that will still be true next month.
- Skip task-specific or project-specific items — those belong in MEMORY.md.
- Don't duplicate existing ABOUT.md bullets."""


def _yesterday_chat_messages() -> str:
    """Return yesterday's chat messages as a single string, or '' if none."""
    import sqlite3
    from datetime import datetime as _dt, timedelta as _td
    db = PROJECT_DIR / ".claude" / "data" / "chat.db"
    if not db.exists():
        return ""
    y_start = _dt.combine((_dt.now(KL) - _td(days=1)).date(), _dt.min.time(), tzinfo=KL).timestamp()
    y_end = y_start + 86400
    try:
        conn = sqlite3.connect(str(db))
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE ts >= ? AND ts < ? ORDER BY ts",
            (y_start, y_end),
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return ""
    return "\n".join(f"{role.upper()}: {content}" for role, content in rows)


def curate_about() -> int:
    """Returns the number of new bullets added (0 on no-op)."""
    sys.path.insert(0, str(PROJECT_DIR / ".claude"))
    from chat import about

    chat_msgs = _yesterday_chat_messages()
    if not chat_msgs.strip():
        print("No chat messages yesterday. Skipping ABOUT curation.")
        return 0
    if not llm.is_available():
        print("`claude` CLI not available. ABOUT curation skipped.", file=sys.stderr)
        return 0

    current = about.load_about()
    prompt = (
        f"YESTERDAY'S #VESPER CHAT MESSAGES:\n\n{chat_msgs}\n\n"
        f"---\n\nCURRENT ABOUT.md:\n\n{current}\n\n"
        f"Return JSON per the schema."
    )
    result = llm.call_json(prompt, system_prompt=ABOUT_SYSTEM, model="haiku", task="memory_about") or {}
    new_bullets = result.get("new_bullets") or []
    if not isinstance(new_bullets, list):
        return 0

    added = 0
    for bullet in new_bullets[:3]:
        if isinstance(bullet, str) and about.append_bullet(bullet):
            added += 1
    print(f"ABOUT curation: added {added} bullet(s).")
    return added


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    days = [yesterday_kl()] if "--force" in argv else pending_days()
    prior = read_status().get("last_reflected_date")
    last_ok, error = prior, None

    if not days:
        print("Reflection is up to date.")
    for day in days:
        items = reflect(day)
        if items is None:
            error = f"reflection failed for {day}"
            print(error, file=sys.stderr)
            break
        appended = append_to_memory(items, source=day)
        written = curate_knowledge(items, source_date=day)
        print(f"Reflection {day}: {appended} item(s) added to MEMORY.md, {written} concept/research note(s) written.")
        last_ok = day

    moved = archive_old_memory()
    if moved:
        print(f"Archived {moved} old MEMORY.md entries to {ARCHIVE.name}.")
    write_status(last_ok, error)
    try:
        curate_about()
    except Exception as exc:
        print(f"ABOUT curation failed (non-fatal): {exc}", file=sys.stderr)
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
