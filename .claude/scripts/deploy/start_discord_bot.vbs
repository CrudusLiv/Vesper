' Hidden launcher for start_discord_bot.ps1.
' wscript.exe is windowless, and Run with intWindowStyle=0 hides the
' PowerShell child too — so the auto-restart wrapper runs without any
' visible console. Toast notifications still surface (same user session).
'
' bWaitOnReturn=True (the 3rd Run arg): wscript blocks until powershell
' exits. This keeps the PS process in Task Scheduler's process tree so
' Stop-ScheduledTask can actually kill it. With False, wscript exited
' immediately and orphan PS loops accumulated on every Stop+Start cycle.
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
psScript = scriptDir & "\start_discord_bot.ps1"
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & psScript & """", 0, True
