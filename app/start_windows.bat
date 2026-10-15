@echo off
cd /d "%~dp0"
title HRM WorkSpace (this PC only)
if not exist ".venv\Scripts\python.exe" (
  echo Run install_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe run.py --open
pause
