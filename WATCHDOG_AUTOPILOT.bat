@echo off
:: OpsWired Autopilot Watchdog - restarts the autopilot if its heartbeat goes stale
title OpsWired Autopilot Watchdog
:loop
cd /d "D:\bots\autopilot"
powershell -NoProfile -Command "$hb='D:\bots\autopilot\status\heartbeat.json'; if (Test-Path $hb) { $age=(Get-Date)-((Get-Item $hb).LastWriteTime); if ($age.TotalMinutes -gt 30) { exit 1 } else { exit 0 } } else { exit 1 }"
if errorlevel 1 (
  echo [%date% %time%] heartbeat stale - restarting autopilot >> watchdog.log
  wscript.exe "D:\bots\autopilot\AUTOPILOT_BACKGROUND.vbs"
  timeout /t 60 /nobreak >nul
)
timeout /t 600 /nobreak >nul
goto loop
