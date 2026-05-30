# One-shot migration: disable the old discord bot Task Scheduler task
# and write the tray app Windows startup registry entry.
#
# Run once from project root:
#   .claude\scripts\deploy\migrate_to_tray.ps1

$ProjectDir = $PSScriptRoot | Split-Path -Parent | Split-Path -Parent | Split-Path -Parent
$TrayApp    = Join-Path $ProjectDir '.claude\scripts\tray_app.py'

# Resolve pythonw.exe from the real Python installation, not the py.exe launcher
$PythonExe = & py -c "import sys; print(sys.executable)"
$Pythonw   = Join-Path ([System.IO.Path]::GetDirectoryName($PythonExe)) 'pythonw.exe'
if (-not (Test-Path $Pythonw)) { $Pythonw = $PythonExe }

# 1. Disable the old bot task using schtasks.exe (works without admin elevation)
$taskName = '\secondbrain-discord'
$result = schtasks /change /tn $taskName /disable 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Disabled Task Scheduler task: $taskName"
} else {
    Write-Host "Could not disable $taskName`: $result"
    Write-Host "Try running as Administrator if this fails."
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
