@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m tools.backup
pause
