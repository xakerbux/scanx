# SCANX — остановка сервера
$Root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $Root "data\scanx.pid"
$Port = 8080

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

Write-Host "[SCANX] Сервер остановлен" -ForegroundColor Green
