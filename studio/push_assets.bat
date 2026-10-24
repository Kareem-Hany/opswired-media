@echo off
REM One-click: copies your Gemini-generated assets into this repo and pushes them, so Claude can pull them.
REM Edit SRC if your folder is different.
set SRC=D:\bots\gemini-mcp\assets\opswired
set DEST=%~dp0inbox
if not exist "%DEST%" mkdir "%DEST%"
xcopy "%SRC%\*.png" "%DEST%\" /Y /D /Q
xcopy "%SRC%\*.jpg" "%DEST%\" /Y /D /Q
cd /d "%~dp0.."
git pull --rebase --autostash
git add studio/inbox
git commit -m "studio: new assets"
git push
echo.
echo Done. Tell Claude: "pushed".
pause
