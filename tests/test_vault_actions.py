"""Tests for vault/actions.py — one per verb. Builds out incrementally."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

from vault import actions, transactions  # noqa: E402


@pytest.fixture
def isolated_log(tmp_data, monkeypatch):
    """Redirect the transaction log to tmp_data so tests don't write to real log."""
    log = tmp_data / "vault_transactions.jsonl"
    monkeypatch.setattr(transactions, "LOG_PATH", log)
    return log


def _read_log(log: Path) -> list[dict]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------- append ----------

def test_append_adds_text_to_existing_file(tmp_vault, isolated_log):
    target = tmp_vault / "notes" / "x.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("hello\n", encoding="utf-8")

    result = actions.append("notes/x.md", "world")
    assert target.read_text(encoding="utf-8") == "hello\nworld"
    assert result["path"] == "notes/x.md"

    log = _read_log(isolated_log)
    assert len(log) == 1
    assert log[0]["action"] == "append"
    assert log[0]["undo_state"]["original_length"] == len("hello\n")


def test_append_errors_when_file_missing(tmp_vault, isolated_log):
    with pytest.raises(FileNotFoundError):
        actions.append("notes/missing.md", "world")
    assert _read_log(isolated_log) == []  # no log entry on failure


# ---------- create ----------

def test_create_writes_new_file(tmp_vault, isolated_log):
    result = actions.create("notes/new.md", "fresh content")
    target = tmp_vault / "notes" / "new.md"
    assert target.read_text(encoding="utf-8") == "fresh content"
    assert result["path"] == "notes/new.md"

    log = _read_log(isolated_log)
    assert len(log) == 1
    assert log[0]["action"] == "create"


def test_create_errors_when_path_exists(tmp_vault, isolated_log):
    target = tmp_vault / "notes" / "x.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("already here", encoding="utf-8")
    with pytest.raises(FileExistsError):
        actions.create("notes/x.md", "would overwrite")
    assert _read_log(isolated_log) == []


def test_create_creates_parent_directories(tmp_vault, isolated_log):
    actions.create("research/new-area/note.md", "content")
    target = tmp_vault / "research" / "new-area" / "note.md"
    assert target.read_text(encoding="utf-8") == "content"
