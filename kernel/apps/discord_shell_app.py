# kernel/apps/discord_shell_app.py
"""Bridge between Discord's asyncio event loop and the synchronous kernel bus.

`post_from_discord()` is called from the Discord bot's `on_message` handler
(async context). It puts a DiscordMessage into the kernel's thread-safe queue
via `runtime.post_external()` — no shared mutable state.

`on_discord_message()` is called by the kernel's main loop (sync context). It
calls `handler.process_message()` and queues the reply back to Discord via
`_send_reply()`, which schedules a coroutine on the bot's event loop."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any

from kernel.app import VesperApp
from kernel.events import DiscordMessage

_CLAUDE = Path(__file__).resolve().parents[2] / ".claude"
sys.path.insert(0, str(_CLAUDE))
sys.path.insert(0, str(_CLAUDE / "scripts"))

from chat import handler  # noqa: E402


class DiscordShellApp(VesperApp):
    name = "discord-shell"
    version = "1.0"
    subscribes = [DiscordMessage]

    def __init__(self, runtime: Any) -> None:
        super().__init__(runtime)
        self._bot_loop: Any = None

    def set_bot_loop(self, loop: Any) -> None:
        self._bot_loop = loop

    def post_from_discord(
        self,
        channel_id: str,
        user_id: str,
        content: str,
        message_obj: Any,
    ) -> None:
        """Called from Discord asyncio on_message; thread-safe."""
        self._runtime.post_external(
            DiscordMessage(
                channel_id=channel_id,
                user_id=user_id,
                content=content,
                message_obj=message_obj,
            )
        )

    def on_discord_message(self, event: DiscordMessage) -> None:
        reply = handler.process_message(event.user_id, event.channel_id, event.content)
        if reply:
            self._send_reply(event, reply)

    def _send_reply(self, event: DiscordMessage, text: str) -> None:
        if self._bot_loop is None or event.message_obj is None:
            self.log(f"no bot loop or message_obj; reply dropped: {text[:60]}")
            return
        import asyncio

        async def _do_send():
            for chunk in _split(text):
                await event.message_obj.channel.send(chunk)

        asyncio.run_coroutine_threadsafe(_do_send(), self._bot_loop)


def _split(text: str, limit: int = 2000) -> list[str]:
    chunks = []
    while len(text) > limit:
        chunks.append(text[:limit])
        text = text[limit:]
    if text:
        chunks.append(text)
    return chunks
