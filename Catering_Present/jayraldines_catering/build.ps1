# ==============================================================================
#  Jayraldine's Catering - One-Click Build Script
#  Usage: Right-click build.ps1 -> Run with PowerShell
#  Optional: .\build.ps1 -Mode onefile
# ==============================================================================

param(
    [ValidateSet("onedir", "onefile")]
    [string]$Mode = "onedir"
)

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
Write-Host "  Build mode: $Mode" -ForegroundColor Yellow
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
& $python -m pip install --upgrade pip --quiet 2>&1 | Out-Null

Print-Info "Installing requirements.txt..."
& $python -m pip install -r requirements.txt --quiet

Print-Info "Installing PyInstaller and Pillow..."
& $python -m pip install pyinstaller pillow --quiet

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

$spec = @"
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import os, sys

block_cipher = None

# --- Collect Qt plugin data files (icons, platforms, etc.) ---
qt_data = collect_data_files('PySide6', includes=[
    'Qt/plugins/platforms/*',
    'Qt/plugins/imageformats/*',
    'Qt/plugins/iconengines/*',
    'Qt/plugins/styles/*',
    'Qt/translations/qtbase_*.qm',
])

# --- Collect all Qt native DLL binaries (Qt6Charts, Qt6Core, etc.) ---
qt_binaries = []
try:
    libs = collect_dynamic_libs('PySide6')
    qt_binaries = [b for b in libs if 'python' not in os.path.basename(b[0]).lower()]
except Exception as e:
    print(f'[spec] Warning: collect_dynamic_libs(PySide6) failed: {e}')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=qt_binaries,
    datas=[
        ('assets', 'assets'),
        ('styles', 'styles'),
        ('jayraldines_catering_clean.sql', '.'),
        ('cebu_address_migration.sql', '.'),
        ('occasions_migration.sql', '.'),
        ('confirmed_only_views_migration.sql', '.'),
        ('analytics_functions_migration.sql', '.'),
        ('fix_customer_ledger_view.sql', '.'),
    ] + qt_data,
    hiddenimports=[
        'shiboken6',
        'psycopg2',
        'psycopg2.extensions',
        'psycopg2.extras',
        'reportlab',
        'reportlab.graphics',
        'reportlab.platypus',
        'reportlab.lib',
        'reportlab.pdfgen',
        'openpyxl',
        'winsound',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'PySide6.QtXml',
        'PySide6.QtPrintSupport',
        'PySide6.QtCharts',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtNetwork',
        # UI Pages (all lazily imported but listed for PyInstaller analysis)
        'ui.dashboard_page',
        'ui.booking_page',
        'ui.customers_page',
        'ui.menu_page',
        'ui.calendar_page',
        'ui.kitchen_page',
        'ui.billing_page',
        'ui.reports_page',
        'ui.expenses_page',
        'ui.ai_page',
        'ui.settings_page',
        # Components
        'components.address_search',
        'components.badges',
        'components.booking_modal',
        'components.card',
        'components.charts',
        'components.confirm_booking_dialog',
        'components.customer_search',
        'components.dialogs',
        'components.export_dialog',
        'components.filter_popover',
        'components.global_ai_floating',
        'components.mascot',
        'components.notifications_panel',
        'components.search_dropdown',
        'components.sidebar',
        'components.splash',
        'components.toast',
        'components.topbar',
        # Utilities
        'utils.accent',
        'utils.ai_client',
        'utils.animations',
        'utils.data_loader',
        'utils.db',
        'utils.exporter',
        'utils.icon_manager',
        'utils.icons',
        'utils.importer',
        'utils.logger',
        'utils.mailer',
        'utils.menu_store',
        'utils.notif_scheduler',
        'utils.paths',
        'utils.reminder_manager',
        'utils.repository',
        'utils.session',
        'utils.signals',
        'utils.sms_sender',
        'utils.theme',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'numpy',
        'PySide6.QtWebEngine', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineCore',
        'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtLocation',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
        'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtQml',
        'PySide6.QtRemoteObjects', 'PySide6.QtSensors', 'PySide6.QtSerialPort',
        'ui.inventory_page', 'ui.test_report', 'test_reports',
        'xmlrpc', 'test', 'unittest',
        'distutils', 'setuptools', 'pkg_resources',
    ],
    noarchive=False,
    cipher=block_cipher,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

"@

if ($Mode -eq "onedir") {
    $spec += @"
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JayraldinesCatering',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
$iconLine
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python*.dll', 'Qt*.dll'],
    name='JayraldinesCatering',
)
"@
} else {
    $spec += @"
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='JayraldinesCatering',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python*.dll', 'Qt*.dll'],
    runtime_tmpdir=None,
    console=False,
$iconLine
)
"@
}

