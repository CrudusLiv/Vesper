# Vesper

A personal second brain built on Claude Code agent layer: Discord UI for chat and inbox, auto-enriching lectures with concepts and study roadmaps, deadline tracking, hybrid-RAG note search, and GCal sync.

The personal vault (notes, schedules, finances) lives locally at `Dynamous/Memory/` — gitignored. Each machine keeps its own vault.

Agent operates in **Advisor mode**: it drafts replies and writes into the vault, but never sends or commits without your review.

## What it does

- **Discord UI** — `#vesper` chat channel, `#inbox` for notes, `#finance` for expenses, and slash commands for schedules, habits, deadlines, and admin.
- **Lecture enrichment** — drop a `.pptx` or `.pdf` into `Dynamous/Memory/inbox/`, get a structured Obsidian note with learning objectives, worked examples, and practice problems extracted and auto-formatted.
- **Concept linking** — lectures are auto-scanned for concepts; concept stub files are created/updated, and wikilinks are auto-added to connect related lectures and concepts.
- **Study roadmaps** — after each lecture, a personalized roadmap is generated with review queue, practice problems, and synthesis tasks, then posted to Discord.
- **Ambient notifications** — heartbeat surfaces meaningful connections (dependency gaps, synthesis readiness, prerequisite alerts) without asking, keeping you aware of what to focus on next.
- **Deadline tracking** — project documents dropped into `inbox/` are classified, dated milestones get promoted into `DEADLINES.md` and mirrored to Google Calendar, with 72h / 24h / overdue threshold tracking.
- **Hybrid-RAG note search** — 70% vector + 30% BM25 over the whole vault. Embeddings are local (FastEmbed / ONNX, no API calls).
- **Heartbeat reasoning** — every 30 min during active hours, Python builds a snapshot diff and an LLM decides what notifications to surface. Feature slices can be toggled via `tray_settings.json`.
- **Daily reflection** — at 08:00 KL, promotes durable items from yesterday's `daily/` log into `MEMORY.md`; rolls `HABITS.md`.
- **Vault guardrails** — path validator, append-only JSONL transaction log, and typo-recovery layer protect the vault from accidental writes.

## Requirements

- Windows 11 (primary deploy target — Linux/macOS works for dev)
- Python 3.14 (`py` launcher on PATH)
- Docker Desktop
- Claude Code
- A Google account (optional — only needed for Calendar sync)
- A GitHub personal access token (optional — only needed for PR activity routing)

---

# Quickstart

## 1. Clone and configure secrets

```powershell
git clone https://github.com/CrudusLiv/Vesper.git
cd Vesper
Copy-Item .env.example .env
```

Open `.env` and fill in `API_SECRET` at minimum (required for frontend → API auth). All other keys are optional — their features silently skip when env vars are missing.

## 2. Install Python deps

```powershell
py -m pip install -r .claude/requirements.txt
```

## 3. Start Discord bot with Docker

```powershell
docker compose up -d
```

Verify:
```powershell
docker compose ps
```

Expected: `discord-bot` and `scheduler` both "Up".

**Heartbeat scheduler** (runs automated tasks every 30 min):

```powershell
docker compose up -d scheduler
```

## 4. Configure settings (optional)

Settings are stored in `.claude/data/tray_settings.json` and read by the scheduler:

- **Active Hours**: when the heartbeat runs (default 09:00–22:00 KL)
- **Heartbeat Interval**: schedule frequency (default 30 min, min 5, max 120)
- **Features**: enable/disable per-feature processing (inbox, reflection, calendar sync, ambient notifications, etc.)

Edit the file directly and settings take effect on the next heartbeat tick.

---

# Full setup

## Google credentials (optional, for Calendar)

Place `google_credentials.json` at `.claude/data/google_credentials.json`. First run of any GCal command triggers an OAuth flow in your browser; the token is cached at `.claude/data/google_token.json` and reused thereafter.

## GitHub (optional)

```ini
GITHUB_TOKEN=ghp_...
GITHUB_ASSIGNMENT_REPOS=owner/repo1,owner/repo2
```

## Vault layout

The agent expects `Dynamous/Memory/` to exist. Minimum required files:

- `SOUL.md` — agent personality (loaded into every session via `SessionStart` hook)
- `USER.md` — user profile (also loaded at session start)

Recommended folders:

- `daily/YYYY-MM-DD.md` — per-day session logs
- `MEMORY.md` — durable promoted items
- `DEADLINES.md` — active deadlines (auto-managed)
- `HABITS.md` — habit tracker (auto-rolled)
- `inbox/` — drop zone for `.pptx` / `.pdf`
- `lectures/<course>/` — output of the lecture-summarizer

---

## Layout

| Path | Purpose |
|------|---------|
| `worker/` | Docker worker base image (discord-bot + heartbeat scheduler) |
| `docker-compose.yml` | Service wiring (discord-bot, scheduler) |
| `chat/` | Discord bot implementation (`discord_bot.py`) |
| `.claude/hooks/` | SessionStart, PreCompact, SessionEnd, PreToolUse, UserPromptSubmit |
| `.claude/scripts/` | Core modules: `query.py` CLI, `heartbeat.py`, `inbox.py`, `ambient_notifier.py`, `concept_linker.py`, `roadmap_generator.py`, integrations, memory (RAG) |
| `.claude/scripts/integrations/` | Service integrations — `github_int.py`, `gcal_int.py`, `gmail_int.py`, `discord_int.py`, etc. |
| `.claude/scripts/vault/` | Vault guardrails — `paths.py`, `transactions.py`, `actions.py` |
| `.claude/skills/` | Skills the agent invokes — `lecture-summarizer`, `note-search`, `vault-structure`, `concept-wiki`, `deadline-tracker` |
| `.claude/settings.json` | Wires hooks into Claude Code |
| `.claude/data/` | Runtime artefacts — OAuth tokens, SQLite memory DB, FastEmbed cache, logs (gitignored) |
| `tests/` | pytest suite |
| `Dynamous/Memory/` | Personal vault (local-only, gitignored) |

## Quick commands

```powershell
# Docker
docker compose up -d                     # start discord-bot + scheduler
docker compose logs -f discord-bot
docker compose logs -f scheduler

# Integration status
py .claude\scripts\query.py status

# Pull data
py .claude\scripts\query.py gcal upcoming --days 14
py .claude\scripts\query.py github pr-list <owner/repo>
py .claude\scripts\query.py vault inbox
py .claude\scripts\query.py gmail recent

# Memory / RAG
py .claude\scripts\memory\memory_index.py                       # rebuild index
py .claude\scripts\memory\memory_search.py "deadline" --top-k 5

# Run heartbeat manually
py .claude\scripts\heartbeat.py

# Tests
pytest
```

Most subcommands accept `--json` for machine-readable output.

See `CLAUDE.md` for full architecture notes, hook lifecycle, and integration details.
