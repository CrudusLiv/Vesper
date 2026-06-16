# Vesper — Personal Second Brain

> *Latin for evening — the hour when the world quiets down and the work starts.*

Vesper is a Claude Code-powered personal agent that runs as a Discord bot and a background scheduler. It keeps your vault of notes, deadlines, lectures, and finances organised — and surfaces what matters next without being asked.

---

## How it works at a glance

```text
You ──► Discord (#vesper, #inbox, #finance)
              │
              ▼
        discord_bot.py
              │
         ┌────┴────────────────────────────────────┐
         │                                         │
    Slash commands                        Drop a file in #inbox
    /schedule, /deadline                  (.pptx / .pdf)
    /habit, /search, /admin                        │
         │                                         ▼
         │                              lecture-summarizer skill
         │                              concept_linker.py
         │                              roadmap_generator.py
         │                                         │
         └────────────┬────────────────────────────┘
                      │
              Dynamous/Memory/ (local vault)
              SOUL.md · MEMORY.md · DEADLINES.md
              daily/ · lectures/ · concepts/
                      │
              heartbeat.py (every 30 min)
              ambient_notifier.py
              gcal_write.py / memory_index.py
```

---

## Features

### Discord interface

- **`#vesper`** — natural-language chat backed by your vault context
- **`#inbox`** — drop a `.pptx` or `.pdf`; get a full Obsidian note back
- **`#finance`** — expense tracking with simple commands
- **Slash commands** — `/schedule`, `/deadline`, `/habit`, `/search`, `/admin`

### Lecture enrichment

Drop any lecture slide deck or PDF into `Dynamous/Memory/inbox/`. The agent:

1. Extracts content slide-by-slide (with optional OCR for scanned PDFs)
2. Writes a structured Obsidian note under `lectures/<course>/`
3. Creates or updates concept stub files and wikilinks in `concepts/`
4. Generates a personalised study roadmap and posts it to Discord

### Deadline tracking

Project docs dropped into `inbox/` are auto-classified. Dated milestones are:

- Promoted into `DEADLINES.md`
- Mirrored to Google Calendar
- Tracked at 72h / 24h / overdue thresholds with Discord alerts

### Hybrid-RAG note search

Search your entire vault with one command. The index combines:

- **70% vector similarity** (FastEmbed / ONNX — fully local, no API calls)
- **30% BM25 keyword match** (SQLite FTS5)

### Heartbeat (ambient intelligence)

Every 30 minutes during active hours, the scheduler:

1. Builds a snapshot diff of your vault
2. Asks the LLM what to surface (dependency gaps, synthesis readiness, prerequisite alerts)
3. Posts only what's meaningful — no noise

### Daily reflection

At 08:00 KL time, durable items are automatically promoted from yesterday's `daily/` log into `MEMORY.md` and `HABITS.md` is rolled.

### Vault guardrails

- Path validator prevents writes outside safe directories
- Append-only JSONL transaction log for every vault mutation
- Typo-recovery layer on all write actions

---

## Requirements

| Dependency | Required | Notes |
| ---------- | -------- | ----- |
| **Python 3.14** | Yes | `py` launcher on PATH (Windows) |
| **Docker Desktop** | Yes | Runs bot + scheduler as containers |
| **Claude Code** | Yes | Agent layer — hooks and skills require it |
| **Discord bot token** | Yes | Create at [discord.com/developers](https://discord.com/developers/applications) |
| Google account | Optional | Calendar sync only |
| GitHub token | Optional | PR activity routing only |

---

## Quickstart

### 1. Clone and set up secrets

```powershell
git clone https://github.com/CrudusLiv/Vesper.git
cd Vesper
Copy-Item .env.example .env
```

Open `.env` and fill in at minimum:

```ini
DISCORD_TOKEN=your_bot_token_here
ANTHROPIC_API_KEY=your_claude_api_key_here
```

All other keys are optional — features silently skip when their env vars are missing.

### 2. Install Python dependencies

```powershell
py -m pip install -r .claude/requirements.txt
```

### 3. Start the bot

```powershell
docker compose up -d
```

Verify both services are running:

```powershell
docker compose ps
```

Expected output:

```text
NAME             STATUS    PORTS
discord-bot      Up
scheduler        Up
```

### 4. Invite the bot to your server

Use the OAuth2 URL from the Discord Developer Portal. The bot needs `bot` scope and the following permissions: `Send Messages`, `Read Message History`, `Attach Files`, `Use Slash Commands`.

---

## Full setup

### Vault structure

Create `Dynamous/Memory/` on your machine (gitignored — stays local). Minimum required files:

```text
Dynamous/Memory/
├── SOUL.md          ← agent personality (loaded every session)
├── USER.md          ← your profile (also loaded at session start)
├── MEMORY.md        ← durable promoted items (auto-managed)
├── DEADLINES.md     ← active deadlines (auto-managed)
├── HABITS.md        ← habit tracker (auto-rolled daily)
├── daily/           ← per-day session logs (YYYY-MM-DD.md)
├── lectures/        ← lecture notes output (by course)
├── concepts/        ← concept wiki stubs
└── inbox/           ← drop zone for .pptx / .pdf files
```

### Google Calendar (optional)

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com) and enable the Calendar API
2. Download `credentials.json` and place it at `.claude/data/google_credentials.json`
3. Run any GCal command — a browser OAuth flow runs once and caches the token

