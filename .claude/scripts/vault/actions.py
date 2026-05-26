"""Vault action verbs. Each function:

  1. Calls paths.validate() before touching disk.
  2. Performs exactly one filesystem operation.
  3. Appends a transaction-log entry (with undo_state) on success.
  4. Raises a stdlib exception on failure (no logging on failure).

Caller (chat handler) translates exceptions into user-facing replies.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from vault import paths, transactions

_KL = timezone(timedelta(hours=8))


def append(path: str, text: str) -> dict:
    """Append `text` to existing `path`. Raises FileNotFoundError if missing."""
    target = paths.validate(path)
    if not target.exists():
        raise FileNotFoundError(path)
    original_length = target.stat().st_size
    with target.open("a", encoding="utf-8") as f:
        f.write(text)
    transactions.append({
        "action": "append",
        "args": {"path": path, "text": text},
        "undo_state": {"original_length": original_length},
    })
    return {"path": path, "appended_chars": len(text)}


def create(path: str, content: str) -> dict:
    """Create new file at `path`. Raises FileExistsError if path exists."""
    target = paths.validate(path)
    if target.exists():
        raise FileExistsError(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    transactions.append({
        "action": "create",
        "args": {"path": path, "content": content},
        "undo_state": {},
    })
    return {"path": path, "bytes": len(content.encode("utf-8"))}


def edit(path: str, find: str, replace: str) -> dict:
    """Replace exactly one occurrence of `find` with `replace`. Raises ValueError if 0 or >1."""
    target = paths.validate(path)
    if not target.exists():
        raise FileNotFoundError(path)
    content = target.read_text(encoding="utf-8")
    count = content.count(find)
    if count != 1:
        raise ValueError(f"edit requires exactly 1 match, got {count} matches for {find!r}")
    target.write_text(content.replace(find, replace, 1), encoding="utf-8")
    transactions.append({
        "action": "edit",
        "args": {"path": path, "find": find, "replace": replace},
        "undo_state": {"find_was": find, "replace_was": replace},
    })
    return {"path": path}


def rename(path: str, new_name: str) -> dict:
    """Rename within the same directory. `new_name` is a bare filename."""
    if "/" in new_name or "\\" in new_name:
        raise ValueError(f"new_name must be a bare filename, got {new_name!r}")
    src = paths.validate(path)
    if not src.exists():
        raise FileNotFoundError(path)
    new_rel = (Path(path).parent / new_name).as_posix()
    dst = paths.validate(new_rel)
    if dst.exists():
        raise FileExistsError(new_rel)
    src.rename(dst)
    transactions.append({
        "action": "rename",
        "args": {"path": path, "new_name": new_name},
        "undo_state": {"old_path": path, "new_path": new_rel},
    })
    return {"path": new_rel}


def move(path: str, dest_dir: str) -> dict:
    """Move file to `dest_dir` (relative directory under vault)."""
    src = paths.validate(path)
    if not src.exists():
        raise FileNotFoundError(path)
    new_rel = (Path(dest_dir) / Path(path).name).as_posix()
    dst = paths.validate(new_rel)
    if dst.exists():
        raise FileExistsError(new_rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    transactions.append({
        "action": "move",
        "args": {"path": path, "dest_dir": dest_dir},
        "undo_state": {"from": path, "to": new_rel},
    })
    return {"path": new_rel}


def delete(path: str) -> dict:
    """Soft-delete: move file to _trash/YYYY-MM-DD/. Never calls unlink."""
    src = paths.validate(path)
    if not src.exists():
        raise FileNotFoundError(path)
    vault_root = paths.vault()
    today = datetime.now(_KL).strftime("%Y-%m-%d")
    trash_dir = vault_root / "_trash" / today
    trash_dir.mkdir(parents=True, exist_ok=True)
    dst = trash_dir / src.name
    i = 1
    while dst.exists():
        dst = trash_dir / f"{src.stem}_{i}{src.suffix}"
        i += 1
    shutil.move(str(src), str(dst))
    trash_rel = dst.relative_to(vault_root).as_posix()
    transactions.append({
        "action": "delete",
        "args": {"path": path},
        "undo_state": {"trash_path": trash_rel, "original_path": path},
    })
    return {"path": path, "trash_path": trash_rel}


def list_dir(directory: str) -> dict:
    """Return non-recursive entry names in `directory`. No log entry.

    list_dir cannot use paths.validate() because that helper assumes a file
    path; we enforce the same safety rules inline.
    """
    if directory.startswith("/") or directory.startswith("\\") or (len(directory) >= 2 and directory[1] == ":"):
        raise ValueError(f"path must be relative, got {directory!r}")
    parts = Path(directory).parts
    if ".." in parts:
        raise ValueError(f"path must not contain '..', got {directory!r}")
    top = parts[0] if parts else ""
    if paths._is_forbidden_prefix(top):
        raise ValueError(f"path under {top}/ is off-limits, got {directory!r}")

    vault_root = paths.vault()
    target = (vault_root / directory).resolve()
    try:
        target.relative_to(vault_root.resolve())
    except ValueError as exc:
        raise ValueError(f"path resolves outside vault: {directory!r}") from exc
    if not target.is_dir():
        raise NotADirectoryError(directory)
    entries = sorted(p.name for p in target.iterdir())
    return {"directory": directory, "entries": entries}
