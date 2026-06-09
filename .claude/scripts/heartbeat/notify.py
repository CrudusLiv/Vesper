"""Notifications: console output with optional Windows toast.

The heartbeat pushes reminders, deadlines, and summaries to stderr so they
surface in scheduler logs. Toast is opt-in per call via `toast=True`.
"""
from __future__ import annotations

import sys

PRIORITY_BADGES = {
    "low":    "[.]",
    "normal": "[*]",
    "high":   "[!]",
    "urgent": "[!!]",
}


def send(title: str, body: str, priority: str = "normal", toast: bool = False) -> None:
    _send_console(title, body, priority)
    if toast:
        try:
            from heartbeat import toast as toast_module
            toast_module.show(title, body)
        except Exception as exc:
            print(f"[notify] toast failed: {exc}", file=sys.stderr)


def _send_console(title: str, body: str, priority: str) -> None:
    badge = PRIORITY_BADGES.get(priority, "[*]")
    line = f"{badge} {title}"
    if body:
        line += f"\n    {body}"
    print(line, file=sys.stderr, flush=True)
