# Discord-as-Dashboard — spec & resume notes

Single source of truth for the Discord dashboard layer. Architecture plan lives at `C:\Users\livne\.claude\plans\plan-a-discord-as-dashboard-layer-gentle-kahn.md`; this file tracks **what's built, what's next, and how to resume.**

---

## Premise

The vault (`Dynamous/Memory/*.md` + `.claude/data/memory.db`) stays the source of truth. Discord is a topical I/O layer: per-channel webhooks fan heartbeat events into the right room. The read-only bot stays read-only; outbound on servers is webhook-only.

Open Discord → see what's going on, organized by concern.

---

## Architecture decisions (locked)

1. **Pragmatic sender split.** `notify.py` keeps DMing CrudusLiv via the bot for pings + urgent alerts (existing DM carve-out). All dashboard channels use webhooks. Bot never posts in server channels.
2. **Forum channels** for `#deadlines` and `#lectures` — one thread per assignment / per lecture. Other channels are plain text.
3. **In-thread chat carve-out** (Slice 7): bot reads replies inside agent-owned forum threads; agent reply posts back via the same thread's webhook.
4. **`#vesper` chatbot channel** (Slice 8): same mechanic at top-level channel scope.
5. **No auto-pin.** Webhooks can't pin. "Next 3 deadlines" is a webhook-edited message at a known ID; user pins it once by hand.
6. **DM scope is outbound-pings-only** (2026-05-24 pivot). The bot does not act on DMs it receives from the owner — those are cache-only. Owner-side input lives in `#inbox`, `#finance`, `#vesper`. Outbound DMs from the bot are limited to `discord_ping.py`'s server-mention forward via `notify.send`. All other prior `notify.send` callers reroute to `dashboard.notify(<kind>, ...)`.
7. **Slice 6 collapsed to one channel** (2026-05-25 pivot). The original plan carved `#morning` / `#evening` / `#digest` by event kind; one user doesn't need three rooms for daily updates. `morning_digest`, `evening_nudge`, and `daily_digest` all route to `DISCORD_HOOK_DAILY`; emoji prefix in the embed (🌅 / 🌙 / 📝) plus color differentiates kind at a glance.

---

## Slice status

| # | Slice                            | Status   | Channel(s)               |
|---|----------------------------------|----------|--------------------------|
| 1 | `#heartbeat` + `#errors`         | **done** | `#heartbeat`, `#errors`  |
| 2 | Input pivot: bot reads `#inbox` + `#finance` + `#vesper` | **done** | `#inbox`, `#finance`, `#vesper` |
| 3 | `#deadlines` (forum + thresholds)| **done** | `#deadlines`             |
| 4 | `#lectures` (forum + TL;DR)      | **done** | `#lectures`              |
| 5 | `#pr-activity` (`#code-review` deferred) | **done** | `#pr-activity`           |
| 6 | `#daily` (unified feed)          | **done** | `#daily`                 |
| 7 | In-thread chat carve-out         | **done** | (no new channel)         |
| 8 | `#vesper` chatbot channel        | **folded into Slice 2** | `#vesper` |

---

## File map

### New files (Slice 1)

- `.claude/scripts/integrations/discord_webhook.py` — low-level webhook client (`post`, `edit`, `delete`). urllib only.
- `.claude/scripts/heartbeat/dashboard.py` — kind→webhook routing. `ROUTES`, `format_embed`, `notify`.
- `.claude/scripts/heartbeat/dashboard_state.py` — idempotency sidecar. `load()` / `save()`.

### Modified (Slice 1)

- `.claude/scripts/heartbeat.py` — added `_compute_tick_status`, `_maybe_post_heartbeat_tick`, `_main_impl` rename, `main()` wrapper with try/except → `dashboard.notify("error", ...)`.
- `.env.example` — added the full `DISCORD_HOOK_*` block.

### Modified (Slice 3)

- `.claude/scripts/heartbeat/imminent.py` — 5-bucket `scan()` (`overdue`/`urgent`/`soon`/`approaching`/`later`), sha1 deadline `key`, `actionable()`/`all_upcoming()` helpers. `format_body` removed (no callers).
- `.claude/scripts/heartbeat/dashboard.py` — formatters for `deadline_72h`/`deadline_24h`/`deadline_overdue` (color-coded embeds) and `next3` (plain-text rollup). New `edit_message()` helper for in-place PATCH.
- `.claude/scripts/heartbeat/dashboard_state.py` — added `next3 = {thread_id, message_id}` namespace; legacy `next3_message_id` key ignored.
- `.claude/scripts/heartbeat.py` — new `_route_deadlines()` replaces the old `urgent, soon = imminent.scan()` block. Wraps in try/except so a routing failure can't break the tick.
- `.env.example` — `DISCORD_HOOK_DEADLINES` already declared in Slice 1's block.

