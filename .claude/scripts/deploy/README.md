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

## Running under Docker (NAS target)

The host Scheduled Tasks above remain the live system. The same four jobs also
exist as compose services in `vesper/` for the eventual NAS migration — they are
**opt-in** behind a `workers` profile, so plain `docker compose up` brings only
the API + web frontend and changes nothing on the host.

```powershell
# From vesper/ — bring up the full stack including the workers:
docker compose --profile workers up -d --build

# Tail the bot / scheduler:
docker compose logs -f discord scheduler
```

| Service | Replaces host task | Notes |
|---|---|---|
| `discord` | `secondbrain-discord` | The bot daemon; vault mounted read-write |
| `scheduler` | `secondbrain-heartbeat`, `-index`, `-reflect` | One loop fires all three at their cadences |

`POST /api/heartbeat/run` (Bearer `API_SECRET`) queues a forced tick: the backend
drops `.claude/data/state/heartbeat-trigger`; the scheduler runs it within ~5s.

Cutover (stopping the host tasks in favour of the containers) is a deliberate
later step done on the NAS — not part of this build.
