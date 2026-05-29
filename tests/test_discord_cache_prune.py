"""Discord cache prune — retention tests."""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path


def _import_module():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude" / "scripts" / "integrations"))
    import discord_int
    return discord_int


def _seed_db(db_path: Path, rows: list[dict]) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, channel_id TEXT, channel_name TEXT,
            guild_id TEXT, guild_name TEXT, is_dm INTEGER, author_id TEXT,
            author_name TEXT, is_self INTEGER, is_bot INTEGER,
            content TEXT, created_at REAL, fetched_at REAL,
            referenced_message_id TEXT, referenced_author_id TEXT
        );
    """)
    for r in rows:
        conn.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r["id"], r.get("channel_id", "ch"), r.get("channel_name", "general"),
                r.get("guild_id", "g"), r.get("guild_name", "Server"), r.get("is_dm", 0),
                r.get("author_id", "111"), r.get("author_name", "alice"),
                r.get("is_self", 0), r.get("is_bot", 0), r.get("content", "hello"),
                r["created_at"], r.get("fetched_at", r["created_at"] + 1),
                r.get("referenced_message_id"), r.get("referenced_author_id"),
            ),
        )
    conn.commit()
    conn.close()


def _count_rows(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    n = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    return n


def test_prune_deletes_old_rows_and_keeps_recent(tmp_path):
    di = _import_module()
    db = tmp_path / "cache.db"
    now = time.time()
    old_ts = now - 8 * 86400   # 8 days ago — over retention window
    new_ts = now - 1 * 86400   # 1 day ago — inside retention window
    _seed_db(db, [
        {"id": "old1", "created_at": old_ts},
        {"id": "new1", "created_at": new_ts},
    ])
    deleted = di.prune(retention_days=7, db_path=db)
    assert deleted == 1
    assert _count_rows(db) == 1
    conn = sqlite3.connect(str(db))
    remaining = conn.execute("SELECT id FROM messages").fetchone()[0]
    conn.close()
    assert remaining == "new1"


def test_prune_returns_zero_when_nothing_expired(tmp_path):
    di = _import_module()
    db = tmp_path / "cache.db"
    now = time.time()
    _seed_db(db, [
        {"id": "r1", "created_at": now - 3600},
        {"id": "r2", "created_at": now - 2 * 86400},
    ])
    deleted = di.prune(retention_days=7, db_path=db)
    assert deleted == 0
    assert _count_rows(db) == 2


def test_prune_db_remains_queryable_after_vacuum(tmp_path):
    di = _import_module()
    db = tmp_path / "cache.db"
    now = time.time()
    _seed_db(db, [
        {"id": "old1", "created_at": now - 8 * 86400},
        {"id": "new1", "created_at": now - 3600},
    ])
    di.prune(retention_days=7, db_path=db)
    # VACUUM must not corrupt the DB — re-querying should succeed
    assert _count_rows(db) == 1


def test_prune_empty_db_returns_zero(tmp_path):
    di = _import_module()
    db = tmp_path / "cache.db"
    _seed_db(db, [])
    deleted = di.prune(retention_days=7, db_path=db)
    assert deleted == 0
