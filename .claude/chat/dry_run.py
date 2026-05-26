"""Stdin-driven harness for the #vesper pipeline.

Usage:
    py .claude/chat/dry_run.py "delete notes/test.md"
    echo "what's due this week?" | py .claude/chat/dry_run.py

Bypasses Discord entirely. Calls handler.process_message with a synthetic
user/channel pair and prints the reply. Use this for manual end-to-end
verification before deploying handler changes."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / ".claude"))

from chat import handler  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        text = " ".join(argv[1:])
    else:
        text = sys.stdin.read().strip()
    if not text:
        print("usage: dry_run.py <message>   OR   echo <message> | dry_run.py", file=sys.stderr)
        return 2

    print(f"--- INPUT ---\n{text}\n")
    reply = handler.process_message(user_id="dry_run_user", channel_id="dry_run_channel", text=text)
    print(f"--- REPLY ---\n{reply}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
