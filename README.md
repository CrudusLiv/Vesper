# BoredBot

My second brain, built on Claude Code. Hooks, scripts, skills, and settings that turn Claude Code into a study partner: deadline tracking, lecture summarisation, note search, code review.

The personal vault (notes, schedules, finances) lives locally at `Dynamous/Memory/` and is **not** committed — that directory is gitignored. Each machine keeps its own vault.

## Setup

Requires Python 3.14 (`py` launcher on Windows), Claude Code installed, and a Google account if you want Gmail/Calendar integration.

```powershell
# 1. Clone this repo
git clone https://github.com/CrudusLiv/BoredBot.git
cd BoredBot

# 2. Install Python deps
py -m pip install -r .claude/requirements.txt

# 3. Set up secrets
Copy-Item .env.example .env
# Edit .env and fill in the values you'll actually use.

# 4. (Optional) Google credentials
# Place google_credentials.json at .claude/data/google_credentials.json
# (.claude/data/ is gitignored.)

# 5. Create your vault
# The agent expects a vault tree at Dynamous/Memory/ with at minimum SOUL.md
# and USER.md (see CLAUDE.md for the full layout). The directory is gitignored
# — copy your own vault into place, or start fresh.

# 6. Open the directory in Claude Code. Hooks fire automatically.
```

## Layout

| Path | Purpose |
|------|---------|
| `.claude/hooks/` | SessionStart, PreCompact, SessionEnd, PreToolUse, UserPromptSubmit hooks |
| `.claude/scripts/` | Unified `query.py` CLI, integrations, heartbeat, memory (RAG), security |
| `.claude/skills/` | Skills the agent invokes (code-reviewer, deadline-tracker, lecture-summarizer, note-search, vault-structure) |
| `.claude/settings.json` | Wires hooks into Claude Code |
| `tests/` | pytest suite |
| `Dynamous/Memory/` | Personal vault (local-only, gitignored) |

## Quick commands

```powershell
py .claude\scripts\query.py status              # which integrations are ready
py .claude\scripts\query.py gmail unread        # recent unread mail
py .claude\scripts\query.py gcal upcoming --days 14
py .claude\scripts\memory\memory_index.py       # rebuild vault search index
py .claude\scripts\memory\memory_search.py "deadline" --top-k 5
pytest                                          # run the test suite
```

See `CLAUDE.md` for the full architecture notes.