### Modified (Slice 4)

- `.claude/scripts/heartbeat/inbox.py` — `_extract_tldr(note_md, n=3)` pulls first n bullets under `## Key concepts`. `_process_one` returns `tldr: list[str]` on lecture results (empty list for projects).
- `.claude/scripts/heartbeat/dashboard.py` — `_format_lecture_new(p)` builds a blue 📚 embed with course tag, lecture title, 3-bullet TL;DR, source filename in footer, vault path in description.
- `.claude/scripts/heartbeat.py` — new `_route_lecture(summary, rel_path)`. Lectures from `inbox.process_new_files()` route to `dashboard.notify("lecture_new", ..., thread_name=f"{course} — {title}")` instead of `daily_digest`. Projects still go to `daily_digest`. Dedupe by `rel_path` against `dashboard_state["lectures"]`.

### Modified (Slice 6)

- `.claude/scripts/heartbeat/dashboard.py` — `_DAILY_STYLES` table + `_format_daily(kind, p)` formatter. `ROUTES` repointed `morning_digest` / `evening_nudge` / `daily_digest` all at `DISCORD_HOOK_DAILY`.
- `.env.example` — replaced `DISCORD_HOOK_MORNING` / `_EVENING` / `_DIGEST` with single `DISCORD_HOOK_DAILY`.
- No call-site changes in `heartbeat.py` — the three kinds were already being emitted, they just had no real formatter.

### New (Slice 7)

- `.claude/scripts/heartbeat/thread_chat.py` — `scan_and_reply(db_path, user_id, state_path)` watcher. Reads `dashboard_state.deadlines` + `dashboard_state.lectures` for known thread ids, queries `discord_cache.db` for owner messages inside them, calls `llm.call` with the kind-specific prompt, posts the reply via `dashboard.notify("deadline_reply" | "lecture_reply", ..., thread_id=...)`.
- `.claude/scripts/heartbeat/thread_chat_prompt.py` — `system_prompt(thread_meta)` + `user_prompt(msg, context)`. Base behavior + deadline/lecture rider + SOUL.md persona.

### Modified (Slice 7)

- `.claude/scripts/heartbeat/dashboard.py` — `_format_thread_reply` (plain text, 2000-char cap). `ROUTES`: `deadline_reply` → `DISCORD_HOOK_DEADLINES`, `lecture_reply` → `DISCORD_HOOK_LECTURES`.
- `.claude/scripts/heartbeat.py` — imports `thread_chat`, calls `thread_chat.scan_and_reply` after `discord_dm_capture.scan_and_route`, sharing the same `state_path`.
- `Dynamous/Memory/USER.md` — platform table + hard-limits line updated to list the three Discord outbound carve-outs (DM pings, webhook posts, in-thread replies).

### Modified (Slice 5)

- `.claude/scripts/integrations/github_int.py` — `_all_user_repos(g, limit=30)` enumerates every repo the token can see, sorted by recent push. `recent_pr_events(repos=None, since=None)` emits `pr_opened` / `pr_merged` / `pr_comment` events with stable dedupe ids (`open:{repo}:{n}` / `merge:{repo}:{n}` / `comment:{id}`). Slice 5 intentionally ignores `GITHUB_ASSIGNMENT_REPOS` — that env var stays scoped to the code-reviewer skill.
- `.claude/scripts/heartbeat/dashboard.py` — `_PR_STYLES` + `_format_pr_event(kind, p)`. Embeds: 🟢 green for opened, 🟣 purple for merged, 💬 slate for comments. Title carries repo + PR ref; description carries title, actor, URL.
- `.claude/scripts/heartbeat.py` — `_route_pr_events()` pulls events with a 24h window each tick, dedupes via `dashboard_state["pr_activity"]["seen_event_ids"]` (capped at last 500 ids), routes through `dashboard.notify(ev["kind"], ev)`. Wired into `_main_impl` right after `_route_deadlines`.

