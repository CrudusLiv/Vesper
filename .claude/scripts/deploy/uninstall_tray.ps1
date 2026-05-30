# Uninstall Vesper Tray — restores original Task Scheduler bot startup.
#
# Run from project root:
#   .claude\scripts\deploy\uninstall_tray.ps1

# 1. Quit the tray app if running
$trayProcs = Get-Process -Name pythonw -ErrorAction SilentlyContinue |
    Where-Object { $_.MainModule.FileName -like '*pythonw.exe' }
if ($trayProcs) {
    $trayProcs | Stop-Process -Force
    Write-Host "Stopped tray app."
} else {
    Write-Host "Tray app not running."
}

# 2. Remove startup registry entry
$regPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
try {
    Remove-ItemProperty -Path $regPath -Name 'VesperTray' -ErrorAction Stop
    Write-Host "Removed VesperTray startup entry."
} catch {
    Write-Host "VesperTray startup entry not found — skipping."
}

# 3. Re-enable the original bot task
$task = Get-ScheduledTask -TaskName 'secondbrain-discord' -ErrorAction SilentlyContinue
if ($task) {
    Enable-ScheduledTask -TaskName 'secondbrain-discord' | Out-Null
    Write-Host "Re-enabled Task Scheduler task: \secondbrain-discord"
} else {
    Write-Host "Task \secondbrain-discord not found — skipping."
}

Write-Host ""
Write-Host "Tray uninstalled. Bot will start at next logon via Task Scheduler as before."
