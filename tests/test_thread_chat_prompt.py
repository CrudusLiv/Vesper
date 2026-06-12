"""Tests for thread_chat_prompt.py — system + user prompt builders."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))


class TestSystemPrompt:
    def test_deadline_kind_includes_rider(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_vault.parent.parent))
        from heartbeat import thread_chat_prompt as mod
        importlib.reload(mod)
        result = mod.system_prompt({"kind": "deadline"})
        assert "deadline" in result.lower()
        assert "assignment" in result.lower()

    def test_lecture_kind_includes_path(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_vault.parent.parent))
        from heartbeat import thread_chat_prompt as mod
        importlib.reload(mod)
        result = mod.system_prompt({"kind": "lecture", "path": "lectures/cs101/week1.md"})
        assert "lectures/cs101/week1.md" in result

    def test_lecture_kind_missing_path_uses_default(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_vault.parent.parent))
        from heartbeat import thread_chat_prompt as mod
        importlib.reload(mod)
        result = mod.system_prompt({"kind": "lecture"})
        assert "lectures/" in result

    def test_unknown_kind_has_base_but_no_rider(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_vault.parent.parent))
        from heartbeat import thread_chat_prompt as mod
        importlib.reload(mod)
        result = mod.system_prompt({"kind": "other"})
        assert "CrudusLiv" in result
        assert "assignment" not in result
        assert "lecture" not in result.lower().replace("lectures/", "")

    def test_soul_md_appended_when_present(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_vault.parent.parent))
        (tmp_vault / "SOUL.md").write_text("# Test Soul\nBe chill.", encoding="utf-8")
        from heartbeat import thread_chat_prompt as mod
        importlib.reload(mod)
        result = mod.system_prompt({"kind": "deadline"})
        assert "Test Soul" in result
        assert "Be chill." in result

    def test_no_soul_md_still_returns_prompt(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_vault.parent.parent))
        from heartbeat import thread_chat_prompt as mod
        importlib.reload(mod)
        result = mod.system_prompt({"kind": "deadline"})
        assert len(result) > 50


class TestUserPrompt:
    def _mod(self):
        from heartbeat import thread_chat_prompt as mod
        return mod

    def test_no_context_omits_thread_header(self):
        mod = self._mod()
        msg = {"content": "What is this deadline?", "author_name": "CrudusLiv"}
        result = mod.user_prompt(msg, [])
        assert "What is this deadline?" in result
        assert "Thread context" not in result

    def test_with_context_includes_header_and_messages(self):
        mod = self._mod()
        msg = {"content": "Still confused", "author_name": "CrudusLiv"}
        context = [
            {"author_name": "CrudusLiv", "content": "What's due?", "is_self": 0},
            {"author_name": "Vesper", "content": "Lab 2 due Friday", "is_self": 1},
        ]
        result = mod.user_prompt(msg, context)
        assert "Thread context" in result
        assert "Vesper" in result
        assert "Lab 2 due Friday" in result
        assert "Still confused" in result

    def test_vesper_label_for_self_messages(self):
        mod = self._mod()
        context = [{"author_name": "bot", "content": "Hello", "is_self": 1}]
        result = mod.user_prompt({"content": "ok"}, context)
        assert "Vesper" in result

    def test_context_message_over_500_chars_truncated(self):
        mod = self._mod()
        context = [{"author_name": "u", "content": "x" * 600, "is_self": 0}]
        result = mod.user_prompt({"content": "ok"}, context)
        assert "..." in result

    def test_latest_message_over_2000_chars_truncated(self):
        mod = self._mod()
        result = mod.user_prompt({"content": "y" * 2500}, [])
        assert "..." in result

    def test_newlines_in_context_flattened(self):
        mod = self._mod()
        context = [{"author_name": "u", "content": "line1\nline2", "is_self": 0}]
        result = mod.user_prompt({"content": "ok"}, context)
        # context messages have newlines replaced with spaces
        lines = result.splitlines()
        context_lines = [l for l in lines if "line1" in l]
        assert context_lines
        assert "\n" not in context_lines[0]
