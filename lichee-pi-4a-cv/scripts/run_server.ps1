# SCANX — запуск сервера с корректной остановкой при закрытии окна
param(
    [int]$Port = 8080
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$py = Join-Path $Root ".venv\Scripts\python.exe"
$pidFile = Join-Path $Root "data\scanx.pid"

if (-not (Test-Path $py)) {
    Write-Host "[SCANX] Сначала запустите install.bat" -ForegroundColor Red
    Read-Host "Enter"
    exit 1
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root "data") | Out-Null

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
Write-Host "[SCANX] Закройте это окно или Ctrl+C для остановки сервера" -ForegroundColor DarkGray
Start-Process "http://127.0.0.1:$Port" | Out-Null

$proc = Start-Process -FilePath $py -ArgumentList "main.py" -WorkingDirectory $Root -PassThru -NoNewWindow
$proc.Id | Set-Content $pidFile -Encoding ASCII

try {
    Wait-Process -Id $proc.Id
} finally {
    Stop-Scanx $proc.Id
    Write-Host "[SCANX] Сервер остановлен" -ForegroundColor Yellow
}
