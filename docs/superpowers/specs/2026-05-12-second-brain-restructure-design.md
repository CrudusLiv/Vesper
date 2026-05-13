# Second Brain Restructure — Design

**Date:** 2026-05-12
**Owner:** CrudusLiv
**Status:** Approved, pending implementation plan

## Summary

A coordinated set of changes to the vault and integration layer:

1. Remove the unused drafts system; keep advisor mode (no auto-sending).
2. Split `MEMORY.md` into `MEMORY.md` + `DEADLINES.md` + `PROJECTS.md`.
3. Remove `goals/` folder; keep `HABITS.md` as a stub until uni starts (June 2026).
4. Discord ping detection fires Windows toast notifications.
5. Discord self-DMs get classified (note / finance / chit-chat) and routed to the right vault location.
6. Delete `inbox/_processed/` source files after a successful lecture summary write.
7. Add automatic `[[wikilinks]]` between sibling notes under `projects/` and `lectures/`.
8. Add Google Calendar write support — push new deadlines and flagged important dates to GCal, skipping any event that already exists.

Implementation order: **vault restructure first**, then new features built on the cleaned-up structure.

---

## Section 1 — Vault Restructure

### Changes

- Delete `Dynamous/Memory/drafts/` and its `active/`, `expired/`, `sent/` subfolders.
- Delete `Dynamous/Memory/goals/` (includes `habits-history/`).
- Create `Dynamous/Memory/DEADLINES.md` — extracted from `MEMORY.md`. Section-loaded in every session.
- Create `Dynamous/Memory/PROJECTS.md` — extracted from `MEMORY.md`. Section-loaded in every session.
- `MEMORY.md` keeps only Decisions and Lessons.
- `HABITS.md` keeps its current structure but with a banner: "Stub — to be reconfigured when uni schedule is set (June 2026)". The four placeholder pillars remain so the file isn't blank.

### File edits

- `SOUL.md` — remove "Draft, don't send" wording that references `drafts/active/`. Replace with "Advise, don't send. Never auto-send Gmail/Outlook/Discord/GitHub. Surface drafts in conversation only." Hard limits unchanged.
- `HEARTBEAT.md` — remove the "Drafts cleanup" line. Remove the daily "Habits reset" line (paused until uni starts). All other tasks unchanged.
- `.claude/hooks/session-start-context.py` — extend the `additionalContext` injection to also load `DEADLINES.md` and `PROJECTS.md` alongside `SOUL.md` and recent daily logs.
- `CLAUDE.md` — update the Vault write rules section: remove the drafts line, note the carve-out for `inbox/_processed/` deletion (added in Section 4).
- `.claude/skills/vault-structure/SKILL.md` — drop the drafts section, add `DEADLINES.md` and `PROJECTS.md` to the top-level files list.

### Migration

- One-off: read existing `MEMORY.md`, split sections into the new files.
- One-off: delete `drafts/` and `goals/` folders.

---

## Section 2 — Discord Ping Reminder (Windows Toast)

### Changes

- New heartbeat task in `.claude/scripts/heartbeat.py` (or whichever module orchestrates the tick): scan Discord for messages mentioning CrudusLiv since the last tick.
- For each new ping, fire a Windows toast.

### Detection

- A "ping" is:
  - A message in any server channel CrudusLiv reads where the content contains `<@user_id>` for CrudusLiv's user ID, OR
  - A DM from any user other than CrudusLiv.
- Self-DMs are routed to Section 3, not toasted.

### Toast format

- Library: `winotify` (preferred over `win10toast` — better Win11 support, less brittle).
- Title: `Discord ping from <sender display name>`
- Body: `<channel name or "DM">: <first 120 chars of message>`
- No action buttons.

### State

- Last-tick timestamp stored in `.claude/data/discord_last_tick.json` (gitignored).
- Format: `{"last_tick": "2026-05-12T14:30:00+08:00", "seen_message_ids": ["...", "..."]}`. Seen IDs prevent double-toast on overlap; kept for the last 24h then trimmed.

### Cadence

- Runs every heartbeat tick (existing 30-min cadence, 09:00–22:00 KL). No new scheduling.

---

## Section 3 — Discord Self-DM Classifier

### Changes

- New heartbeat task: scan DMs CrudusLiv sent to a dedicated capture bot, then classify and route.
- **Mechanism note:** Discord's built-in "Note to self" feature is private to the user — bots can't read it. The implementation uses a dedicated bot account that CrudusLiv DMs deliberately (acts as the capture channel). The existing Discord integration already has the bot token; reusing the same bot is fine as long as CrudusLiv opens a DM with it.
- Each new DM from CrudusLiv to the bot is classified into one of three labels, then routed accordingly.

### Labels and routing

| Label | Definition | Destination |
|-------|------------|-------------|
| `note` | Idea, reminder, study thought, code snippet, anything substantive | Append to today's `daily/YYYY-MM-DD.md` under a `## Captured` heading with a `HH:MM` timestamp |
| `finance` | Mentions money — currency symbols (RM, $, USD), keywords ("spent", "paid", "earned", "income", "expense") | Append to `finance/YYYY-MM.md` (existing monthly file) under a `## Captured` heading |
| `chit-chat` | Short, reactive, non-substantive ("lol", "ok", "test", greetings) | Discarded, not logged |

### Classifier

