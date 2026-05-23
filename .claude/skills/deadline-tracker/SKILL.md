---
name: deadline-tracker
description: Pull assignment and class deadlines from Gmail and Google Calendar, deduplicate, and refresh the ## Active section in DEADLINES.md. Heartbeat re-runs this every tick.
---

# Deadline Tracker

Keep `DEADLINES.md` `## Active` accurate and current. The heartbeat re-runs this skill on every tick to escalate items due in <72h.

## Procedure

1. **Pull Gmail (last 7 days):**
   ```
   py .claude/scripts/query.py gmail recent --days 7 --max 30 --json
   ```
   Filter the result for messages whose subject or body mentions any of:
   - `due`, `deadline`, `submit`, `submission`
   - `assignment`, `quiz`, `exam`, `project`, `tutorial`
   - the university domain in `USER.md` (once filled in)
   - any course code from `USER.md`

2. **Pull Google Calendar (next 14 days):**
   ```
   py .claude/scripts/query.py gcal upcoming --days 14 --json
   ```
   Filter for events whose summary contains the same keywords or a course code.

3. **Extract structured items** — for each candidate, build:
   ```json
   {
     "due_date": "2026-06-12",
     "course": "CS101",
     "title": "Assignment 1: Pointers",
     "source": "gmail:abc123" or "gcal:eventid",
     "notes": "submission via Moodle, 15% of grade"
   }
   ```
   `course` is `?` if you can't infer it. `notes` is optional — only include something useful.

4. **Deduplicate.** A Gmail announcement and a Calendar event for the same item should merge. Dedup key: `(course, lowercased-title-keywords, due_date)`. When merging, prefer the entry with more `notes`. List both source IDs comma-separated.

5. **Read existing deadlines** from `DEADLINES.md` `## Active`. Preserve every existing line — manual entries (added by CrudusLiv) and prior auto-extracted entries both live here and must never be overwritten.

6. **Re-render the section.** Sort by `due_date` ascending. Format:
   ```markdown
   ## Active

   - 2026-06-12 — CS101 — Assignment 1: Pointers
   - 2026-06-15 — manual — Pay tuition deposit
   - 2026-06-18 — CS102 — Quiz 1
   ```
   The line format is `- <YYYY-MM-DD> — <course> — <title>` — one row per deadline, matching what the heartbeat writer (`heartbeat/deadlines.py`) and the imminent scanner (`heartbeat/imminent.py`) expect. To opt a row out of Google Calendar push, prefix the date with `nogcal:` (e.g. `- nogcal: 2026-06-15 — manual — Pay tuition deposit`).

7. **Edit `DEADLINES.md`** with the Edit tool, replacing **only** the `## Active` section. Leave the `## Format` heading and surrounding prose untouched.

8. **Note the action** in today's `daily/YYYY-MM-DD.md`:
   `[HH:MM] Refreshed DEADLINES.md ## Active: <N> items, <M> new since last run.`

## Heartbeat behaviour (Phase 6)

When invoked from the heartbeat:
- Items due within **72h** → notification on every tick.
- Items due within **24h** → notification + Windows Toast.
- Items beyond 14 days → ignore until they enter the window.

## Quality bar

- **Only deadlines explicitly stated.** Don't infer "assignment due next Friday" from "we'll have an assignment soon". False positives erode trust faster than false negatives.
- **Don't draft replies here** — that's the heartbeat's job (Phase 6). This skill only updates the deadline list.
- **Don't delete existing entries.** Treat anything already in `## Active` as load-bearing; only append.

## Edge cases

- No Gmail/Calendar configured (status `[--]`) — exit early with a one-liner: "Gmail or Calendar not configured. Add `.claude/data/google_credentials.json` to enable."
- Same deadline appears in Gmail AND Calendar — merge into one entry, list both source IDs.
- Conflicting due dates between sources — pick the Calendar date (more authoritative for events) and add `notes: "Gmail mentioned earlier date <X>"`.

## Don't

- Don't list deadlines that have already passed.
- Don't add deadlines that don't have a clear due date — vague "before end of term" entries belong in `projects/`, not `DEADLINES.md`.
- Don't run if Gmail is not configured — silently empty results would erase the existing deadline list.
