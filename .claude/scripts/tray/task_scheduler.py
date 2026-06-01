from __future__ import annotations

import csv
import io
import subprocess

_TIMEOUT = 5  # seconds per schtasks call

# The tray runs under pythonw.exe, which has no console. Without this flag each
# schtasks call spawns a fresh, visible cmd window (and the allocation is slow,
# stalling the Tk event loop). CREATE_NO_WINDOW is Windows-only; 0 elsewhere.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

TASK_NAMES: dict[str, str] = {
    "heartbeat": "secondbrain-heartbeat",
    "reflect":   "secondbrain-reflect",
    "index":     "secondbrain-index",
}


def get_status(task_name: str) -> dict:
    """Return {enabled, status, last_run, next_run} for a Task Scheduler task.
    Returns a fallback dict on any failure."""
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/v", "/tn", task_name],
            capture_output=True, text=True, timeout=_TIMEOUT,
            creationflags=_NO_WINDOW,
        )
        if result.returncode != 0:
            return _fallback()
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        if not rows:
            return _fallback()
        row = rows[0]
        state = row.get("Scheduled Task State", "").strip()
        return {
            "enabled": state.lower() == "enabled",
            "status":   row.get("Status",        "unknown").strip(),
            "last_run": row.get("Last Run Time",  "N/A").strip(),
            "next_run": row.get("Next Run Time",  "N/A").strip(),
        }
    except Exception:
        return _fallback()


def set_enabled(task_name: str, enabled: bool) -> bool:
    """Enable or disable a task. Returns True on success."""
    flag = "/enable" if enabled else "/disable"
    result = subprocess.run(
        ["schtasks", "/change", "/tn", task_name, flag],
        capture_output=True, timeout=_TIMEOUT,
        creationflags=_NO_WINDOW,
    )
    return result.returncode == 0


def run_now(task_name: str) -> bool:
    """Trigger an immediate run. Returns True on success."""
    result = subprocess.run(
        ["schtasks", "/run", "/tn", task_name],
        capture_output=True, timeout=_TIMEOUT,
        creationflags=_NO_WINDOW,
    )
    return result.returncode == 0


def set_interval(task_name: str, minutes: int) -> bool:
    """Change the repetition interval. Returns True on success."""
    result = subprocess.run(
        ["schtasks", "/change", "/tn", task_name, "/ri", str(minutes)],
        capture_output=True, timeout=_TIMEOUT,
        creationflags=_NO_WINDOW,
    )
    return result.returncode == 0


def _fallback() -> dict:
    return {"enabled": False, "status": "unknown", "last_run": "N/A", "next_run": "N/A"}
