"""Preview the new ping-DM embed format by sending a live test DM.

Run from the project root:
    py .claude/scripts/heartbeat/test_ping_dm.py

Sends one DM simulating a server @mention with a blockquote, Discord
timestamp, and jump URL. Does not touch the DB or state file.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / ".claude"))

import integrations._env  # noqa: F401  -- loads .env
from heartbeat import notify

# ---------------------------------------------------------------------------
# Helpers that mirror the planned discord_ping.format_dm() output
# ---------------------------------------------------------------------------

def _humanize(content: str, user_id: str | None) -> str:
    import re
    def repl(m: re.Match) -> str:
        return "@you" if user_id and m.group(1) == user_id else "@user"
    return re.sub(r"<@!?(\d+)>", repl, content)


def _jump_url(ping: dict) -> str | None:
    gid = ping.get("guild_id")
    cid = ping.get("channel_id")
    mid = ping.get("id")
    if gid and cid and mid:
        return f"https://discord.com/channels/{gid}/{cid}/{mid}"
    return None


def _build_ping_embed(ping: dict, *, user_id: str | None = None) -> dict:
    """Build the embed dict for a forwarded ping (planned format)."""
    sender      = ping.get("author_name") or "unknown"
    channel     = "DM" if ping.get("is_dm") else (ping.get("channel_name") or "channel")
    raw_content = (ping.get("content") or "").strip()
    created_at  = ping.get("created_at") or time.time()

    has_mention = bool(user_id) and (
        f"<@{user_id}>" in raw_content or f"<@!{user_id}>" in raw_content
    )
    is_reply = bool(user_id) and ping.get("referenced_author_id") == user_id

    if has_mention:
        title = f"Discord ping from {sender}"
    elif is_reply:
        title = f"Discord reply from {sender}"
    else:
        title = f"Discord DM from {sender}"

    cleaned = _humanize(raw_content, user_id)
    discord_ts = f"<t:{int(created_at)}:F>"  # renders as full local date/time in Discord
    jump = _jump_url(ping)

    # Description: blockquote + location line
    quote_block = f"> {cleaned}" if cleaned else "> (no text)"
    location_parts = [f"#{channel}" if not ping.get("is_dm") else "DM", discord_ts]
    if jump:
        location_parts.append(f"[Jump to message ↗]({jump})")
    location_line = " · ".join(location_parts)
    description = f"{quote_block}\n\n{location_line}"

    color, emoji = notify.PRIORITY_STYLES["high"]
    full_title = f"{emoji} {title}".strip()

    from datetime import datetime, timedelta, timezone
    KL = timezone(timedelta(hours=8))
    when = datetime.fromtimestamp(created_at, tz=KL).strftime("%H:%M KL")

    return {
        "author": {"name": "Vesper"},
        "title": full_title[:256],
        "description": description,
        "color": color,
        "footer": {"text": f"{when}  ·  high"},
    }


def send_test(ping: dict, user_id: str | None = None) -> None:
    embed = _build_ping_embed(ping, user_id=user_id)
    token    = os.environ.get("DISCORD_BOT_TOKEN")
    uid      = os.environ.get("DISCORD_USER_ID")
    if not token or not uid:
        print("DISCORD_BOT_TOKEN or DISCORD_USER_ID not set — cannot send", file=sys.stderr)
        sys.exit(1)
    channel_id = notify._ensure_dm_channel(token, uid)
    notify._post_message(token, channel_id, embeds=[embed])
    safe_title = embed['title'].encode('ascii', errors='replace').decode('ascii')
    print(f"  sent: {safe_title}")


if __name__ == "__main__":
    user_id = os.environ.get("DISCORD_USER_ID")

    # --- Test 1: server @mention with a jump URL ---
    fake_guild_id   = "111111111111111111"
    fake_channel_id = "222222222222222222"
    fake_message_id = "333333333333333333"

    mention_ping = {
        "id":                 fake_message_id,
        "channel_id":         fake_channel_id,
        "channel_name":       "general",
        "guild_id":           fake_guild_id,
        "is_dm":              0,
        "author_id":          "999999999999999999",
        "author_name":        "Test",
        "content":            f"<@{user_id}> hey check this out, the new format looks clean",
        "created_at":         time.time() - 300,   # 5 min ago
        "referenced_author_id": None,
    }

    print("Sending test DMs...")
    send_test(mention_ping, user_id=user_id)
    print("Done. Check your Discord DMs from the bot.")
