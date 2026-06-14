from __future__ import annotations
import importlib
import importlib.util
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

KL = timezone(timedelta(hours=8))

# Stub modules that heartbeat.py imports at module level to avoid side effects.
_STUBS = [
    "_env",
    "core", "core.deadlines", "core.habits", "core.imminent",
    "core.inbox", "core.llm", "core.snapshot",
    "core.gcal_sync", "core.vault_state_writer", "core.dashboard",
    "core.dashboard_state", "core.thread_chat",
    "tray", "tray.config",
    "security", "security.sanitize",
    "vault", "vault.daily",
    "agents", "agents.deadline_tracker", "agents.progress_monitor", "agents.study_planner",
    "agents.state",
]
_PREV = {}
for _name in _STUBS:
    if _name not in sys.modules:
        _PREV[_name] = None
        sys.modules[_name] = MagicMock()

# heartbeat.py is a script that lives alongside the heartbeat/ package.
# importlib loads it by path so the package directory doesn't shadow it.
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(ROOT))
_spec = importlib.util.spec_from_file_location("heartbeat_script", SCRIPTS / "heartbeat.py")
heartbeat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(heartbeat)

# Remove stubs so they don't pollute sys.modules for other test files.
for _name in list(_PREV):
    sys.modules.pop(_name, None)


def test_in_active_hours_respects_config_start():
    cfg = {"active_hours_start": "10:00", "active_hours_end": "22:00", "features": {}}
    with patch.object(heartbeat._tray_config, "load", return_value=cfg):
        t = datetime(2026, 1, 1, 9, 30, tzinfo=KL)   # 09:30 < start 10:00
        assert heartbeat.in_active_hours(now=t) is False


def test_in_active_hours_respects_config_end():
    cfg = {"active_hours_start": "09:00", "active_hours_end": "20:00", "features": {}}
    with patch.object(heartbeat._tray_config, "load", return_value=cfg):
        t = datetime(2026, 1, 1, 21, 0, tzinfo=KL)   # 21:00 >= end 20:00
        assert heartbeat.in_active_hours(now=t) is False


def test_in_active_hours_falls_back_on_config_error():
    with patch.object(heartbeat._tray_config, "load", side_effect=Exception("no config")):
        t = datetime(2026, 1, 1, 10, 0, tzinfo=KL)   # within default (9, 22)
        assert heartbeat.in_active_hours(now=t) is True
