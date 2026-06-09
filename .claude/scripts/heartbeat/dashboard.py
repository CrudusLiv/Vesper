"""Heartbeat event routing — feed and toast only.

Each call to notify() writes an entry to the web feed store and optionally
fires a Windows toast. Discord webhooks have been removed."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

KL = timezone(timedelta(hours=8))

# Kinds never written to the web feed.
_FEED_SKIP: frozenset[str] = frozenset({"deadline_reply", "lecture_reply", "vesper_reply"})
# Kinds that fire a Windows toast in addition to the feed write.
_TOAST_KINDS: frozenset[str] = frozenset({"deadline_24h", "deadline_overdue", "error"})


def _maybe_feed_and_toast(kind: str, payload: dict) -> None:
    """Write to the web feed store and optionally fire a Windows toast."""
    if kind in _FEED_SKIP:
        return
    if kind == "heartbeat_tick" and payload.get("status") == "ok":
        return
    try:
        from heartbeat import feed as _feed
        record = _feed.append(kind, payload)
        if kind in _TOAST_KINDS:
            try:
                from heartbeat import toast as _toast
                _toast.show(record.get("title", ""), record.get("body", ""))
            except Exception as exc:
                print(f"[dashboard] toast failed: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"[dashboard] feed append failed: {exc}", file=sys.stderr)


def notify(
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    thread_id: str | None = None,
    thread_name: str | None = None,
) -> dict[str, Any] | None:
    """Route a kind+payload to the feed (and optional toast). Always returns None."""
    _maybe_feed_and_toast(kind, payload or {})
    return None


def edit_message(
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    message_id: str,
    thread_id: str | None = None,
) -> dict[str, Any] | None:
    """No-op stub — Discord message editing removed."""
    return None
