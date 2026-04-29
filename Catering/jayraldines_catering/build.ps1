# =============================================================================
#  Jayraldine's Catering — One-Click Build Script
#  Run this once on Windows to produce a ready-to-distribute installer.
#
#  Usage:
#    Right-click build.ps1 → "Run with PowerShell"
#    OR in PowerShell terminal:
#      Set-ExecutionPolicy -Scope Process Bypass
#      .\build.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Jayraldine's Catering — Build"

function Print-Step($msg) {
    Write-Host ""
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
}

function Print-OK($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Print-Info($msg) { Write-Host "[..] $msg" -ForegroundColor Yellow }
function Print-Fail($msg) { Write-Host "[!!] $msg" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# 0. Confirm we are in the right folder
# ---------------------------------------------------------------------------
if (-not (Test-Path "main.py")) {
    Print-Fail "main.py not found. Please run this script from the project root folder."
    Pause
    exit 1
}

Write-Host ""
Write-Host "  Jayraldine's Catering — Windows Build Script" -ForegroundColor Magenta
Write-Host "  This will build the app and create a Windows installer." -ForegroundColor Magenta
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Check Python
# ---------------------------------------------------------------------------
Print-Step "Step 1 — Checking Python"

try {
    $pyver = python --version 2>&1
    Print-OK "Found: $pyver"
} catch {
    Print-Fail "Python not found. Install from https://python.org (check 'Add to PATH')"
    Pause
    exit 1
}

# ---------------------------------------------------------------------------
# 2. Create / activate virtual environment
# ---------------------------------------------------------------------------
Print-Step "Step 2 — Setting Up Virtual Environment"

if (-not (Test-Path "venv")) {
    Print-Info "Creating venv..."
    python -m venv venv
    Print-OK "venv created"
} else {
    Print-OK "venv already exists, skipping"
}

$pip    = ".\venv\Scripts\pip.exe"
$python = ".\venv\Scripts\python.exe"

# ---------------------------------------------------------------------------
# 3. Install dependencies
# ---------------------------------------------------------------------------
Print-Step "Step 3 — Installing Dependencies"

Print-Info "Upgrading pip..."
& $pip install --upgrade pip --quiet

Print-Info "Installing requirements.txt..."
& $pip install -r requirements.txt --quiet

Print-Info "Installing PyInstaller and Pillow..."
& $pip install pyinstaller pillow --quiet

Print-OK "All dependencies installed"

# ---------------------------------------------------------------------------
# 4. Convert logo.png to logo.ico
# ---------------------------------------------------------------------------
Print-Step "Step 4 — Converting Logo to .ico"

if (-not (Test-Path "assets\logo.png")) {
    Print-Fail "assets\logo.png not found. Skipping icon conversion."
    Print-Info "The build will use a default icon."
    $iconArg = ""
} else {
    & $python -c @"
from PIL import Image
img = Image.open('assets/logo.png').convert('RGBA')
img.save('assets/logo.ico', sizes=[(16,16),(32,32),(48,48),(256,256)])
print('logo.ico created')
"@
    Print-OK "assets\logo.ico created"
    $iconArg = "assets\\logo.ico"
}

# ---------------------------------------------------------------------------
# 5. Write the .spec file
# ---------------------------------------------------------------------------
Print-Step "Step 5 — Writing PyInstaller Spec File"

$iconLine = if ($iconArg) { "icon='$iconArg'," } else { "" }

$specContent = @"
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets',     'assets'),
        ('styles',     'styles'),
        ('components', 'components'),
        ('ui',         'ui'),
        ('utils',      'utils'),
    ],
    hiddenimports=[
        'psycopg2',
        'psycopg2.extensions',
        'psycopg2.extras',
        'reportlab',
        'openpyxl',
        *collect_submodules('PySide6'),
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JayraldinesCatering',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    $iconLine
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='JayraldinesCatering',
)
"@

Set-Content -Path "jayraldines.spec" -Value $specContent
Print-OK "jayraldines.spec written"

# ---------------------------------------------------------------------------
# 6. Run PyInstaller
# ---------------------------------------------------------------------------
Print-Step "Step 6 — Building Executable (this may take a few minutes)"

if (Test-Path "dist") {
    Print-Info "Cleaning old dist folder..."
    Remove-Item -Recurse -Force "dist"
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

& $python -m PyInstaller jayraldines.spec

if (-not (Test-Path "dist\JayraldinesCatering\JayraldinesCatering.exe")) {
    Print-Fail "Build failed — JayraldinesCatering.exe not found in dist\"
    Pause
    exit 1
}

Print-OK "Build successful: dist\JayraldinesCatering\JayraldinesCatering.exe"

# ---------------------------------------------------------------------------
# 7. Write Inno Setup script
# ---------------------------------------------------------------------------
Print-Step "Step 7 — Writing Inno Setup Installer Script"

$issIcon = if ($iconArg) { "SetupIconFile=assets\logo.ico" } else { "" }

$issContent = @"
[Setup]
AppName=Jayraldine's Catering
AppVersion=1.0
AppPublisher=Jayraldine's Catering
DefaultDirName={autopf}\JayraldinesCatering
DefaultGroupName=Jayraldine's Catering
OutputDir=installer_output
OutputBaseFilename=JayraldinesSetup
$issIcon
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\JayraldinesCatering\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Jayraldine's Catering"; Filename: "{app}\JayraldinesCatering.exe"
Name: "{commondesktop}\Jayraldine's Catering"; Filename: "{app}\JayraldinesCatering.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\JayraldinesCatering.exe"; Description: "Launch Jayraldine's Catering"; Flags: postinstall nowait skipifsilent
"@

New-Item -ItemType Directory -Force -Path "installer_output" | Out-Null
Set-Content -Path "installer.iss" -Value $issContent
Print-OK "installer.iss written"

# ---------------------------------------------------------------------------
# 8. Try to compile installer with Inno Setup (if installed)
# ---------------------------------------------------------------------------
Print-Step "Step 8 — Compiling Installer (Inno Setup)"

$innoPath = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($innoPath) {
    Print-Info "Found Inno Setup at: $innoPath"
    & $innoPath installer.iss
    if (Test-Path "installer_output\JayraldinesSetup.exe") {
        Print-OK "Installer created: installer_output\JayraldinesSetup.exe"
    } else {
        Print-Fail "Inno Setup ran but installer was not created. Check the output above."
    }
} else {
    Write-Host ""
    Write-Host "  Inno Setup not found — skipping installer creation." -ForegroundColor Yellow
    Write-Host "  To create an installer later:" -ForegroundColor Yellow
    Write-Host "    1. Download Inno Setup from https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host "    2. Open installer.iss with Inno Setup" -ForegroundColor Yellow
    Write-Host "    3. Press F9 to compile" -ForegroundColor Yellow
    Write-Host "    4. Installer will be at installer_output\JayraldinesSetup.exe" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Standalone app folder : dist\JayraldinesCatering\" -ForegroundColor White
Write-Host "  Run directly          : dist\JayraldinesCatering\JayraldinesCatering.exe" -ForegroundColor White
if (Test-Path "installer_output\JayraldinesSetup.exe") {
    Write-Host "  Installer             : installer_output\JayraldinesSetup.exe" -ForegroundColor White
}
Write-Host ""
Write-Host "  NOTE: PostgreSQL must be installed on the target machine." -ForegroundColor Yellow
Write-Host "  DB setup: psql -U postgres -c ""CREATE DATABASE jayraldines_catering;""" -ForegroundColor Yellow
Write-Host "            psql -U postgres -d jayraldines_catering -f jayraldines_catering.sql" -ForegroundColor Yellow
Write-Host ""

Pause
