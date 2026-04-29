# =============================================================================
#  Jayraldine's Catering — Full Setup Script (New PC)
#  Run this once on any Windows machine to install everything needed
#  to run the app with:  python main.py
#
#  Usage:
#    Right-click setup.ps1 → "Run with PowerShell"
#    OR in PowerShell:
#      Set-ExecutionPolicy -Scope Process Bypass
#      .\setup.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Jayraldine's Catering — Setup"

function Print-Step($msg) {
    Write-Host ""
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
}
function Print-OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Print-Info($msg) { Write-Host "  [..] $msg" -ForegroundColor Yellow }
function Print-Fail($msg) { Write-Host "  [!!] $msg" -ForegroundColor Red }
function Print-Skip($msg) { Write-Host "  [--] $msg" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host "   Jayraldine's Catering — Environment Setup " -ForegroundColor Magenta
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  This script will:" -ForegroundColor White
Write-Host "    1. Check and install Python 3.11+" -ForegroundColor White
Write-Host "    2. Check and install PostgreSQL 16" -ForegroundColor White
Write-Host "    3. Set up a Python virtual environment" -ForegroundColor White
Write-Host "    4. Install all Python packages" -ForegroundColor White
Write-Host "    5. Create and initialize the database" -ForegroundColor White
Write-Host "    6. Verify the app can start" -ForegroundColor White
Write-Host ""
Write-Host "  Press ENTER to continue or Ctrl+C to cancel..." -ForegroundColor Yellow
Read-Host

# ---------------------------------------------------------------------------
# Helper: check if a command exists
# ---------------------------------------------------------------------------
function Command-Exists($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

# ---------------------------------------------------------------------------
# Helper: download a file
# ---------------------------------------------------------------------------
function Download-File($url, $dest) {
    Print-Info "Downloading: $url"
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
}

# ---------------------------------------------------------------------------
# STEP 1 — Python
# ---------------------------------------------------------------------------
Print-Step "Step 1 — Python 3.11+"

$pythonOk = $false
if (Command-Exists "python") {
    $pyver = python --version 2>&1
    if ($pyver -match "Python 3\.(1[1-9]|[2-9]\d)") {
        Print-OK "Already installed: $pyver"
        $pythonOk = $true
    } else {
        Print-Info "Found $pyver but need 3.11+. Will install newer version."
    }
}

if (-not $pythonOk) {
    $pyInstaller = "$env:TEMP\python-installer.exe"
    Print-Info "Downloading Python 3.12.4..."
    Download-File "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe" $pyInstaller
    Print-Info "Installing Python (this may take a minute)..."
    Start-Process -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1" -Wait
    Remove-Item $pyInstaller -Force
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $pyver = python --version 2>&1
    Print-OK "Python installed: $pyver"
}

# ---------------------------------------------------------------------------
# STEP 2 — PostgreSQL
# ---------------------------------------------------------------------------
Print-Step "Step 2 — PostgreSQL 16"

$pgOk = $false
$pgPaths = @(
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files\PostgreSQL\15\bin\psql.exe",
    "C:\Program Files\PostgreSQL\14\bin\psql.exe"
)
$psqlExe = $pgPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($psqlExe) {
    Print-OK "Already installed: $psqlExe"
    $pgOk = $true
} elseif (Command-Exists "psql") {
    $psqlExe = (Get-Command "psql").Source
    Print-OK "Already installed: $psqlExe"
    $pgOk = $true
}

if (-not $pgOk) {
    $pgInstaller = "$env:TEMP\postgresql-installer.exe"
    Print-Info "Downloading PostgreSQL 16..."
    Download-File "https://get.enterprisedb.com/postgresql/postgresql-16.3-1-windows-x64.exe" $pgInstaller
    Print-Info "Installing PostgreSQL..."
    Print-Info "IMPORTANT: When prompted, set the postgres superuser password to: 12345678"
    Write-Host ""
    Write-Host "  The installer will open now. Please:" -ForegroundColor Yellow
    Write-Host "    - Use default installation directory" -ForegroundColor Yellow
    Write-Host "    - Set password to: 12345678" -ForegroundColor Yellow
    Write-Host "    - Keep default port: 5432" -ForegroundColor Yellow
    Write-Host "    - Click through the rest with defaults" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Press ENTER when PostgreSQL is fully installed..." -ForegroundColor Yellow
    Start-Process -FilePath $pgInstaller -Wait
    Read-Host
    Remove-Item $pgInstaller -Force -ErrorAction SilentlyContinue

    $psqlExe = $pgPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $psqlExe) {
        if (Command-Exists "psql") {
            $psqlExe = (Get-Command "psql").Source
        }
    }

    if ($psqlExe) {
        Print-OK "PostgreSQL installed"
    } else {
        Print-Fail "psql.exe not found after installation."
        Print-Fail "Please add PostgreSQL bin folder to PATH and re-run this script."
        Pause
        exit 1
    }
}

# Add pg bin to current session PATH if not already there
$pgBin = Split-Path $psqlExe
if ($env:Path -notlike "*$pgBin*") {
    $env:Path = "$pgBin;" + $env:Path
}

# ---------------------------------------------------------------------------
# STEP 3 — Python virtual environment
# ---------------------------------------------------------------------------
Print-Step "Step 3 — Python Virtual Environment"

if (-not (Test-Path "main.py")) {
    Print-Fail "main.py not found. Please run this script from the project folder."
    Pause
    exit 1
}

if (Test-Path "venv") {
    Print-Skip "venv already exists, skipping creation"
} else {
    Print-Info "Creating venv..."
    python -m venv venv
    Print-OK "venv created"
}

$pip    = ".\venv\Scripts\pip.exe"
$python = ".\venv\Scripts\python.exe"

# ---------------------------------------------------------------------------
# STEP 4 — Python packages
# ---------------------------------------------------------------------------
Print-Step "Step 4 — Installing Python Packages"

Print-Info "Upgrading pip..."
& $pip install --upgrade pip --quiet

Print-Info "Installing from requirements.txt..."
& $pip install -r requirements.txt

$extras = @()
if (-not (& $python -c "import PIL" 2>&1 | Select-String "ModuleNotFoundError")) {
    Print-Skip "Pillow already installed"
} else {
    $extras += "pillow"
}

if ($extras.Count -gt 0) {
    Print-Info "Installing extras: $($extras -join ', ')..."
    & $pip install @extras --quiet
}

Print-OK "All packages installed"

# ---------------------------------------------------------------------------
# STEP 5 — Database setup
# ---------------------------------------------------------------------------
Print-Step "Step 5 — Database Setup"

$dbName   = "jayraldines_catering"
$dbUser   = "postgres"
$sqlFile  = "jayraldines_catering_clean.sql"
$sqlFileFallback = "jayraldines_catering.sql"

if (-not (Test-Path $sqlFile)) {
    if (Test-Path $sqlFileFallback) {
        $sqlFile = $sqlFileFallback
        Print-Info "Using $sqlFile (clean file not found)"
    } else {
        Print-Fail "No SQL file found ($sqlFile or $sqlFileFallback). Cannot set up database."
        Pause
        exit 1
    }
}

Write-Host ""
Write-Host "  Enter the PostgreSQL superuser (postgres) password." -ForegroundColor Yellow
Write-Host "  Default used during this setup: 12345678" -ForegroundColor Yellow
$pgPass = Read-Host "  Password (press ENTER for 12345678)"
if ([string]::IsNullOrWhiteSpace($pgPass)) { $pgPass = "12345678" }

$env:PGPASSWORD = $pgPass

Print-Info "Checking if database '$dbName' already exists..."
$exists = & $psqlExe -U $dbUser -h localhost -p 5432 -tAc "SELECT 1 FROM pg_database WHERE datname='$dbName';" 2>&1
if ($exists -eq "1") {
    Write-Host ""
    Write-Host "  Database '$dbName' already exists." -ForegroundColor Yellow
    $choice = Read-Host "  Drop and recreate it? All data will be lost. (y/N)"
    if ($choice -eq "y" -or $choice -eq "Y") {
        Print-Info "Recreating database..."
        & $psqlExe -U $dbUser -h localhost -p 5432 -f $sqlFile
        Print-OK "Database recreated from $sqlFile"
    } else {
        Print-Skip "Keeping existing database"
    }
} else {
    Print-Info "Creating database from $sqlFile..."
    & $psqlExe -U $dbUser -h localhost -p 5432 -f $sqlFile
    Print-OK "Database '$dbName' created successfully"
}

$env:PGPASSWORD = ""

# ---------------------------------------------------------------------------
# STEP 6 — Verify DB connection from Python
# ---------------------------------------------------------------------------
Print-Step "Step 6 — Verifying Database Connection"

$testScript = @"
import sys, os
os.environ['DB_PASSWORD'] = '$pgPass'
sys.path.insert(0, '.')
import utils.db as db
ok = db.connect()
if ok:
    print('DB_OK')
else:
    print('DB_FAIL')
"@

$result = & $python -c $testScript 2>&1
if ($result -like "*DB_OK*") {
    Print-OK "Database connection successful"
} else {
    Print-Fail "Database connection failed."
    Write-Host "  Output: $result" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Check that PostgreSQL is running and the password is correct." -ForegroundColor Yellow
    Write-Host "  You can set the password in utils\db.py (DB_PASSWORD default)." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# STEP 7 — Write a run.bat launcher
# ---------------------------------------------------------------------------
Print-Step "Step 7 — Creating run.bat Launcher"

$batContent = @"
@echo off
cd /d "%~dp0"
call venv\Scripts\activate
set DB_PASSWORD=$pgPass
python main.py
pause
"@

Set-Content -Path "run.bat" -Value $batContent
Print-OK "run.bat created — double-click it to start the app"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "   SETUP COMPLETE" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  To start the app:" -ForegroundColor White
Write-Host "    Double-click  run.bat" -ForegroundColor Cyan
Write-Host "    OR in terminal:  venv\Scripts\activate  then  python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "  DB password saved in run.bat — edit if you change it later." -ForegroundColor Yellow
Write-Host ""

$launch = Read-Host "  Launch the app now? (y/N)"
if ($launch -eq "y" -or $launch -eq "Y") {
    Start-Process "run.bat"
}

Pause
