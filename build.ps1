<#
.SYNOPSIS
    Builds the TRIAD Desktop application into a standalone Windows executable using PyInstaller.
#>

param(
    [switch]$Clean,
    [switch]$Shortcut
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Building TRIAD Local AI Workspace " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Verify virtual environment
$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python.exe"
}

Write-Host "[1/4] Checking Python environment..." -ForegroundColor Yellow
& $PythonExe --version

# Ensure application icon exists
$IconPath = "assets/triad.ico"
if (-not (Test-Path $IconPath)) {
    Write-Host "Generating application icons..." -ForegroundColor Yellow
    & $PythonExe tools/generate_icon.py
}

if ($Clean) {
    Write-Host "[2/4] Cleaning build artifacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist
}

Write-Host "[3/4] Running PyInstaller..." -ForegroundColor Yellow
& $PythonExe -m PyInstaller `
    --noconfirm `
    --name="TRIAD" `
    --onedir `
    --windowed `
    --icon="assets/triad.ico" `
    --add-data="app/ui/styles.qss;app/ui" `
    --add-data="app/ui/styles/theme.qss;app/ui/styles" `
    --add-data="assets/triad.ico;assets" `
    --add-data="assets/triad.png;assets" `
    --hidden-import="sqlite3" `
    --hidden-import="win32gui" `
    --hidden-import="win32process" `
    --hidden-import="win32api" `
    --hidden-import="win32con" `
    --hidden-import="psutil" `
    --hidden-import="PySide6.QtCore" `
    --hidden-import="PySide6.QtGui" `
    --hidden-import="PySide6.QtWidgets" `
    main.py

Write-Host "[4/4] Build complete!" -ForegroundColor Green
Write-Host "Executable location: .\dist\TRIAD\TRIAD.exe" -ForegroundColor Green

if ($Shortcut) {
    Write-Host ""
    Write-Host "Creating desktop shortcut..." -ForegroundColor Yellow
    & powershell -ExecutionPolicy Bypass -File .\Create-DesktopShortcut.ps1
}

