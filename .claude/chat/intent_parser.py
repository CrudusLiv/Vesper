"""Extract a vault action (or absence of one) from an LLM reply.

The LLM is told to either reply with plain text OR include a JSON block of
the shape {"action": <verb>, "args": {...}}. This parser is forgiving:
it accepts bare JSON, JSON inside a code fence (with or without `json`
language tag), and falls back to "treat as plain text" on any malformation.

Validation is intentionally narrow — we whitelist known verbs and require
an `args` dict. Anything else is rejected so the dispatcher only ever sees
shapes it knows.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

VALID_VERBS = {"append", "edit", "create", "delete", "rename", "move", "list", "undo"}

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
_BARE_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class ParseResult:
    text: str               # text reply portion (empty if pure action)
    action: Optional[dict]  # validated action dict, or None


def _validate_action(candidate: dict) -> Optional[dict]:
    """Return the dict if it has shape {action: known_verb, args: dict}, else None."""
    if not isinstance(candidate, dict):
        return None
    verb = candidate.get("action")
    args = candidate.get("args")
    if verb not in VALID_VERBS:
        return None
    if not isinstance(args, dict):
        return None
    return {"action": verb, "args": args}


def _try_extract_json(text: str) -> tuple[Optional[dict], int, int]:
    """Find the first JSON object in `text`. Returns (parsed_or_None, start, end).
    `start` and `end` mark the span to strip from the text portion."""
    # 1. Fenced code block
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1).strip()), m.start(), m.end()
        except json.JSONDecodeError:
            pass

    # 2. Bare {...} object
    m = _BARE_OBJECT_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0)), m.start(), m.end()
        except json.JSONDecodeError:
            pass

    return None, -1, -1


def parse(llm_output: str) -> ParseResult:
    """Parse an LLM reply into a ParseResult."""
    text = (llm_output or "").strip()
    if not text:
        return ParseResult(text="", action=None)

    candidate, start, end = _try_extract_json(text)
    if candidate is None:
        return ParseResult(text=text, action=None)

    validated = _validate_action(candidate)
    if validated is None:
        return ParseResult(text=text, action=None)

    # Strip the action span from the text portion
    stripped = (text[:start] + text[end:]).strip()
    return ParseResult(text=stripped, action=validated)
