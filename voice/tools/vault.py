"""Vault tools: read notes (safe), append/create notes (require confirmation)."""
from __future__ import annotations
from pathlib import Path
import voice  # noqa: F401

_ROOT = Path(__file__).resolve().parents[2]
_VAULT = _ROOT / "Dynamous" / "Memory"


def read_note(path: str) -> str:
    full = (_VAULT / path).resolve()
    try:
        full.relative_to(_VAULT.resolve())
    except ValueError:
        return f"Error: {path!r} is outside the vault."
    if not full.exists():
        return f"File not found: {path}"
    return full.read_text(encoding="utf-8")


def append_note(path: str, text: str) -> str:
    from vault import actions  # type: ignore
    try:
        r = actions.append(path, text)
        return f"Appended {r['appended_chars']} chars to {path}."
    except Exception as exc:
        return f"Error: {exc}"


def create_note(path: str, text: str) -> str:
    from vault import actions  # type: ignore
    try:
        r = actions.create(path, text)
        return f"Created {path} ({r['bytes']} bytes)."
    except Exception as exc:
        return f"Error: {exc}"