- **First pass — rule-based:**
  - If message matches `\b(rm|usd|\$|myr)\s*\d+` or contains `spent|paid|earned|expense|income|cost` → `finance`.
  - If message length < 10 chars OR matches a small chit-chat allowlist (`lol`, `ok`, `nice`, `hi`, `hey`, `test`, etc.) → `chit-chat`.
  - Otherwise → `note`.
- **Fallback — LLM:** if the rule-based pass is ambiguous (e.g., short message containing money keywords), one zero-shot classification call to Claude Haiku with a small system prompt. Cheap. Used sparingly.

### State

- Reuses the same `.claude/data/discord_last_tick.json` from Section 2 (`seen_message_ids` covers both pings and self-DMs).

---

## Section 4 — Delete `_processed/` After Processing

### Changes

- After the lecture-summarizer writes a markdown note, the source file in `inbox/_processed/` is deleted.

### Success check

A "successful write" requires all of:
- Output `.md` file exists at the target path.
- File has YAML frontmatter (parses successfully).
- File has at least one non-empty content section after the frontmatter.

If any check fails, the source file is kept and a warning is logged. Reprocessing is possible.

### Policy carve-out

- `SOUL.md` and `CLAUDE.md` "Never delete" rule gets one explicit exception: deletion is permitted **only** for files inside `inbox/_processed/`. Everything else under `Dynamous/Memory/` stays protected.
- The folder itself stays with a `.gitkeep`.

### One-off cleanup

- A small migration script walks existing `inbox/_processed/` files, checks for corresponding `.md` notes in `lectures/<course>/` or `projects/<...>/`, and deletes the source file if a valid note is found.

---

## Section 5 — Project / Lecture Sibling Wikilinks

### Changes

- New helper `.claude/scripts/memory/wikilinks.py` with one public function:

  ```python
  def add_sibling_wikilinks(file_path: Path) -> None:
      """Append a `## Related` section linking to siblings in the same folder."""
  ```

### Behavior

- "Siblings" = all other `.md` files in the same parent folder AND any subfolders one level deep (e.g., `projects/DIP209/Assessment_2/note.md` sees siblings in `projects/DIP209/Assessment_2/` and `projects/DIP209/Assessment_3/`).
- Appends `## Related` at the end of the target file. Each sibling appears as `- [[sibling-filename-without-ext]]`.
- Idempotent: if `## Related` already exists, missing wikilinks are added; existing ones are left alone. Self-links are skipped.

### Integration points

- **Write-time:** after the lecture-summarizer writes a new `projects/` or `lectures/` note, call `add_sibling_wikilinks(new_file)` and then call it again on each sibling so links are bidirectional.
- **Batch backfill:** `.claude/scripts/wikilink_backfill.py` walks `projects/` and `lectures/`, calls the helper on every file. Idempotent — re-runs safely.

### Scope

- Only `projects/` and `lectures/` get auto-wikilinks. `research/`, `daily/`, and root files (`MEMORY.md`, `SOUL.md`, etc.) are not touched — manual linking only.

---

## Section 6 — Google Calendar Write

### Changes

- Re-authorize `google_credentials.json` with the `https://www.googleapis.com/auth/calendar.events` scope.
- New module `.claude/scripts/integrations/gcal_write.py` exposing:

  ```python
  def create_event(title: str, date: str, description: str = "", calendar_id: str = "primary") -> str | None:
      """Create an all-day GCal event. Returns event ID, or None if a duplicate already exists."""
  ```

### Dedup

- Before creating, query GCal for events on the same date with the same exact title (case-insensitive match).
- If found, skip and return `None`. This protects existing test events.

### Triggers

- **DEADLINES.md sync:** heartbeat reads `DEADLINES.md`, diffs against `.claude/data/gcal_synced.json`, pushes new rows.
- **Daily/MEMORY tags:** any line in `daily/YYYY-MM-DD.md` or `MEMORY.md` matching the pattern `gcal: <date> | <title>` is pushed. Once pushed, the line is replaced with `gcal: <date> | <title> [synced:<event_id>]`.

### State

- `.claude/data/gcal_synced.json` keeps `{ "<title>::<date>": "<event_id>" }` to avoid re-querying GCal on every tick.

### Non-goals

- No event deletion, no event modification. If a deadline changes, the user updates GCal manually. Keeps the integration safe and side-effect-light.

### Re-auth flow

- First run after the new scope is added: existing token at `.claude/data/google_token.json` is deleted automatically. The next call to any Google integration triggers a browser OAuth flow with both calendar read and write scopes. Gmail token shares the same file — re-auth covers both.

---

## Out of Scope

- HABITS.md reconfiguration — deferred until June 2026 when the uni schedule lands.
- Auto-sending any message (Discord, Gmail, GitHub). Advisor mode remains the hard rule.
- Auto-deleting any file outside `inbox/_processed/`.
- GCal event editing/deletion.
- Cross-folder wikilinks (e.g., linking a `projects/` file to a `lectures/` file). Manual.

---

## Implementation Order

1. **Vault restructure** (Section 1) — pure file/config changes. No new code paths.
2. **Processed-file deletion** (Section 4) — small, isolated change to lecture-summarizer.
3. **Sibling wikilinks** (Section 5) — touches the same lecture-summarizer; logical pair with #2.
4. **Discord toast + self-DM classifier** (Sections 2 + 3) — both extend the heartbeat with new Discord scans; share the state file.
5. **GCal write** (Section 6) — last, because it depends on `DEADLINES.md` existing (Section 1).
