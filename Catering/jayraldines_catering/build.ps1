# ==============================================================================
#  Jayraldine's Catering - One-Click Build Script
#  Usage: Right-click build.ps1 -> Run with PowerShell
# ==============================================================================

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Jayraldines Catering - Build"

trap {
    Write-Host ""
    Write-Host "  [FATAL ERROR]" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  The build script encountered an error. See message above." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press ENTER to exit"
    exit 1
}

function Print-Step($msg) {
    Write-Host ""
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
}
function Print-OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Print-Info($msg) { Write-Host "  [..] $msg" -ForegroundColor Yellow }
function Print-Fail($msg) { Write-Host "  [!!] $msg" -ForegroundColor Red }

# ------------------------------------------------------------------------------
# 0. Confirm correct folder
# ------------------------------------------------------------------------------
if (-not (Test-Path "main.py")) {
    Print-Fail "main.py not found. Run this script from the project root folder."
    Read-Host "Press ENTER to exit"
    exit 1
}

Write-Host ""
Write-Host "  Jayraldines Catering - Windows Build Script" -ForegroundColor Magenta
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Check Python
# ------------------------------------------------------------------------------
Print-Step "Step 1 - Checking Python"

try {
    $pyver = python --version 2>&1
    Print-OK "Found: $pyver"
} catch {
    Print-Fail "Python not found. Install from https://python.org (check Add to PATH)"
    Read-Host "Press ENTER to exit"
    exit 1
}

# ------------------------------------------------------------------------------
# 2. Create virtual environment
# ------------------------------------------------------------------------------
Print-Step "Step 2 - Setting Up Virtual Environment"

if (-not (Test-Path "venv")) {
    Print-Info "Creating venv..."
    python -m venv venv
    Print-OK "venv created"
} else {
    Print-OK "venv already exists"
}

$pip    = ".\venv\Scripts\pip.exe"
$python = ".\venv\Scripts\python.exe"

# ------------------------------------------------------------------------------
# 3. Install dependencies
# ------------------------------------------------------------------------------
Print-Step "Step 3 - Installing Dependencies"

Print-Info "Upgrading pip..."
& $pip install --upgrade pip --quiet

Print-Info "Installing requirements.txt..."
& $pip install -r requirements.txt --quiet

Print-Info "Installing PyInstaller and Pillow..."
& $pip install pyinstaller pillow --quiet

Print-OK "All dependencies installed"

# ------------------------------------------------------------------------------
# 4. Convert logo to .ico
# ------------------------------------------------------------------------------
Print-Step "Step 4 - Converting Logo to .ico"

if (-not (Test-Path "assets\logo.png")) {
    Print-Info "assets\logo.png not found. Skipping icon conversion."
    $iconLine = ""
} else {
    & $python -c "from PIL import Image; img = Image.open('assets/logo.png').convert('RGBA'); img.save('assets/logo.ico', sizes=[(16,16),(32,32),(48,48),(256,256)]); print('Done')"
    Print-OK "assets\logo.ico created"
    $iconLine = "icon='assets\\logo.ico',"
}

# ------------------------------------------------------------------------------
# 5. Write spec file
# ------------------------------------------------------------------------------
Print-Step "Step 5 - Writing PyInstaller Spec File"

$spec = "from PyInstaller.utils.hooks import collect_submodules, collect_data_files`n"
$spec += "`n"
$spec += "block_cipher = None`n"
$spec += "`n"
$spec += "a = Analysis(`n"
$spec += "    ['main.py'],`n"
$spec += "    pathex=['.'],`n"
$spec += "    binaries=[],`n"
$spec += "    datas=[`n"
$spec += "        ('assets',     'assets'),`n"
$spec += "        ('styles',     'styles'),`n"
$spec += "        ('components', 'components'),`n"
$spec += "        ('ui',         'ui'),`n"
$spec += "        ('utils',      'utils'),`n"
$spec += "        ('jayraldines_catering_clean.sql', '.'),`n"
$spec += "        *collect_data_files('PySide6'),`n"
$spec += "    ],`n"
$spec += "    hiddenimports=[`n"
$spec += "        'psycopg2',`n"
$spec += "        'psycopg2.extensions',`n"
$spec += "        'psycopg2.extras',`n"
$spec += "        'reportlab',`n"
$spec += "        'reportlab.graphics',`n"
$spec += "        'reportlab.platypus',`n"
$spec += "        'reportlab.lib',`n"
$spec += "        'openpyxl',`n"
$spec += "        'PySide6.QtSvg',`n"
$spec += "        'PySide6.QtSvgWidgets',`n"
$spec += "        'PySide6.QtXml',`n"
$spec += "        'PySide6.QtPrintSupport',`n"
$spec += "        'PySide6.QtCharts',`n"
$spec += "        'PySide6.QtOpenGL',`n"
$spec += "        'PySide6.QtOpenGLWidgets',`n"
$spec += "        *collect_submodules('PySide6'),`n"
$spec += "    ],`n"
$spec += "    hookspath=[],`n"
$spec += "    runtime_hooks=[],`n"
$spec += "    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy'],`n"
$spec += "    noarchive=False,`n"
$spec += "    cipher=block_cipher,`n"
$spec += ")`n"
$spec += "`n"
$spec += "pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)`n"
$spec += "`n"
$spec += "exe = EXE(`n"
$spec += "    pyz,`n"
$spec += "    a.scripts,`n"
$spec += "    [],`n"
$spec += "    exclude_binaries=True,`n"
$spec += "    name='JayraldinesCatering',`n"
$spec += "    debug=False,`n"
$spec += "    bootloader_ignore_signals=False,`n"
$spec += "    strip=False,`n"
$spec += "    upx=False,`n"
$spec += "    console=False,`n"
if ($iconLine) {
    $spec += "    $iconLine`n"
}
$spec += ")`n"
$spec += "`n"
$spec += "coll = COLLECT(`n"
$spec += "    exe,`n"
$spec += "    a.binaries,`n"
$spec += "    a.zipfiles,`n"
$spec += "    a.datas,`n"
$spec += "    strip=False,`n"
$spec += "    upx=False,`n"
$spec += "    name='JayraldinesCatering',`n"
$spec += ")`n"

