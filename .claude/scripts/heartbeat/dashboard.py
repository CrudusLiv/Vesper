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
import urllib.parse
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

VAULT_NAME = "Memory"  # Folder under Dynamous/ holding all notes.


def _obsidian_url(vault_path: str) -> str:
    """Build an `obsidian://` deep link for a vault-relative path.

    Slashes stay literal so the URL is human-skimmable; spaces and other
    reserved chars are percent-encoded by quote()."""
    encoded = urllib.parse.quote(vault_path, safe="/")
    return f"obsidian://open?vault={VAULT_NAME}&file={encoded}"


def _vesper_embed(
    title: str,
    description: str,
    color: int,
    *,
    channel_label: str,
    vault_path: str | None = None,
    url: str | None = None,
    fields: list[dict] | None = None,
    ts: float | None = None,
) -> dict:
    """Return the inner embed dict for a Vesper-branded Discord post.

    Caller wraps in `{"embeds": [...]}`. If both `vault_path` and `url`
    are given, the explicit `url` wins (used for PR events that link to
    GitHub instead of the vault)."""
    now = datetime.fromtimestamp(ts, tz=KL) if ts else datetime.now(KL)
    when = now.strftime("%H:%M KL")

    link = url or (_obsidian_url(vault_path) if vault_path else None)
    if vault_path and not url:
        footer_text = f"{when}  ·  \U0001F4C2 {vault_path}"
    else:
        footer_text = when

    embed: dict = {
        "author": {"name": f"Vesper · {channel_label}"},
        "title": title[:256],
        "description": description,
        "color": color,
        "fields": fields or [],
        "footer": {"text": footer_text[:2048]},
    }
    if link:
        embed["url"] = link
    return embed


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
    # Slice 6 pivot (2026-05-25): three kinds collapse onto one channel.
    # Original plan had separate #morning / #evening / #digest; one user
    # doesn't need three rooms for daily updates. Emoji prefix in the
    # embed differentiates kind at a glance.
    "morning_digest":   "DISCORD_HOOK_DAILY",
    "evening_nudge":    "DISCORD_HOOK_DAILY",
    "daily_digest":     "DISCORD_HOOK_DAILY",
    "inbox_text":       "DISCORD_HOOK_INBOX",
    "inbox_attachment": "DISCORD_HOOK_INBOX",
    "idea":             "DISCORD_HOOK_IDEAS",
    "email_uni":        "DISCORD_HOOK_EMAIL_UNI",
    "email_personal":   "DISCORD_HOOK_EMAIL_PERSONAL",
    "vesper_reply":     "DISCORD_HOOK_VESPER",
    # Slice 7: in-thread chat replies. Routed by the thread's origin
    # channel (a reply in a deadline thread goes back via the deadlines
    # webhook with thread_id=...; same for lectures).
    "deadline_reply":   "DISCORD_HOOK_DEADLINES",
    "lecture_reply":    "DISCORD_HOOK_LECTURES",
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
    if kind in ("deadline_72h", "deadline_24h", "deadline_overdue"):
        return _format_deadline(kind, payload)
    if kind == "next3":
        return _format_next3(payload)
    if kind == "lecture_new":
        return _format_lecture_new(payload)
    if kind in ("morning_digest", "evening_nudge", "daily_digest"):
        return _format_daily(kind, payload)
    if kind in ("deadline_reply", "lecture_reply"):
        return _format_thread_reply(payload)
    if kind in ("pr_opened", "pr_merged", "pr_comment"):
        return _format_pr_event(kind, payload)
    # Generic fallback for kinds whose slice hasn't landed yet.
    return {
        "content": (
            f"`{kind}` (no formatter yet)\n"
            f"```json\n{json.dumps(payload, default=str)[:1800]}\n```"
        )
    }


_HEARTBEAT_COLORS = {
    "ok":       0x2ECC71,  # green
    "degraded": 0xF1C40F,  # yellow
    "red":      0xE74C3C,  # red
}


def _format_heartbeat_tick(p: dict[str, Any]) -> dict[str, Any]:
    status = p.get("status", "ok")
    failing = p.get("failing") or []
    color = _HEARTBEAT_COLORS.get(status, 0x95A5A6)
    if failing:
        title = f"\U0001F534 Degraded — {', '.join(failing)}"
        description = f"{len(failing)} check(s) failed · other integrations ok"
    else:
        title = "All systems green"
        description = "all integrations ok"
    return {"embeds": [_vesper_embed(
        title=title,
        description=description,
        color=color,
        channel_label="Heartbeat",
        ts=p.get("tick_ts"),
    )]}


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


