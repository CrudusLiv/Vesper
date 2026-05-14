# Repo Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `BoredBot` into a shareable runtime-code repo and a private personal-vault repo, then squash history into one fresh commit.

**Architecture:** Three phases, each independently reversible until the last. Phase 1 stands up the new vault repo with full backups. Phase 2 untracks the vault tree, swaps in a nested clone, removes starter cruft, adds three newly tracked files. Phase 3 orphan-commits the cleaned tree as a single "Initial commit" and force-pushes.

**Tech Stack:** Git (PowerShell on Windows), GitHub web UI for repo creation, Python 3.14 for smoke-test scripts already in the repo.

**Spec:** [docs/superpowers/specs/2026-05-14-repo-cleanup-design.md](../specs/2026-05-14-repo-cleanup-design.md)

---

## Pre-flight

This plan file lives at `docs/superpowers/plans/2026-05-14-repo-cleanup.md` and will be **deleted by Task 13** when `docs/superpowers/` is removed. Copy it (and the spec) into the cold backup created by Task 1 before proceeding past Phase 2, so the executor can still reference it.

All commands assume PowerShell from the BoredBot repo root unless noted otherwise. Paths use `D:\GitHub\` because that's where BoredBot lives. Adjust if your layout differs.

---

## Phase 1 — Stand up the vault repo

### Task 1: Cold filesystem backup

**Files:**
- Create: `D:\GitHub\second-brain-backup-2026-05-14\` (rescue copy of the entire BoredBot working tree)

- [ ] **Step 1: Verify nothing is mid-commit**

```powershell
git status
```

Expected: working tree may show modifications and untracked files (that's fine), but no merge/rebase/cherry-pick in progress. If anything weird (e.g. `interactive rebase in progress`), abort and resolve before continuing.

- [ ] **Step 2: Create the backup directory and copy everything**

```powershell
$backup = "D:\GitHub\second-brain-backup-2026-05-14"
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item -Path "D:\GitHub\second-brain-starter\*" -Destination $backup -Recurse -Force
Copy-Item -Path "D:\GitHub\second-brain-starter\.claude" -Destination $backup -Recurse -Force
Copy-Item -Path "D:\GitHub\second-brain-starter\.gitignore" -Destination $backup -Force
Copy-Item -Path "D:\GitHub\second-brain-starter\.git" -Destination $backup -Recurse -Force
```

(Three explicit dot-prefix copies because `Copy-Item *` skips hidden items by default on Windows.)

- [ ] **Step 3: Verify backup completeness**

```powershell
(Get-ChildItem $backup -Recurse -File | Measure-Object).Count
(Get-ChildItem "D:\GitHub\second-brain-starter" -Recurse -File | Measure-Object).Count
```

Expected: both counts should be within 1-2 of each other (a few transient files like `.git/index.lock` may differ). If they differ by more than 5, re-run Step 2.

- [ ] **Step 4: Verify the backup's git history is intact**

```powershell
git -C $backup log --oneline | Select-Object -First 3
```

Expected: top commit is the spec commit (`46e9856 docs: repo cleanup spec — split code from personal vault` or whatever your HEAD is). Three lines shown.

### Task 2: Tag the pre-cleanup state in git

**Files:**
- Modify: BoredBot git refs (new tag `pre-cleanup-2026-05-14`)

- [ ] **Step 1: Create the tag locally**

```powershell
git tag -a pre-cleanup-2026-05-14 -m "Snapshot before repo cleanup (split code from vault, squash history)"
```

Expected: silent success.

- [ ] **Step 2: Push the tag**

```powershell
git push origin pre-cleanup-2026-05-14
```

Expected: `* [new tag] pre-cleanup-2026-05-14 -> pre-cleanup-2026-05-14`.

- [ ] **Step 3: Verify the tag exists locally and remotely**

```powershell
git tag --list pre-cleanup-2026-05-14
git ls-remote --tags origin pre-cleanup-2026-05-14
```

Expected: both commands print one line containing `pre-cleanup-2026-05-14`.

### Task 3: Create the empty private vault repo on GitHub

**Files:**
- Create: `github.com/CrudusLiv/second-brain-vault` (private, empty)

This is a **manual GitHub UI step** because `gh` CLI is not installed.

- [ ] **Step 1: Create the repo**

In a browser, go to https://github.com/new and:
- Owner: `CrudusLiv`
- Repository name: `second-brain-vault`
- Description: `Private personal vault for my second brain (clones into BoredBot/Dynamous/Memory/)`
- Visibility: **Private**
- **Do NOT** check "Add a README", "Add .gitignore", or "Choose a license". The repo must start empty.
- Click "Create repository".

Expected: the repo page shows "Quick setup — if you've done this kind of thing before" with an empty repo URL.

- [ ] **Step 2: Note the clone URL**

Should be `https://github.com/CrudusLiv/second-brain-vault.git`. Confirm in the browser before proceeding.

