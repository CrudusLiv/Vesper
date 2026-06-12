"""Container scheduler — drives the periodic second-brain jobs that ran as
Windows Scheduled Tasks on the host (heartbeat, memory-index, reflect).

One always-on loop (compose service `scheduler`). Each job runs as a subprocess
so a crash or hang can't kill the loop. Each iteration also checks for the
heartbeat trigger sentinel dropped by POST /api/heartbeat/run and, if present,
runs a forced tick (HEARTBEAT_FORCE=1) then removes it.

The job's own in_active_hours()/_too_soon() guards stay authoritative for
scheduled runs — the scheduler just fires; the job decides whether to act."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import schedule

LOOP_SLEEP_SECONDS = 5
KL = timezone(timedelta(hours=8))


def _proj() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[1])


def _heartbeat_script() -> Path:
    return _proj() / ".claude" / "scripts" / "heartbeat.py"


def _index_script() -> Path:
    return _proj() / ".claude" / "scripts" / "memory" / "memory_index.py"


def _reflect_script() -> Path:
    return _proj() / ".claude" / "scripts" / "memory_reflect.py"


def _sentinel() -> Path:
    return _proj() / ".claude" / "data" / "state" / "heartbeat-trigger"


def _reflect_stamp() -> Path:
    return _proj() / ".claude" / "data" / "state" / "reflect-last-run"


def _reflect_ran_today() -> bool:
    stamp = _reflect_stamp()
    if not stamp.exists():
        return False
    return stamp.read_text(encoding="utf-8").strip() == datetime.now(KL).strftime("%Y-%m-%d")


def _mark_reflect_ran() -> None:
    stamp = _reflect_stamp()
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(datetime.now(KL).strftime("%Y-%m-%d"), encoding="utf-8")


def run_reflect_if_needed() -> None:
    if _reflect_ran_today():
        return
    rc = run_job(_reflect_script())
    if rc == 0:
        _mark_reflect_ran()


def run_job(script: Path, *, env_extra: dict | None = None) -> int:
    """Run one job script as a subprocess. Returns its exit code (-1 if it
    failed to launch). Never raises — the loop must survive any job."""
    env = {**os.environ}
    if env_extra:
        env.update(env_extra)
    print(f"[scheduler] running {script.name}", flush=True)
    try:
        proc = subprocess.run([sys.executable, str(script)], cwd=str(_proj()), env=env)
        print(f"[scheduler] {script.name} exited {proc.returncode}", flush=True)
        return proc.returncode
    except Exception as exc:  # noqa: BLE001 -- loop must not die
        print(f"[scheduler] {script.name} failed to launch: {exc}", file=sys.stderr, flush=True)
        return -1


def check_sentinel() -> bool:
    """If the heartbeat trigger sentinel exists, run a forced tick and delete it.
    Returns True if a forced tick ran. Unlink happens before the run so a long
    tick can't be re-triggered by its own sentinel."""
    path = _sentinel()
    if not path.exists():
        return False
    try:
        path.unlink()
    except OSError:
        pass
    run_job(_heartbeat_script(), env_extra={"HEARTBEAT_FORCE": "1"})
    return True


def _load_heartbeat_interval() -> int:
    """Load heartbeat interval from tray_settings.json, default to 30."""
    proj = _proj()
    settings_file = proj / ".claude" / "data" / "tray_settings.json"
    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        return int(data.get("heartbeat_interval_minutes", 30))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 30


def setup_schedule(interval_minutes: int = 30) -> None:
    schedule.every(interval_minutes).minutes.do(run_job, _heartbeat_script())
    schedule.every(10).minutes.do(run_job, _index_script())
    schedule.every(60).minutes.do(run_reflect_if_needed)


def main() -> int:
    interval = _load_heartbeat_interval()
    setup_schedule(interval)
    print(f"[scheduler] started; heartbeat/{interval}m, index/10m, reflect/once-per-day", flush=True)
    # Run reflect immediately on startup in case today's hasn't happened yet.
    run_reflect_if_needed()
    while True:
        schedule.run_pending()
        check_sentinel()
        time.sleep(LOOP_SLEEP_SECONDS)
    return 0  # unreachable; keeps type checkers happy


if __name__ == "__main__":
    sys.exit(main())