[System.IO.File]::WriteAllText("$PWD\jayraldines.spec", $spec, [System.Text.Encoding]::UTF8)
Print-OK "jayraldines.spec written"

# ------------------------------------------------------------------------------
# 6. Run PyInstaller
# ------------------------------------------------------------------------------
Print-Step "Step 6 - Building Executable (mode: $Mode)"

if (Test-Path "dist") {
    Print-Info "Cleaning old dist..."
    Remove-Item -Recurse -Force "dist"
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

& $python -m PyInstaller jayraldines.spec

$builtExe = if ($Mode -eq "onedir") {
    "dist\JayraldinesCatering\JayraldinesCatering.exe"
} else {
    "dist\JayraldinesCatering.exe"
}

if (-not (Test-Path $builtExe)) {
    Print-Fail "Build failed - exe not found: $builtExe"
    Read-Host "Press ENTER to exit"
    exit 1
}

Print-OK "Build successful: $builtExe"
if ($Mode -eq "onedir") {
    Print-Info "Default onedir build selected for faster startup after install."
} else {
    Print-Info "Portable one-file build created. Note: first startup may be slower."
}

# ------------------------------------------------------------------------------
# 7. Write Inno Setup script
# ------------------------------------------------------------------------------
Print-Step "Step 7 - Writing Inno Setup Installer Script"

$iss  = "[Setup]`r`n"
$iss += "AppName=Jayraldines Catering`r`n"
$iss += "AppVersion=4.0.5`r`n"
$iss += "AppPublisher=Jayraldines Catering`r`n"
$iss += "DefaultDirName={autopf}\JayraldinesCatering`r`n"
$iss += "DefaultGroupName=Jayraldines Catering`r`n"
$iss += "OutputDir=installer_output`r`n"
$iss += "OutputBaseFilename=JayraldinesSetup_v4.0.5`r`n"
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
if ($Mode -eq "onedir") {
    $iss += "Source: `"dist\JayraldinesCatering\*`"; DestDir: `"{app}`"; Flags: ignoreversion recursesubdirs createallsubdirs`r`n"
} else {
    $iss += "Source: `"dist\JayraldinesCatering.exe`"; DestDir: `"{app}`"; Flags: ignoreversion`r`n"
}
$iss += "Source: `"jayraldines_catering_clean.sql`"; DestDir: `"{app}`"; Flags: ignoreversion`r`n"
$iss += "Source: `"cebu_address_migration.sql`"; DestDir: `"{app}`"; Flags: ignoreversion`r`n"
$iss += "Source: `"occasions_migration.sql`"; DestDir: `"{app}`"; Flags: ignoreversion`r`n"
$iss += "Source: `"confirmed_only_views_migration.sql`"; DestDir: `"{app}`"; Flags: ignoreversion`r`n"
$iss += "Source: `"setup.ps1`"; DestDir: `"{app}`"; Flags: ignoreversion`r`n"
$iss += "`r`n"
$iss += "[Icons]`r`n"
$iss += "Name: `"{group}\Jayraldines Catering`"; Filename: `"{app}\JayraldinesCatering.exe`"`r`n"
$iss += "Name: `"{commondesktop}\Jayraldines Catering`"; Filename: `"{app}\JayraldinesCatering.exe`"; Tasks: desktopicon`r`n"
$iss += 'Name: "{group}\Setup Database"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\setup.ps1"""; WorkingDir: "{app}"' + "`r`n"
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
if ($Mode -eq "onedir") {
    Write-Host "  App Folder  : dist\JayraldinesCatering\" -ForegroundColor White
    Write-Host "  Main EXE    : dist\JayraldinesCatering\JayraldinesCatering.exe" -ForegroundColor White
    Write-Host "  This is the recommended faster-startup build for installed use." -ForegroundColor White
} else {
    Write-Host "  Single EXE  : dist\JayraldinesCatering.exe" -ForegroundColor White
    Write-Host "  Portable one-file build. First startup may be slower." -ForegroundColor White
}
if (Test-Path "installer_output\JayraldinesSetup.exe") {
    Write-Host "  Installer   : installer_output\JayraldinesSetup.exe" -ForegroundColor White
}
Write-Host ""
Write-Host "  NOTE: PostgreSQL must be installed and running on the target machine." -ForegroundColor Yellow
Write-Host ""

Read-Host "Press ENTER to exit"
