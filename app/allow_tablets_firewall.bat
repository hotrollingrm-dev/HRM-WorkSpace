@echo off
rem Opens TCP 8000 for the company network only (Domain/Private profiles). Needs administrator rights.
net session >nul 2>&1
if errorlevel 1 (
  echo Right-click this file and choose "Run as administrator".
  pause
  exit /b 1
)
netsh advfirewall firewall delete rule name="HRM WorkSpace 8000" >nul 2>&1
netsh advfirewall firewall add rule name="HRM WorkSpace 8000" dir=in action=allow protocol=TCP localport=8000 profile=domain,private
echo Firewall rule "HRM WorkSpace 8000" added (Domain + Private networks only).
pause
