"""Tests for chat/intent_parser.py — extracts action JSON from LLM replies."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude"))

from chat.intent_parser import ParseResult, parse  # noqa: E402

VALID_VERBS = {"append", "edit", "create", "delete", "rename", "move", "list", "undo"}


def test_plain_text_reply_has_no_action():
    result = parse("here's your answer, no action needed")
    assert result == ParseResult(text="here's your answer, no action needed", action=None)


def test_pure_json_reply_extracts_action():
    raw = '{"action": "append", "args": {"path": "notes/x.md", "text": "hi"}}'
    result = parse(raw)
    assert result.text == ""
    assert result.action == {"action": "append", "args": {"path": "notes/x.md", "text": "hi"}}


def test_fenced_json_extracts_action():
    raw = 'sure, adding that.\n```json\n{"action": "append", "args": {"path": "x.md", "text": "hi"}}\n```'
    result = parse(raw)
    assert result.text.strip() == "sure, adding that."
    assert result.action["action"] == "append"


def test_json_without_lang_tag_in_fence_still_parses():
    raw = '```\n{"action": "undo", "args": {}}\n```'
    result = parse(raw)
    assert result.action == {"action": "undo", "args": {}}


def test_malformed_json_treated_as_plain_text():
    raw = "i'd say {action: oops"
    result = parse(raw)
    assert result.action is None
    assert "oops" in result.text


def test_unknown_verb_rejected_as_plain_text():
    raw = '{"action": "explode", "args": {}}'
    result = parse(raw)
    # Action shape was valid but verb is not in whitelist → treat as text
    assert result.action is None


def test_action_without_args_field_rejected():
    raw = '{"action": "undo"}'
    result = parse(raw)
    # undo legitimately has empty args, but the field is required
    assert result.action is None


def test_action_with_non_dict_args_rejected():
    raw = '{"action": "append", "args": "hi"}'
    result = parse(raw)
    assert result.action is None
