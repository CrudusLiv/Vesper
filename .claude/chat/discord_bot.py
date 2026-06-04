"""Discord bot: headless cache-only listener.

Caches every message to discord_cache.db so discord_ping.scan_pings can
detect mentions/replies and forward them as DMs + Windows toasts.
No channel handlers. No slash commands.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / ".claude"))

import integrations._env  # noqa: F401, E402

from integrations import discord_int  # noqa: E402

_self_id: dict = {"id": None}


async def on_message(message) -> None:
    try:
        discord_int._store_message(message, _self_id["id"])
    except Exception as exc:
        print(f"cache write failed: {exc}", file=sys.stderr)


def main() -> int:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("DISCORD_BOT_TOKEN not set in .env", file=sys.stderr)
        return 1

    try:
        import discord
    except ImportError:
        print("discord.py not installed: py -m pip install -r .claude/requirements.txt",
              file=sys.stderr)
        return 1

    intents = discord.Intents.default()
    intents.message_content = True
    intents.dm_messages = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        _self_id["id"] = str(client.user.id) if client.user else None
        print(f"Connected as {client.user} (id={_self_id['id']}) — cache-only mode")

    client.event(on_message)
    client.run(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
