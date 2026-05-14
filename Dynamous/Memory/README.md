# Daily Boot Checklist

Everything you need to do when you turn your laptop on.

---

## TL;DR

Most of the time: **nothing**. Scheduled tasks auto-start. Drop files in the inbox or DM the bot, get Discord notifications back. Done.

This file is for when something looks off, or you want to verify everything is running.

---

## 1. Verify the four scheduled tasks are running

Open PowerShell (regular, not admin), paste:

```powershell
Get-ScheduledTask -TaskName 'secondbrain-*' |
    Format-Table TaskName, State -AutoSize
```

Expected: all four `Ready` or `Running` (never `Disabled` or missing).

| Task                    | What it does                                                                      |
| ----------------------- | --------------------------------------------------------------------------------- |
| `secondbrain-heartbeat` | Every 30 min, 09:00–22:00 KL. Classifies new inbox files, DMs reminders.          |
| `secondbrain-index`     | Every 10 min. Re-embeds changed vault files for note search.                      |
| `secondbrain-reflect`   | Daily 08:00 KL. Promotes durable items from yesterday's daily log into MEMORY.md. |
| `secondbrain-discord`   | Starts at logon. Long-running Discord bot for DM file drops.                      |

If a task is missing or disabled, reinstall (elevated PowerShell):

```powershell
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\install_tasks.ps1
```

## 2. Check the Discord bot is online

Easiest way: open Discord, find the server where the bot lives, look at the member list. The bot should have a green status dot.

If it's offline:

```powershell
Start-ScheduledTask -TaskName 'secondbrain-discord'
```

Wait 10 seconds, refresh Discord. If still offline, tail the log:

```powershell
Get-Content .claude\data\logs\discord-*.log -Tail 30
```

---

## Daily workflow

### Drop a lecture or project file

Two ways, either works.

**Way 1 — DM the bot:** drag-drop a `.pdf` or `.pptx` into the DM with your bot. You get an immediate ack (`got 1 file(s) in inbox...`), and a summary DM 30-60 seconds later.

**Way 2 — File Explorer:** copy the file into `Dynamous\Memory\inbox\`. The next heartbeat tick (within 30 min) classifies and summarises it. To skip the wait:

```powershell
py .claude\scripts\heartbeat.py
```

Either way, the summary lands in Obsidian under:
- `lectures/<SUBJECT>/...` for teaching material
- `projects/<SUBJECT>/<Assignment_N>/...` for assignment / project documents

Deadlines mentioned in the document auto-populate `MEMORY.md` `## Deadlines` and you get a DM as the date approaches (48h = high, 24h = urgent).

### Search your notes

```powershell
py .claude\scripts\memory\memory_search.py "what you're looking for"
```

Or open Obsidian and use its built-in search (Ctrl+Shift+F).

### Read your daily log

Open Obsidian, navigate to `daily/YYYY-MM-DD.md`. The session-end hook auto-appends a block here when each Claude Code session ends. Tomorrow morning at 08:00, the reflection promotes durable items into MEMORY.md.

---

## Troubleshooting

### "I dropped a file but got no Discord DM"

1. Heartbeat may still be processing (30-60s for the LLM call).
2. Bot might not be running — see step 2 above.
3. File extension not supported — only `.pdf` and `.pptx` work today.
4. Tail the log: `Get-Content .claude\data\logs\discord-*.log -Tail 20`

### "I get 'discord DM failed' in heartbeat output"

The bot needs to share a server with you and your DM-from-server-members setting must be on. Right-click the server → Privacy Settings → "Direct Messages" ON.

### "Wrong subject code"

Check the doc actually mentions the right code. If multiple codes appear (e.g. DIP215 and DIP1006), the classifier prefers ones that already exist as folders. So make sure your first file for each subject filed correctly — that anchors future files.

### "File didn't auto-classify"

Sometimes a corrupt PDF or `.ppt` (not `.pptx`) bombs the extractor. Check terminal output of `py .claude\scripts\heartbeat.py` for an `extract failed` line.

---

## Where things live

```
.
├── Dynamous/Memory/          ← your vault (Obsidian opens this)
│   ├── SOUL.md USER.md MEMORY.md HABITS.md HEARTBEAT.md
│   ├── daily/                ← timestamped session logs
│   ├── lectures/<SUBJECT>/   ← classified lecture notes
│   ├── projects/<SUBJECT>/   ← classified project notes
│   ├── inbox/                ← drop zone
│   │   └── _processed/       ← archived sources after summarisation
│   └── drafts/{active,sent,expired}/
└── .claude/                  ← agent code (don't edit by hand)
    ├── scripts/heartbeat.py  ← the brain
    ├── scripts/deploy/       ← install/uninstall scheduled tasks
    └── data/logs/            ← Discord bot daily logs
```

## Hard limits (security)

The agent will never:
- Send Gmail / Outlook on your behalf
- Send Discord messages outside DMs to you
- Make purchases or touch financial data
- Delete anything under `Dynamous/Memory/`

All drafts land in `drafts/active/` for you to review before any send.
