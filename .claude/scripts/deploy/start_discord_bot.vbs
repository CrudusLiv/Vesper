' Hidden launcher for start_discord_bot.ps1.
' wscript.exe is windowless, and Run with intWindowStyle=0 hides the
' PowerShell child too — so the auto-restart wrapper runs without any
' visible console. Toast notifications still surface (same user session).
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
psScript = scriptDir & "\start_discord_bot.ps1"
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & psScript & """", 0, False
