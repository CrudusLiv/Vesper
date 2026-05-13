---
name: code-reviewer
description: First-pass code review on a GitHub commit or PR from CrudusLiv's assignment repos. Drafts feedback to drafts/active/ — never comments on GitHub directly.
---

# Code Reviewer (first pass)

Review a single commit (by SHA) or an open PR on a repo listed in `GITHUB_ASSIGNMENT_REPOS`. Output is a draft markdown file CrudusLiv reads, decides on, and (if useful) pastes to GitHub manually.

## When to invoke

- CrudusLiv pastes a SHA or PR link from an assignment repo.
- Heartbeat detects a new push to a repo in `GITHUB_ASSIGNMENT_REPOS` (Phase 6).
- CrudusLiv asks "review this commit" / "review my latest push".

## Procedure

1. **Verify the repo is in scope.** Read `GITHUB_ASSIGNMENT_REPOS` from env (it's loaded by `_env.py`). If the target isn't in the list, stop and tell CrudusLiv. **Do not** review random repos.

2. **Fetch the diff:**
   ```
   py .claude/scripts/query.py github diff <owner/repo> <sha> --json
   ```
   The result includes commit metadata + per-file `patch` (truncated to 8 KB per file).

3. **Apply the rubric** at `references/review-rubric.md` — load on demand with the Read tool. Don't memorise the whole rubric upfront.

4. **Write the draft** to:
   ```
   Dynamous/Memory/drafts/active/<YYYY-MM-DD>_codereview_<repo-slug>_<sha7>.md
   ```
   `repo-slug` = repo name, lowercase, hyphenated. `sha7` = first 7 chars of the commit SHA.

   Format:
   ```markdown
   ---
   type: codereview
   source_id: github:<owner>/<repo>@<sha>
   created: <ISO timestamp>
   status: active
   ---

   ## Original Commit

   <repo>@<sha7> by <author> on <date>

   > <commit message, first line>

   ## Files changed

   - <filename>  (+<additions> -<deletions>)
   - ...

   ## Review

   ### Correctness

   - **bug** `path/to/file.py:42` — <specific finding>
   - **smell** `path/to/file.py:67` — <looks suspicious, here's why>

   ### Edge cases

   - <input that would break this — empty? boundary? concurrent?>

   ### Style and clarity

   - **nit** `path/to/file.py:15` — <variable name, function length, comment quality>

   ### Complexity

   - <Big-O note if there's an obvious issue, otherwise "no concerns">

   ## Suggested follow-up

   1. <most important next step>
   2. <second most important>
   3. <if applicable>
   ```

5. **Append a line** to today's `daily/YYYY-MM-DD.md`:
   `[HH:MM] Code review draft -> drafts/active/<filename>`

## Calibration for degree-level CS

- **Bug**: definitely wrong. Will fail on some realistic input.
- **Smell**: probably fine, worth a second look.
- **Nit**: style only — separate section, keep brief.
- Catch: off-by-one, naive complexity (O(n²) where O(n) suffices), unhandled empty/None, missing input validation, mutable default args, silent `except: pass`.
- Don't critique architecture as if it were enterprise software. Coursework is small by design.
- If the code is fine, say so plainly: "No issues found in correctness or edge cases. Style is consistent."

## Hard rules

- **Never post the review to GitHub.** No comment, no review, no PR action. The agent is forbidden from commenting on PRs (USER.md hard limits). The draft is read-only output for the user.
- **Never review repos not in `GITHUB_ASSIGNMENT_REPOS`.** If CrudusLiv asks for a review on something outside that list, refuse and explain.
- **Never grade.** "This is correct" / "This has a bug" — never "this is a B+". Professors grade.

## Don't

- Don't lecture on best practices that aren't relevant to the diff in front of you.
- Don't repeat findings — one mention per location.
- Don't include the entire diff in the draft. Cite filename:line; the user can `git show` for context.
