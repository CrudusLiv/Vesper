"""Tests for Obsidian deep-link injection in handler.py."""
from __future__ import annotations

import sys
from pathlib import Path


def _import_handler(monkeypatch, vault_name="Memory"):
    monkeypatch.setenv("OBSIDIAN_VAULT_NAME", vault_name)
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude" / "scripts"))
    sys.path.insert(0, str(repo_root / ".claude"))
    # Must import after env var is set, reload to pick up new value.
    if "chat.handler" in sys.modules:
        del sys.modules["chat.handler"]
    # Also delete chat module so it reimports handler
    if "chat" in sys.modules:
        del sys.modules["chat"]
    from chat import handler
    return handler


def test_obsidian_uri_encodes_slashes(monkeypatch):
    h = _import_handler(monkeypatch)
    uri = h._obsidian_uri("lectures/DIP215/2026-05-11_file.md")
    assert uri == "obsidian://open?vault=Memory&file=lectures%2FDIP215%2F2026-05-11_file.md"


def test_obsidian_uri_respects_vault_name_env(monkeypatch):
    h = _import_handler(monkeypatch, vault_name="MyVault")
    uri = h._obsidian_uri("notes/NOTES.md")
    assert uri == "obsidian://open?vault=MyVault&file=notes%2FNOTES.md"


def test_obsidian_uri_encodes_vault_name_with_spaces(monkeypatch):
    h = _import_handler(monkeypatch, vault_name="My Notes")
    uri = h._obsidian_uri("daily/2026-05-21.md")
    assert uri == "obsidian://open?vault=My%20Notes&file=daily%2F2026-05-21.md"


def test_inject_converts_backtick_md_path(monkeypatch):
    h = _import_handler(monkeypatch)
    text = "see `lectures/DIP215/file.md` for details"
    result = h._inject_obsidian_links(text)
    assert result == (
        "see [lectures/DIP215/file.md]"
        "(obsidian://open?vault=Memory&file=lectures%2FDIP215%2Ffile.md)"
        " for details"
    )


def test_inject_converts_multiple_paths(monkeypatch):
    h = _import_handler(monkeypatch)
    text = "see `lectures/a.md` and `notes/b.md`"
    result = h._inject_obsidian_links(text)
    assert "[lectures/a.md](obsidian://open?vault=Memory&file=lectures%2Fa.md)" in result
    assert "[notes/b.md](obsidian://open?vault=Memory&file=notes%2Fb.md)" in result


def test_inject_leaves_non_md_backticks_alone(monkeypatch):
    h = _import_handler(monkeypatch)
    text = "run `pytest tests/` to verify"
    result = h._inject_obsidian_links(text)
    assert result == text


def test_inject_leaves_text_without_backticks_alone(monkeypatch):
    h = _import_handler(monkeypatch)
    text = "nothing to linkify here"
    assert h._inject_obsidian_links(text) == text
