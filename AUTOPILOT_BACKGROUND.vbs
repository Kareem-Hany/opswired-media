' OpsWired Autopilot Silent Background Launcher
' Runs start.bat detached without an open terminal window (same pattern as JOB BRO)

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\bots\autopilot"
WshShell.Run "cmd /c ""D:\bots\autopilot\start.bat""", 0, False