### GitHub (optional)

```ini
GITHUB_TOKEN=ghp_...
GITHUB_ASSIGNMENT_REPOS=owner/repo1,owner/repo2
```

### Heartbeat settings

Edit `.claude/data/tray_settings.json` to tune behaviour:

```json
{
  "active_hours_start": "09:00",
  "active_hours_end": "22:00",
  "heartbeat_interval_minutes": 30,
  "features": {
    "inbox_processing": true,
    "daily_reflection": true,
    "calendar_sync": true,
    "ambient_notifications": true
  }
}
```

Changes take effect on the next heartbeat tick — no restart needed.

---

## Project layout

```text
Vesper/
├── docker-compose.yml          ← service wiring (discord-bot, scheduler)
├── worker/                     ← shared Docker base image
├── .claude/
│   ├── chat/
│   │   └── discord_bot.py      ← Discord UI (commands, channels, webhooks)
│   ├── hooks/                  ← lifecycle hooks (SessionStart, PreCompact, SessionEnd, ...)
│   ├── scripts/
│   │   ├── query.py            ← unified CLI dispatcher
│   │   ├── heartbeat.py        ← ambient reasoning loop
│   │   ├── ambient_notifier.py ← decides what to surface to Discord
│   │   ├── concept_linker.py   ← auto-wikilinks between lectures + concepts
│   │   ├── roadmap_generator.py← post-lecture study roadmaps
│   │   ├── integrations/       ← gcal_int.py, github_int.py, gmail_int.py, discord_int.py
│   │   ├── memory/             ← RAG layer (chunker, embeddings, hybrid search, indexer)
│   │   └── vault/              ← guardrails (paths.py, transactions.py, actions.py)
│   ├── skills/
│   │   ├── lecture-summarizer/ ← .pptx / .pdf → Obsidian note
│   │   ├── note-search/        ← semantic + keyword vault search
│   │   └── vault-structure/    ← vault layout + write rules
│   ├── settings.json           ← wires hooks into Claude Code
│   └── data/                   ← runtime: tokens, SQLite DB, FastEmbed cache (gitignored)
├── tests/                      ← pytest suite
└── Dynamous/Memory/            ← personal vault (local-only, gitignored)
```

---

## Command reference

### Docker

```powershell
docker compose up -d                     # start both services
docker compose ps                        # check status
docker compose logs -f discord-bot       # tail bot logs
docker compose logs -f scheduler         # tail scheduler logs
docker compose restart discord-bot       # restart after config change
```

### Integration status and data pull

```powershell
py .claude\scripts\query.py status                          # check which integrations are live
py .claude\scripts\query.py gcal upcoming --days 14        # next 2 weeks of calendar events
py .claude\scripts\query.py github pr-list <owner/repo>    # open PRs
py .claude\scripts\query.py vault inbox                    # list unprocessed inbox files
py .claude\scripts\query.py gmail recent                   # recent emails
```

Add `--json` to any subcommand for machine-readable output.

### Memory and search

```powershell
py .claude\scripts\memory\memory_index.py                        # rebuild the search index
py .claude\scripts\memory\memory_search.py "linear algebra"      # search the vault
py .claude\scripts\memory\memory_search.py "deadline" --top-k 5  # limit results
```

### Manual triggers

```powershell
py .claude\scripts\heartbeat.py          # run one heartbeat tick now
pytest                                   # run the test suite
pytest tests/test_ocr.py -v             # run a specific test
```

---

## Environment variables

| Variable | Required | Purpose |
| -------- | -------- | ------- |
| `DISCORD_TOKEN` | Yes | Discord bot authentication |
| `ANTHROPIC_API_KEY` | Yes | Claude API access |
| `DISCORD_HOOK_VESPER` | Recommended | Webhook for `#vesper` heartbeat posts |
| `DISCORD_HOOK_INBOX` | Recommended | Webhook for inbox processing results |
| `DISCORD_HOOK_FINANCE` | Recommended | Webhook for finance channel |
| `GOOGLE_CLIENT_ID` | Optional | Calendar / Gmail OAuth |
| `GOOGLE_CLIENT_SECRET` | Optional | Calendar / Gmail OAuth |
| `GITHUB_TOKEN` | Optional | PR activity routing |
| `GITHUB_ASSIGNMENT_REPOS` | Optional | Comma-separated list of repos to watch |

---

## Architecture notes

- **Advisor mode** — the agent drafts replies and writes to the vault, but never sends messages to third parties or commits without your review
- **Local embeddings** — FastEmbed (ONNX) runs entirely on-device; no embeddings are sent to an API
- **Vault is local** — `Dynamous/Memory/` is gitignored; each machine keeps its own vault
- **Hooks drive the agent layer** — `SessionStart` injects `SOUL.md` + recent daily logs; `PreCompact` flushes context to today's log before auto-compaction

See [CLAUDE.md](CLAUDE.md) for full architecture details, hook lifecycle, and integration docs.
