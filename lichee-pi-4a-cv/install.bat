@echo off
chcp 65001 >nul
cd /d "%~dp0"
for %%I in ("%~dp0..") do set "SCANX_ROOT=%%~fI"
powershell -ExecutionPolicy Bypass -NoProfile -File "%SCANX_ROOT%\Установщик\install.ps1"
if errorlevel 1 (
  echo.
  echo [SCANX] Install failed
  pause
  exit /b 1
)
echo.
echo [SCANX] Install complete. Use ..\Установщик\run.bat
pause
