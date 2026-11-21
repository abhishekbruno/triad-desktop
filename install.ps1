<#
.SYNOPSIS
    Installs TRIAD by compiling the standalone Windows application and creating a desktop shortcut.
.DESCRIPTION
    Runs build.ps1 to package dist\TRIAD\TRIAD.exe and then runs Create-DesktopShortcut.ps1
    to place the TRIAD icon on the current user's desktop.
#>

param(
    [switch]$NoClean
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " TRIAD - Complete One-Click Installation " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Build application
$BuildArgs = @("-ExecutionPolicy", "Bypass", "-File", (Join-Path $ScriptDir "build.ps1"))
if (-not $NoClean) {
    $BuildArgs += "-Clean"
}

Write-Host "[Step 1/2] Building standalone executable..." -ForegroundColor Yellow
& powershell @BuildArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

# 2. Create Desktop Shortcut
Write-Host ""
Write-Host "[Step 2/2] Creating desktop shortcut..." -ForegroundColor Yellow
& powershell -ExecutionPolicy Bypass -File (Join-Path $ScriptDir "Create-DesktopShortcut.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Shortcut creation failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "TRIAD installation is complete! You can now launch TRIAD from your desktop." -ForegroundColor Green

