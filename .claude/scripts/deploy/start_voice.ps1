#Requires -Version 5.1
<#
.SYNOPSIS
Long-running launcher for the Vesper voice assistant.

.DESCRIPTION
Task Scheduler runs this at logon. Restarts the voice app if it crashes
(fast crash loops are throttled). Logs to .claude/data/logs/voice-YYYY-MM-DD.log.

Two layers of restart resilience:
  1. This loop catches process exit and relaunches after a short backoff.
  2. Task Scheduler restarts the whole PowerShell process if this script
     itself dies (RestartCount=999, RestartInterval=1min in install_tasks.ps1).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'

$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..\..").Path
$LogsDir    = Join-Path $ProjectDir '.claude\data\logs'
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

$py = (Get-Command py.exe -ErrorAction Stop).Source

$MinBackoff     = 5
$MaxBackoff     = 300
$FastFailWindow = 60
$backoff        = $MinBackoff

while ($true) {
    $logFile = Join-Path $LogsDir ("voice-{0}.log" -f (Get-Date -Format 'yyyy-MM-dd'))
    $stamp   = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $logFile -Value "[$stamp] launcher: starting voice app"

    $start = Get-Date
    try {
        & $py -u -m voice --wakeword 2>&1 | ForEach-Object {
            $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $_
            Add-Content -Path $logFile -Value $line
        }
        $exit = $LASTEXITCODE
    } catch {
        Add-Content -Path $logFile -Value "[$(Get-Date -Format 'HH:mm:ss')] launcher: exception $_"
        $exit = 1
    }

    $uptime = ((Get-Date) - $start).TotalSeconds
    $stamp  = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $logFile -Value ("[$stamp] launcher: voice exited code={0} uptime={1:N0}s" -f $exit, $uptime)

    if ($uptime -lt $FastFailWindow) {
        $backoff = [Math]::Min($backoff * 2, $MaxBackoff)
        Add-Content -Path $logFile -Value "[$stamp] launcher: fast-fail, backoff=${backoff}s"
    } else {
        $backoff = $MinBackoff
    }

    Start-Sleep -Seconds $backoff
}