_DEADLINE_STYLES: dict[str, tuple[int, str]] = {
    # kind -> (color, status field value)
    "deadline_72h":     (0xF1C40F, "\U0001F7E1 Approaching (72h)"),
    "deadline_24h":     (0xE67E22, "\U0001F7E0 Due today/tomorrow"),
    "deadline_overdue": (0xE74C3C, "\U0001F534 OVERDUE"),
}


def _format_deadline(kind: str, p: dict[str, Any]) -> dict[str, Any]:
    """Embed for a single deadline threshold post (72h / 24h / overdue).

    Title is the assignment (course-tagged) and clicks through to
    DEADLINES.md. A 'Status' field carries the threshold label; the
    description carries the due-date phrasing."""
    color, status_value = _DEADLINE_STYLES.get(
        kind, (0x95A5A6, "Deadline")
    )
    course = (p.get("course") or "").strip()
    title = (p.get("title") or "(untitled)").strip()
    due = p.get("due") or "?"
    days = p.get("days")

    if kind == "deadline_overdue":
        when = (
            f"was due **{due}** ({-days}d ago)"
            if isinstance(days, int) else f"was due **{due}**"
        )
    else:
        when = (
            f"due **{due}** (in {days}d)"
            if isinstance(days, int) else f"due **{due}**"
        )

    title_text = f"[{course}] {title}" if course else title
    return {"embeds": [_vesper_embed(
        title=title_text,
        description=when,
        color=color,
        channel_label="Deadlines",
        vault_path="DEADLINES.md",
        fields=[{"name": "Status", "value": status_value, "inline": True}],
        ts=p.get("ts"),
    )]}


_DAILY_STYLES: dict[str, tuple[str, int]] = {
    # kind -> (emoji prefix, embed color)
    "morning_digest": ("🌅", 0xF39C12),  # warm amber
    "evening_nudge":  ("🌙", 0x8E44AD),  # muted purple
    "daily_digest":   ("📝", 0x95A5A6),  # slate
}


def _format_daily(kind: str, p: dict[str, Any]) -> dict[str, Any]:
    """Single embed shape for the three daily-feed kinds.

    All three route to the same channel (DISCORD_HOOK_DAILY). The emoji
    prefix is the only at-a-glance differentiator -- color is a secondary
    cue. Payload shape matches what heartbeat.py already produces:
    {title, body, priority?}."""
    emoji, color = _DAILY_STYLES.get(kind, ("📝", 0x95A5A6))
    title = (p.get("title") or "Daily").strip()
    body = (p.get("body") or "").strip()
    now = datetime.now(KL).strftime("%H:%M KL")
    description = body if len(body) <= 4000 else body[:3997] + "..."
    embed = {
        "title": f"{emoji} {title}"[:256],
        "description": description or "_(no body)_",
        "color": color,
        "footer": {"text": now},
    }
    return {"embeds": [embed]}


_PR_STYLES: dict[str, tuple[str, int, str]] = {
    # kind -> (emoji, color, headline)
    "pr_opened":  ("🟢", 0x2ECC71, "PR opened"),
    "pr_merged":  ("🟣", 0x8E44AD, "PR merged"),
    "pr_comment": ("💬", 0x95A5A6, "PR comment"),
}


def _format_pr_event(kind: str, p: dict[str, Any]) -> dict[str, Any]:
    """Embed for one PR event (open / merge / comment).

    payload keys: repo, pr_number, pr_title, pr_url, actor, ts, id."""
    emoji, color, headline = _PR_STYLES.get(kind, ("🔧", 0x95A5A6, "PR event"))
    repo = (p.get("repo") or "").strip()
    pr_number = p.get("pr_number")
    pr_title = (p.get("pr_title") or "").strip()
    pr_url = (p.get("pr_url") or "").strip()
    actor = (p.get("actor") or "").strip()

    pr_ref = f"#{pr_number}" if pr_number else ""
    title_bits = [f"{emoji} {headline}", repo, pr_ref]
    title = "  ·  ".join(b for b in title_bits if b)[:256]

    desc_parts: list[str] = []
    if pr_title:
        desc_parts.append(f"**{pr_title}**")
    if actor:
        verb = {"pr_opened": "opened by", "pr_merged": "merged by", "pr_comment": "commented by"}.get(kind, "by")
        desc_parts.append(f"{verb} `{actor}`")
    if pr_url:
        desc_parts.append(pr_url)
    description = "\n".join(desc_parts) or "_(no details)_"

    embed = {
        "title": title,
        "description": description,
        "color": color,
    }
    return {"embeds": [embed]}


