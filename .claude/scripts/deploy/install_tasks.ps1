#Requires -Version 5.1
<#
.SYNOPSIS
Registers the four Second Brain background tasks in Windows Task Scheduler.

.DESCRIPTION
Idempotent: re-running replaces existing tasks instead of erroring.

  secondbrain-heartbeat   Daily 09:00 KL, repeats every 30 min for 13 hours
  secondbrain-reflect     Daily 08:00 KL
  secondbrain-index       Every 10 min, all day
  secondbrain-discord     At logon, restart on failure (long-running)

All tasks run as the current interactive user so Windows Toast notifications
surface on the desktop.

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File .claude\scripts\deploy\install_tasks.ps1
#>
[CmdletBinding()]
param(
    [string]$User = $env:USERNAME
)

$ErrorActionPreference = 'Stop'

# Register-ScheduledTask requires elevation even when registering as the
# current user. Fail fast with a clear message rather than half-registering.
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "ERROR: This script must be run from an elevated PowerShell." -ForegroundColor Red
    Write-Host "Right-click PowerShell -> 'Run as administrator', then re-run:" -ForegroundColor Red
    Write-Host "  pwsh -ExecutionPolicy Bypass -File $PSCommandPath" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

$ProjectDir   = (Resolve-Path "$PSScriptRoot\..\..\..").Path
$ScriptsDir   = Join-Path $ProjectDir '.claude\scripts'
$LogsDir      = Join-Path $ProjectDir '.claude\data\logs'
$VoiceLaunch   = Join-Path $PSScriptRoot 'start_voice.vbs'

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

# Resolve py launcher up front so the user sees the failure here, not deep
# inside a task that silently exits 9009.
$py = Get-Command py.exe -ErrorAction SilentlyContinue
if (-not $py) {
    throw "py.exe not found on PATH. Install Python from python.org so the launcher is available."
}
$PyPath = $py.Source

# Common task settings: allow on battery, restart on failure, don't stop after
# arbitrary deadline. The Discord task uses a stricter restart policy below.
function New-CommonSettings {
    New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)
}

function Register-Task {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [ciminstance[]]$Trigger,
        [Parameter(Mandatory)] [ciminstance]$Action,
        [Parameter(Mandatory)] [ciminstance]$Settings,
        [string]$Description
    )
    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        Write-Host "  replacing existing task: $Name"
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    } else {
        Write-Host "  creating new task: $Name"
    }
    Register-ScheduledTask `
        -TaskName $Name `
        -Trigger $Trigger `
        -Action $Action `
        -Settings $Settings `
        -Description $Description `
        -User $User `
        -RunLevel Limited | Out-Null
}

Write-Host "Installing Second Brain scheduled tasks..."
Write-Host "  project: $ProjectDir"
Write-Host "  user:    $User"
Write-Host "  py:      $PyPath"
Write-Host ""

# ----- secondbrain-heartbeat: every 30 min, 09:00-22:00 KL -----
# Interval now configurable via web UI Settings panel. Task Scheduler enforces
# the time window; heartbeat.py also self-gates via in_active_hours().
#
# PS 5.1 quirk: on a fresh -Daily trigger, .Repetition is $null, so writing
# .Repetition.Interval throws "property cannot be found on this object". The
# workaround: build a -Once trigger with the repetition we want, then copy
# its (already-instantiated) Repetition object onto the daily trigger.
$hbRepeatSrc = New-ScheduledTaskTrigger -Once -At '09:00' `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Hours 13)
$hbTrigger = New-ScheduledTaskTrigger -Daily -At '09:00'
$hbTrigger.Repetition = $hbRepeatSrc.Repetition
$HbLaunch = Join-Path $PSScriptRoot 'run_heartbeat.vbs'
$hbAction = New-ScheduledTaskAction `
    -Execute 'wscript.exe' `
    -Argument "`"$HbLaunch`"" `
    -WorkingDirectory $ProjectDir
Register-Task `
    -Name 'secondbrain-heartbeat' `
    -Trigger $hbTrigger `
    -Action $hbAction `
    -Settings (New-CommonSettings) `
    -Description 'Second Brain heartbeat tick. Gathers integration state, drafts replies, fires Toast notifications.'

# ----- secondbrain-reflect: daily 08:00 KL -----
$reflectTrigger = New-ScheduledTaskTrigger -Daily -At '08:00'
$reflectAction = New-ScheduledTaskAction `
    -Execute $PyPath `
    -Argument "`"$ScriptsDir\memory_reflect.py`"" `
    -WorkingDirectory $ProjectDir
Register-Task `
    -Name 'secondbrain-reflect' `
    -Trigger $reflectTrigger `
    -Action $reflectAction `
    -Settings (New-CommonSettings) `
    -Description 'Second Brain daily reflection. Promotes durable items from yesterday daily log into MEMORY.md and rolls HABITS.md.'

# ----- secondbrain-index: every 10 min, all day -----
# [TimeSpan]::MaxValue serialises to an out-of-range ISO duration that Task
# Scheduler rejects. Use the same daily-trigger + copied-repetition pattern as
# the heartbeat: the daily re-trigger at midnight restarts the 24-hour window,
# so effectively every 10 min forever.
$idxRepeatSrc = New-ScheduledTaskTrigger -Once -At '00:00' `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration (New-TimeSpan -Hours 24)
$idxTrigger = New-ScheduledTaskTrigger -Daily -At '00:00'
$idxTrigger.Repetition = $idxRepeatSrc.Repetition
$IdxLaunch = Join-Path $PSScriptRoot 'run_index.vbs'
$idxAction = New-ScheduledTaskAction `
    -Execute 'wscript.exe' `
    -Argument "`"$IdxLaunch`"" `
    -WorkingDirectory $ProjectDir
Register-Task `
    -Name 'secondbrain-index' `
    -Trigger $idxTrigger `
    -Action $idxAction `
    -Settings (New-CommonSettings) `
    -Description 'Second Brain vector indexer. Re-embeds vault files whose hash changed since last run.'

# ----- secondbrain-voice: at logon, long-running, restart on failure -----
$voiceTrigger = New-ScheduledTaskTrigger -AtLogOn -User $User
$voiceAction = New-ScheduledTaskAction `
    -Execute 'wscript.exe' `
    -Argument "`"$VoiceLaunch`"" `
    -WorkingDirectory $ProjectDir
$voiceSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)
Register-Task `
    -Name 'secondbrain-voice' `
    -Trigger $voiceTrigger `
    -Action $voiceAction `
    -Settings $voiceSettings `
    -Description 'Vesper voice assistant. Starts orb UI + wakeword listener at logon. Wrapper auto-restarts on crashes.'

Write-Host ""
Write-Host "Installed. Inspect with:"
Write-Host "  Get-ScheduledTask -TaskName 'secondbrain-*' | Format-Table TaskName,State,LastRunTime,NextRunTime"
Write-Host ""
Write-Host "Tail logs from:"
Write-Host "  $LogsDir"
