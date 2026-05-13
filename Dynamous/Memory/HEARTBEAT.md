# HEARTBEAT

> Checklist of signals the heartbeat scans every tick. Edit this file to change priorities — `heartbeat.py` reads it on every run.

## Every tick (every 30 min, 09:00–22:00 UTC+8)

- [ ] **Gmail unread (last 7 days)** — extract any new deadlines, draft replies for personal / university messages
- [ ] **Discord DMs (since last tick)** — draft replies for new DMs (never send)
- [ ] **GitHub pushes (assignment repos, since last tick)** — generate code-review draft per new commit / PR
- [ ] **Google Calendar (next 14 days)** — pull events tagged `assignment`, `due`, `quiz`, `exam` into deadlines view
- [ ] **Inbox folder** (`Dynamous/Memory/inbox/`) — trigger lecture-summarizer skill on any new `.pptx` / `.pdf`
- [ ] **Discord pings (since last tick)** — Windows toast for new server `@CrudusLiv` mentions and DMs from others
- [ ] **Self-DM capture** — classify DMs CrudusLiv sent to the capture bot; route to `daily/`, `finance/`, or discard
- [ ] **DEADLINES.md → GCal** — push new rows to Google Calendar (skip duplicates)

## Daily (08:00 UTC+8)

- [ ] **Memory reflection** — promote durable items from yesterday's `daily/` log into `MEMORY.md` (Decisions / Lessons sections)
- [ ] **MEMORY.md trim** — if `MEMORY.md` exceeds ~5000 tokens, summarize the oldest Lessons section

## Priority bumps

- Anything in `MEMORY.md` `## Deadlines` due within **48h** → notification on every tick
- Anything due within **24h** → notification + Windows Toast on every tick
- New email from a domain matching the university domain in `USER.md` → draft + notification immediately
