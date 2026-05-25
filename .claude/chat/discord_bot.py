"""Phase 7 Discord bot: cache messages (Phase 4.1) AND reply to DMs from
the authorized user. Replaces the bot in `discord_int.run_bot()`.

SECURITY CARVE-OUT
==================
This is the ONLY place in the codebase that calls `channel.send()`. The
guardrail is two-pronged and AND-ed:

1.  message.guild is None       -- DMs only, never server channels.
2.  message.author.id matches DISCORD_USER_ID from .env -- only CrudusLiv.

Without both, the bot does NOT reply. The cache write (Phase 4.1 read-only
behavior) still happens for every message, regardless.

ENV REQUIRED
============
- DISCORD_BOT_TOKEN  -- the bot token (Phase 4.1, already set)
- DISCORD_USER_ID    -- your numeric Discord user ID. To find it: enable
  Developer Mode in Discord (Settings -> Advanced -> Developer Mode), then
  right-click your name anywhere -> Copy User ID.

RUN
===
    py .claude/chat/discord_bot.py
    # or via Phase 9 launcher: .claude/scripts/deploy/start_discord_bot.ps1
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / ".claude"))

import integrations._env  # noqa: F401, E402  -- loads .env

from chat import handler  # noqa: E402
from finance import tracker as finance_tracker  # noqa: E402
from heartbeat import dashboard as dashboard  # noqa: E402
from heartbeat import discord_dm_capture  # noqa: E402
from integrations import discord_int  # noqa: E402

from datetime import datetime, timedelta, timezone  # noqa: E402

KL = timezone(timedelta(hours=8))
NOTES_FILE = PROJECT_DIR / "Dynamous" / "Memory" / "notes" / "NOTES.md"

MAX_DISCORD_MSG = 2000

INBOX = PROJECT_DIR / "Dynamous" / "Memory" / "inbox"
HEARTBEAT_SCRIPT = PROJECT_DIR / ".claude" / "scripts" / "heartbeat.py"
INBOX_EXTS = {".pdf", ".pptx"}


async def _save_attachments_to_inbox(message) -> list[str]:
    """Download supported attachments to inbox/. Returns saved filenames."""
    INBOX.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for att in message.attachments:
        ext = Path(att.filename).suffix.lower()
        if ext not in INBOX_EXTS:
            continue
        # Avoid overwriting -- append _1, _2, ... if needed.
        dest = INBOX / att.filename
        i = 1
        while dest.exists():
            dest = INBOX / f"{Path(att.filename).stem}_{i}{ext}"
            i += 1
        try:
            await att.save(dest)
            saved.append(dest.name)
        except Exception as exc:
            print(f"attachment save failed for {att.filename}: {exc}", file=sys.stderr)
    return saved


def _spawn_heartbeat() -> None:
    """Kick off a heartbeat tick in the background. Fire-and-forget --
    output goes to stderr/stdout of the bot process. The bot doesn't wait
    on it, so the DM ack returns immediately."""
    try:
        subprocess.Popen(
            [sys.executable, str(HEARTBEAT_SCRIPT)],
            cwd=str(PROJECT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        print(f"heartbeat spawn failed: {exc}", file=sys.stderr)


def _split_for_discord(text: str) -> list[str]:
    """Discord caps single messages at 2000 chars. Split on paragraph
    boundaries so we don't slice mid-word."""
    if len(text) <= MAX_DISCORD_MSG:
        return [text]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > MAX_DISCORD_MSG:
        cut = remaining.rfind("\n\n", 0, MAX_DISCORD_MSG)
        if cut < MAX_DISCORD_MSG // 2:
            cut = remaining.rfind("\n", 0, MAX_DISCORD_MSG)
        if cut < MAX_DISCORD_MSG // 2:
            cut = MAX_DISCORD_MSG
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def main() -> int:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("DISCORD_BOT_TOKEN not set in .env", file=sys.stderr)
        return 1
    owner_id = os.environ.get("DISCORD_USER_ID", "").strip()
    if not owner_id:
        print(
            "DISCORD_USER_ID not set in .env -- bot will cache messages but "
            "won't reply to anyone. See header comment for how to find it.",
            file=sys.stderr,
        )

    inbox_channel_id   = os.environ.get("DISCORD_INBOX_CHANNEL_ID", "").strip()
    finance_channel_id = os.environ.get("DISCORD_FINANCE_CHANNEL_ID", "").strip()
    vesper_channel_id  = os.environ.get("DISCORD_VESPER_CHANNEL_ID", "").strip()

    try:
        import discord
    except ImportError:
        print("discord.py not installed: py -m pip install -r .claude/requirements.txt", file=sys.stderr)
        return 1

    intents = discord.Intents.default()
    intents.message_content = True
    intents.dm_messages = True
    intents.guilds = True

    client = discord.Client(intents=intents)
    self_id_holder: dict = {"id": None}

    @client.event
    async def on_ready() -> None:
        self_id_holder["id"] = str(client.user.id) if client.user else None
        owner_status = f"owner={owner_id}" if owner_id else "NO OWNER (cache-only mode)"
        print(f"Connected as {client.user} (id={self_id_holder['id']}) | {owner_status}")
        arms = [
            ("inbox",   inbox_channel_id),
            ("finance", finance_channel_id),
            ("vesper",  vesper_channel_id),
        ]
        for name, cid in arms:
            status = f"enabled (channel={cid})" if cid else "DISABLED (env var unset)"
            print(f"  {name} arm: {status}")

    async def _handle_inbox(message) -> None:
        content = (message.content or "").strip()
        handled = False

        if message.attachments:
            saved = await _save_attachments_to_inbox(message)
            if saved:
                _spawn_heartbeat()
                handled = True
                try:
                    await message.add_reaction("✅")
                except Exception as exc:
                    print(f"_handle_inbox reaction failed: {exc}", file=sys.stderr)
            elif any(Path(a.filename).suffix.lower() in INBOX_EXTS for a in message.attachments):
                try:
                    await message.add_reaction("❌")
                    await message.channel.send("[inbox] attachment save returned no files — check logs.")
                except Exception as exc:
                    print(f"_handle_inbox failure-react failed: {exc}", file=sys.stderr)
                return

        if discord_dm_capture.classify(content) == "note":
            try:
                dt = datetime.now(tz=KL)
                stripped = await asyncio.to_thread(
                    discord_dm_capture._append_note, NOTES_FILE, dt, content,
                )
                if stripped:
                    handled = True
                    try:
                        await message.add_reaction("✅")
                    except Exception as exc:
                        print(f"_handle_inbox reaction failed: {exc}", file=sys.stderr)
                else:
                    handled = True
                    try:
                        await message.add_reaction("❌")
                        await message.channel.send("[inbox] note was empty after stripping `note:` prefix.")
                    except Exception as exc:
                        print(f"_handle_inbox empty-note react failed: {exc}", file=sys.stderr)
            except Exception as exc:
                print(f"_handle_inbox note failed: {exc}", file=sys.stderr)
                try:
                    await message.add_reaction("❌")
                    await message.channel.send(f"[inbox] note save error: {type(exc).__name__}")
                except Exception:
                    pass
                return

        if not handled:
            try:
                await message.add_reaction("❓")
            except Exception as exc:
                print(f"_handle_inbox unknown-react failed: {exc}", file=sys.stderr)

    async def _handle_finance(message) -> None:
        content = (message.content or "").strip()

        if content.lower() in ("totals", "finance", "spend"):
            try:
                summary = await asyncio.to_thread(finance_tracker.month_summary)
                await message.channel.send(f"```\n{summary}\n```")
            except Exception as exc:
                print(f"finance summary failed: {exc}", file=sys.stderr)
                try:
                    await message.channel.send(f"[finance summary error: {type(exc).__name__}]")
                except Exception:
                    pass
            return

        expense = finance_tracker.parse(content)
        if expense:
            try:
                result = await asyncio.to_thread(
                    finance_tracker.log,
                    expense["amount"],
                    expense["category"],
                    expense["note"],
                )
                ack = (
                    f"logged {finance_tracker.CURRENCY}{expense['amount']:.2f} / "
                    f"{expense['category']}"
                    + (f" ({expense['note']})" if expense['note'] else "")
                    + f"\nmonth total {finance_tracker.CURRENCY}{result['month_total']:.2f}"
                    + f" | {expense['category']} {finance_tracker.CURRENCY}{result['category_total']:.2f}"
                )
                await message.channel.send(ack)
            except Exception as exc:
                print(f"finance log failed: {exc}", file=sys.stderr)
                try:
                    await message.channel.send(f"[finance log error: {type(exc).__name__}]")
                except Exception:
                    pass
            return

        try:
            await message.add_reaction("❓")
        except Exception as exc:
            print(f"_handle_finance unknown-react failed: {exc}", file=sys.stderr)

    async def _handle_vesper(message) -> None:
        try:
            async with message.channel.typing():
                reply = await asyncio.to_thread(
                    handler.process_message,
                    str(message.author.id),
                    str(message.channel.id),
                    message.content,
                )
            for chunk in _split_for_discord(reply):
                await message.channel.send(chunk)
        except Exception as exc:
            print(f"vesper reply failed: {exc}", file=sys.stderr)
            try:
                await message.channel.send(f"[error generating reply: {type(exc).__name__}]")
            except Exception:
                pass

    async def _route_message(message) -> bool:
        """Dispatch by channel.id. Returns True if a handler ran."""
        cid = str(message.channel.id)
        if cid and cid == inbox_channel_id:
            await _handle_inbox(message)
            return True
        if cid and cid == finance_channel_id:
            await _handle_finance(message)
            return True
        if cid and cid == vesper_channel_id:
            await _handle_vesper(message)
            return True
        return False

    @client.event
    async def on_message(message) -> None:
        try:
            discord_int._store_message(message, self_id_holder["id"])
        except Exception as exc:
            print(f"cache write failed: {exc}", file=sys.stderr)

        # Channel input router (pivot). Owner-only.
        if (
            message.guild is not None
            and owner_id
            and str(message.author.id) == owner_id
            and not message.author.bot
        ):
            if await _route_message(message):
                return

        # Reply gate -- both conditions required.
        if message.guild is not None:
            return
        if not owner_id or str(message.author.id) != owner_id:
            return
        if message.author.bot:
            return
        if str(message.author.id) == self_id_holder["id"]:
            return  # don't reply to ourselves

        content = (message.content or "").strip()

        # Finance: try the expense parser first. If the message matches the
        # "<amount> <category> [note]" pattern, log it and skip the chat
        # handler -- no need for the LLM to read it.
        expense = finance_tracker.parse(content)
        if expense and not message.attachments:
            try:
                result = await asyncio.to_thread(
                    finance_tracker.log,
                    expense["amount"],
                    expense["category"],
                    expense["note"],
                )
                ack = (
                    f"logged {finance_tracker.CURRENCY}{expense['amount']:.2f} / "
                    f"{expense['category']}"
                    + (f" ({expense['note']})" if expense['note'] else "")
                    + f"\nmonth total {finance_tracker.CURRENCY}{result['month_total']:.2f}"
                    + f" | {expense['category']} {finance_tracker.CURRENCY}{result['category_total']:.2f}"
                )
                await message.channel.send(ack)
            except Exception as exc:
                print(f"finance log failed: {exc}", file=sys.stderr)
                await message.channel.send(f"[finance log error: {type(exc).__name__}]")
            return

        # Note capture: classify and append directly to notes/NOTES.md.
        # The bot's reply confirms what code actually did, not what an LLM
        # guesses happened.
        if discord_dm_capture.classify(content) == "note":
            try:
                dt = datetime.now(tz=KL)
                stripped = await asyncio.to_thread(
                    discord_dm_capture._append_note, NOTES_FILE, dt, content,
                )
                if stripped:
                    ack = "got it — note appended to `notes/NOTES.md`."
                    try:
                        dashboard.notify("inbox_text", {
                            "content": stripped,
                            "ts": dt.timestamp(),
                            "vault_path": "notes/NOTES.md",
                        })
                    except Exception as exc:
                        print(f"inbox_text notify failed: {exc}", file=sys.stderr)
                else:
                    ack = "note was empty after stripping the `note:` prefix — nothing written."
                await message.channel.send(ack)
            except Exception as exc:
                print(f"note route failed: {exc}", file=sys.stderr)
                try:
                    await message.channel.send(f"[note route error: {type(exc).__name__}]")
                except Exception:
                    pass
            return

        # "totals" -- show the month summary.
        if content.lower() in ("totals", "finance", "spend"):
            try:
                summary = await asyncio.to_thread(finance_tracker.month_summary)
                await message.channel.send(f"```\n{summary}\n```")
            except Exception as exc:
                print(f"finance summary failed: {exc}", file=sys.stderr)
            return

        # Inbox drop-zone: if the owner DM'd a .pdf or .pptx, save it and
        # kick off a heartbeat tick so it gets classified + summarised.
        if message.attachments:
            saved = await _save_attachments_to_inbox(message)
            if saved:
                _spawn_heartbeat()
                created_ts = message.created_at.replace(tzinfo=timezone.utc).timestamp()
                for filename in saved:
                    try:
                        dashboard.notify("inbox_attachment", {
                            "filename": filename,
                            "vault_path": f"inbox/{filename}",
                            "ts": created_ts,
                        })
                    except Exception as exc:
                        print(f"inbox_attachment notify failed: {exc}", file=sys.stderr)
                ack = f"got {len(saved)} file(s) in inbox: {', '.join(saved)}\nprocessing now -- summary DM incoming."
                try:
                    await message.channel.send(ack)
                except Exception as exc:
                    print(f"ack send failed: {exc}", file=sys.stderr)
                # If the message has no text, don't also run it through the
                # chat handler (it'd just see an empty prompt).
                if not (message.content or "").strip():
                    return

        try:
            async with message.channel.typing():
                reply = await asyncio.to_thread(
                    handler.process_message,
                    str(message.author.id),
                    str(message.channel.id),
                    message.content,
                )
            for chunk in _split_for_discord(reply):
                await message.channel.send(chunk)
        except Exception as exc:
            print(f"reply failed: {exc}", file=sys.stderr)
            try:
                await message.channel.send(f"[error generating reply: {type(exc).__name__}]")
            except Exception:
                pass

    client.run(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
