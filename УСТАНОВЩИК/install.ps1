# SCANX installer: Python, venv, dependencies, model
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

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Refresh-PathEnv {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Test-PythonExe([string]$exe, [string[]]$prefixArgs) {
    try {
        $args = @()
        if ($prefixArgs) { $args += $prefixArgs }
        $args += @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        $out = & $exe @args 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $ver = ($out | Select-Object -Last 1).ToString().Trim()
        if ($ver -match '^\d+\.\d+$' -and ([version]$ver -ge [version]"3.10")) {
            return @{ Exe = $exe; PrefixArgs = $prefixArgs; Version = $ver }
        }
    } catch {}
    return $null
}

function Find-Python {
    $candidates = @(
        @{ Exe = "py"; PrefixArgs = @("-3.12") },
        @{ Exe = "py"; PrefixArgs = @("-3.11") },
        @{ Exe = "py"; PrefixArgs = @("-3.10") },
        @{ Exe = "py"; PrefixArgs = @("-3") },
        @{ Exe = "py"; PrefixArgs = @() },
        @{ Exe = "python"; PrefixArgs = @() },
        @{ Exe = "python3"; PrefixArgs = @() }
    )
    $best = $null
    foreach ($c in $candidates) {
        $found = Test-PythonExe $c.Exe $c.PrefixArgs
        if (-not $found) { continue }
        if (-not $best) { $best = $found; continue }
        if ([version]$found.Version -lt [version]$best.Version) {
            $best = $found
        }
    }
    return $best
}

function Install-PythonWinget {
    Write-Step "Python 3.12 not found, installing via winget"
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python not found. Install Python 3.10+ from https://www.python.org/downloads/ (check Add to PATH)"
    }
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --disable-interactivity
    Refresh-PathEnv
    Start-Sleep -Seconds 4
    $found = Find-Python
    if (-not $found) {
        throw "Python installed but not in PATH. Restart terminal and run install.bat again"
    }
    return $found
}

function Invoke-Python([hashtable]$pyInfo, [string[]]$commandArgs) {
    $call = @()
    if ($pyInfo.PrefixArgs) { $call += $pyInfo.PrefixArgs }
    $call += $commandArgs
    & $pyInfo.Exe @call
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($pyInfo.Exe) $($call -join ' ')"
    }
}

function Test-Venv([string]$venvPy, [string]$appRoot) {
    if (-not (Test-Path $venvPy)) { return $false }

    $cfgPath = Join-Path $appRoot ".venv\pyvenv.cfg"
    if (Test-Path $cfgPath) {
        $cfg = Get-Content $cfgPath -Raw
        $expected = Join-Path $appRoot ".venv"
        if ($cfg -notmatch [regex]::Escape($expected)) {
            return $false
        }
    }

    try {
        & $venvPy -c "import cv2, fastapi, onnxruntime, uvicorn" 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

Write-Host ""
Write-Host "  SCANX installer" -ForegroundColor White
Write-Host "  App: $AppRoot" -ForegroundColor DarkGray
Write-Host ""

if (-not (Test-Path (Join-Path $AppRoot "main.py"))) {
    throw "main.py not found in $AppRoot"
}

Write-Step "Find Python 3.10+"
$pyInfo = Find-Python
if (-not $pyInfo) {
    $pyInfo = Install-PythonWinget
}
$pyLabel = if ($pyInfo.PrefixArgs) { "$($pyInfo.Exe) $($pyInfo.PrefixArgs -join ' ')" } else { $pyInfo.Exe }
Write-Host "  OK: Python $($pyInfo.Version) ($pyLabel)" -ForegroundColor Green

$venvDir = Join-Path $AppRoot ".venv"
$venvPy = Join-Path $venvDir "Scripts\python.exe"

Write-Step "Virtual environment .venv"
if (-not (Test-Venv $venvPy $AppRoot)) {
    if (Test-Path $venvDir) {
        Write-Host "  Recreating broken .venv" -ForegroundColor Yellow
        Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    Invoke-Python $pyInfo @("-m", "venv", $venvDir)
    if (-not (Test-Path $venvPy)) {
        throw "Failed to create .venv"
    }
}
Write-Host "  OK: $venvPy" -ForegroundColor Green

Write-Step "Install dependencies"
& $venvPy -m pip install -U pip wheel
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $venvPy -m pip install -r (Join-Path $AppRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
Write-Host "  OK" -ForegroundColor Green

Write-Step "Create folders"
@("videos", "data", "data\logs", "data\events", "models") | ForEach-Object {
    New-Item -ItemType Directory -Force -Path (Join-Path $AppRoot $_) | Out-Null
}
Write-Host "  Put .mp4 files into videos\" -ForegroundColor DarkGray

Write-Step "Download YOLOv8n model"
& $venvPy (Join-Path $AppRoot "scripts\download_model.py")
if ($LASTEXITCODE -ne 0) { throw "Model download failed" }

Write-Step "Verify imports"
Push-Location $AppRoot
try {
    & $venvPy -c "from cv_module.api.app import create_app; from cv_module.config import load_config; create_app(load_config())"
    if ($LASTEXITCODE -ne 0) { throw "App import check failed" }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "  Done!" -ForegroundColor Green
Write-Host "  Run:    run.bat" -ForegroundColor White
Write-Host "  Stop:   stop.bat" -ForegroundColor White
Write-Host "  Browser http://127.0.0.1:8080" -ForegroundColor White
Write-Host ""
