# BoredBot

My second brain, built on Claude Code. Hooks, scripts, skills, and settings that turn Claude Code into a study partner: deadline tracking, lecture summarisation, and hybrid-RAG note search.

The personal vault (notes, schedules, finances) lives locally at `Dynamous/Memory/` and is **not** committed — that directory is gitignored. Each machine keeps its own vault.

## What it does

- **Deadline tracking** — pulls assignment and class deadlines from Google Calendar, deduplicates, refreshes `DEADLINES.md`, and fires Toast notifications at 24h / 48h.
- **Lecture summarisation** — drop a `.pptx` or `.pdf` into `Dynamous/Memory/inbox/`, get a structured Obsidian note under `lectures/<course>/`.
- **Note search (hybrid RAG)** — 70% vector + 30% BM25 over the whole vault. Embeddings are local (FastEmbed / ONNX, no API calls).
- **Discord DM chat** — Phase 7 bot replies to your own DMs only. Read-only everywhere else.
- **Daily reflection** — at 08:00 KL, promotes durable items from the previous day's `daily/` log into `MEMORY.md`.

Agent operates in **Advisor mode**: it drafts DM replies and sends nothing else without your review.

## Requirements

- Windows 11 (Task Scheduler is the deploy target — Linux/macOS works for dev only)
- Python 3.14 (`py` launcher on PATH)
- Claude Code
- Google account if you want Calendar integration
- Discord bot token if you want Discord features

## Setup

```powershell
# 1. Clone
git clone https://github.com/CrudusLiv/BoredBot.git
cd BoredBot

# 2. Install Python deps
py -m pip install -r .claude/requirements.txt

# 3. Secrets
Copy-Item .env.example .env
# Edit .env — only fill in what you'll actually use.

# 4. (Optional) Google credentials
#    Place google_credentials.json at .claude/data/google_credentials.json
#    First run of the Calendar integration triggers the OAuth flow; the
#    token is cached at .claude/data/google_token.json.

# 5. Vault
#    The agent expects Dynamous/Memory/ with at minimum SOUL.md and USER.md
#    (see CLAUDE.md for the full layout). The directory is gitignored —
#    copy your own vault into place, or start fresh from the templates.

# 6. Open the directory in Claude Code. Session hooks fire automatically.

# 7. Verify everything is wired up
py .claude\scripts\query.py status
```

## Deploying the background bot

The four scheduled tasks live in `.claude/scripts/deploy/`. Open PowerShell **as Administrator** (`Register-ScheduledTask` requires elevation, even for user-scoped tasks):

```powershell
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\install_tasks.ps1
```

Idempotent — re-running replaces any existing `secondbrain-*` task.

| Task | Trigger | What it runs |
|---|---|---|
| `secondbrain-heartbeat` | Daily 09:00 KL, every 30 min for 13 h | `heartbeat.py` — integration scan, draft replies, Toast alerts |
| `secondbrain-reflect`   | Daily 08:00 KL | `memory_reflect.py` — promote daily log into `MEMORY.md` |
| `secondbrain-index`     | Every 10 min | `memory/memory_index.py` — re-embed changed vault files |
| `secondbrain-discord`   | At logon, restart on failure | `start_discord_bot.ps1` — DM chat + message cache |

Inspect:

```powershell
Get-ScheduledTask -TaskName 'secondbrain-*' |
    Format-Table TaskName, State, LastRunTime, NextRunTime
Get-ScheduledTaskInfo -TaskName 'secondbrain-heartbeat'
Get-Content .claude\data\logs\discord-*.log -Wait -Tail 20
```

## Pausing the bot (disable without uninstalling)

If you want the bot to **stop auto-running** but keep all the task definitions, env, OAuth tokens, and vault intact for later — disable the scheduled tasks. They stay registered but won't fire until you re-enable them.

Open PowerShell **as Administrator**:

```powershell
# Disable all four tasks at once
Get-ScheduledTask -TaskName 'secondbrain-*' | Disable-ScheduledTask

# Or disable individually
Disable-ScheduledTask -TaskName 'secondbrain-heartbeat'
Disable-ScheduledTask -TaskName 'secondbrain-discord'
```

A disabled task survives reboots, Windows updates, and re-logons — it will not run again until you explicitly enable it. The Discord bot, since it runs at logon, also needs the **already-running** process killed if you disable it mid-session:

```powershell
# Kill the live Discord bot loop (the launcher will not restart it once the task is disabled)
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

If you want the tasks **gone**, not just paused:

```powershell
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\uninstall_tasks.ps1
```

Removes all four tasks. Logs and vault data are preserved — delete `.claude\data\logs\` and `Dynamous\Memory\` manually if you want those gone too.

## Layout

| Path | Purpose |
|------|---------|
| `.claude/hooks/` | SessionStart, PreCompact, SessionEnd, PreToolUse, UserPromptSubmit |
| `.claude/scripts/` | `query.py` CLI dispatcher, `heartbeat.py`, `memory_reflect.py`, integrations, memory (RAG), deploy scripts |
| `.claude/scripts/deploy/` | `install_tasks.ps1`, `uninstall_tasks.ps1`, `start_discord_bot.ps1` |
| `.claude/chat/` | Discord DM chat bot (Phase 7) |
| `.claude/skills/` | Skills the agent invokes — `deadline-tracker`, `lecture-summarizer`, `note-search`, `vault-structure` |
| `.claude/settings.json` | Wires hooks into Claude Code |
| `.claude/data/` | Runtime artefacts — OAuth tokens, SQLite memory DB, FastEmbed cache, logs (gitignored) |
| `tests/` | pytest suite |
| `Dynamous/Memory/` | Personal vault (local-only, gitignored) |

## Quick commands

```powershell
# Integration status
py .claude\scripts\query.py status

# Pull data
py .claude\scripts\query.py gcal upcoming --days 14
py .claude\scripts\query.py discord recent --hours 24
py .claude\scripts\query.py github pr-list <owner/repo>
py .claude\scripts\query.py vault inbox

# Memory / RAG
py .claude\scripts\memory\memory_index.py                          # rebuild index
py .claude\scripts\memory\memory_search.py "deadline" --top-k 5

# Run heartbeat manually (useful for testing toasts / drafts)
py .claude\scripts\heartbeat.py

# Tests
pytest
```

Most subcommands accept `--json` for machine-readable output.

See `CLAUDE.md` for the full architecture notes, hook lifecycle, and integration-template walkthrough.
