@echo off
cd /d "%~dp0"
title HRM WorkSpace (PC + tablets)
if not exist ".venv\Scripts\python.exe" (
  echo Run install_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m tools.backup >nul 2>&1
.venv\Scripts\python.exe run.py --lan --open
pause
