# SCANX server launcher
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

$py = Join-Path $AppRoot ".venv\Scripts\python.exe"
$pidFile = Join-Path $AppRoot "data\scanx.pid"

if (-not (Test-Path $py)) {
    Write-Host "[SCANX] Run install.bat first" -ForegroundColor Red
    Read-Host "Press Enter"
    exit 1
}

Set-Location $AppRoot
New-Item -ItemType Directory -Force -Path (Join-Path $AppRoot "data") | Out-Null

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
}

Write-Host "[SCANX] http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "[SCANX] Close this window to stop the server" -ForegroundColor DarkGray
Start-Process "http://127.0.0.1:$Port" | Out-Null

$proc = Start-Process -FilePath $py -ArgumentList "main.py" -WorkingDirectory $AppRoot -PassThru -NoNewWindow
$proc.Id | Set-Content $pidFile -Encoding ASCII

try {
    Wait-Process -Id $proc.Id
} finally {
    Stop-Scanx $proc.Id
    Write-Host "[SCANX] Server stopped" -ForegroundColor Yellow
}
