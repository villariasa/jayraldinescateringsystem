# ======================================================================
# Jayraldine's Catering - Custom Version Installer Builder (PowerShell)
# ======================================================================

param (
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          JAYRALDINE'S CATERING - INSTALLER BUILD SCRIPT              " -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan

$PythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    & $PythonExe (Join-Path $ScriptDir "build_installer.py")
} else {
    & $PythonExe (Join-Path $ScriptDir "build_installer.py") --version $Version
}

Write-Host "`nBuild complete! Press any key to open the output folder..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

$OutputDir = Join-Path $ScriptDir "installer_output"
if (Test-Path $OutputDir) {
    Invoke-Item $OutputDir
}