def _format_thread_reply(p: dict[str, Any]) -> dict[str, Any]:
    """Slice 7 in-thread reply -- plain text, no embed. The thread itself
    is the context, so the reply doesn't need an emoji/header. Discord
    caps webhook content at 2000 chars; truncate with an ellipsis."""
    text = (p.get("text") or "").strip()
    if not text:
        text = "_(empty reply)_"
    if len(text) > 2000:
        text = text[:1997] + "..."
    return {"content": text}


def _format_lecture_new(p: dict[str, Any]) -> dict[str, Any]:
    """Forum-thread starter for a freshly-summarised lecture.

    payload keys: name (course), title, tldr (list), vault_path, source."""
    title = (p.get("title") or "(untitled)").strip()
    tldr = p.get("tldr") or []
    vault_path = p.get("vault_path") or ""
    source = (p.get("source") or "").strip()

    bullets = (
        "\n".join(f"- {b}" for b in tldr[:3])
        if tldr else "_(no Key concepts section)_"
    )
    if len(bullets) > 4000:
        bullets = bullets[:3997] + "..."

    embed = _vesper_embed(
        title=title,
        description=bullets,
        color=0x3498DB,
        channel_label="Lectures",
        vault_path=vault_path or None,
        ts=p.get("ts"),
    )
    if source:
        embed["footer"]["text"] = (
            f"{embed['footer']['text']}  ·  source: {source}"
        )[:2048]
    return {"embeds": [embed]}


def _next3_dot(days: Any) -> str:
    """Red / yellow / green dot for a deadline based on days-until-due."""
    if not isinstance(days, int) or days < 0:
        return "\U0001F534"  # red (overdue or unknown)
    if days <= 3:
        return "\U0001F7E1"  # yellow (within 72h)
    return "\U0001F7E2"      # green (later)


def _format_next3(p: dict[str, Any]) -> dict[str, Any]:
    """Embed rollup of the next 3 deadlines, edited in place each tick."""
    items = p.get("items") or []
    if not items:
        description = "Nothing in DEADLINES.md ## Active."
    else:
        lines: list[str] = []
        for i in items:
            course = (i.get("course") or "").strip()
            title = (i.get("title") or "(untitled)").strip()
            due = i.get("due") or "?"
            days = i.get("days")
            if isinstance(days, int):
                rel = (
                    f"{-days}d overdue" if days < 0
                    else "today" if days == 0
                    else f"in {days}d"
                )
            else:
                rel = ""
            tag = f"[{course}] " if course else ""
            dot = _next3_dot(days)
            rel_part = f" ({rel})" if rel else ""
            lines.append(f"{dot} `{due}`{rel_part} — {tag}{title}")
        description = "\n".join(lines)
    return {"embeds": [_vesper_embed(
        title="Next 3 deadlines",
        description=description,
        color=0x5865F2,
        channel_label="Deadlines",
        vault_path="DEADLINES.md",
        ts=p.get("ts"),
    )]}


def _format_error(p: dict[str, Any]) -> dict[str, Any]:
    script = p.get("script") or "unknown"
    trace = (p.get("trace") or "").strip()
    if len(trace) > 1800:
        trace = "...\n" + trace[-1797:]
    description = f"```\n{trace}\n```" if trace else "(no trace captured)"
    return {"embeds": [_vesper_embed(
        title=f"Error in {script}",
        description=description,
        color=0xE74C3C,
        channel_label="Errors",
        ts=p.get("ts"),
    )]}


def _route_url(kind: str) -> str | None:
    env_var = ROUTES.get(kind)
    if not env_var:
        return None
    url = (os.environ.get(env_var) or "").strip()
    return url or None


def edit_message(
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    message_id: str,
    thread_id: str | None = None,
) -> dict[str, Any] | None:
    """PATCH a previously-posted dashboard message in place.

    Used by Slice 3's 'Next 3 deadlines' (rewritten each tick) and any
    future edit-in-place rollups. Returns None when the route is unset or
    Discord rejects the edit (message deleted, wrong thread, etc.) -- the
    caller is expected to fall back to recreating the message."""
    url = _route_url(kind)
    if not url:
        return None
    body = format_embed(kind, payload or {})
    try:
        return discord_webhook.edit(
            url,
            message_id,
            content=body.get("content"),
            embeds=body.get("embeds"),
            thread_id=thread_id,
        )
    except Exception as exc:
        print(f"dashboard.edit_message({kind}) failed: {exc}", file=sys.stderr)
        return None


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