[System.IO.File]::WriteAllText("$PWD\jayraldines.spec", $spec, [System.Text.Encoding]::UTF8)
Print-OK "jayraldines.spec written"

# ------------------------------------------------------------------------------
# 6. Run PyInstaller
# ------------------------------------------------------------------------------
Print-Step "Step 6 - Building Executable (may take a few minutes)"

if (Test-Path "dist") {
    Print-Info "Cleaning old dist..."
    Remove-Item -Recurse -Force "dist"
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

& $python -m PyInstaller jayraldines.spec

if (-not (Test-Path "dist\JayraldinesCatering\JayraldinesCatering.exe")) {
    Print-Fail "Build failed - exe not found in dist\"
    Read-Host "Press ENTER to exit"
    exit 1
}

Print-OK "Build successful: dist\JayraldinesCatering\JayraldinesCatering.exe"

# ------------------------------------------------------------------------------
# 7. Write Inno Setup script
# ------------------------------------------------------------------------------
Print-Step "Step 7 - Writing Inno Setup Installer Script"

$iss  = "[Setup]`r`n"
$iss += "AppName=Jayraldines Catering`r`n"
$iss += "AppVersion=1.0`r`n"
$iss += "AppPublisher=Jayraldines Catering`r`n"
$iss += "DefaultDirName={autopf}\JayraldinesCatering`r`n"
$iss += "DefaultGroupName=Jayraldines Catering`r`n"
$iss += "OutputDir=installer_output`r`n"
$iss += "OutputBaseFilename=JayraldinesSetup`r`n"
if (Test-Path "assets\logo.ico") {
    $iss += "SetupIconFile=assets\logo.ico`r`n"
}
$iss += "Compression=lzma`r`n"
$iss += "SolidCompression=yes`r`n"
$iss += "WizardStyle=modern`r`n"
$iss += "`r`n"
$iss += "[Languages]`r`n"
$iss += "Name: `"english`"; MessagesFile: `"compiler:Default.isl`"`r`n"
$iss += "`r`n"
$iss += "[Files]`r`n"
$iss += "Source: `"dist\JayraldinesCatering\*`"; DestDir: `"{app}`"; Flags: ignoreversion recursesubdirs createallsubdirs`r`n"
$iss += "Source: `"jayraldines_catering_clean.sql`"; DestDir: `"{app}`"; Flags: ignoreversion`r`n"
$iss += "`r`n"
$iss += "[Icons]`r`n"
$iss += "Name: `"{group}\Jayraldines Catering`"; Filename: `"{app}\JayraldinesCatering.exe`"`r`n"
$iss += "Name: `"{commondesktop}\Jayraldines Catering`"; Filename: `"{app}\JayraldinesCatering.exe`"; Tasks: desktopicon`r`n"
$iss += "`r`n"
$iss += "[Tasks]`r`n"
$iss += "Name: `"desktopicon`"; Description: `"Create a desktop shortcut`"; GroupDescription: `"Additional icons:`"`r`n"
$iss += "`r`n"
$iss += "[Run]`r`n"
$iss += "Filename: `"{app}\JayraldinesCatering.exe`"; Description: `"Launch Jayraldines Catering`"; Flags: postinstall nowait skipifsilent`r`n"

New-Item -ItemType Directory -Force -Path "installer_output" | Out-Null
[System.IO.File]::WriteAllText("$PWD\installer.iss", $iss, [System.Text.Encoding]::UTF8)
Print-OK "installer.iss written"

# ------------------------------------------------------------------------------
# 8. Compile installer with Inno Setup (if installed)
# ------------------------------------------------------------------------------
Print-Step "Step 8 - Compiling Installer"

$innoPath = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($innoPath) {
    Print-Info "Found Inno Setup: $innoPath"
    & $innoPath installer.iss
    if (Test-Path "installer_output\JayraldinesSetup.exe") {
        Print-OK "Installer created: installer_output\JayraldinesSetup.exe"
    } else {
        Print-Fail "Inno Setup ran but installer was not created."
    }
} else {
    Write-Host ""
    Write-Host "  Inno Setup not found - skipping installer step." -ForegroundColor Yellow
    Write-Host "  To create an installer later:" -ForegroundColor Yellow
    Write-Host "    1. Download from https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host "    2. Open installer.iss with Inno Setup and press F9" -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# Done
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  App folder  : dist\JayraldinesCatering\" -ForegroundColor White
Write-Host "  Run directly: dist\JayraldinesCatering\JayraldinesCatering.exe" -ForegroundColor White
if (Test-Path "installer_output\JayraldinesSetup.exe") {
    Write-Host "  Installer   : installer_output\JayraldinesSetup.exe" -ForegroundColor White
}
Write-Host ""
Write-Host "  NOTE: PostgreSQL must be installed and running on the target machine." -ForegroundColor Yellow
Write-Host ""

Read-Host "Press ENTER to exit"
