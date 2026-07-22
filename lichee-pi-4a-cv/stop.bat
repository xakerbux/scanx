@echo off
chcp 65001 >nul
cd /d "%~dp0"
for %%I in ("%~dp0..") do set "SCANX_ROOT=%%~fI"
powershell -ExecutionPolicy Bypass -NoProfile -File "%SCANX_ROOT%\Установщик\stop.ps1"
pause
