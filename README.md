# BoredBot

A second brain built on Claude Code. Hooks, scripts, skills, and scheduled tasks that turn Claude Code into a study partner: deadline tracking, lecture summarisation, hybrid-RAG note search, a Discord dashboard that mirrors the vault, and Windows-Toast pings the moment you get @mentioned.

The personal vault (notes, schedules, finances) lives locally at `Dynamous/Memory/` and is **not** committed — that directory is gitignored. Each machine keeps its own vault.

Agent operates in **Advisor mode**: it drafts replies and writes into the vault, but never sends or commits without your review.

## What it does

- **Discord @mention + reply pings** — when you're @mentioned or someone replies to one of your messages, a Windows Toast pops up and you get a DM-to-self. No LLM in the loop; fastest path from "someone needs me" to "I know."
- **Discord dashboard** — every event the heartbeat cares about (deadlines, lectures, PR activity, daily digest, errors, heartbeat liveness) posts to a dedicated channel via webhooks. Forum-style channels (`#deadlines`, `#lectures`) spawn a per-row thread; the in-thread chatbot (Slice 7) replies when you talk back.
- **Discord channel input** — `#inbox` captures notes and `.pdf` / `.pptx` attachments; `#finance` parses expense lines into the ledger; `#vesper` is the LLM chat channel. DMs from you are cache-only.
- **Deadline tracking** — project documents dropped into `inbox/` are classified, dated milestones get promoted into `DEADLINES.md`, mirrored to Google Calendar, and routed into forum threads at 72h / 24h / overdue thresholds.
- **Lecture summarisation** — drop a `.pptx` or `.pdf` into `Dynamous/Memory/inbox/`, get a structured Obsidian note under `lectures/<course>/` and a new forum thread in `#lectures`.
- **Hybrid-RAG note search** — 70% vector + 30% BM25 over the whole vault. Embeddings are local (FastEmbed / ONNX, no API calls).
- **Heartbeat reasoning** — every 30 min during active hours, Python builds a snapshot diff and an LLM decides what (if anything) is worth notifying you about. Cheap tasks (inbox classification, heartbeat actions, memory reflection) route to a local Ollama instance; security-sensitive and in-thread chat tasks stay on Claude Haiku. Routing is configurable via `.claude/data/llm-config.json`.
- **Discord embed redesign** — all webhook posts and bot DMs now use a unified Vesper embed style: consistent colour palette, structured fields, and Obsidian deep-link buttons where applicable.
- **Daily reflection** — at 08:00 KL, promotes durable items from yesterday's `daily/` log into `MEMORY.md`; rolls `HABITS.md`.
- **Vault guardrails** — a path validator with hard-coded forbidden prefixes, an append-only JSONL transaction log, and a `suggest_for_missing` typo-recovery layer protect the vault from accidental writes.

## Requirements

- Windows 11 (Task Scheduler is the deploy target — Linux/macOS works for dev only)
- Python 3.14 (`py` launcher on PATH)
- Claude Code
- A Discord bot token (required for pings and everything Discord-related)
- A Google account (optional — only needed for Calendar sync)
- A GitHub personal access token (optional — only needed for PR activity routing)

---

# Quickstart: just Discord @mention pings

The minimum viable setup. You'll get a Windows Toast + a DM-to-self every time someone @mentions you in a Discord server the bot has been invited to. **No vault required, no Google account, no LLM call, no webhooks.**

## 1. Create the Discord bot

