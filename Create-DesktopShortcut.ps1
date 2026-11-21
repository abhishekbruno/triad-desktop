<#
.SYNOPSIS
    Creates a Windows Desktop Shortcut for the packaged TRIAD application.
.DESCRIPTION
    Locates the packaged executable (dist\TRIAD\TRIAD.exe), resolves the actual
    Windows Desktop path (including OneDrive redirection support), and creates a
    working desktop shortcut (TRIAD.lnk) pointing to the standalone executable
    with working directory and TRIAD icon correctly assigned.
#>

param(
    [string]$DistPath = ""
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " TRIAD - Desktop Shortcut Creation " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Resolve Executable Path
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $DistPath) {
    $ExePath = Join-Path $ScriptDir "dist\TRIAD\TRIAD.exe"
} else {
    $ExePath = [System.IO.Path]::GetFullPath($DistPath)
}

if (-not (Test-Path $ExePath)) {
    Write-Host "[ERROR] Packaged executable not found at:" -ForegroundColor Red
    Write-Host "        $ExePath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Please build the packaged application first by running:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\build.ps1 -Clean" -ForegroundColor Yellow
    exit 1
}

$ExeFullPath = (Resolve-Path $ExePath).Path
$WorkingDir = Split-Path -Parent $ExeFullPath
Write-Host "[1/4] Found packaged executable:" -ForegroundColor Green
Write-Host "      $ExeFullPath" -ForegroundColor Gray

# 2. Resolve Windows Desktop Path (Compatible with OneDrive Redirection)
$DesktopPath = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)

# Check registry override for relocated or OneDrive-managed Desktop folders
try {
    $RegProps = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" -ErrorAction SilentlyContinue
    if ($RegProps -and $RegProps.Desktop) {
        $ExpandedRegDesktop = [Environment]::ExpandEnvironmentVariables($RegProps.Desktop)
        if (Test-Path $ExpandedRegDesktop) {
            $DesktopPath = $ExpandedRegDesktop
        }
    }
} catch {
    # Keep standard Environment SpecialFolder path
}

if (-not (Test-Path $DesktopPath)) {
    Write-Host "[ERROR] Could not resolve a valid Windows Desktop folder: $DesktopPath" -ForegroundColor Red
    exit 1
}

Write-Host "[2/4] Resolved Windows Desktop location:" -ForegroundColor Green
Write-Host "      $DesktopPath" -ForegroundColor Gray

# 3. Resolve Icon Path
$IconPath = Join-Path $ScriptDir "assets\triad.ico"
if (-not (Test-Path $IconPath)) {
    $IconPath = $ExeFullPath
}
Write-Host "[3/4] Resolved application icon:" -ForegroundColor Green
Write-Host "      $IconPath" -ForegroundColor Gray

# 4. Create or Overwrite Desktop Shortcut (TRIAD.lnk)
$ShortcutPath = Join-Path $DesktopPath "TRIAD.lnk"

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExeFullPath
    $Shortcut.WorkingDirectory = $WorkingDir
    $Shortcut.Description = "TRIAD - Local AI Consensus Workspace"
    $Shortcut.IconLocation = "$IconPath,0"
    $Shortcut.Save()
    
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($WshShell) | Out-Null
} catch {
    Write-Host "[ERROR] Failed to write desktop shortcut: $_" -ForegroundColor Red
    exit 1
}

Write-Host "[4/4] Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Shortcut: $ShortcutPath" -ForegroundColor White
Write-Host " Target:   $ExeFullPath" -ForegroundColor White
Write-Host " Working:  $WorkingDir" -ForegroundColor White
Write-Host " Icon:     $IconPath" -ForegroundColor White
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now double-click the TRIAD desktop icon to launch your workspace!" -ForegroundColor Green
