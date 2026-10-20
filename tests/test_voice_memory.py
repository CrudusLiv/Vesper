"""Tests for voice/memory.py::load_context() -- the vault files concatenated
into every voice conversation's system prompt (see voice/brain.py::_build_system)."""
from __future__ import annotations

from voice import memory


def test_load_context_empty_when_no_vault(monkeypatch):
    monkeypatch.setattr("voice.config.get_vault_dir", lambda: None)
    assert memory.load_context() == ""


def test_load_context_includes_user_memory_and_about(tmp_path, monkeypatch):
    (tmp_path / "USER.md").write_text("User profile.", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text("Durable memory.", encoding="utf-8")
    (tmp_path / "ABOUT.md").write_text("- prefers tea", encoding="utf-8")
    monkeypatch.setattr("voice.config.get_vault_dir", lambda: tmp_path)
    ctx = memory.load_context()
    assert "User profile." in ctx
    assert "Durable memory." in ctx
    assert "prefers tea" in ctx


def test_load_context_skips_missing_files(tmp_path, monkeypatch):
    (tmp_path / "MEMORY.md").write_text("Durable memory.", encoding="utf-8")
    monkeypatch.setattr("voice.config.get_vault_dir", lambda: tmp_path)
    ctx = memory.load_context()
    assert ctx == "Durable memory."
