# Redirect to SCANX installer in parent folder
$AppRoot = Split-Path -Parent $PSScriptRoot
$Installer = Join-Path (Split-Path $AppRoot -Parent) "Установщик\install.ps1"
if (-not (Test-Path $Installer)) {
    throw "Installer not found: $Installer"
}
& $Installer -AppRoot $AppRoot
