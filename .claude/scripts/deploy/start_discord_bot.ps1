#Requires -Version 5.1
<#
.SYNOPSIS
Long-running launcher for the Second Brain Discord bot.

.DESCRIPTION
Task Scheduler runs this at logon. It restarts the bot if it crashes (a fast
crash loop is throttled). Logs to .claude/data/logs/discord-YYYY-MM-DD.log.

Two layers of restart resilience:
  1. This loop catches process exit and relaunches after a short backoff.
  2. Task Scheduler restarts the *whole* PowerShell process if this script
     itself dies (RestartCount=999, RestartInterval=1min in install_tasks.ps1).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'

$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..\..").Path
# Phase 7 bot: caches messages (Phase 4.1 behavior) AND replies to DMs from
# DISCORD_USER_ID. The Phase 4.1 cache-only bot at scripts/integrations/
# discord_int.py is superseded -- the chat bot does both.
$BotScript  = Join-Path $ProjectDir '.claude\chat\discord_bot.py'
$LogsDir    = Join-Path $ProjectDir '.claude\data\logs'
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

$py = (Get-Command py.exe -ErrorAction Stop).Source

# Backoff state: if the bot exits within $FastFailWindow seconds, sleep longer
# next time. Reset once the bot stays up.
$MinBackoff      = 5
$MaxBackoff      = 300
$FastFailWindow  = 60
$backoff         = $MinBackoff

while ($true) {
    $logFile = Join-Path $LogsDir ("discord-{0}.log" -f (Get-Date -Format 'yyyy-MM-dd'))
    $stamp   = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $logFile -Value "[$stamp] launcher: starting bot"

    $start = Get-Date
    try {
        # Stream stdout+stderr to the daily log. 2>&1 merges them so order is
        # preserved. -u forces unbuffered stdout so on_ready prints reach the
        # log immediately instead of waiting for an 8KB block to fill. The
        # python process inherits this script's environment, so .env loading
        # happens inside discord_int.py via _env.py.
        & $py -u $BotScript 2>&1 | ForEach-Object {
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
    Add-Content -Path $logFile -Value ("[$stamp] launcher: bot exited code={0} uptime={1:N0}s" -f $exit, $uptime)

    if ($uptime -lt $FastFailWindow) {
        $backoff = [Math]::Min($backoff * 2, $MaxBackoff)
        Add-Content -Path $logFile -Value "[$stamp] launcher: fast-fail detected, backoff=${backoff}s"
    } else {
        $backoff = $MinBackoff
    }

    Start-Sleep -Seconds $backoff
}
