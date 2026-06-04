"""_too_soon() must bypass the catch-up guard when HEARTBEAT_FORCE=1 so the
/api/heartbeat/run manual trigger always fires (added in the workers-in-docker
cycle). Run from the project root:
    py -m pytest .claude/scripts/heartbeat/test_too_soon_force.py -v

`heartbeat.py` (the script) and `heartbeat/` (the package) coexist in
.claude/scripts/, so a plain `import heartbeat` resolves to the *package*. Load
the script file directly via importlib so the test reaches the script's
_too_soon without touching production import semantics.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts" / "integrations"))

import _env  # noqa: F401, E402 -- loads .env

_SCRIPT = PROJECT_DIR / ".claude" / "scripts" / "heartbeat.py"
_spec = importlib.util.spec_from_file_location("heartbeat_main", _SCRIPT)
heartbeat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(heartbeat)


def test_too_soon_false_when_forced(monkeypatch):
    monkeypatch.setenv("HEARTBEAT_FORCE", "1")
    # Even with a brand-new recent tick in state, force wins.
    monkeypatch.setattr(heartbeat.snapshot, "load_state", lambda: {"timestamp": time.time()})
    assert heartbeat._too_soon() is False


def test_too_soon_consults_state_when_not_forced(monkeypatch):
    monkeypatch.delenv("HEARTBEAT_FORCE", raising=False)
    monkeypatch.setattr(heartbeat.snapshot, "load_state", lambda: {"timestamp": time.time()})
    assert heartbeat._too_soon() is True
