"""Tests for vault/paths.py — the safety gate every action calls."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make .claude/scripts importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

from vault import paths  # noqa: E402


def test_validate_accepts_simple_relative_path(tmp_vault):
    result = paths.validate("notes/x.md")
    assert result == tmp_vault / "notes" / "x.md"


def test_validate_rejects_absolute_path(tmp_vault):
    with pytest.raises(ValueError, match="must be relative"):
        paths.validate("/etc/passwd")


def test_validate_rejects_windows_drive(tmp_vault):
    with pytest.raises(ValueError, match="must be relative"):
        paths.validate("C:/Windows/system32")


def test_validate_rejects_parent_traversal(tmp_vault):
    with pytest.raises(ValueError, match=r"\.\."):
        paths.validate("../outside.md")


def test_validate_rejects_resolved_escape_via_symlink(tmp_vault, tmp_path):
    # Symlink notes/escape -> tmp_path (outside vault). validate must catch this
    # via .resolve() comparison even when the literal path looks clean.
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_vault / "notes" / "escape"
    (tmp_vault / "notes").mkdir(exist_ok=True)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform/user")
    with pytest.raises(ValueError, match="outside vault"):
        paths.validate("notes/escape/x.md")


def test_validate_rejects_trash(tmp_vault):
    with pytest.raises(ValueError, match="_trash"):
        paths.validate("_trash/2026-05-25/x.md")


def test_validate_rejects_finance(tmp_vault):
    with pytest.raises(ValueError, match="finance"):
        paths.validate("finance/2026-05.md")
