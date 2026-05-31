# Tray Task Scheduler Control — Design Spec
_2026-05-31_

## Goal

Make the tray app the single control surface for all background tasks. Task Scheduler still owns the clocks; the tray reads and writes Task Scheduler state via `schtasks.exe` (no elevation, no PowerShell).

## Scope

Three Task Scheduler tasks brought under tray control:
- `secondbrain-heartbeat` — every 30 min, 09:00–22:00
- `secondbrain-reflect` — daily 08:00 (currently disabled)
- `secondbrain-index` — every 10 min

The Discord bot is already managed by the tray via `process_mgr`. No changes there.

---

## Architecture

### New: `tray/task_scheduler.py`

Single module, four functions. All use `schtasks.exe` via `subprocess.run` — no PowerShell, no elevation required for current-user tasks.

```python
TASKS = {
    "heartbeat": "secondbrain-heartbeat",
    "reflect":   "secondbrain-reflect",
    "index":     "secondbrain-index",
}

def get_status(task_name: str) -> dict:
    # schtasks /query /fo CSV /tn <task_name> /v
    # Returns: {enabled: bool, status: str, last_run: str, next_run: str}

def set_enabled(task_name: str, enabled: bool) -> bool:
    # schtasks /change /tn <task_name> /enable|/disable
    # Returns True on success

def run_now(task_name: str) -> bool:
    # schtasks /run /tn <task_name>
    # Returns True on success

def set_interval(task_name: str, minutes: int) -> bool:
    # schtasks /change /tn <task_name> /ri <minutes>
    # Heartbeat only — other tasks have fixed schedules
    # Returns True on success
```

`get_status` is called on a 5-second poll (same cadence as the existing bot status poll in `_poll_status`). The Schedule tab refreshes its task cards each tick via the same `root.after(3000, ...)` loop.

---

## Settings Window Changes

### Features tab

Remove `reflect` from `_FEATURE_META`. It is a Task Scheduler task, not a heartbeat feature gate.

Remaining entries (no logic changes):
- Inbox Processing
- GCal Sync
- Thread Chat
- Toast Notifications

### Schedule tab

Replace the current read-only interval label with three task cards. Each card shows:

```
[ Task Label ]   ● <status>   Last: <X>m ago   Next: <Y>m
  [enable toggle]   [interval input + save]   [Run Now button]
```

- **Heartbeat card**: enable toggle, editable interval field (default 30, reads from `tray_config`), "Run Now" button, last/next run.
- **Memory Reflect card**: enable toggle, last/next run. No interval input (fixed daily trigger).
- **Index card**: enable toggle, last/next run. No interval input.

Active hours inputs and auto-start toggle remain below the task cards, unchanged.

Toggling enabled calls `task_scheduler.set_enabled()`. Saving interval calls `task_scheduler.set_interval()` and updates `tray_config`. "Run Now" calls `task_scheduler.run_now()`.

### Status tab

No changes.

---

## Config Changes (`tray/config.py`)

- Remove `"reflect"` from `_DEFAULT["features"]`.
- Add `"heartbeat_interval_minutes": 30` to `_DEFAULT` (top-level, not under features).

The interval value in config is the UI default. Task Scheduler is authoritative at runtime — if they diverge (e.g., task was edited outside the tray), the Schedule tab shows the Task Scheduler value and overwrites config on next save.

---

## Error Handling

- `get_status` returns `{enabled: False, status: "unknown", last_run: "N/A", next_run: "N/A"}` on any subprocess failure.
- `set_enabled` / `run_now` / `set_interval` show a brief error label in the UI on failure (e.g., task not found). They do not raise.
- All schtasks calls have a 5-second timeout to avoid hanging the UI thread.

---

## What Does NOT Change

- `heartbeat.py` — no changes. Reflect is controlled by the Task Scheduler task state, not a heartbeat feature gate.
- `process_mgr.py` — no changes.
- `tray_app.py` — no changes (the "Run Heartbeat Now" menu item calls subprocess directly; that stays as-is).
- `install_tasks.ps1` — no changes. Task registration is still manual/one-time.

---

## Files Changed

| File | Change |
|------|--------|
| `.claude/scripts/tray/task_scheduler.py` | **New** |
| `.claude/scripts/tray/settings_window.py` | Schedule tab rebuilt, reflect removed from Features |
| `.claude/scripts/tray/config.py` | Remove `reflect` feature, add `heartbeat_interval_minutes` |
| `tests/test_tray_config.py` | Update to remove reflect assertion |
