"""Discord bot: cache every message AND route owner posts in three input
channels (#inbox, #finance, #vesper) to per-channel handlers. Replaces the
bot in `discord_int.run_bot()`.

SECURITY CARVE-OUT (post 2026-05-24 input pivot)
================================================
This is the ONLY place in the codebase that calls `channel.send()`. The
guardrail is two-pronged and AND-ed:

1.  message.author.id matches DISCORD_USER_ID from .env -- only CrudusLiv.
2.  message.channel.id matches DISCORD_INBOX_CHANNEL_ID, _FINANCE_, or
    _VESPER_ -- input is channel-scoped, never wildcard.

DMs from the owner are CACHE-ONLY: they are stored in discord_cache.db but
trigger no handler, no reply, no react. The pre-pivot DM-input branches
(finance parser, note classifier, totals, attachment, chat) have moved to
_handle_finance / _handle_inbox / _handle_vesper respectively. The cache
write (Phase 4.1 read-only behavior) still fires for every message,
regardless of author or channel, before the gate runs.

Outbound DMs from this codebase are limited to discord_ping.py's
server-mention forward via notify.send. Everything else routes through
dashboard.notify(<kind>, ...) webhooks. See:
docs/superpowers/specs/2026-05-24-discord-input-pivot-design.md

ENV REQUIRED
============
- DISCORD_BOT_TOKEN  -- the bot token (Phase 4.1, already set)
- DISCORD_USER_ID    -- your numeric Discord user ID. Developer Mode ->
  right-click your name -> Copy User ID.
- DISCORD_INBOX_CHANNEL_ID, DISCORD_FINANCE_CHANNEL_ID,
  DISCORD_VESPER_CHANNEL_ID -- right-click each channel -> Copy Channel ID.
  Each is optional; that arm is disabled if unset.

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
from heartbeat import discord_dm_capture  # noqa: E402
from integrations import discord_int  # noqa: E402
from vault import actions as vault_actions  # noqa: E402
import schedule_parser  # noqa: E402

from datetime import datetime, timedelta, timezone  # noqa: E402

KL = timezone(timedelta(hours=8))
NOTES_FILE = PROJECT_DIR / "Dynamous" / "Memory" / "notes" / "NOTES.md"

MAX_DISCORD_MSG = 2000

INBOX = PROJECT_DIR / "Dynamous" / "Memory" / "inbox"
HEARTBEAT_SCRIPT = PROJECT_DIR / ".claude" / "scripts" / "heartbeat.py"
INBOX_EXTS = {".pdf", ".pptx"}

HELP_TITLE = "**Vesper — Quick Reference**"


def build_help_text() -> str:
    """The preset reference text. Used by /help and the pinned message.

    Opens with HELP_TITLE so the pin can be found and edited in place on
    restart (Discord renders text literally, so no hidden marker is usable)."""
    return (
        f"{HELP_TITLE}\n"
        "\n"
        "Slash commands (work in any channel, only you can use them):\n"
        "• `/schedule text:<timetable>` — set or replace your class timetable\n"
        "   (if one already exists, re-run with `confirm:true` to replace it)\n"
        "• `/note text:<note>` — save a quick note to NOTES.md\n"
        "• `/finance text:<e.g. 12.50 food lunch>` — log an expense\n"
        "• `/totals` — this month's spending summary\n"
        "• `/list dir:<folder>` — list files in a vault folder\n"
        "• `/delete path:<file>` — soft-delete a vault file (recoverable via /undo)\n"
        "• `/undo` — undo the last vault action\n"
        "• `/help` — show this message\n"
        "\n"
        "You can also:\n"
        "• Just talk to me in #vesper\n"
        "• Drop .pdf / .pptx lecture files in #inbox to get them summarized\n"
        "• Use the text prefixes in their channels: `schedule:`, `note:`, "
        "`delete:`, `list:`, `undo`, `totals`\n"
    )


def _slash_text(reaction: str | None, text: str | None) -> str:
    """Map a helper's (reaction, text) result to an ephemeral slash reply.

    Slash commands can't add reactions, so when a helper signals success
    purely via a reaction (text is None) we substitute a short phrase."""
    if text:
        return text
    return {"✅": "Done.", "❌": "Failed.", "❓": "Unrecognized."}.get(reaction or "", "Done.")


def run_schedule(raw: str, *, confirm: bool) -> tuple[str | None, str | None]:
    """Schedule-set flow. Returns (reaction, text).

    confirm=True  -> write the stashed pending entries (the `schedule: yes` path).
    confirm=False -> parse `raw`; if a schedule already exists, stash pending and
                     ask the caller to confirm; otherwise write immediately.
    Blocking I/O — async callers wrap this in asyncio.to_thread."""
    try:
        if confirm:
            entries = schedule_parser.read_pending()
            if entries is None:
                return "❓", "Nothing pending. Send a schedule first."
            schedule_parser.write_schedule(entries)
            schedule_parser.clear_pending()
            return "✅", "Done — schedule updated."

        entries, summary = schedule_parser.parse_timetable(raw)
        if schedule_parser.has_existing_schedule():
            schedule_parser.write_pending(entries)
            return "❓", (
                f"You already have a schedule. Here's what I parsed:\n{summary}\n"
                "Confirm to replace it (`schedule: yes` or `/schedule confirm:true`)."
            )
        schedule_parser.write_schedule(entries)
        return "✅", summary
    except ValueError:
        return "❌", "[schedule] Failed to parse timetable — try again or paste in a different format."
    except Exception as exc:
        print(f"run_schedule failed: {exc}", file=sys.stderr)
        return "❌", f"[schedule] Write error: {type(exc).__name__}"


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
            elif discord_dm_capture.classify(content) != "note":
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

        # schedule: prefix — parse timetable or confirm pending overwrite
        if not handled and content.lower().startswith("schedule:"):
            handled = True
            raw = content[len("schedule:"):].strip()
            try:
                if raw.lower() == "yes":
                    entries = await asyncio.to_thread(schedule_parser.read_pending)
                    if entries is None:
                        await message.channel.send(
                            "Nothing pending. Send `schedule: [text]` first."
                        )
                        try:
                            await message.add_reaction("❓")
                        except Exception as exc:
                            print(f"_handle_inbox schedule-react failed: {exc}", file=sys.stderr)
                    else:
                        await asyncio.to_thread(schedule_parser.write_schedule, entries)
                        await asyncio.to_thread(schedule_parser.clear_pending)
                        await message.channel.send("Done — schedule updated.")
                        try:
                            await message.add_reaction("✅")
                        except Exception as exc:
                            print(f"_handle_inbox schedule-react failed: {exc}", file=sys.stderr)
                else:
                    entries, summary = await asyncio.to_thread(
                        schedule_parser.parse_timetable, raw
                    )
                    if await asyncio.to_thread(schedule_parser.has_existing_schedule):
                        await asyncio.to_thread(schedule_parser.write_pending, entries)
                        await message.channel.send(
                            f"You already have a schedule. Here's what I parsed:\n{summary}\n"
                            "Send `schedule: yes` to replace it."
                        )
                        try:
                            await message.add_reaction("❓")
                        except Exception as exc:
                            print(f"_handle_inbox schedule-react failed: {exc}", file=sys.stderr)
                    else:
                        await asyncio.to_thread(schedule_parser.write_schedule, entries)
                        await message.channel.send(summary)
                        try:
                            await message.add_reaction("✅")
                        except Exception as exc:
                            print(f"_handle_inbox schedule-react failed: {exc}", file=sys.stderr)
            except ValueError:
                try:
                    await message.add_reaction("❌")
                    await message.channel.send(
                        "[schedule] Failed to parse timetable — try again or paste in a different format."
                    )
                except Exception as exc:
                    print(f"_handle_inbox schedule-error-react failed: {exc}", file=sys.stderr)
            except Exception as exc:
                print(f"_handle_inbox schedule failed: {exc}", file=sys.stderr)
                try:
                    await message.add_reaction("❌")
                    await message.channel.send(f"[schedule] Write error: {type(exc).__name__}")
                except Exception:
                    pass

        # Deterministic verb dispatch: `undo`, `delete: <path>`, `list: <dir>`.
        # No LLM. These call into vault.actions (Tasks 4-7 infrastructure).
        if not handled:
            lowered = content.lower()
            verb_text: str | None = None
            try:
                if lowered == "undo":
                    result = await asyncio.to_thread(vault_actions.undo)
                    verb_text = result["message"]
                elif lowered.startswith("delete:"):
                    target = content[len("delete:"):].strip()
                    result = await asyncio.to_thread(vault_actions.delete, target)
                    verb_text = f"soft-deleted {result['path']} -> {result['trash_path']}"
                elif lowered.startswith("list:"):
                    target = content[len("list:"):].strip()
                    result = await asyncio.to_thread(vault_actions.list_dir, target)
                    entries = result["entries"]
                    if not entries:
                        verb_text = f"{result['directory']}/ is empty"
                    else:
                        listing = ", ".join(entries[:20])
                        more = f" (+{len(entries) - 20} more)" if len(entries) > 20 else ""
                        verb_text = f"{result['directory']}/: {listing}{more}"

                if verb_text is not None:
                    handled = True
                    try:
                        await message.add_reaction("✅")
                    except Exception as exc:
                        print(f"_handle_inbox verb-react failed: {exc}", file=sys.stderr)
                    await message.channel.send(f"[inbox] {verb_text}")
            except (FileNotFoundError, FileExistsError, ValueError, NotADirectoryError) as exc:
                handled = True
                try:
                    await message.add_reaction("❌")
                    await message.channel.send(f"[inbox] {type(exc).__name__}: {exc}")
                except Exception as exc2:
                    print(f"_handle_inbox verb error-react failed: {exc2}", file=sys.stderr)
            except Exception as exc:
                handled = True
                print(f"_handle_inbox verb failed: {exc}", file=sys.stderr)
                try:
                    await message.add_reaction("❌")
                    await message.channel.send(f"[inbox] verb error: {type(exc).__name__}")
                except Exception:
                    pass

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
        # Cache every message, always. Phase 4.1 behavior preserved.
        try:
            discord_int._store_message(message, self_id_holder["id"])
        except Exception as exc:
            print(f"cache write failed: {exc}", file=sys.stderr)

        # Owner-only gate. Bots, other users, and our own messages are ignored.
        if not owner_id or str(message.author.id) != owner_id:
            return
        if message.author.bot:
            return
        if str(message.author.id) == self_id_holder["id"]:
            return

        # Channel input router. Owner posts in configured channels get handled.
        if message.guild is not None:
            await _route_message(message)
            return

        # Owner DMs the bot: cache-only per the 2026-05-24 input pivot.
        # See docs/superpowers/specs/2026-05-24-discord-input-pivot-design.md
        return

    client.run(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
