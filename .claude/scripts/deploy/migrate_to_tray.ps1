# One-shot migration: disable the old discord bot Task Scheduler task
# and write the tray app Windows startup registry entry.
#
# Run once from project root:
#   .claude\scripts\deploy\migrate_to_tray.ps1

$ProjectDir = $PSScriptRoot | Split-Path -Parent | Split-Path -Parent | Split-Path -Parent
$TrayApp    = Join-Path $ProjectDir '.claude\scripts\tray_app.py'
$Pythonw    = Join-Path ([System.IO.Path]::GetDirectoryName((Get-Command py.exe).Source)) 'pythonw.exe'
if (-not (Test-Path $Pythonw)) { $Pythonw = (Get-Command py.exe).Source }

# 1. Disable the old bot task (leave it so it can be re-enabled if needed)
$taskName = '\secondbrain-discord'
$task = Get-ScheduledTask -TaskName 'secondbrain-discord' -ErrorAction SilentlyContinue
if ($task) {
    Disable-ScheduledTask -TaskName 'secondbrain-discord' | Out-Null
    Write-Host "Disabled Task Scheduler task: $taskName"
} else {
    Write-Host "Task $taskName not found — skipping."
}

# 2. Write tray app to Windows startup registry
$regPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$cmd     = "`"$Pythonw`" `"$TrayApp`""
Set-ItemProperty -Path $regPath -Name 'VesperTray' -Value $cmd -Type String
Write-Host "Startup entry written: VesperTray = $cmd"

Write-Host ""
Write-Host "Migration complete."
Write-Host "Run the tray app manually once to confirm it works:"
Write-Host "  py .claude\scripts\tray_app.py"
Write-Host "Then reboot to confirm auto-start."