### Task 4: Populate the vault repo locally

**Files:**
- Create: `D:\GitHub\second-brain-vault\` (sibling to BoredBot, contains a clone of the empty vault repo seeded with the current Dynamous/Memory contents)

- [ ] **Step 1: Clone the empty vault repo as a sibling to BoredBot**

```powershell
git clone https://github.com/CrudusLiv/second-brain-vault.git D:\GitHub\second-brain-vault
```

Expected: `warning: You appear to have cloned an empty repository.` That's correct.

- [ ] **Step 2: Copy current vault contents into the new repo**

```powershell
Copy-Item -Path "D:\GitHub\second-brain-starter\Dynamous\Memory\*" `
          -Destination "D:\GitHub\second-brain-vault" -Recurse -Force
```

- [ ] **Step 3: Verify the copy**

```powershell
Test-Path "D:\GitHub\second-brain-vault\SOUL.md"
Test-Path "D:\GitHub\second-brain-vault\MEMORY.md"
Test-Path "D:\GitHub\second-brain-vault\daily\2026-05-13.md"
(Get-ChildItem "D:\GitHub\second-brain-vault" -Recurse -File | Measure-Object).Count
```

Expected: first three return `True`. File count is non-zero (will be 30-50+ depending on your current vault state).

- [ ] **Step 4: Add a `.gitkeep` to inbox so the empty folder survives**

```powershell
$ik = "D:\GitHub\second-brain-vault\inbox\.gitkeep"
if (-not (Test-Path $ik)) { New-Item -ItemType File -Path $ik | Out-Null }
```

(Defensive — current vault already has this file but the inbox itself may have been pruned during the copy if it was empty.)

### Task 5: Write the vault README and initial commit

**Files:**
- Create: `D:\GitHub\second-brain-vault\README.md`

- [ ] **Step 1: Write `D:\GitHub\second-brain-vault\README.md`**

Exact content:

```markdown
# second-brain-vault

Private personal vault for my second brain. Pairs with [BoredBot](https://github.com/CrudusLiv/BoredBot).

## Setup on a new machine

1. Clone BoredBot first (it expects this repo to live at `Dynamous/Memory/`):

   ```powershell
   git clone https://github.com/CrudusLiv/BoredBot.git
   cd BoredBot
   ```

2. Clone this repo into `Dynamous/Memory/`:

   ```powershell
   git clone https://github.com/CrudusLiv/second-brain-vault.git Dynamous/Memory
   ```

3. Pull updates on whichever machine you used last:

   ```powershell
   cd Dynamous/Memory
   git pull
   ```

## What's in here

- `SOUL.md`, `MEMORY.md`, `DEADLINES.md`, `HABITS.md`, `HEARTBEAT.md`, `PROJECTS.md`, `USER.md` — durable context loaded by the SessionStart hook.
- `daily/` — per-session logs.
- `finance/`, `goals/`, `lectures/`, `notes/`, `projects/`, `research/` — topic folders.
- `inbox/` — drop zone for lecture files. `inbox/_processed/` is gitignored.

## Why this is private

Contains personal notes, schedules, and finances. Should never be shared.
```

- [ ] **Step 2: Stage, commit, and push**

