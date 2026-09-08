@echo off
setlocal
set "SCRIPT=%~dp0game.py"
set "VENV_PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe"

if exist "%VENV_PY%" (
  start "" "%VENV_PY%" "%SCRIPT%"
  goto :ok
)
where pythonw >nul 2>&1 (
  start "" pythonw "%SCRIPT%"
  goto :ok
)
where python >nul 2>&1 (
  start "" python "%SCRIPT%"
  goto :ok
)
echo [XX] No usable Python found. Install Python 3.8+ with pygame, or run the bundled env.
pause
exit /b 1
:ok
exit /b 0