### Untouched, planned for later slices

- `#code-review` channel + draft-generation pipeline (deferred to its own plan; not part of Slice 5).

---

## State file

**Path:** `.claude/data/discord_dashboard_state.json` (gitignored).

```jsonc
{
  "heartbeat": {
    "last_status": "green" | "red" | null,
    "last_tick_ts": <epoch>,
    "ticks_since_post": <int>
  },
  "deadlines": {
    "<key>": { "fired": ["72h","24h","overdue"], "thread_id": "...", "starter_message_id": "...", "last_message_id": "..." }
  },
  "lectures": {
    "<note-path>": { "thread_id": "...", "starter_message_id": "..." }
  },
  "pr_activity": {
    "<owner/repo#PR>": { "last_event_id": "..." }
  },
  "next3": { "thread_id": "...", "message_id": "..." }
}
```

Each slice owns its namespace. Old state files are forward-compatible — missing keys are seeded from `DEFAULT_STATE` in `dashboard_state.py`.

---

## Environment variables

All in `.env`. Empty values silently skip (`dashboard.notify` returns `None`).

```
DISCORD_HOOK_HEARTBEAT       # Slice 1
DISCORD_HOOK_ERRORS          # Slice 1
DISCORD_HOOK_INBOX           # Slice 2
DISCORD_HOOK_DEADLINES       # Slice 3 (forum)
DISCORD_HOOK_LECTURES        # Slice 4 (forum)
DISCORD_HOOK_PR_ACTIVITY     # Slice 5
DISCORD_HOOK_CODE_REVIEW     # Slice 5
DISCORD_HOOK_DAILY           # Slice 6 (morning_digest + evening_nudge + daily_digest)
DISCORD_HOOK_VESPER          # Slice 8
DISCORD_HOOK_IDEAS           # later
DISCORD_HOOK_EMAIL_UNI       # later (Outlook lands June 2026)
DISCORD_HOOK_EMAIL_PERSONAL  # later (Gmail opted out 2026-05-11)
```

`.env.example` carries the full block as a checklist.

---

## Slice 1 — `#heartbeat` + `#errors` (done)

Behavior:

- After every snapshot, compute `green` / `red` from per-integration `error` keys in the snapshot dict.
- Post to `#heartbeat` when (a) status changed since `last_status`, (b) `ticks_since_post >= 8` (~4h at 30min cadence), or (c) first tick of the KL-local day. Otherwise increment `ticks_since_post` silently.
- State only advances when `dashboard.notify` returns a non-`None` response (so a transient failure can retry).
- `main()` wraps `_main_impl()` in try/except → `dashboard.notify("error", {script, trace, tick_ts})` → re-raises.

Manual checks:

```powershell
# Sanity ping (bypasses state):
py -c "import sys; sys.path.insert(0, '.claude/scripts'); from heartbeat import dashboard; dashboard.notify('heartbeat_tick', {'status':'green','failing':[],'tick_ts':0})"

# Force fresh post (resets throttle):
del .claude\data\discord_dashboard_state.json
py .claude\scripts\heartbeat.py

# Force an error (note: heartbeat.py vs heartbeat/ package naming collision —
# you must import the submodule first, then runpy the script):
py -c "import sys; sys.path.insert(0, '.claude/scripts'); from heartbeat import snapshot; snapshot.build_snapshot = lambda: 1/0; import runpy; runpy.run_path('.claude/scripts/heartbeat.py', run_name='__main__')"
```

---

## Slice 2 — Input pivot: bot reads `#inbox` + `#finance` + `#vesper` (done)

Behavior:

- Owner posts in any of three configured channels (env: `DISCORD_INBOX_CHANNEL_ID`, `DISCORD_FINANCE_CHANNEL_ID`, `DISCORD_VESPER_CHANNEL_ID`) → `discord_bot.on_message` routes by channel id.
- `#inbox`: `note: ...` text → appended to `notes/NOTES.md` + ✅ react. `.pdf` / `.pptx` attachment → saved to `Dynamous/Memory/inbox/` + ✅ react + heartbeat spawned. Unrecognised content → ❓ react.
- `#finance`: matches `tracker.parse` → log + reply with running totals. `totals` / `finance` / `spend` keyword → reply with month summary. Other → ❓ react.
- `#vesper`: anything → `handler.process_message` → reply via `channel.send`, split at 2000 chars.
- Owner DMs to the bot → cached (Phase 4.1 behavior) but NO action taken.
- The `#inbox` webhook (`DISCORD_HOOK_INBOX`) and `inbox_text` / `inbox_attachment` formatters from the original Slice 2 plan are now dead-code paths — kept declared for future system-side posts but no live callers.

