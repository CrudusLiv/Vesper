"""Section 3: classify and route self-DMs sent to the capture bot.

CrudusLiv DMs a dedicated bot (the same one that powers the Phase 4
read-only cache). Each new DM authored by CrudusLiv is classified:

  note      → append to today's daily/YYYY-MM-DD.md under ## Captured
  finance   → append to finance/YYYY-MM.md under ## Captured
  chit-chat → discard

Classifier is rule-based first; the LLM is only used when the rules
return None (ambiguous). The single LLM call is a Haiku zero-shot
classification — cheap, used rarely.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
VAULT = PROJECT_DIR / "Dynamous" / "Memory"
KL = timezone(timedelta(hours=8))

_FINANCE_RE = re.compile(r"(?:^|(?<=\s))(?:rm|usd|myr|\$)\s*\d+", re.IGNORECASE)
_FINANCE_KEYWORDS = re.compile(
    r"\b(spent|paid|earned|expense|income|salary|invoice)\b",
    re.IGNORECASE,
)
_CHIT_CHAT_ALLOWLIST = {
    "lol", "ok", "okay", "nice", "hi", "hey", "yo", "test", "y", "n",
    "sure", "k", "yep", "nope", "haha", "hmm", "thx", "ty",
}
# Standalone money words that ARE ambiguous (LLM should decide).
_AMBIGUOUS_TOKENS = {"cost", "cash", "money"}


def classify_rule_based(content: str) -> Optional[str]:
    """Return 'note' | 'finance' | 'chit-chat', or None if ambiguous."""
    if not content:
        return "chit-chat"
    text = content.strip()
    lowered = text.lower()

    # Currency symbol or money-pattern → finance.
    if _FINANCE_RE.search(text):
        return "finance"
    if _FINANCE_KEYWORDS.search(text):
        return "finance"

    # Length-based + allowlist chit-chat.
    if len(text) < 10:
        # If the entire short message is an ambiguous money token, escalate.
        if lowered in _AMBIGUOUS_TOKENS:
            return None
        if lowered in _CHIT_CHAT_ALLOWLIST:
            return "chit-chat"
        # Strip trailing punctuation/whitespace then re-check the allowlist
        # so "nice!" or "ok." still classify as chit-chat.
        stripped_punct = lowered.rstrip("!?.,;: ")
        if stripped_punct in _CHIT_CHAT_ALLOWLIST:
            return "chit-chat"
        if not any(c.isalnum() for c in text):
            return "chit-chat"
        # Default short messages → chit-chat.
        return "chit-chat"

    return "note"


def classify_with_llm(content: str) -> str:
    """LLM fallback for ambiguous content. Returns one of the three labels."""
    from heartbeat import llm
    system = (
        "Classify the message into one of: note, finance, chit-chat.\n"
        "- finance: mentions money, spending, earning, currency.\n"
        "- chit-chat: short, reactive, low-content.\n"
        "- note: substantive idea, reminder, or thought.\n"
        "Output one word only."
    )
    result = (llm.call(content, system_prompt=system, model="haiku", timeout=15) or "note").strip().lower()
    if result not in ("note", "finance", "chit-chat"):
        return "note"
    return result


def classify(content: str) -> str:
    label = classify_rule_based(content)
    if label is None:
        label = classify_with_llm(content)
    return label


def _append(target: Path, header: str, body: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(f"# {target.stem}\n\n", encoding="utf-8")
    text = target.read_text(encoding="utf-8")
    if "## Captured" not in text:
        text = text.rstrip() + "\n\n## Captured\n"
    text = text.rstrip() + f"\n- [{header}] {body}\n"
    target.write_text(text, encoding="utf-8")


def route(msg: dict, *, label: Optional[str] = None) -> str:
    """Route a DM dict to its destination. Returns the label used."""
    if label is None:
        label = classify(msg.get("content") or "")
    if label == "chit-chat":
        return label
    dt = datetime.fromtimestamp(float(msg.get("created_at") or time.time()), tz=KL)
    timestamp = dt.strftime("%H:%M")
    body = (msg.get("content") or "").strip().replace("\n", " ")
    if label == "finance":
        target = VAULT / "finance" / f"{dt.strftime('%Y-%m')}.md"
        _append(target, timestamp, body)
    elif label == "note":
        target = VAULT / "daily" / f"{dt.strftime('%Y-%m-%d')}.md"
        _append(target, timestamp, body)
    return label


def scan_and_route(
    db_path: Path,
    *,
    user_id: str,
    state_path: Path,
    bot_dm_channel_id: Optional[str] = None,
) -> dict[str, int]:
    """Find new self-DMs sent to the capture bot, classify, and route.

    Shares state_path with discord_ping (seen_message_ids covers both).
    bot_dm_channel_id, if provided, restricts the scan to that channel."""
    import json
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {
        "last_tick": None, "seen_message_ids": [],
    }
    seen = {s["id"] for s in state.get("seen_message_ids") or []}

    if not db_path.exists():
        return {"note": 0, "finance": 0, "chit-chat": 0}

    sql = """
        SELECT id, channel_id, content, created_at
        FROM messages
        WHERE is_dm = 1 AND is_self = 1
    """
    params: list[str] = []
    if bot_dm_channel_id:
        sql += " AND channel_id = ?"
        params.append(bot_dm_channel_id)
    sql += " ORDER BY created_at ASC"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

    counts = {"note": 0, "finance": 0, "chit-chat": 0}
    for r in rows:
        if r["id"] in seen:
            continue
        label = route(r)
        counts[label] = counts.get(label, 0) + 1
        state.setdefault("seen_message_ids", []).append({"id": r["id"], "t": r["created_at"]})

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return counts
