from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Literal

import psutil


def _proj() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])


def _pid_file() -> Path:
    return _proj() / ".claude" / "data" / "bot.pid"


def _read_pid() -> int | None:
    try:
        return int(_pid_file().read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def bot_status() -> Literal["running", "stopped"]:
    pid = _read_pid()
    if pid is None:
        return "stopped"
    return "running" if _pid_alive(pid) else "stopped"


def start_bot() -> None:
    """Launch the bot via the VBS restart wrapper. No-op if already running."""
    pid = _read_pid()
    if pid is not None and _pid_alive(pid):
        return
    proj = _proj()
    vbs = proj / ".claude" / "scripts" / "deploy" / "start_discord_bot.vbs"
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(proj)}
    proc = subprocess.Popen(["wscript.exe", str(vbs)], cwd=str(proj), env=env)
    pf = _pid_file()
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(str(proc.pid), encoding="utf-8")


def stop_bot() -> None:
    """Terminate the restart wrapper and its full process tree, then remove PID file."""
    pid = _read_pid()
    if pid is None:
        return
    if _pid_alive(pid):
        try:
            proc = psutil.Process(pid)
            children = proc.children(recursive=True)
            proc.terminate()
            for child in children:
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    try:
        _pid_file().unlink()
    except FileNotFoundError:
        pass
