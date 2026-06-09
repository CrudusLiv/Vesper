"""Tests for heartbeat.py daily-log wiring (commit + alert lines)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Stub modules that heartbeat.py imports at module level to avoid side effects.
_STUBS = [
    "_env",
    "heartbeat.deadlines", "heartbeat.imminent", "heartbeat.inbox",
    "heartbeat.notify", "heartbeat.toast",
    "heartbeat.gcal_sync",
    "heartbeat.vault_state_writer", "heartbeat.dashboard",
    "heartbeat.dashboard_state",
    "security", "security.sanitize",
]
_PREV = {}
for _name in _STUBS:
    if _name not in sys.modules:
        _PREV[_name] = None
        sys.modules[_name] = MagicMock()

# heartbeat.py is a script that lives alongside the heartbeat/ package.
# importlib loads it by path so the package directory doesn't shadow it.
_spec = importlib.util.spec_from_file_location("heartbeat_script", SCRIPTS / "heartbeat.py")
heartbeat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(heartbeat)

# Remove stubs so they don't pollute sys.modules for other test files.
for _name in list(_PREV):
    sys.modules.pop(_name, None)

import vault.daily as daily_mod  # noqa: E402


# --- execute() alert wiring ---

def test_execute_writes_alert_line(tmp_vault, monkeypatch):
    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))
    heartbeat.dashboard.notify = MagicMock()

    heartbeat.execute({"notifications": [
        {"title": "New GitHub push", "body": "CrudusLiv/Vesper — fix auth bug"},
    ]})

    assert written == ["Alert: New GitHub push — CrudusLiv/Vesper — fix auth bug"]


def test_execute_writes_multiple_alert_lines(tmp_vault, monkeypatch):
    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))
    heartbeat.dashboard.notify = MagicMock()

    heartbeat.execute({"notifications": [
        {"title": "A", "body": "b"},
        {"title": "C", "body": "d"},
    ]})

    assert "Alert: A — b" in written
    assert "Alert: C — d" in written


def test_execute_empty_notifications_no_write(monkeypatch):
    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))
    heartbeat.execute({"notifications": []})
    assert written == []


# --- _log_commits() ---

def test_log_commits_personal(tmp_vault, monkeypatch):
    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))
    monkeypatch.delenv("GITHUB_ASSIGNMENT_REPOS", raising=False)

    heartbeat._log_commits({"new_pushes": [
        {"repo": "CrudusLiv/myrepo", "message": "update readme"},
    ]})

    assert written == ["Commit [personal]: CrudusLiv/myrepo — update readme"]


def test_log_commits_assignment(tmp_vault, monkeypatch):
    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))
    monkeypatch.setenv("GITHUB_ASSIGNMENT_REPOS", "CrudusLiv/Vesper")

    heartbeat._log_commits({"new_pushes": [
        {"repo": "CrudusLiv/Vesper", "message": "fix auth bug"},
    ]})

    assert written == ["Commit [assignment]: CrudusLiv/Vesper — fix auth bug"]


def test_log_commits_empty_no_write(monkeypatch):
    written: list[str] = []
    monkeypatch.setattr(daily_mod, "append_line", lambda line: written.append(line))
    heartbeat._log_commits({"new_pushes": []})
    assert written == []