```powershell
git -C D:\GitHub\second-brain-vault add -A
git -C D:\GitHub\second-brain-vault commit -m "Initial commit: personal vault snapshot 2026-05-14"
git -C D:\GitHub\second-brain-vault push -u origin main
```

Expected push line: `* [new branch] main -> main`. (If the default branch name is `master`, use `master` instead — verify in the GitHub UI.)

- [ ] **Step 3: Verify the push**

```powershell
git -C D:\GitHub\second-brain-vault log --oneline
```

Expected: one line — the initial commit, with a short SHA.

---

## Phase 2 — Untrack vault, swap to inner clone, clean cruft

### Task 6: Untrack the vault tree from BoredBot's index

**Files:**
- Modify: `.gitignore` (add `Dynamous/Memory/`)
- Remove from index (keep on disk): `Dynamous/Memory/**`

- [ ] **Step 1: Untrack everything under `Dynamous/Memory/` without deleting from disk**

```powershell
git rm -r --cached Dynamous/Memory/
```

Expected: a long list of `rm 'Dynamous/Memory/...'` lines, one per tracked file. No errors.

- [ ] **Step 2: Add the path to `.gitignore`**

Edit `.gitignore`. Find this section:

```
# Vault transient state
Dynamous/Memory/inbox/_processed/
```

Replace with:

```
# Personal vault (lives in separate private repo: CrudusLiv/second-brain-vault)
# Cloned into Dynamous/Memory/ on each device.
Dynamous/Memory/
```

- [ ] **Step 3: Verify the index update**

```powershell
git ls-files Dynamous/Memory/ | Measure-Object -Line
git status --short Dynamous/Memory/ | Select-Object -First 5
```

Expected: first command shows `Lines: 0`. Second command shows nothing (because the path is now gitignored).

- [ ] **Step 4: Commit**

```powershell
git add .gitignore
git commit -m "chore: untrack personal vault (moved to second-brain-vault repo)"
```

Expected: commit summary mentions ~30-50 deletions and one modification (`.gitignore`).

### Task 7: Replace on-disk vault with a nested clone of the vault repo

**Files:**
- Delete on disk: `D:\GitHub\second-brain-starter\Dynamous\Memory\`
- Create on disk: `D:\GitHub\second-brain-starter\Dynamous\Memory\` as a clone of `CrudusLiv/second-brain-vault`

- [ ] **Step 1: Delete the existing on-disk directory**

```powershell
Remove-Item -Path "D:\GitHub\second-brain-starter\Dynamous\Memory" -Recurse -Force
```

Expected: silent success. (Safety: Task 4 already pushed all this content to the new private repo, and Task 1 has the cold backup.)

- [ ] **Step 2: Clone the vault repo into the same path**

```powershell
git clone https://github.com/CrudusLiv/second-brain-vault.git D:\GitHub\second-brain-starter\Dynamous\Memory
```

Expected: standard clone output. `Resolving deltas: 100% ...`, `done.`.

- [ ] **Step 3: Verify the swap**

```powershell
Test-Path "D:\GitHub\second-brain-starter\Dynamous\Memory\SOUL.md"
Test-Path "D:\GitHub\second-brain-starter\Dynamous\Memory\.git"
git -C D:\GitHub\second-brain-starter\Dynamous\Memory remote -v
```

Expected: both `Test-Path` return `True`. Remote shows `origin https://github.com/CrudusLiv/second-brain-vault.git (fetch)` and `(push)`.

- [ ] **Step 4: Confirm outer BoredBot ignores it**

```powershell
git status --short Dynamous/Memory/
```

Expected: no output. The nested git repo is fully invisible to BoredBot.

### Task 8: Smoke test — hooks still find vault files

**Files:** (no changes — verification only)

- [ ] **Step 1: Run the integrations status check**

```powershell
py .claude\scripts\query.py status
```

Expected: a table or list of integrations with readiness states. No traceback, no `FileNotFoundError`.

- [ ] **Step 2: Manually run the SessionStart hook against a fake payload**

```powershell
'{"hook_event_name":"SessionStart","matcher":"startup"}' | py .claude\hooks\session-start-context.py
```

Expected: JSON output containing `additionalContext` with text from `SOUL.md` ("SOUL — Agent Personality" header should appear). No traceback.