In the [Discord Developer Portal](https://discord.com/developers/applications):

1. **New Application** → name it whatever
2. **Bot** tab → **Reset Token** → copy the token (this becomes `DISCORD_BOT_TOKEN`)
3. **Privileged Gateway Intents** → enable **Message Content Intent**
4. **OAuth2 → URL Generator** → scopes: `bot`; permissions: `Read Messages/View Channels`, `Read Message History`. Open the generated URL and add the bot to the servers you want to be pinged from.

Then grab your own user ID:

- Discord client → Settings → Advanced → enable **Developer Mode**
- Right-click your username → **Copy User ID** (this becomes `DISCORD_USER_ID`)

## 2. Install Python deps

```powershell
git clone https://github.com/CrudusLiv/BoredBot.git
cd BoredBot
py -m pip install -r .claude/requirements.txt
```

## 3. Configure secrets

```powershell
Copy-Item .env.example .env
```

Open `.env` and fill in only these two:

```ini
DISCORD_BOT_TOKEN=<your bot token>
DISCORD_USER_ID=<your numeric user ID>
```

Leave every other key empty. Webhook URLs, Google creds, GitHub tokens — all optional. Their corresponding features silently skip when env vars are missing.

## 4. Install the two tasks you need

Open PowerShell **as Administrator** (`Register-ScheduledTask` requires elevation, even for user-scoped tasks):

```powershell
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\install_tasks.ps1
```

The installer registers four `secondbrain-*` tasks. For pings-only, you need:

- `secondbrain-discord` — runs the bot at logon. It writes every visible message into `.claude/data/discord_cache.db`.
- `secondbrain-heartbeat` — every 30 min between 09:00–22:00 KL, scans the cache for new `<@your_id>` mentions and fires the Toast + DM.

Disable the two you don't need:

```powershell
Disable-ScheduledTask -TaskName 'secondbrain-reflect'   # needs a vault
Disable-ScheduledTask -TaskName 'secondbrain-index'     # needs vault files to embed
```

The Discord task fires at logon — to start it now without rebooting:

```powershell
Start-ScheduledTask -TaskName 'secondbrain-discord'
```

## 5. Verify

```powershell
# Both should be Running / Ready
Get-ScheduledTask -TaskName 'secondbrain-discord','secondbrain-heartbeat' |
    Format-Table TaskName, State, LastRunTime, NextRunTime

# Tail the bot log to confirm it connected
Get-Content .claude\data\logs\discord-*.log -Wait -Tail 20

# Manual heartbeat tick (don't wait for the next 30-min mark)
py .claude\scripts\heartbeat.py
```

Have someone @mention you in a server the bot is in. Within 30 minutes (or immediately if you run the heartbeat manually) you should get a Toast and a DM.

**Troubleshooting:** no Toast on Windows means `winotify` failed silently; check the heartbeat's stderr. No DM means `DISCORD_USER_ID` is wrong or the bot can't open a DM with you (Discord requires you share a server).

---

# Full setup

If you want everything — dashboard, deadlines, lectures, RAG search, the LLM chat — pick up from the quickstart and add the rest.

## Google credentials (optional, for Calendar)

Place `google_credentials.json` at `.claude/data/google_credentials.json`. First run of any GCal command triggers an OAuth flow in your browser; the token is cached at `.claude/data/google_token.json` and reused thereafter.

## Discord dashboard webhooks

The dashboard routes events to channels via Discord webhooks. Each `DISCORD_HOOK_*` env var is one channel; empty values silently skip, so you can wire channels incrementally.

In Discord, for each channel: **Channel Settings → Integrations → Webhooks → New Webhook → Copy URL**. Paste into the matching key in `.env`:

| Env var | Channel role | Event kinds routed here |
|---|---|---|
| `DISCORD_HOOK_HEARTBEAT` | `#heartbeat` | `heartbeat_tick` — throttled liveness post |
| `DISCORD_HOOK_ERRORS` | `#errors` | Uncaught script exceptions |
| `DISCORD_HOOK_INBOX` | `#inbox` | `inbox_text`, `inbox_attachment` |
| `DISCORD_HOOK_DEADLINES` | `#deadlines` *(forum)* | `deadline_72h`, `deadline_24h`, `deadline_overdue`, `next3`, `deadline_reply` |
| `DISCORD_HOOK_LECTURES` | `#lectures` *(forum)* | `lecture_new`, `lecture_reply` |
| `DISCORD_HOOK_PR_ACTIVITY` | `#pr-activity` | `pr_opened`, `pr_merged`, `pr_comment` |
| `DISCORD_HOOK_CODE_REVIEW` | `#code-review` | `code_review` |
| `DISCORD_HOOK_DAILY` | `#daily` | `morning_digest`, `evening_nudge`, `daily_digest` (emoji prefix distinguishes) |
| `DISCORD_HOOK_VESPER` | `#vesper` | `vesper_reply` |
| `DISCORD_HOOK_IDEAS` | `#ideas` | `idea` |
| `DISCORD_HOOK_EMAIL_UNI`, `_EMAIL_PERSONAL` | `#email-*` | Reserved for email-source integrations |

`#deadlines` and `#lectures` must be **forum channels** — the heartbeat creates a thread per deadline / lecture so the in-thread chatbot (Slice 7) can reply when you talk back.

## Discord channel input

The bot reads messages in three specific channels and routes them to handlers. Each is independent — leave any unset and that arm is disabled.

| Env var | Channel | What it does |
|---|---|---|
| `DISCORD_INBOX_CHANNEL_ID` | `#inbox` | Text → appended to `notes/NOTES.md`. `.pdf`/`.pptx` attachments → saved to `Dynamous/Memory/inbox/` and queued for the lecture-summarizer. |
| `DISCORD_FINANCE_CHANNEL_ID` | `#finance` | Lines like `lunch 12.50` get parsed and appended to the finance ledger. Totals are posted back. |
| `DISCORD_VESPER_CHANNEL_ID` | `#vesper` | LLM chat with the agent's persona. |

Right-click a channel in Discord (with Developer Mode on) → **Copy Channel ID**.

**Security model:** the bot only ever calls `channel.send()` when the message author matches `DISCORD_USER_ID` *and* the channel ID matches one of these three. DMs are cache-only — no replies, no reacts.

## GitHub (optional)

```ini
GITHUB_TOKEN=ghp_...                       # scope: repo
GITHUB_ASSIGNMENT_REPOS=owner/repo1,owner/repo2  # scoped to the code-reviewer skill
```

`GITHUB_TOKEN` enables the PR activity router — every open/merge/comment across every repo your token can see posts to `#pr-activity`. `GITHUB_ASSIGNMENT_REPOS` is a separate, narrower list used by the code-reviewer skill.

## Vault layout

The agent expects `Dynamous/Memory/` to exist. Minimum required files:

- `SOUL.md` — agent personality (loaded into every session via `SessionStart` hook)
- `USER.md` — user profile (also loaded at session start)

Recommended folders (created on first use, but worth knowing):

- `daily/YYYY-MM-DD.md` — per-day session logs
- `MEMORY.md` — durable promoted items
- `DEADLINES.md` — active deadlines (auto-managed)
- `HABITS.md` — habit tracker (auto-rolled)
- `inbox/` — drop zone for `.pptx` / `.pdf`
- `inbox/_processed/` — gitignored; sources are deleted after summarisation, the folder stays via `.gitkeep`
- `lectures/<course>/` — output of the lecture-summarizer
- `notes/NOTES.md` — `#inbox` channel notes land here

The vault is gitignored — copy your own in, or start fresh from templates.

## Deploying the background bot

Four scheduled tasks live in `.claude/scripts/deploy/`. Open PowerShell **as Administrator**:

```powershell
# Default — heartbeat runs invisibly (no console window)
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\install_tasks.ps1

# Optional — show a console window for the heartbeat (useful for debugging)
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\install_tasks.ps1 -VisibleHeartbeat
```

Idempotent — re-running replaces any existing `secondbrain-*` task.

| Task | Trigger | What it runs |
|---|---|---|
| `secondbrain-heartbeat` | Daily 09:00 KL, every 30 min for 13 h | `run_heartbeat.vbs` → `heartbeat.py` — snapshot diff, LLM reasoning, dashboard posts, Toast pings |
| `secondbrain-reflect` | Daily 08:00 KL | `memory_reflect.py` — promote yesterday's daily log into `MEMORY.md`, roll `HABITS.md` |
| `secondbrain-index` | Every 10 min | `run_index.vbs` → `memory/memory_index.py` — re-embed changed vault files |
| `secondbrain-discord` | At logon, restart on failure | `start_discord_bot.vbs` → `start_discord_bot.ps1` — message cache + channel router |

**Choosing heartbeat launch style:**

| Mode | How it runs | When to use |
|---|---|---|
| Default (invisible) | `wscript.exe run_heartbeat.vbs` — no popup | Normal daily use — output is written to `state/refresh-log.md` in the vault |
| `-VisibleHeartbeat` | `py heartbeat.py` directly — shows a console window | Debugging; lets you read stdout/stderr live |

The `secondbrain-discord` task triggers at logon. After installing, either reboot or start it manually:

```powershell
Start-ScheduledTask -TaskName 'secondbrain-discord'
```

Inspect:

```powershell
Get-ScheduledTask -TaskName 'secondbrain-*' |
    Format-Table TaskName, State, LastRunTime, NextRunTime
Get-ScheduledTaskInfo -TaskName 'secondbrain-heartbeat'
Get-Content .claude\data\logs\discord-*.log -Wait -Tail 20
```

## Pausing the bot (disable without uninstalling)

Disable the scheduled tasks. They stay registered but won't fire until re-enabled.

Open PowerShell **as Administrator**:

```powershell
# Disable all four
Get-ScheduledTask -TaskName 'secondbrain-*' | Disable-ScheduledTask

# Or individually
Disable-ScheduledTask -TaskName 'secondbrain-heartbeat'
Disable-ScheduledTask -TaskName 'secondbrain-discord'
```

A disabled task survives reboots, Windows updates, and re-logons — it won't run again until you explicitly enable it. The Discord bot, since it runs at logon, also needs the already-running process killed if you disable it mid-session:

```powershell
Get-Process -Name pwsh, wscript, python, py -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like '*BoredBot*' -or $_.CommandLine -like '*discord_bot*' } |
    Stop-Process -Force
```

Confirm everything is paused:

```powershell
Get-ScheduledTask -TaskName 'secondbrain-*' | Format-Table TaskName, State
# State should read 'Disabled' for all four.
```

### Re-enabling later

```powershell
Get-ScheduledTask -TaskName 'secondbrain-*' | Enable-ScheduledTask
```

The Discord task will fire again at your next logon (or run `Start-ScheduledTask -TaskName 'secondbrain-discord'` to start it immediately). The heartbeat and index pick up on their next scheduled tick.

### Fully uninstalling

```powershell
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\uninstall_tasks.ps1
```

Removes all four tasks. Logs and vault data are preserved — delete `.claude\data\logs\` and `Dynamous\Memory\` manually if you want those gone too.

## Layout

| Path | Purpose |
|------|---------|
| `.claude/hooks/` | SessionStart, PreCompact, SessionEnd, PreToolUse, UserPromptSubmit |
| `.claude/scripts/` | `query.py` CLI dispatcher, `heartbeat.py`, `memory_reflect.py`, integrations, memory (RAG), deploy scripts |
| `.claude/scripts/heartbeat/` | Tick sub-modules — `dashboard.py` (Vesper embed router), `discord_ping.py` (@mention + reply scanner), `deadlines.py`, `inbox.py`, `imminent.py`, `gcal_sync.py`, `toast.py`, `notify.py`, `llm.py` (Ollama/Claude routing), `thread_chat.py`, `backfill_lectures.py` (one-shot vault → `#lectures` poster), etc. |
| `.claude/scripts/vault/` | Vault guardrails — `paths.py` (path validator), `transactions.py` (append-only JSONL log), `actions.py` (append/create helpers) |
| `.claude/scripts/deploy/` | `install_tasks.ps1`, `uninstall_tasks.ps1`, `start_discord_bot.ps1`, `run_heartbeat.vbs`, `run_index.vbs` |
| `.claude/chat/` | Discord bot — message cache + `#inbox` / `#finance` / `#vesper` channel router |
| `.claude/skills/` | Skills the agent invokes — `deadline-tracker`, `lecture-summarizer`, `note-search`, `vault-structure` |
| `.claude/settings.json` | Wires hooks into Claude Code |
| `.claude/data/` | Runtime artefacts — OAuth tokens, SQLite memory DB, FastEmbed cache, Discord cache, dashboard state, logs (gitignored) |
| `tests/` | pytest suite |
| `Dynamous/Memory/` | Personal vault (local-only, gitignored) |

## Quick commands

```powershell
# Integration status — which features are wired up
py .claude\scripts\query.py status

# Pull data
py .claude\scripts\query.py gcal upcoming --days 14
py .claude\scripts\query.py discord recent --hours 24
py .claude\scripts\query.py github pr-list <owner/repo>
py .claude\scripts\query.py vault inbox

# Memory / RAG
py .claude\scripts\memory\memory_index.py                          # rebuild index
py .claude\scripts\memory\memory_search.py "deadline" --top-k 5

# Run heartbeat manually (shows console, useful for debugging)
py .claude\scripts\heartbeat.py

# On-demand refresh without the scheduler — updates Obsidian dashboard + fires ping notifications
py .claude\scripts\refresh.py

# Backfill existing vault lectures to the #lectures forum (idempotent — skips already-posted)
py .claude\scripts\heartbeat\backfill_lectures.py

# Tests
pytest
```

Most subcommands accept `--json` for machine-readable output.

See `CLAUDE.md` for full architecture notes, hook lifecycle, and the integration-template walkthrough.
