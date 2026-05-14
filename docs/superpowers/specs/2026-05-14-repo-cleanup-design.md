# Repo Cleanup — Split Code From Personal Vault

**Date:** 2026-05-14
**Status:** Spec — awaiting plan
**Repo:** `github.com/CrudusLiv/BoredBot`

## Problem

The `BoredBot` repo currently mixes three concerns that should be separated:

1. **Runtime code** — hooks, scripts, skills, settings that make the second brain work.
2. **Personal vault data** — `Dynamous/Memory/` containing `SOUL.md`, `MEMORY.md`, daily logs, finance, etc. Private to CrudusLiv.
3. **Build artefacts** — design specs, implementation plans, the original starter kit's PRD generator and README.

CrudusLiv wants to:

- Share the runtime code with one friend (clone-only, no ongoing collab).
- Sync personal vault data privately across his own devices.
- Get a clean "plug and play" experience on a fresh clone — no cruft, no orphaned spec files.
- Remove all non-CrudusLiv commits from history (3 commits by Cole Medin, the original starter author).

## Target end state

Two repositories:

### Repo A: `CrudusLiv/BoredBot` (shared with friend)

```
BoredBot/
├── .claude/
│   ├── hooks/            # all hook scripts, including note-capture.py
│   ├── scripts/          # heartbeat, integrations, memory, security, finance
│   ├── skills/           # code-reviewer, deadline-tracker, lecture-summarizer,
│   │                     # note-search, vault-structure
│   │                     # (REMOVED: create-second-brain-prd)
│   ├── settings.json     # newly tracked — wires up hooks
│   └── requirements.txt
├── tests/
├── pytest.ini
├── CLAUDE.md
├── .env.example          # new — template with required vars listed, no values
├── .gitignore            # updated: ignores Dynamous/Memory/ entirely
└── README.md             # new — short, CrudusLiv-authored setup guide

Single commit: "Initial commit" (CrudusLiv)
Branch: main only
```

### Repo B: `CrudusLiv/second-brain-vault` (PRIVATE, just CrudusLiv)

```
second-brain-vault/
├── SOUL.md
├── MEMORY.md
├── DEADLINES.md
├── HABITS.md
├── HEARTBEAT.md
├── PROJECTS.md
├── USER.md
├── README.md             # explains: clone into BoredBot/Dynamous/Memory/
├── daily/
├── finance/
├── goals/
├── lectures/
├── notes/
├── projects/
├── research/
└── inbox/.gitkeep        # (inbox/_processed/ stays gitignored)
```

On any device: clone BoredBot, then clone vault repo into `BoredBot/Dynamous/Memory/`.

## What gets removed from BoredBot

- `Dynamous/Memory/` — entire tree moves to the vault repo, then gitignored here.
- `docs/superpowers/` — specs and plans (including this file once cleanup is done).
- `.claude/skills/create-second-brain-prd/` — original starter kit's PRD generator. Useful once at design time; not part of the runtime.
- `README.md` — original starter's README. Replaced with a short CrudusLiv-authored one.
- `SecondBrainArchitecture.png`, `WhyBuildYourOwnSecondBrain.png` — original starter's diagrams.

## What stays in BoredBot

- All of `.claude/hooks/`, `.claude/scripts/`, `.claude/requirements.txt`.
- `.claude/skills/` minus `create-second-brain-prd/`.
- `.claude/settings.json` — newly tracked. Verified clean (no secrets, just hook command paths using `$CLAUDE_PROJECT_DIR`).
- `tests/`, `pytest.ini`, `CLAUDE.md`.
- `.gitignore` — extended to ignore `Dynamous/Memory/` entirely.

## What gets newly added to BoredBot

- `.env.example` — lists required environment variable names (no values). Friend copies to `.env` and fills in his own credentials.
- `README.md` — short setup guide: clone, copy `.env.example` → `.env`, `pip install -r .claude/requirements.txt`, clone vault repo into `Dynamous/Memory/` (or create it fresh from `Dynamous/Memory/README.md` instructions).

## History strategy

**Squash all 43 existing commits into one fresh "Initial commit" authored by CrudusLiv.**

- Rationale: removes 3 Cole Medin commits at the root cleanly with no rebase fragility, simplifies history to one snapshot, no attribution carryover.
- Trade-off: loses CrudusLiv's 40+ commit messages. Acceptable — this is a personal repo, not a project with a contribution history that matters.
- Mechanism: `git checkout --orphan` a new branch from the cleaned working tree, commit, replace `main`, force-push.

## Approach: staged migration

Three phases, each independently reversible until the last.

### Phase 1 — Stand up the vault repo

