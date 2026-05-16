"""GitHub integration -- read-only via PyGithub.

Powers the code-reviewer skill: lists recent commits on assignment repos
and surfaces diffs for review. Set GITHUB_ASSIGNMENT_REPOS=owner/repo1,owner/repo2
in .env to scope which repos the code reviewer touches."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _env  # noqa: F401, E402

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])


def _get_client():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set in .env", file=sys.stderr)
        return None
    try:
        from github import Auth, Github
    except ImportError:
        print("PyGithub not installed: py -m pip install -r .claude/requirements.txt", file=sys.stderr)
        return None
    return Github(auth=Auth.Token(token))


def _assignment_repos() -> list[str]:
    raw = os.environ.get("GITHUB_ASSIGNMENT_REPOS", "").strip()
    if not raw:
        return []
    return [r.strip() for r in raw.split(",") if r.strip()]


def _resolve_targets(g, repos: list[str] | None) -> list[str]:
    if repos:
        return repos
    target = _assignment_repos()
    if target:
        return target
    return [r.full_name for r in g.get_user().get_repos()][:20]


def recent_pushes(days: int = 7, repos: list[str] | None = None) -> list[dict]:
    g = _get_client()
    if not g:
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict] = []
    for full_name in _resolve_targets(g, repos):
        try:
            repo = g.get_repo(full_name)
            for commit in repo.get_commits(since=since):
                out.append({
                    "repo": full_name,
                    "sha": commit.sha[:7],
                    "author": commit.commit.author.name,
                    "date": commit.commit.author.date.isoformat(),
                    "message": commit.commit.message.splitlines()[0][:120],
                })
        except Exception as exc:
            out.append({"repo": full_name, "error": str(exc)})
    out.sort(key=lambda c: c.get("date", ""), reverse=True)
    return out


def pr_list(repo_name: str | None = None) -> list[dict]:
    g = _get_client()
    if not g:
        return []
    out: list[dict] = []
    targets = [repo_name] if repo_name else _resolve_targets(g, None)
    for full_name in targets:
        try:
            repo = g.get_repo(full_name)
            for pr in repo.get_pulls(state="open"):
                out.append({
                    "repo": full_name,
                    "number": pr.number,
                    "title": pr.title,
                    "author": pr.user.login,
                    "url": pr.html_url,
                    "updated": pr.updated_at.isoformat(),
                })
        except Exception as exc:
            out.append({"repo": full_name, "error": str(exc)})
    return out


def diff(repo_name: str, sha: str) -> dict:
    g = _get_client()
    if not g:
        return {"error": "no client"}
    try:
        repo = g.get_repo(repo_name)
        commit = repo.get_commit(sha)
        return {
            "repo": repo_name,
            "sha": commit.sha,
            "author": commit.commit.author.name,
            "date": commit.commit.author.date.isoformat(),
            "message": commit.commit.message,
            "files": [
                {
                    "filename": f.filename,
                    "status": f.status,
                    "additions": f.additions,
                    "deletions": f.deletions,
                    "patch": (f.patch or "")[:8000],
                }
                for f in commit.files
            ],
        }
    except Exception as exc:
        return {"repo": repo_name, "sha": sha, "error": str(exc)}


def handle_query(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="query.py github")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    p_rp = sub.add_parser("recent-pushes")
    p_rp.add_argument("--days", type=int, default=7)
    p_pr = sub.add_parser("pr-list")
    p_pr.add_argument("repo", nargs="?")
    p_d = sub.add_parser("diff")
    p_d.add_argument("repo")
    p_d.add_argument("sha")
    args = parser.parse_args(argv)
    json_out = args.json

    if args.subcommand == "recent-pushes":
        rows = recent_pushes(days=args.days)
        if json_out:
            print(json.dumps(rows, indent=2, default=str))
        else:
            for r in rows:
                if "error" in r:
                    print(f"!! {r['repo']}: {r['error']}")
                else:
                    print(f"{r['date'][:10]}  {r['repo']}  {r['sha']}  {r['author']}: {r['message']}")
    elif args.subcommand == "pr-list":
        rows = pr_list(args.repo)
        if json_out:
            print(json.dumps(rows, indent=2, default=str))
        else:
            for r in rows:
                if "error" in r:
                    print(f"!! {r['repo']}: {r['error']}")
                else:
                    print(f"#{r['number']:<5}  {r['repo']}  by {r['author']}  -- {r['title']}")
    elif args.subcommand == "diff":
        result = diff(args.repo, args.sha)
        print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(handle_query(sys.argv[1:]))
