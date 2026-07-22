# SCANX runtime data cleanup
param(
    [string]$AppRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$InstallerDir = $PSScriptRoot
if (-not $AppRoot) {
    $AppRoot = Join-Path (Split-Path $InstallerDir -Parent) "lichee-pi-4a-cv"
}
$AppRoot = (Resolve-Path -LiteralPath $AppRoot -ErrorAction Stop).Path

$eventsDir = Join-Path $AppRoot "data\events"
$logsDir = Join-Path $AppRoot "data\logs"
$eventsJson = Join-Path $AppRoot "data\events.json"
$pidFile = Join-Path $AppRoot "data\scanx.pid"

$removed = 0
if (Test-Path $eventsDir) {
    $files = Get-ChildItem $eventsDir -File -ErrorAction SilentlyContinue
    $removed = $files.Count
    $files | Remove-Item -Force -ErrorAction SilentlyContinue
}

if (Test-Path $logsDir) {
    Get-ChildItem $logsDir -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}

foreach ($path in @($eventsJson, $pidFile)) {
    if (Test-Path $path) { Remove-Item $path -Force -ErrorAction SilentlyContinue }
}

Write-Host "[SCANX] Removed event frames: $removed" -ForegroundColor Green
Write-Host "[SCANX] Logs and events.json cleared" -ForegroundColor Green
