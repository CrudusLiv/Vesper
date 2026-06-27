"""Confirmation gate for tools that can modify the vault.

Tools listed in config.json `requires_confirmation` must be approved
interactively before brain.py dispatches them.
"""
from __future__ import annotations

import json


def requires_confirmation(tool_name: str) -> bool:
    """Return True if this tool name needs user approval before running."""
    from voice import config as cfg
    gate: list[str] = cfg.load().get("requires_confirmation", [])
    return tool_name in gate


def prompt_confirm(tool_name: str, args: dict) -> bool:
    """Print a confirm prompt; return True if user says yes."""
    args_str = json.dumps(args, ensure_ascii=False)
    if len(args_str) > 80:
        args_str = args_str[:77] + "..."
    print(f"\n  [confirm] {tool_name}({args_str})")
    try:
        answer = input("  proceed? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")
