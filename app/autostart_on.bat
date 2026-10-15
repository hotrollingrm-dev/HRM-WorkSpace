@echo off
rem Start HRM WorkSpace automatically when this Windows user logs in.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([Environment]::GetFolderPath('Startup')+'\HRM WorkSpace.lnk'); $s.TargetPath='%~dp0start_for_tablets.bat'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()"
echo HRM WorkSpace will start automatically after login.
echo To turn it off: run autostart_off.bat
pause
