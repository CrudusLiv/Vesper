Set fso = CreateObject("Scripting.FileSystemObject")
projectDir = fso.GetParentFolderName(fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName)))
heartbeatScript = projectDir & "\.claude\scripts\heartbeat.py"
CreateObject("WScript.Shell").Run "py """ & heartbeatScript & """", 0, False
