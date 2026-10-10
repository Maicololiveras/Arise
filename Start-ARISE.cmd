@echo off
cd /d "%~dp0"
if exist "ARISE.exe" (
  start "" "%~dp0ARISE.exe" %*
) else if exist ".venv\Scripts\pythonw.exe" (
  start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0run.py" %*
) else (
  echo Ejecuta Install-Dev.ps1 o descarga el instalador compilado.
  pause
)