- [ ] **Step 3: Verify the daily log path still works**

```powershell
Test-Path "Dynamous\Memory\daily\2026-05-13.md"
```

Expected: `True`.

If any step fails, **stop and investigate** — do not proceed to Task 9.

### Task 9: Remove starter cruft

**Files:**
- Delete: `docs/superpowers/`, `.claude/skills/create-second-brain-prd/`, `README.md`, `SecondBrainArchitecture.png`, `WhyBuildYourOwnSecondBrain.png`

- [ ] **Step 1: First copy this plan + the spec to the cold backup**

(They live under `docs/superpowers/` which we're about to delete. We need them for the executor to follow Phase 3 and for future reference.)

```powershell
$backup = "D:\GitHub\second-brain-backup-2026-05-14"
Copy-Item -Path "docs\superpowers\specs\2026-05-14-repo-cleanup-design.md" -Destination "$backup\repo-cleanup-spec.md" -Force
Copy-Item -Path "docs\superpowers\plans\2026-05-14-repo-cleanup.md" -Destination "$backup\repo-cleanup-plan.md" -Force
```

Expected: silent success. Verify both files exist at the backup paths.

- [ ] **Step 2: `git rm` the cruft**

```powershell
git rm -r docs/superpowers/
git rm -r .claude/skills/create-second-brain-prd/
git rm README.md SecondBrainArchitecture.png WhyBuildYourOwnSecondBrain.png
```

Expected: a list of `rm ...` lines, no errors.

- [ ] **Step 3: Confirm the deletions**

```powershell
Test-Path "docs\superpowers"
Test-Path ".claude\skills\create-second-brain-prd"
Test-Path "README.md"
```

Expected: all three return `False`.

### Task 10: Track new files and write the new README

**Files:**
- Stage existing untracked: `.claude/settings.json`, `.claude/hooks/note-capture.py`
- Create: `.env.example`, `README.md` (new content)

- [ ] **Step 1: Verify `.claude/settings.json` has no secrets**

```powershell
Get-Content .claude\settings.json
```

Expected: JSON with `hooks` blocks using `$CLAUDE_PROJECT_DIR\.claude\hooks\*.py` commands. No API keys, no tokens, no email addresses. (Already verified during spec-writing, but re-check on this machine.)

If anything secret is present, stop and ask the user.

- [ ] **Step 2: Write `.env.example` at the repo root**

Exact content:

```ini
# Google OAuth (Gmail + Calendar)
# Put google_credentials.json at .claude/data/google_credentials.json instead;
# this file just lists what the integrations expect.

# Discord
DISCORD_BOT_TOKEN=
DISCORD_USER_ID=
DISCORD_GUILD_ID=

# GitHub
GITHUB_TOKEN=

# OpenAI / LLM (if used by heartbeat LLM step)
OPENAI_API_KEY=

# Optional: override the vault root (defaults to Dynamous/Memory under repo root)
# VAULT_ROOT=
```

(If the executor finds additional env vars referenced by `.claude/scripts/integrations/_env.py` or `registry.py` that aren't listed here, add them — but do not invent ones that aren't actually used.)

- [ ] **Step 3: Cross-check env var list against the registry**

```powershell
Select-String -Path .claude\scripts\integrations\registry.py -Pattern "os\.environ|getenv|env\." -SimpleMatch:$false
Select-String -Path .claude\scripts\integrations\_env.py -Pattern "os\.environ|getenv" -SimpleMatch:$false
```

Expected: a list of references. Any env var seen here that isn't in `.env.example` should be added. Any var in `.env.example` that isn't referenced should be removed.

- [ ] **Step 4: Write the new `README.md` at the repo root**

Exact content:

```markdown
# BoredBot

My second brain, built on Claude Code. Hooks, scripts, skills, and settings that turn Claude Code into a study partner: deadline tracking, lecture summarisation, note search, code review.

The personal vault data (notes, schedules, finances) lives in a separate private repo and clones into `Dynamous/Memory/`.

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

# 5. (Personal vault — owner only)
# git clone https://github.com/CrudusLiv/second-brain-vault.git Dynamous/Memory

# 6. Open the directory in Claude Code. Hooks fire automatically.
```

## Layout

| Path | Purpose |
|------|---------|
| `.claude/hooks/` | SessionStart, PreCompact, SessionEnd, PreToolUse, UserPromptSubmit hooks |
| `.claude/scripts/` | Unified `query.py` CLI, integrations, heartbeat, memory (RAG), finance, security |
| `.claude/skills/` | Skills the agent invokes (code-reviewer, deadline-tracker, lecture-summarizer, note-search, vault-structure) |
| `.claude/settings.json` | Wires hooks into Claude Code |
| `tests/` | pytest suite |
| `Dynamous/Memory/` | Personal vault (gitignored — separate private repo) |

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
```

- [ ] **Step 5: Stage all new and modified tracked content**

```powershell
git add .claude/settings.json .claude/hooks/note-capture.py .env.example README.md
git status --short
```

Expected: shows the four `A` (added) entries plus the deletions from Task 9. No `??` for these files.

### Task 11: Commit and push Phase 2

- [ ] **Step 1: Commit**

```powershell
git commit -m "chore: remove starter cruft; track settings, note-capture, env example, new README"
```

Expected: commit summary lists the deletions from Task 9 and additions from Task 10.

- [ ] **Step 2: Push**

```powershell
git push origin main
```

Expected: normal push, no force needed. History is still old + 2 new commits.

- [ ] **Step 3: End-of-phase verification**

```powershell
git log --oneline | Select-Object -First 5
git ls-files | Measure-Object -Line
```

Expected: top commit is the Phase 2 chore commit. Tracked file count dropped substantially (from 93 to ~60-65, accounting for vault removal + skill removal + docs removal + a few new files).

---

## Phase 3 — Squash history and force-push

> **CHECKPOINT:** This phase is destructive. Confirm with the user before starting. Once Task 13 completes, the old history can only be recovered from the `pre-cleanup-2026-05-14` tag or the cold backup.

### Task 12: User checkpoint

- [ ] **Step 1: Ask the user**

"Phase 2 complete and pushed. The repo is now clean but history still shows all 43 commits. Phase 3 squashes it to one commit and force-pushes. After that, your other devices will need `git fetch && git reset --hard origin/main` to follow. Proceed?"

Wait for explicit confirmation. Do not start Task 13 without it.

### Task 13: Squash to one fresh commit

**Files:** (no file changes — git refs only)

- [ ] **Step 1: Confirm the current working tree is what we want as "Initial commit"**

```powershell
git status
```

Expected: `working tree clean` and `Your branch is up to date with 'origin/main'`. If not clean, stop.

- [ ] **Step 2: Create an orphan branch from the current tree**

```powershell
git checkout --orphan clean-main
```

Expected: `Switched to a new branch 'clean-main'`. All files appear staged (because orphan branches start with no parent).

- [ ] **Step 3: Stage everything and commit**

```powershell
git add -A
git commit -m "Initial commit"
```

Expected: commit summary lists ~60-65 files added.

- [ ] **Step 4: Verify the new branch has exactly one commit**

```powershell
git log --oneline
```

Expected: exactly one line — `<sha> Initial commit`.

- [ ] **Step 5: Replace `main` with `clean-main`**

```powershell
git branch -D main
git branch -M clean-main main
```

Expected: first command shows `Deleted branch main`. Second is silent. `git status` should show `On branch main`.

### Task 14: Force-push the squashed main

- [ ] **Step 1: Push with lease**

```powershell
git push --force-with-lease origin main
```

Expected: forced update notation, something like `+ <oldsha>...<newsha> main -> main (forced update)`.

`--force-with-lease` (not `--force`) is intentional: it refuses to push if someone else pushed to `main` since you last fetched. On a personal repo this is paranoid but cheap.

- [ ] **Step 2: Verify the remote state**

```powershell
git fetch origin
git log origin/main --oneline
```

Expected: one line — the Initial commit you just pushed.

- [ ] **Step 3: Verify the backup tag is still reachable**

```powershell
git tag --list pre-cleanup-2026-05-14
git show pre-cleanup-2026-05-14 --stat | Select-Object -First 5
```

Expected: tag still exists and points to the old (pre-cleanup) state.

### Task 15: Validate on a fresh clone

**Files:**
- Create: `D:\GitHub\boredbot-validate\` (temporary, deleted at the end)

- [ ] **Step 1: Clone fresh into a tmp directory**

```powershell
git clone https://github.com/CrudusLiv/BoredBot.git D:\GitHub\boredbot-validate
cd D:\GitHub\boredbot-validate
git log --oneline
```

Expected: one commit shown — Initial commit. No vault tree, no `docs/superpowers/`, no `create-second-brain-prd` skill.

- [ ] **Step 2: Confirm essential files are present**

```powershell
Test-Path .claude\settings.json
Test-Path .claude\hooks\session-start-context.py
Test-Path .claude\hooks\note-capture.py
Test-Path .claude\scripts\query.py
Test-Path .env.example
Test-Path CLAUDE.md
Test-Path README.md
Test-Path pytest.ini
Test-Path tests\conftest.py
```

Expected: all `True`.

- [ ] **Step 3: Confirm cruft is gone**

```powershell
Test-Path docs\superpowers
Test-Path .claude\skills\create-second-brain-prd
Test-Path Dynamous\Memory
Test-Path SecondBrainArchitecture.png
```

Expected: all `False`.

- [ ] **Step 4: Install deps and run a smoke command**

```powershell
py -m pip install -r .claude\requirements.txt
py .claude\scripts\query.py status
```

Expected: pip succeeds; query.py prints integration statuses (most will be unready because there's no `.env` — that's correct).

- [ ] **Step 5: Clone the vault into place and re-run status**

```powershell
git clone https://github.com/CrudusLiv/second-brain-vault.git Dynamous\Memory
'{"hook_event_name":"SessionStart","matcher":"startup"}' | py .claude\hooks\session-start-context.py
```

Expected: the hook prints JSON with `additionalContext` containing SOUL content. (Same as Task 8 Step 2 but on a fresh clone.)

- [ ] **Step 6: Clean up the validation clone**

```powershell
cd D:\GitHub\second-brain-starter
Remove-Item -Path "D:\GitHub\boredbot-validate" -Recurse -Force
```

Expected: silent success.

### Task 16: Post-flight notes for the user

(Not a code change — communicate to the user.)

- [ ] **Step 1: Print these reminders**

> Repo cleanup complete. A few follow-ups for you:
>
> 1. **Other devices:** On any other machine where you have BoredBot cloned, run `git fetch && git reset --hard origin/main` to pick up the new history. Their old clone history is incompatible.
> 2. **Privacy:** Old commit SHAs remain reachable on GitHub for ~90 days. If you want the prior vault contents fully gone from public view, flip the BoredBot repo to **Private** in GitHub Settings → General → Danger Zone → Change repository visibility. Your friend can still be added as a collaborator on a private repo.
> 3. **Sharing with friend:** Send him the BoredBot clone URL and the `.env.example` setup instructions in the new README. He does NOT get access to `second-brain-vault`.
> 4. **Backup retention:** Keep `D:\GitHub\second-brain-backup-2026-05-14\` and the `pre-cleanup-2026-05-14` tag for at least a week. After that, delete the directory; the tag can stay.

---

## Self-review notes

- **Spec coverage:** All four "what gets removed" items mapped to Task 9. All five "what stays" items implicitly preserved (nothing in the plan touches them). All four "what gets newly added" items mapped to Task 10. Three-phase staging matches the spec exactly. Validation checklist from the spec is covered by Task 15.
- **Placeholders:** None — every command is literal, every file content is given verbatim.
- **Type consistency:** Path conventions consistent throughout (`D:\GitHub\second-brain-starter` for current repo, `D:\GitHub\second-brain-vault` for the new vault repo). Branch name `clean-main` only mentioned in Phase 3 and renamed back to `main` before push.
- **Plan self-deletion:** Handled by Task 9 Step 1 (copy spec + plan to cold backup before deleting `docs/superpowers/`).
