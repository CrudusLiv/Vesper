"""Kind -> webhook routing for the Discord dashboard.

Each event kind maps to an env var holding a channel webhook URL. URLs are
read lazily so an empty .env key silently skips -- you can wire channels
incrementally without breaking existing slices.

Slice 1 only implements formatters for `heartbeat_tick` and `error`. Other
kinds fall back to a generic JSON-dump body until their slice supplies a
real formatter.

This module is NOT a bot-identity sender. All outbound here is via channel
webhooks. Bot DMs to CrudusLiv continue through heartbeat.notify."""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Make `integrations.discord_webhook` importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrations import discord_webhook  # noqa: E402

# Load .env so DISCORD_HOOK_* keys reach os.environ when this module is
# invoked directly (e.g. `py -c "from heartbeat.dashboard import notify; ..."`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations"))
import _env  # noqa: F401, E402

KL = timezone(timedelta(hours=8))

ROUTES: dict[str, str] = {
    "heartbeat_tick":   "DISCORD_HOOK_HEARTBEAT",
    "error":            "DISCORD_HOOK_ERRORS",
    "deadline_72h":     "DISCORD_HOOK_DEADLINES",
    "deadline_24h":     "DISCORD_HOOK_DEADLINES",
    "deadline_overdue": "DISCORD_HOOK_DEADLINES",
    "next3":            "DISCORD_HOOK_DEADLINES",
    "lecture_new":      "DISCORD_HOOK_LECTURES",
    "pr_opened":        "DISCORD_HOOK_PR_ACTIVITY",
    "pr_merged":        "DISCORD_HOOK_PR_ACTIVITY",
    "pr_comment":       "DISCORD_HOOK_PR_ACTIVITY",
    "code_review":      "DISCORD_HOOK_CODE_REVIEW",
    "morning_digest":   "DISCORD_HOOK_MORNING",
    "evening_nudge":    "DISCORD_HOOK_EVENING",
    "daily_digest":     "DISCORD_HOOK_DIGEST",
    "inbox_text":       "DISCORD_HOOK_INBOX",
    "inbox_attachment": "DISCORD_HOOK_INBOX",
    "idea":             "DISCORD_HOOK_IDEAS",
    "email_uni":        "DISCORD_HOOK_EMAIL_UNI",
    "email_personal":   "DISCORD_HOOK_EMAIL_PERSONAL",
    "vesper_reply":     "DISCORD_HOOK_VESPER",
}


def format_embed(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return a Discord-API body dict: {content?, embeds?, thread_name?, ...}."""
    if kind == "heartbeat_tick":
        return _format_heartbeat_tick(payload)
    if kind == "error":
        return _format_error(payload)
    if kind == "inbox_text":
        return _format_inbox_text(payload)
    if kind == "inbox_attachment":
        return _format_inbox_attachment(payload)
    # Generic fallback for kinds whose slice hasn't landed yet.
    return {
        "content": (
            f"`{kind}` (no formatter yet)\n"
            f"```json\n{json.dumps(payload, default=str)[:1800]}\n```"
        )
    }


def _format_heartbeat_tick(p: dict[str, Any]) -> dict[str, Any]:
    status = p.get("status", "unknown")
    failing = p.get("failing") or []
    ts = p.get("tick_ts") or 0
    now = datetime.fromtimestamp(ts, tz=KL) if ts else datetime.now(KL)
    when = now.strftime("%H:%M KL")
    if status == "red" and failing:
        line = f"[heartbeat] red — {', '.join(failing)}  {when}"
    else:
        line = f"[heartbeat] {status}  {when}"
    return {"content": line}


def _format_inbox_text(p: dict[str, Any]) -> dict[str, Any]:
    content = (p.get("content") or "").strip()
    vault_path = p.get("vault_path") or "notes/NOTES.md"
    ts = p.get("ts") or 0
    when = (datetime.fromtimestamp(ts, tz=KL) if ts else datetime.now(KL)).strftime("%H:%M KL")
    snippet = content if len(content) <= 1500 else content[:1497] + "..."
    return {"content": f"[note] {when} — `{vault_path}`\n{snippet}"}


def _format_inbox_attachment(p: dict[str, Any]) -> dict[str, Any]:
    filename = p.get("filename") or "(unknown)"
    size = p.get("size")
    vault_path = p.get("vault_path") or ""
    ts = p.get("ts") or 0
    when = (datetime.fromtimestamp(ts, tz=KL) if ts else datetime.now(KL)).strftime("%H:%M KL")
    size_str = f" ({size:,} bytes)" if isinstance(size, int) else ""
    return {"content": f"[inbox] {when} — saved `{filename}`{size_str} → `{vault_path}`"}


def _format_error(p: dict[str, Any]) -> dict[str, Any]:
    script = p.get("script") or "unknown"
    trace = (p.get("trace") or "").strip()
    # Tail of the trace is usually more informative than the top frame.
    if len(trace) > 1800:
        trace = "...\n" + trace[-1797:]
    embed = {
        "title": f"Error in {script}",
        "description": f"```\n{trace}\n```" if trace else "(no trace captured)",
        "color": 0xE74C3C,
    }
    return {"embeds": [embed]}


def _route_url(kind: str) -> str | None:
    env_var = ROUTES.get(kind)
    if not env_var:
        return None
    url = (os.environ.get(env_var) or "").strip()
    return url or None


def notify(
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    thread_id: str | None = None,
    thread_name: str | None = None,
) -> dict[str, Any] | None:
    """Post a kind+payload to its routed channel.

    Returns the parsed webhook response (with `id`, and `channel_id` for
    forum creates), or None if the env var is unset or the post fails.

    On failure, attempts a follow-up post to #errors -- unless the failing
    kind is itself `error`, to avoid recursive storms."""
    url = _route_url(kind)
    if not url:
        return None
    body = format_embed(kind, payload or {})
    try:
        return discord_webhook.post(
            url,
            content=body.get("content"),
            embeds=body.get("embeds"),
            thread_name=thread_name or body.get("thread_name"),
            thread_id=thread_id,
            applied_tags=body.get("applied_tags"),
        )
    except Exception as exc:
        print(f"dashboard.notify({kind}) failed: {exc}", file=sys.stderr)
        if kind != "error":
            try:
                error_url = _route_url("error")
                if error_url:
                    err_body = _format_error({
                        "script": f"dashboard.notify({kind})",
                        "trace": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                    })
                    discord_webhook.post(
                        error_url,
                        content=err_body.get("content"),
                        embeds=err_body.get("embeds"),
                    )
            except Exception:
                pass
        return None
