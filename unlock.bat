@echo off
title Obsidian2 90-2440 unlock
cd /d "%~dp0"
set PY=python
if exist C:\Python27\python.exe set PY=C:\Python27\python.exe
echo.
echo Close any Glide / 3D programs first. This takes a few minutes.
echo Do NOT touch the video cable while it runs.
echo.
%PY% unlock.py %*
if errorlevel 1 (
  echo.
  echo *** FAILED - see the messages above, or C:\unlock_log.txt ***
) else (
  echo.
  echo *** Done. Start your 3D application now. ***
)
echo.
pause
