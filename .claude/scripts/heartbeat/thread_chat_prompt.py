"""System + user prompts for the in-thread chat carve-out (Slice 7).

A thread is either a deadline thread (one per row in DEADLINES.md ## Active,
opened by Slice 3) or a lecture thread (one per summarised lecture, opened
by Slice 4). The kind shapes the system prompt so replies stay anchored to
that thread's subject -- no general chit-chat in deadline threads.

SOUL.md is embedded as persona so voice matches the rest of the agent."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
VAULT = PROJECT_DIR / "Dynamous" / "Memory"

BASE = (
    "You are CrudusLiv's study partner replying inside a Discord forum "
    "thread that you (the agent) opened. Replies are short, direct, and in "
    "voice with SOUL.md. Use plain text -- no markdown headers, no "
    "preambles, no sign-offs. Reply only with the response body; do not "
    "include mentions, do not quote the user's message back at them."
)

DEADLINE_RIDER = (
    "\n\nThis thread tracks a single deadline. Keep replies focused on the "
    "assignment: clarifying what's due, helping plan the work, surfacing "
    "blockers, drafting outlines. Don't summarise content you don't have."
)

LECTURE_RIDER = (
    "\n\nThis thread tracks a lecture summarised in the vault at `{path}`. "
    "Keep replies focused on the lecture material: explaining concepts, "
    "comparing approaches, suggesting study angles. If a question is "
    "outside the lecture's scope, say so briefly."
)


def _load_soul() -> str:
    soul = VAULT / "SOUL.md"
    if not soul.exists():
        return ""
    try:
        return soul.read_text(encoding="utf-8")
    except OSError:
        return ""


def system_prompt(thread_meta: dict) -> str:
    """Build the full system prompt: base behavior + kind-specific rider +
    persona. thread_meta carries `kind` ('deadline' or 'lecture') and
    optional `path` (lecture note path)."""
    parts = [BASE]
    kind = thread_meta.get("kind")
    if kind == "deadline":
        parts.append(DEADLINE_RIDER)
    elif kind == "lecture":
        parts.append(LECTURE_RIDER.format(path=thread_meta.get("path") or "lectures/"))
    soul = _load_soul()
    if soul:
        parts.append("\n\n# Persona (from SOUL.md)\n\n")
        parts.append(soul)
    return "".join(parts)


def user_prompt(msg: dict, context: list[dict]) -> str:
    """Wrap the latest user message in thread context. `context` is the
    last N messages in the thread, oldest first; each dict has
    author_name / content / is_self."""
    lines: list[str] = []
    if context:
        lines.append("Thread context (oldest first):")
        for m in context:
            who = "Vesper" if m.get("is_self") else (m.get("author_name") or "user")
            content = (m.get("content") or "").strip().replace("\n", " ")
            if len(content) > 500:
                content = content[:497] + "..."
            lines.append(f"- {who}: {content}")
        lines.append("")
    lines.append("CrudusLiv's latest message:")
    latest = (msg.get("content") or "").strip()
    if len(latest) > 2000:
        latest = latest[:1997] + "..."
    lines.append(latest)
    lines.append("")
    lines.append("Reply in voice. Plain text, no preamble.")
    return "\n".join(lines)
