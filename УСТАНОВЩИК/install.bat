@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo [SCANX] Install failed
  pause
  exit /b 1
)
echo.
echo [SCANX] Install complete. Run run.bat
pause
