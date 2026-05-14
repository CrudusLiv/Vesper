# USER

## Profile

- **Name:** CrudusLiv
- **Role:** Software Developer / Computer Science student
- **Timezone:** Asia/Kuala_Lumpur (UTC+8)
- **Status (as of 2026-05-08):** Pre-semester. Classes begin June 2026. Currently unemployed.
- **OS:** Windows 11
- **Editor / IDE:** VSCode

## Top tasks for the agent

1. Track assignment deadlines — surface anything due in 72h, escalate at 24h.
2. Summarize uploaded lecture PowerPoints / PDFs into searchable Obsidian notes under `lectures/<course>/`.
3. Keep notes organized and searchable via hybrid RAG over the vault.
4. Initial code review on assignment repos — correctness, edge cases, style, complexity.

## Platforms

| Platform | Use | Auth | Notes |
|---|---|---|---|
| Gmail | Personal email | OAuth2 (`credentials.json`) | Scope: `gmail.readonly` |
| Outlook | University email | MSAL device-code flow | Defer until classes start (June 2026) |
| Google Calendar | Schedule + deadlines | Shares Gmail OAuth token | Scope: `calendar.readonly` |
| Discord | Chat / DMs | Bot token | Read-only — never send (carve-out: Phase 7 DM chat replies in CrudusLiv's own DMs only) |
| GitHub | Code hosting | Fine-grained PAT | Scope: `repo`, `read:user` |
| Obsidian | Notes + tasks | Local filesystem | Vault at `Dynamous/Memory/` |

## Assignment repos (Phase 4.2 — code reviewer)

_(Fill in once classes start. Format: `owner/repo`. The code-reviewer skill only runs on these.)_

- _(none yet)_

## Drafting criteria

**Always draft (never send):**

- Gmail / Outlook replies to messages from the university domain or addressed personally
- Code-review comments on assignment-repo pushes

**Skip drafting:**

- Newsletters, marketing email, automated notifications
- Discord server channels (only DMs warrant drafts)
- Commits with `wip` or `checkpoint` messages

## Voice for drafts

- Match how CrudusLiv writes. RAG retrieval over `drafts/sent/` provides examples per platform.
- Default to plain text, no greetings/sign-offs unless the original message has them.
- **Discord:** lowercase, short, no formality.
- **Gmail:** polite but brief. Keep the parent thread's subject line.
- **Outlook (university):** slightly more formal — professors and admin staff.

## Hard limits (security boundaries)

- ❌ Send Gmail / Outlook messages
- ❌ Send Discord messages (carve-out: Phase 7 DM chat replies in CrudusLiv's own DMs only)
- ❌ Post to social media
- ❌ Touch financial data or make purchases
- ❌ Delete any file under `Dynamous/Memory/`

## Heartbeat schedule

- **Active hours:** 09:00–22:00 UTC+8, every 30 min
- **Daily reflection:** 08:00 UTC+8
- **Late-day habit nudge:** 18:00 UTC+8 if pillars still unchecked

## Account / integration IDs

_(Fill in as you set them up. These never get sent to the LLM — Python wrappers handle auth.)_

- Discord user ID: 1100305330304458794
- GitHub username: CrudusLiv
- Gmail address: _(your Gmail address)_
- Outlook address: _(your university email)_
- University email domain: _(e.g., `students.university.edu.my`)_
