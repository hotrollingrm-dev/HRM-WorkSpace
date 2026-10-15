@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title HRM WorkSpace - Install
echo.
echo  ==============================================
echo    HRM WorkSpace - install / update
echo  ==============================================
echo.

rem ---- find Python 3.11 or newer --------------------------------------
set "PY="
for %%V in (3.14 3.13 3.12 3.11) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo  [X] Python 3.11 or newer was not found.
  echo      Install Python from https://www.python.org/downloads/windows/
  echo      and tick "Add python.exe to PATH", then run this file again.
  echo.
  pause
  exit /b 1
)
echo  [1/5] Python found: %PY%

rem ---- private environment -------------------------------------------
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 (
    echo  [X] Could not create the .venv folder.
    pause
    exit /b 1
  )
)
echo  [2/5] Environment ready (.venv)

rem ---- packages: offline wheels if present, otherwise internet --------
for /f %%i in ('.venv\Scripts\python.exe -c "import sys;print(str(sys.version_info[0])+str(sys.version_info[1]))"') do set "PYV=%%i"
if exist "wheels\py%PYV%" (
  echo  [3/5] Installing packages from wheels\py%PYV% ^(offline^)
  .venv\Scripts\python.exe -m pip install --quiet --no-index --find-links "wheels\py%PYV%" -r requirements.txt
) else (
  echo  [3/5] Installing packages from the internet
  .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
)
if errorlevel 1 (
  echo  [X] Package install failed. If this PC has no internet, copy the "wheels" folder
  echo      from the offline package next to this file and run again.
  pause
  exit /b 1
)

rem ---- self-check: load the app once with the installed packages ------
.venv\Scripts\python.exe -c "import hrm.main" >nul 2>&1
if errorlevel 1 (
  echo  [X] Self-check failed - the program cannot load with this Python/package set.
  echo      Details:
  .venv\Scripts\python.exe -c "import hrm.main"
  echo.
  echo      Send a photo of this window to the developer.
  pause
  exit /b 1
)
echo  [4/5] Self-check passed (Python %PYV%)

rem ---- desktop shortcut ------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\HRM WorkSpace.lnk'); $s.TargetPath='%~dp0start_for_tablets.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%SystemRoot%\System32\shell32.dll,13'; $s.Save()" >nul 2>&1
echo  [5/5] Desktop shortcut "HRM WorkSpace" created
echo.

if not exist "company_data\master_seed.json" (
  echo  [!] company_data folder has no company files yet.
  echo      Copy the files from HRM_company_data.zip into the company_data folder
  echo      before the first start. See INSTALL_TH.md, step 3.
  echo.
)
echo  Done. Double-click "HRM WorkSpace" on the desktop to start.
echo.
pause