Spec: `docs/superpowers/specs/2026-05-24-discord-input-pivot-design.md`
Plan: `docs/superpowers/plans/2026-05-24-discord-input-pivot.md`

Manual probes (run after restart):
- `#inbox`: post `note: probe` → ✅ + bullet in `notes/NOTES.md`. Upload `test.pdf` → ✅ + file in `inbox/`.
- `#finance`: post `5.50 coffee` → reply with totals.
- `#vesper`: post `hi` → LLM reply.
- DM: post `note: ignored` → cached but no react, no NOTES.md write.

---

## Slice 3 — `#deadlines` (done)

Behavior:

- `imminent.scan()` returns 5 buckets — `overdue` (`days<0`), `urgent` (`0..1`), `soon` (`2`), `approaching` (`3`), `later` (`>=4`). Each item carries a stable `key = sha1(due|course|title)[:12]`.
- `heartbeat._route_deadlines()` walks the actionable buckets (overdue → urgent → soon → approaching). First sighting of a key creates a forum thread via `thread_name=f"{course} — {title}"` (truncated to 100 chars). Forum-channel `wait=true` response: `channel_id` = thread id, `id` = starter message id.
- Follow-up threshold crossings post into the same thread via `?thread_id=`. `fired` list tracks which embeds have gone out (`72h` / `24h` / `overdue`); only un-fired thresholds trigger a new post.
- "Next 3 deadlines" lives in its own forum thread (`#deadlines` is a forum channel so there's no plain channel to post to). The starter message is PATCH-edited each tick via `dashboard.edit_message`. CrudusLiv pins it once by hand.
- **Key includes the date.** Editing the date in `DEADLINES.md` orphans the old thread and spawns a new one — by design, treats date edits as new deadlines. If this proves noisy, the key can later be narrowed to `course|title`.

Validation done (2026-05-25): synthetic row at 2026-05-27, then monkey-patched `imminent.scan` to simulate the row aging into urgent + overdue. Verified the same `thread_id` received all three embeds, `fired` accumulated correctly, `last_message_id` advanced. Next 3 was PATCHed in place across runs.

Manual probes:

```powershell
# Add a fake row that won't push to GCal:
#   echo "- nogcal: 2026-05-28 — TEST — probe" >> Dynamous/Memory/DEADLINES.md
py -c "import sys; sys.path.insert(0, '.claude/scripts'); sys.path.insert(0, '.claude/scripts/integrations'); import _env, runpy; m = runpy.run_path('.claude/scripts/heartbeat.py'); m['_route_deadlines']()"

# Inspect the deadlines namespace:
py -c "import json; print(json.dumps(json.load(open('.claude/data/discord_dashboard_state.json'))['deadlines'], indent=2))"
```

---

## Slice 4 — `#lectures` (done)

Behavior:

- When `inbox.process_new_files()` returns a lecture result, `_route_lecture(summary, rel_path)` posts a new forum thread with the 3-bullet TL;DR embed. Source PPTX/PDF has already been moved to `inbox/_processed/` by the time the result lands, so re-running the tick can't re-fire — but a manual re-call with the same `rel_path` short-circuits via the `lectures` state lookup.
- Projects (`type == "project"`) keep routing to `daily_digest` — `#projects` is out of scope until a dedicated slice.
- TL;DR is the first 3 bullets under `## Key concepts` in the generated note (`_extract_tldr`). If the section is missing the embed shows _(no Key concepts section)_ instead of failing.
- Embed footer carries the source filename; description ends with the vault path so CrudusLiv can jump straight to the full note.
- State recorded under `dashboard_state["lectures"][rel_path] = {thread_id, starter_message_id}`. Slice 7 (in-thread chat) will read this to recognise agent-owned threads.

Validation done (2026-05-25): synthetic `summary` dict routed through `_route_lecture`; embed posted to `#lectures`, state recorded. Dedupe verified by calling again with the same `rel_path` — no second thread, state unchanged. `_extract_tldr` unit-checked against a sample note (correct section, n cap, empty input).

Manual probes:

```powershell
# Synthetic post (bypasses LLM):
py -c "import sys; sys.path.insert(0, '.claude/scripts'); sys.path.insert(0, '.claude/scripts/integrations'); import _env, runpy; m = runpy.run_path('.claude/scripts/heartbeat.py'); m['_route_lecture']({'name':'CS101','title':'Probe','tldr':['a','b','c'],'source':'probe.pptx','type':'lecture'}, 'lectures/CS101/probe.md')"

# Real end-to-end: drop a .pptx into Dynamous/Memory/inbox/, then:
py .claude/scripts/heartbeat.py
```

---

## Slice 6 — `#daily` unified feed (done)

Behavior:

- One Discord text channel for everything that isn't deadlines, lectures, system, or capture: habit auto-checks (`morning_digest`), evening habit nudges (`evening_nudge`), and generic daily items / project-inbox filings (`daily_digest`).
- `dashboard.py:_format_daily(kind, p)` reads the same payload shape heartbeat.py already produces (`{title, body, priority?}`) and emits an embed with an emoji prefix + color picked from `_DAILY_STYLES`:
  - 🌅 amber for `morning_digest`
  - 🌙 muted purple for `evening_nudge`
  - 📝 slate for `daily_digest`
- No call-site changes — heartbeat.py already used the three kinds; only `ROUTES` repointed all three at `DISCORD_HOOK_DAILY` and the fallback formatter was replaced with a real one.

Validation done (2026-05-25): one synthetic post per kind via `dashboard.notify`. Three embeds with distinct emoji+color landed in `#daily`.

Manual probe:

```powershell
py -c "import sys; sys.path.insert(0, '.claude/scripts'); sys.path.insert(0, '.claude/scripts/integrations'); import _env; from heartbeat import dashboard; dashboard.notify('morning_digest', {'title': 'probe', 'body': 'amber sunrise'})"
```

---

## Slice 7 — In-thread chat carve-out (done)

Behavior:

- `thread_chat.scan_and_reply(db_path, user_id, state_path)` runs each tick after `discord_dm_capture.scan_and_route` and shares the same `state_path` (`.claude/data/discord_last_tick.json`) — `seen_message_ids` is the union across all three scanners.
- Known threads are pulled fresh from `dashboard_state` each call. The SQL filter is `channel_id IN (...) AND is_dm = 0 AND is_self = 0 AND is_bot = 0 AND author_id = DISCORD_USER_ID AND created_at >= now - 24h`.
- For each new row: pull last 20 messages from the thread (oldest first, current row excluded), build the prompt via `thread_chat_prompt`, call Haiku via `llm.call` with a 60s timeout, post the response via `dashboard.notify` with `thread_id`. LLM/post failures still mark the row seen so the loop can't get stuck on a poisoned message.
- Two route kinds: `deadline_reply` → `DISCORD_HOOK_DEADLINES`, `lecture_reply` → `DISCORD_HOOK_LECTURES`. The thread's `kind` field (recorded by Slice 3/4) picks which.
- Bot identity remains read-only. All outbound is via the channel webhook with `thread_id`. USER.md hard-limits + platform table updated to call out the carve-out.

Validation done (2026-05-25): created a synthetic lecture thread via `_route_lecture`, hand-inserted a cache row into `discord_cache.db` pointing at that thread with `author_id = DISCORD_USER_ID`, monkey-patched `llm.call` to return a canned reply (no LLM credit burn). One reply posted; second run posted zero (idempotent).

Manual probe (LLM-mocked, no credit cost):

```powershell
# Insert a row into discord_cache.db with channel_id = a known thread_id, then:
py -c "import sys; sys.path.insert(0,'.claude/scripts'); sys.path.insert(0,'.claude/scripts/integrations'); import _env; from heartbeat import thread_chat, llm; llm.call = lambda *a,**k: 'canned probe reply'; import os, pathlib; print(thread_chat.scan_and_reply(pathlib.Path('.claude/data/discord_cache.db'), user_id=os.environ['DISCORD_USER_ID'], state_path=pathlib.Path('.claude/data/discord_last_tick.json')))"
```

---

## Slice 5 — `#pr-activity` (done)

Behavior:

- `github_int.recent_pr_events(since)` walks every repo the token can see (top 30 by recent push, via `_all_user_repos`). Per repo it does two API walks:
  - `repo.get_pulls(state="all", sort="updated", direction="desc")` — break out of the iterator the moment `pr.updated_at < since`. Within the window, emits `pr_opened` if `created_at >= since` and `pr_merged` if `merged_at >= since`.
  - `repo.get_issues_comments(since=...)` — filters to comments on PRs by checking `/pull/` in `html_url`.
- Stable dedupe ids let `_route_pr_events` re-run safely across ticks; the seen list is capped at 500 entries (insertion order preserved) so the JSON state stays bounded.
- "All repos" specifically means "every repo the GITHUB_TOKEN can list," not `GITHUB_ASSIGNMENT_REPOS` (which still drives the code-reviewer skill).
- `#code-review` channel is deferred. PR comments land in `#pr-activity` as raw events; a separate plan will add review-draft generation.

Validation done (2026-05-25): live token enumeration returned 11 repos; no PR activity in the last 30 days so end-to-end was exercised by monkey-patching `github_int.recent_pr_events` to emit three synthetic events (open + merge + comment). Three embeds landed in `#pr-activity`; second run posted zero (idempotent via `seen_event_ids`).

Manual probes:

```powershell
# Live API smoke (no posts):
py -c "import sys, time; sys.path.insert(0,'.claude/scripts'); sys.path.insert(0,'.claude/scripts/integrations'); import _env; from integrations import github_int; print(len(github_int.recent_pr_events(since=time.time()-30*86400)))"

# Synthetic post (bypasses live API):
py -c "import sys, time; sys.path.insert(0,'.claude/scripts'); sys.path.insert(0,'.claude/scripts/integrations'); import _env; import runpy; m = runpy.run_path('.claude/scripts/heartbeat.py'); import integrations.github_int as g; g.recent_pr_events = lambda since=None: [{'id':'open:probe:1','kind':'pr_opened','repo':'probe/repo','pr_number':1,'pr_title':'probe','pr_url':'https://example.com','actor':'me','ts':time.time()}]; m['_route_pr_events']()"
```

---

## Slice 8 — folded into Slice 2

`#vesper` is already read+reply via `discord_bot.on_message` (no webhook needed, the bot replies via `channel.send` inside the carve-out). The `vesper_reply` route + `DISCORD_HOOK_VESPER` env var remain declared but unused.

---

## Open questions (deferred)

Carried over from the original plan, still unresolved:

1. **Webhook avatar + name per channel.** Defaulting to per-channel names ("Heartbeat", "Errors", "Inbox", …); set when creating each webhook in Discord's UI.
2. **Embed style.** Current call: embed for `error` (red bar), plain text for `heartbeat_tick`. Slice 3+ will likely use embeds throughout.
3. **Forum tag taxonomy** for `#deadlines` (e.g. `urgent`, `overdue`, `submitted`) — skipped for v1.
4. **`#heartbeat` content scope** — locked to "status + failing integrations only."
5. **`#code-review` source** — deferred. Slice 5 routes raw PR events only.

---

## How to resume

In a new session:

1. Re-read this file (`docs/discord-dashboard.md`).
2. For deeper architecture context, re-read the original plan at `C:\Users\livne\.claude\plans\plan-a-discord-as-dashboard-layer-gentle-kahn.md`.
3. Re-read the three Slice 1 modules to refresh on the shape of `notify` / `format_embed` / state IO:
   - `.claude/scripts/integrations/discord_webhook.py`
   - `.claude/scripts/heartbeat/dashboard.py`
   - `.claude/scripts/heartbeat/dashboard_state.py`
4. Pick the next pending slice (Slice 2 unless something else jumps the queue).
5. Create the channel + webhook in Discord, paste URL into `.env`.
6. Code → validate end-to-end → mark the row in the slice status table here.

---

## Constraints (do not violate)

- Vault is read-only by default; only `Dynamous/Memory/inbox/_processed/` may have deletes.
- No general Discord sends from the bot. Outbound on servers MUST go through one-way webhooks.
- The read-only bot stays read-only. The only inbound carve-out is DMs filtered to `DISCORD_USER_ID`.
- Idempotency: every outbound channel tracks what it has already sent in `discord_dashboard_state.json`. No re-spamming the same alert every 30 min.
- Reuse the existing heartbeat (`.claude/scripts/heartbeat/`) and integration scaffolding (`.claude/scripts/integrations/`). Don't rebuild what's there.
