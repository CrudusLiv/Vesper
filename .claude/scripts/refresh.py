#!/usr/bin/env python3
"""Manual refresh -- gather a snapshot from integrations and write vault state files.

No LLM calls, no notifications, no habits. Just data gather + vault write.
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
VAULT = PROJECT_DIR / "Dynamous" / "Memory"

sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts" / "integrations"))

import _env  # noqa: F401, E402

from heartbeat import discord_ping, inbox, notify, snapshot, toast, vault_state_writer  # noqa: E402

KL = timezone(timedelta(hours=8))


def _write_log(lines: list[str]) -> None:
    dt = datetime.now(tz=KL).strftime("%Y-%m-%dT%H:%M:%S")
    content = f"---\nupdated: {dt}\n---\n" + "\n".join(lines) + "\n"
    state_dir = VAULT / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "refresh-log.md").write_text(content, encoding="utf-8")


def main() -> int:
    lines: list[str] = []
    dt = datetime.now(tz=KL).strftime("%H:%M · %Y-%m-%d")
    lines.append(f"Last refresh: {dt}")

    for summary in inbox.process_new_files():
        rel = summary["path"].relative_to(VAULT).as_posix()
        label = "Lecture summarised" if summary["type"] == "lecture" else "Project filed"
        lines.append(f"  {label}: {summary['title']} → {rel}")

    inbox.refresh_daily_timeline()

    prev_saved = snapshot.load_state()
    # Skip the GitHub API call: it dominates the refresh latency (~19s vs
    # ~150ms for everything else) and the scheduled 30-min heartbeat already
    # keeps github-counts.md fresh. Carry forward the last heartbeat's github
    # snapshot so write_github() has data instead of blanking the file.
    curr = {
        "timestamp": time.time(),
        "discord": snapshot._safe(snapshot._snapshot_discord),
        "github":  (prev_saved or {}).get("github") or {},
        "inbox":   snapshot._safe(snapshot._snapshot_inbox),
    }
    # Preserve the scheduled heartbeat run time so the dashboard "Last ran"
    # shows when the heartbeat actually fired, not when the user hit Refresh.
    if prev_saved and prev_saved.get("heartbeat_ran_at"):
        curr["heartbeat_ran_at"] = prev_saved["heartbeat_ran_at"]
    vault_state_writer.write_all(curr)
    snapshot.save_state(curr)

    # Ping count: @mentions + DMs from others since last refresh
    ping_count = 0
    ping_error = None
    user_id = __import__("os").environ.get("DISCORD_USER_ID")
    if user_id:
        db_path = PROJECT_DIR / ".claude" / "data" / "discord_cache.db"
        state_path = PROJECT_DIR / ".claude" / "data" / "discord_last_tick.json"
        try:
            pings = discord_ping.scan_pings(db_path, user_id=user_id, state_path=state_path)
            ping_count = len(pings)
            for ping in pings:
                title, body = discord_ping.format_toast(ping, user_id=user_id)
                toast.show(title, body)
                notify.send(title, body, priority="high")
        except Exception as exc:
            ping_error = str(exc)

    # Write ping count to vault state so dashboard can read it
    state_dir = VAULT / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    dt_iso = datetime.now(tz=KL).strftime("%Y-%m-%dT%H:%M:%S")
    (state_dir / "discord-pings.md").write_text(
        f"---\nupdated: {dt_iso}\nping_count: {ping_count}\n---\n",
        encoding="utf-8",
    )

    discord = curr.get("discord") or {}
    github = curr.get("github") or {}
    inbox_state = curr.get("inbox") or {}

    ping_detail = ping_error or f"{ping_count} new pings"
    github_detail = github.get('error') or f"{github.get('push_count', 0)} pushes"
    inbox_detail  = inbox_state.get('error') or f"{inbox_state.get('count', 0)} files"
    lines.append(f"  Discord: {ping_detail}")
    lines.append(f"  GitHub:  {github_detail}")
    lines.append(f"  Inbox:   {inbox_detail}")
    lines.append("Done.")

    _write_log(lines)
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
