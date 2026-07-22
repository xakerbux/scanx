# SCANX server stop
param(
    [string]$AppRoot = "",
    [int]$Port = 8080
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$InstallerDir = $PSScriptRoot
if (-not $AppRoot) {
    $AppRoot = Join-Path (Split-Path $InstallerDir -Parent) "lichee-pi-4a-cv"
}
$AppRoot = (Resolve-Path -LiteralPath $AppRoot -ErrorAction Stop).Path

$pidFile = Join-Path $AppRoot "data\scanx.pid"

function Stop-Scanx([int]$PidToStop = 0) {
    if ($PidToStop -gt 0) {
        Stop-Process -Id $PidToStop -Force -ErrorAction SilentlyContinue
    }
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            if ($_.OwningProcess -gt 0) {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
    if (Test-Path $pidFile) { Remove-Item $pidFile -Force -ErrorAction SilentlyContinue }
}

if (Test-Path $pidFile) {
    $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($oldPid -match '^\d+$') { Stop-Scanx ([int]$oldPid) }
} else {
    Stop-Scanx
}

Write-Host "[SCANX] Server stopped" -ForegroundColor Green
