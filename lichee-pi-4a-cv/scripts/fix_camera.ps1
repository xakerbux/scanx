# Camera repair script (no admin required)
param()

$Log = Join-Path $PSScriptRoot "fix_camera.log"
function Log($msg) {
    $line = "$(Get-Date -Format o) $msg"
    $line | Tee-Object -FilePath $Log -Append
}

$ErrorActionPreference = "Continue"
Log "=== fix_camera start ==="

Get-Process -Name droidcam -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    Log "stopped droidcam pid $($_.Id)"
}

Log "install usbvideo.inf"
pnputil /add-driver C:\Windows\INF\usbvideo.inf /install 2>&1 | ForEach-Object { Log $_ }

Get-PnpDevice -Class Camera -ErrorAction SilentlyContinue | ForEach-Object {
    Log "device $($_.FriendlyName) status=$($_.Status)"
    if ($_.Status -ne "OK") {
        try {
            Enable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -ErrorAction Stop
            Log "enabled $($_.FriendlyName)"
        } catch {
            Log "enable skip: $($_.Exception.Message)"
        }
    }
}

Log "pnputil scan"
pnputil /scan-devices 2>&1 | ForEach-Object { Log $_ }

try {
    Restart-Service FrameServer -Force -ErrorAction Stop
    Log "FrameServer restarted"
} catch {
    Log "FrameServer skip: $($_.Exception.Message)"
}

Start-Sleep -Seconds 2

$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"
$check = Join-Path $PSScriptRoot "check_camera.py"
if ((Test-Path $py) -and (Test-Path $check)) {
    & $py $check 2>&1 | ForEach-Object { Log $_ }
}

Log "=== fix_camera done ==="
