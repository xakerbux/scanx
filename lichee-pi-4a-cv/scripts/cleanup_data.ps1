#!/usr/bin/env pwsh
# Очистка runtime-данных SCANX (кадры событий, логи, JSON)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$eventsDir = Join-Path $Root "data\events"
$logsDir = Join-Path $Root "data\logs"
$eventsJson = Join-Path $Root "data\events.json"

$removed = 0
if (Test-Path $eventsDir) {
    $files = Get-ChildItem $eventsDir -File -ErrorAction SilentlyContinue
    $removed = $files.Count
    $files | Remove-Item -Force -ErrorAction SilentlyContinue
}

if (Test-Path $logsDir) {
    Get-ChildItem $logsDir -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}

if (Test-Path $eventsJson) {
    Remove-Item $eventsJson -Force
}

Write-Host "SCANX: удалено кадров событий: $removed" -ForegroundColor Green
Write-Host "       логи и events.json очищены" -ForegroundColor Green
