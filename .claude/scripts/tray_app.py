#!/usr/bin/env python3
"""Vesper system tray app.

Run: py .claude/scripts/tray_app.py
"""
from __future__ import annotations
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / ".claude"))

import integrations._env  # noqa: F401 — loads .env

import pystray
from tray import config as tray_config, icon as tray_icon, process_mgr
from tray.settings_window import open_settings

_POLL_INTERVAL = 5  # seconds
_icon_ref: pystray.Icon | None = None


def _build_menu() -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem(
            lambda item: f"Bot: {process_mgr.bot_status().capitalize()}",
            None, enabled=False,
        ),
        pystray.MenuItem(
            lambda item: _hb_label(),
            None, enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Settings", lambda: open_settings()),
        pystray.MenuItem("Run Heartbeat Now", _run_heartbeat_now),
        pystray.MenuItem(
            lambda item: "Stop Bot" if process_mgr.bot_status() == "running" else "Start Bot",
            _toggle_bot,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _quit),
    )


def _hb_label() -> str:
    try:
        from heartbeat import snapshot
        snap = snapshot.load_state() or {}
        ts = snap.get("heartbeat_ran_at") or snap.get("timestamp") or 0
        if ts:
            mins = int((time.time() - float(ts)) // 60)
            return f"HB: {mins}m ago"
    except Exception:
        pass
    return "HB: unknown"


def _toggle_bot() -> None:
    if process_mgr.bot_status() == "running":
        process_mgr.stop_bot()
    else:
        process_mgr.start_bot()


def _run_heartbeat_now() -> None:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_DIR)}
    subprocess.Popen(
        [sys.executable, str(PROJECT_DIR / ".claude" / "scripts" / "heartbeat.py")],
        cwd=str(PROJECT_DIR), env=env,
    )


def _quit() -> None:
    global _icon_ref
    if process_mgr.bot_status() == "running":
        process_mgr.stop_bot()
    if _icon_ref:
        _icon_ref.stop()


def _poll_loop(icon: pystray.Icon) -> None:
    while True:
        status = process_mgr.bot_status()
        icon.icon = tray_icon.make_icon("ok" if status == "running" else "error")
        icon.update_menu()
        time.sleep(_POLL_INTERVAL)


def main() -> None:
    global _icon_ref
    cfg = tray_config.load()

    if cfg.get("auto_start_bot", True):
        process_mgr.start_bot()

    status = process_mgr.bot_status()
    img = tray_icon.make_icon("ok" if status == "running" else "error")
    icon = pystray.Icon("VesperTray", img, "Vesper", _build_menu())
    _icon_ref = icon

    threading.Thread(target=_poll_loop, args=(icon,), daemon=True).start()

    icon.run()


if __name__ == "__main__":
    main()
