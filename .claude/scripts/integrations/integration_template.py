"""Template for new integrations. Copy this file, rename, replace TODOs.

Pattern: each integration is a Python module that exports `handle_query(argv)`
so `query.py` can dispatch to it. Internal API calls are wrapped behind named
functions; the LLM never sees credentials or makes raw HTTP calls."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _env  # noqa: F401, E402

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])


# TODO: replace with the env vars / files this integration actually needs.
def _is_configured() -> bool:
    # Example: return bool(os.environ.get("MYSERVICE_TOKEN"))
    return False


# TODO: implement query functions for this integration.
def list_recent(days: int = 7) -> list[dict]:
    if not _is_configured():
        return []
    return []


def handle_query(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="query.py myintegration")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    p = sub.add_parser("recent")
    p.add_argument("--days", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    json_out = getattr(args, "json", False) or "--json" in argv

    rows = list_recent(args.days)
    if json_out:
        print(json.dumps(rows, indent=2, default=str))
    else:
        for r in rows:
            print(r)
    return 0


if __name__ == "__main__":
    sys.exit(handle_query(sys.argv[1:]))
