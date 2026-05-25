"""Path safety gate for vault actions.

Every function in vault/actions.py calls validate() before touching disk.
The validator enforces the USER.md hard limits in code, not in the prompt,
so a misread LLM cannot bypass them.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
VAULT = PROJECT_DIR / "Dynamous" / "Memory"

_FORBIDDEN_PREFIXES = ("_trash", "finance")


def validate(path: str) -> Path:
    """Resolve `path` under VAULT, raising ValueError on any unsafe input.

    Rules:
      - Must be relative (no leading slash, no Windows drive letter)
      - Must not contain `..` segments
      - After resolving symlinks, must remain under VAULT
      - Must not target `_trash/` (restores go through undo only)
      - Must not target `finance/` (finance writes live in _handle_finance)
    """
    if not path or not isinstance(path, str):
        raise ValueError("path must be a non-empty string")

    # Absolute path or drive letter
    if path.startswith("/") or path.startswith("\\"):
        raise ValueError(f"path must be relative, got {path!r}")
    if len(path) >= 2 and path[1] == ":":
        raise ValueError(f"path must be relative, got {path!r}")

    parts = Path(path).parts
    if ".." in parts:
        raise ValueError(f"path must not contain '..', got {path!r}")

    top = parts[0] if parts else ""
    if top in _FORBIDDEN_PREFIXES:
        raise ValueError(f"path under {top}/ is off-limits, got {path!r}")

    # Re-read CLAUDE_PROJECT_DIR at call time so test fixtures work
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
    vault = project_dir / "Dynamous" / "Memory"

    candidate = (vault / path).resolve()
    vault_resolved = vault.resolve()
    try:
        candidate.relative_to(vault_resolved)
    except ValueError:
        raise ValueError(f"path resolves outside vault: {path!r}")

    return candidate
