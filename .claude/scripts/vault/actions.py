"""Vault action verbs. Each function:

  1. Calls paths.validate() before touching disk.
  2. Performs exactly one filesystem operation.
  3. Appends a transaction-log entry (with undo_state) on success.
  4. Raises a stdlib exception on failure (no logging on failure).

Caller (chat handler) translates exceptions into user-facing replies.
"""
from __future__ import annotations

from pathlib import Path

from vault import paths, transactions


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
