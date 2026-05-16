"""Notifications: Discord DM to CrudusLiv, console fallback.

The Second Brain pushes everything (reminders, deadlines, summaries, drafts) to
a single Discord DM channel so it lives where CrudusLiv already is. Toast is
opt-in per call via `toast=True`; DM is always the primary surface.

Env required:
    DISCORD_BOT_TOKEN  -- bot in CrudusLiv's DMs (already shared with the
                          Phase 4.1 cache bot and Phase 7 chat bot).
    DISCORD_USER_ID    -- numeric user ID to DM.

Falls back to stderr if either is missing or the API call errors -- the
heartbeat is never silent.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
# DM channel ID is stable per (bot, user) pair, so cache it once. The first
# heartbeat tick makes the lookup call; subsequent ticks read from disk.
DM_CHANNEL_CACHE = PROJECT_DIR / ".claude" / "data" / "discord_dm_channel.txt"
API_BASE = "https://discord.com/api/v10"

PRIORITY_BADGES = {
    "low":    "[.]",
    "normal": "[*]",
    "high":   "[!]",
    "urgent": "[!!]",
}


def send(title: str, body: str, priority: str = "normal", toast: bool = False) -> None:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    user_id = os.environ.get("DISCORD_USER_ID")
    if token and user_id:
        if not _send_discord_dm(token, user_id, title, body, priority):
            _send_console(title, body, priority)
    else:
        _send_console(title, body, priority)
    if toast:
        try:
            from heartbeat import toast as toast_module
            toast_module.show(title, body)
        except Exception as exc:
            print(f"[notify] toast piggyback failed: {exc}", file=sys.stderr)


def _send_discord_dm(token: str, user_id: str, title: str, body: str, priority: str) -> bool:
    badge = PRIORITY_BADGES.get(priority, "[*]")
    content = f"{badge} **{title}**"
    if body:
        content += f"\n{body}"
    # Discord caps single messages at 2000 chars. Truncation is fine for
    # notifications -- the full draft/lecture lives in the vault.
    if len(content) > 1990:
        content = content[:1987] + "..."

    try:
        channel_id = _ensure_dm_channel(token, user_id)
        _post_message(token, channel_id, content)
        return True
    except urllib.error.HTTPError as exc:
        # Surface Discord's JSON error body so 403/50007 etc. are debuggable.
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        print(f"discord DM failed ({exc} body={body[:300]}); falling back to console", file=sys.stderr)
        return False
    except (urllib.error.URLError, KeyError, OSError) as exc:
        print(f"discord DM failed ({exc}); falling back to console", file=sys.stderr)
        return False


def _ensure_dm_channel(token: str, user_id: str) -> str:
    if DM_CHANNEL_CACHE.exists():
        cached = DM_CHANNEL_CACHE.read_text().strip()
        if cached:
            return cached
    req = urllib.request.Request(
        f"{API_BASE}/users/@me/channels",
        method="POST",
        data=json.dumps({"recipient_id": user_id}).encode(),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            # Discord runs behind Cloudflare and blocks stock Python-urllib
            # User-Agents with a 1010 fingerprint error. The docs require a
            # User-Agent in this format:
            # https://discord.com/developers/docs/reference#user-agent
            "User-Agent": "DiscordBot (https://github.com/CrudusLiv/BoredBot, 1.0)",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read())
    channel_id = payload["id"]
    DM_CHANNEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DM_CHANNEL_CACHE.write_text(channel_id)
    return channel_id


def _post_message(token: str, channel_id: str, content: str) -> None:
    req = urllib.request.Request(
        f"{API_BASE}/channels/{channel_id}/messages",
        method="POST",
        data=json.dumps({"content": content}).encode(),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            # Discord runs behind Cloudflare and blocks stock Python-urllib
            # User-Agents with a 1010 fingerprint error. The docs require a
            # User-Agent in this format:
            # https://discord.com/developers/docs/reference#user-agent
            "User-Agent": "DiscordBot (https://github.com/CrudusLiv/BoredBot, 1.0)",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def _send_console(title: str, body: str, priority: str) -> None:
    badge = PRIORITY_BADGES.get(priority, "[*]")
    line = f"{badge} {title}"
    if body:
        line += f"\n    {body}"
    print(line, file=sys.stderr, flush=True)
