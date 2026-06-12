"""Tests for thread_chat.py — in-thread chat carve-out."""
from __future__ import annotations

import importlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))


def _make_db(path: Path, messages: list[dict]) -> Path:
    db = path / "discord_cache.db"
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            channel_id TEXT,
            content TEXT,
            author_id TEXT,
            author_name TEXT,
            created_at REAL,
            is_dm INTEGER DEFAULT 0,
            is_self INTEGER DEFAULT 0,
            is_bot INTEGER DEFAULT 0
        )
    """)
    for m in messages:
        conn.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                m["id"], m.get("channel_id", "t1"), m.get("content", ""),
                m.get("author_id", "u1"), m.get("author_name", "user"),
                m.get("created_at", time.time()),
                m.get("is_dm", 0), m.get("is_self", 0), m.get("is_bot", 0),
            ),
        )
    conn.commit()
    conn.close()
    return db


# ──────────────────────── _load_state / _save_state ───────────────────────────

class TestStateHelpers:
    def test_load_missing_returns_defaults(self, tmp_data):
        from heartbeat.thread_chat import _load_state
        state = _load_state(tmp_data / "noexist.json")
        assert state == {"last_tick": None, "seen_message_ids": []}

    def test_load_corrupt_returns_defaults(self, tmp_data):
        from heartbeat.thread_chat import _load_state
        p = tmp_data / "corrupt.json"
        p.write_text("not json", encoding="utf-8")
        assert _load_state(p) == {"last_tick": None, "seen_message_ids": []}

    def test_save_writes_file(self, tmp_data):
        from heartbeat.thread_chat import _save_state
        _save_state(tmp_data / "state.json", {"seen_message_ids": []}, time.time())
        assert (tmp_data / "state.json").exists()

    def test_save_evicts_entries_older_than_ttl(self, tmp_data):
        from heartbeat.thread_chat import _save_state
        now = time.time()
        state = {
            "seen_message_ids": [
                {"id": "old", "t": now - 25 * 3600},
                {"id": "new", "t": now},
            ]
        }
        _save_state(tmp_data / "state.json", state, now)
        saved = json.loads((tmp_data / "state.json").read_text())
        ids = [s["id"] for s in saved["seen_message_ids"]]
        assert "old" not in ids
        assert "new" in ids

    def test_save_sets_last_tick(self, tmp_data):
        from heartbeat.thread_chat import _save_state
        _save_state(tmp_data / "state.json", {"seen_message_ids": []}, time.time())
        saved = json.loads((tmp_data / "state.json").read_text())
        assert saved["last_tick"] is not None


# ──────────────────────────── scan_and_reply ──────────────────────────────────

class TestScanAndReply:
    def _ds_state(self, threads: dict) -> dict:
        return {"deadlines": {k: {"thread_id": v} for k, v in threads.items()}}

    def test_no_threads_returns_zero(self, tmp_data):
        with patch("heartbeat.dashboard_state.load", return_value={}):
            from heartbeat import thread_chat as mod
            importlib.reload(mod)
            db = _make_db(tmp_data, [])
            result = mod.scan_and_reply(db, user_id="u1", state_path=tmp_data / "state.json")
        assert result == 0

    def test_missing_db_returns_zero(self, tmp_data):
        ds = self._ds_state({"lab1": "t1"})
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            from heartbeat import thread_chat as mod
            importlib.reload(mod)
            result = mod.scan_and_reply(
                tmp_data / "noexist.db", user_id="u1", state_path=tmp_data / "state.json",
            )
        assert result == 0

    def test_already_seen_message_skipped(self, tmp_data):
        ds = self._ds_state({"lab1": "t1"})
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            from heartbeat import thread_chat as mod
            importlib.reload(mod)
        db = _make_db(tmp_data, [
            {"id": "m1", "channel_id": "t1", "content": "hi", "author_id": "u1",
             "created_at": time.time()},
        ])
        sp = tmp_data / "state.json"
        sp.write_text(
            json.dumps({"seen_message_ids": [{"id": "m1", "t": time.time()}]}),
            encoding="utf-8",
        )
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            with patch("heartbeat.llm.call", return_value="reply"):
                with patch("heartbeat.dashboard.notify", return_value={"id": "r"}):
                    result = mod.scan_and_reply(db, user_id="u1", state_path=sp)
        assert result == 0

    def test_new_message_generates_and_posts_reply(self, tmp_data):
        ds = self._ds_state({"lab1": "t1"})
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            from heartbeat import thread_chat as mod
            importlib.reload(mod)
        db = _make_db(tmp_data, [
            {"id": "m2", "channel_id": "t1", "content": "can you explain?",
             "author_id": "u1", "created_at": time.time()},
        ])
        sp = tmp_data / "state.json"
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            with patch("heartbeat.llm.call", return_value="Sure."):
                with patch("heartbeat.dashboard.notify", return_value={"id": "r"}) as mock_notify:
                    result = mod.scan_and_reply(db, user_id="u1", state_path=sp, now=time.time())
        assert result == 1
        mock_notify.assert_called_once()

    def test_reply_uses_deadline_kind(self, tmp_data):
        ds = self._ds_state({"lab1": "t1"})
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            from heartbeat import thread_chat as mod
            importlib.reload(mod)
        db = _make_db(tmp_data, [
            {"id": "m3", "channel_id": "t1", "content": "when is it due?",
             "author_id": "u1", "created_at": time.time()},
        ])
        notified_kinds = []
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            with patch("heartbeat.llm.call", return_value="Friday."):
                with patch("heartbeat.dashboard.notify",
                           side_effect=lambda k, p, **kw: notified_kinds.append(k) or {"id": "r"}):
                    mod.scan_and_reply(db, user_id="u1", state_path=tmp_data / "state.json")
        assert notified_kinds == ["deadline_reply"]

    def test_llm_failure_marks_seen_does_not_raise(self, tmp_data):
        ds = self._ds_state({"lab1": "t1"})
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            from heartbeat import thread_chat as mod
            importlib.reload(mod)
        db = _make_db(tmp_data, [
            {"id": "m4", "channel_id": "t1", "content": "hello",
             "author_id": "u1", "created_at": time.time()},
        ])
        sp = tmp_data / "state.json"
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            with patch("heartbeat.llm.call", side_effect=RuntimeError("LLM down")):
                result = mod.scan_and_reply(db, user_id="u1", state_path=sp, now=time.time())
        assert result == 0
        state = json.loads(sp.read_text())
        assert any(s["id"] == "m4" for s in state["seen_message_ids"])

    def test_bot_messages_ignored(self, tmp_data):
        ds = self._ds_state({"lab1": "t1"})
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            from heartbeat import thread_chat as mod
            importlib.reload(mod)
        db = _make_db(tmp_data, [
            {"id": "bot1", "channel_id": "t1", "content": "I am a bot",
             "author_id": "u1", "is_bot": 1, "created_at": time.time()},
        ])
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            with patch("heartbeat.llm.call", return_value="reply"):
                with patch("heartbeat.dashboard.notify", return_value={"id": "r"}):
                    result = mod.scan_and_reply(db, user_id="u1", state_path=tmp_data / "state.json")
        assert result == 0

    def test_lecture_thread_uses_lecture_reply_kind(self, tmp_data):
        ds = {
            "deadlines": {},
            "lectures": {"lectures/cs101/week1.md": {"thread_id": "lt1"}},
        }
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            from heartbeat import thread_chat as mod
            importlib.reload(mod)
        db = _make_db(tmp_data, [
            {"id": "lm1", "channel_id": "lt1", "content": "explain big-O",
             "author_id": "u1", "created_at": time.time()},
        ])
        notified_kinds = []
        with patch("heartbeat.dashboard_state.load", return_value=ds):
            with patch("heartbeat.llm.call", return_value="Big-O is..."):
                with patch("heartbeat.dashboard.notify",
                           side_effect=lambda k, p, **kw: notified_kinds.append(k) or {"id": "r"}):
                    mod.scan_and_reply(db, user_id="u1", state_path=tmp_data / "state.json")
        assert notified_kinds == ["lecture_reply"]
