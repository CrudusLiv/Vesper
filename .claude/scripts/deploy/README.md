# Deployment (Phase 9)

Local-only Windows install. One installer, four scheduled tasks, no services.

## Install

Open PowerShell **as Administrator** (Register-ScheduledTask requires it, even for user-scoped tasks):

```powershell
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\install_tasks.ps1
```

Idempotent — re-running replaces any existing `secondbrain-*` task.

| Task | Trigger | Action |
|---|---|---|
| `secondbrain-heartbeat` | Daily 09:00 KL, repeats every 30 min for 13 hours | `py heartbeat.py` |
| `secondbrain-reflect`   | Daily 08:00 KL                                  | `py memory_reflect.py` |
| `secondbrain-index`     | Every 10 min, all day                           | `py memory/memory_index.py` |
| `secondbrain-discord`   | At logon, restart on failure                    | `start_discord_bot.ps1` |

## Inspect

```powershell
Get-ScheduledTask -TaskName 'secondbrain-*' |
    Format-Table TaskName, State, LastRunTime, NextRunTime
Get-ScheduledTaskInfo -TaskName 'secondbrain-heartbeat'
```

Tail logs:

```powershell
Get-Content .claude\data\logs\discord-*.log -Wait -Tail 20
```

## Uninstall

```powershell
pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\uninstall_tasks.ps1
```

Removes all four tasks. Logs and vault data are preserved — delete manually if wanted.

## Notes

- `heartbeat.py` self-gates via `in_active_hours()`; the 13-hour repetition window is belt-and-suspenders.
- The Discord wrapper has two restart layers: inner `while ($true)` loop with exponential backoff on fast-fails, plus Task Scheduler `RestartCount=999` if PowerShell itself dies.
- Tasks run as the current user with `RunLevel Limited` so Windows Toast notifications can surface on the desktop.
