"""Email tools: triage inbox, filter subscriptions. Read-only."""
from __future__ import annotations
import voice  # noqa: F401

_URGENT = ["urgent", "asap", "deadline", "overdue", "action required",
           "respond by", "reply needed", "important", "follow up"]
_SUB = ["unsubscribe", "newsletter", "noreply", "no-reply",
        "marketing", "promo", "notification", "digest", "weekly"]


def triage_inbox(days: int = 3) -> str:
    try:
        from integrations import gmail_int  # type: ignore
        emails = gmail_int.list_recent(days=days, max_results=20)
    except Exception as exc:
        return f"Gmail unavailable: {exc}"
    if not emails:
        return f"No emails in the last {days} day(s)."
    urgent, normal = [], []
    for e in emails:
        subj = (e.get("subject") or "").lower()
        snip = (e.get("snippet") or "").lower()
        if any(k in subj or k in snip for k in _URGENT):
            urgent.append(e)
        else:
            normal.append(e)
    lines = [f"{len(emails)} email(s) in last {days}d -- {len(urgent)} flagged urgent."]
    if urgent:
        lines.append("Urgent:")
        for e in urgent[:5]:
            frm = (e.get("from") or "?")[:40]
            subj = (e.get("subject") or "(no subject)")[:60]
            lines.append(f"  ! {frm} -- {subj}")
    if normal:
        lines.append(f"Other: {len(normal)} email(s)")
    return "\n".join(lines)


def filter_subscriptions(days: int = 3) -> str:
    try:
        from integrations import gmail_int  # type: ignore
        emails = gmail_int.list_recent(days=days, max_results=30)
    except Exception as exc:
        return f"Gmail unavailable: {exc}"
    subs = [
        e for e in emails
        if any(k in (e.get("from") or "").lower() or
               k in (e.get("snippet") or "").lower() for k in _SUB)
    ]
    if not subs:
        return "No obvious subscription emails found."
    senders = list({(e.get("from") or "?")[:50] for e in subs})[:8]
    return f"{len(subs)} subscription-type emails from: {', '.join(senders)}"