1. **Cold backup first:** copy the entire current `Dynamous/Memory/` to a path outside the repo (e.g. `~/second-brain-backup-2026-05-14/`). This is the rescue copy if anything in Phase 1 or 2 goes wrong.
2. Tag current BoredBot `main` as `pre-cleanup-2026-05-14` and push the tag (second backup, in-repo).
3. Create `CrudusLiv/second-brain-vault` on GitHub (private, empty).
4. Initialise a new local clone of the vault repo in a sibling directory (NOT inside BoredBot yet).
5. Copy current `Dynamous/Memory/` contents into the vault repo working tree.
6. Add a `README.md` to the vault repo explaining placement (`clone into BoredBot/Dynamous/Memory/`).
7. Initial commit + push the vault repo.

After Phase 1: vault repo exists on GitHub with all data. BoredBot is unchanged. If anything goes wrong, delete the new repo and try again.

### Phase 2 — Untrack vault, swap to inner clone, clean cruft

Order matters here: untrack the vault tree from git **before** replacing the on-disk contents with a nested clone, so git's index doesn't see a confusing partial state.

1. In BoredBot, `git rm -r --cached Dynamous/Memory/` — untracks all vault files without deleting them from disk.
2. Update `.gitignore`: add `Dynamous/Memory/` (the whole tree, because the inner clone will be its own git repo).
3. Commit: "chore: untrack personal vault (moved to second-brain-vault repo)".
4. **Now safe to replace contents:** delete the on-disk `Dynamous/Memory/` directory entirely, then `git clone` the vault repo into that path. Result: BoredBot has a nested git repo at `Dynamous/Memory/.git/`, fully gitignored by the outer repo.
5. Smoke test: run `py .claude/scripts/query.py status` and open a Claude Code session — confirm SessionStart hook still loads `SOUL.md` and daily logs from the new path. (Path is identical, so it should just work.)
6. Remove remaining cruft (`git rm -r`):
   - `docs/superpowers/`
   - `.claude/skills/create-second-brain-prd/`
   - `README.md`
   - `SecondBrainArchitecture.png`
   - `WhyBuildYourOwnSecondBrain.png`
7. Add newly tracked files:
   - `.claude/settings.json`
   - `.claude/hooks/note-capture.py`
   - `.env.example` (new file)
   - `README.md` (new content, CrudusLiv-authored)
8. Commit: "chore: remove starter cruft; track settings and note-capture hook".
9. Push.

End of Phase 2: BoredBot on GitHub has a clean working tree but still carries the old 43-commit history. Reversible via the `pre-cleanup-2026-05-14` tag.

### Phase 3 — Squash history and force-push

1. Re-confirm with user before this step (it's the irreversible one).
2. `git checkout --orphan clean-main`
3. `git add -A && git commit -m "Initial commit"`
4. `git branch -M clean-main main`
5. `git push --force-with-lease origin main`
6. **(Optional) Flip BoredBot to private** on GitHub if friend should never see prior public history. This is a manual GitHub UI step; the spec only flags the recommendation.

After this, the backup tag `pre-cleanup-2026-05-14` is the only path back. Keep it locally; delete the remote tag only after a week of confidence.

## Validation checklist

After Phase 3, on a separate fresh clone (e.g. tmp dir), confirm:

- `git clone <BoredBot>` succeeds.
- `cp .env.example .env` and fill stub values.
- `py -m pip install -r .claude/requirements.txt` succeeds.
- Clone vault repo into `Dynamous/Memory/`.
- Open the directory in Claude Code; SessionStart hook fires (check that `SOUL.md` shows up in injected context).
- `py .claude/scripts/query.py status` lists integrations correctly.
- `pytest` runs (tests pass or fail consistently with current state).

If all pass, the cleanup is complete.

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Lose vault data during migration | Two layered backups before any destructive step: (a) cold filesystem copy outside the repo, (b) git tag on `main`. Phase 1 only *copies* into the new repo; on-disk deletion in BoredBot waits until the vault repo is pushed and verified. |
| Hooks break because they reference old paths | Hooks use `$CLAUDE_PROJECT_DIR/Dynamous/Memory/...` — that path is unchanged because the vault repo gets cloned into the same location. Phase 1 step 5 validates this. |
| Old commit SHAs remain reachable on GitHub | Acknowledged. Force-push reduces visibility but GitHub keeps unreferenced commits for ~90 days. Flipping BoredBot to private is the only way to fully prevent friend from seeing old vault content. |
| Force-push breaks any other clone (CrudusLiv's other devices) | Each device must `git fetch && git reset --hard origin/main` after Phase 3. Document this in the cutover step. |
| `.claude/settings.json` contains a secret we missed | Already scanned: contains only hook command strings using `$CLAUDE_PROJECT_DIR`. No secrets. Re-verify before Phase 2 commit. |

## Out of scope

- Migrating the heartbeat scheduler or any Windows Task Scheduler entries (those reference local paths only; no change needed).
- Rewriting `.claude/data/` state (gitignored already).
- Setting up CI on either repo.
- Writing the new `README.md` content in detail — spec says "short setup guide"; exact wording handled in the implementation plan.
- Any cleanup inside the vault repo itself (e.g. pruning old daily logs) — out of scope.
