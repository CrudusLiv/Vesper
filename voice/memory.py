"""Vault-backed memory: USER.md + MEMORY.md context, fact write/remove."""
from __future__ import annotations
from pathlib import Path
import voice  # noqa: F401

_ROOT = Path(__file__).resolve().parents[1]
_VAULT = _ROOT / "Dynamous" / "Memory"


def load_context() -> str:
    parts = []
    for fname in ("USER.md", "MEMORY.md"):
        p = _VAULT / fname
        if p.exists():
            text = p.read_text(encoding="utf-8").strip()
            if text:
                parts.append(text)
    return "\n\n---\n\n".join(parts)


def remember(key: str, value: str) -> str:
    from vault import actions  # type: ignore
    try:
        actions.append("MEMORY.md", f"\n- {key}: {value}")
        return f"Remembered: {key}: {value}"
    except Exception as exc:
        return f"Error saving fact: {exc}"


def forget(key: str) -> str:
    from vault import actions, paths  # type: ignore
    try:
        target = paths.validate("MEMORY.md")
        content = target.read_text(encoding="utf-8")
        line = next(
            (l for l in content.splitlines() if l.strip().startswith(f"- {key}:")),
            None,
        )
        if not line:
            return f"No fact with key: {key}"
        for needle in (line + "\n", line):
            if needle in content:
                actions.edit("MEMORY.md", find=needle, replace="")
                return f"Removed: {key}"
        return f"Could not remove: {key}"
    except Exception as exc:
        return f"Error: {exc}"


def log_session(text: str) -> None:
    from vault import actions  # type: ignore
    from datetime import datetime, timedelta, timezone
    kl = timezone(timedelta(hours=8))
    today = datetime.now(kl).strftime("%Y-%m-%d")
    try:
        actions.append(f"daily/{today}.md", f"\n{text}")
    except Exception:
        pass
