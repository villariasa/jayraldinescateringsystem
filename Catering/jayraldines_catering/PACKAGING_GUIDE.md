# Jayraldine's Catering — Windows Packaging Guide

## Prerequisites

- Windows 10 or 11
- Python 3.11+ installed from https://python.org (check "Add to PATH" during install)
- PostgreSQL installed and running on the target machine
- The project folder copied to the Windows machine

---

## Step 1 — Set Up Virtual Environment

Open **Command Prompt** inside the project folder:

```cmd
python -m venv venv
venv\Scripts\activate
```

---

## Step 2 — Install Dependencies

```cmd
pip install -r requirements.txt
pip install pyinstaller pillow
```

---

## Step 3 — Convert Logo to .ico

```cmd
python -c "from PIL import Image; img = Image.open('assets/logo.png'); img.save('assets/logo.ico', sizes=[(16,16),(32,32),(48,48),(256,256)])"
```

---

## Step 4 — Create the Spec File

Create a file named `jayraldines.spec` in the project root with this content:

```python
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
    icon='assets\\logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='JayraldinesCatering',
)
```

---

## Step 5 — Build the Executable

```cmd
pyinstaller jayraldines.spec
```

This will create:
```
dist/
  JayraldinesCatering/
    JayraldinesCatering.exe   ← main executable
    ...                        ← all required DLLs and assets
```

> The entire `dist/JayraldinesCatering/` folder is the app.
> You can zip it and share it as-is. The `.exe` inside is what users double-click.

---

## Step 6 — Test the Build

Before creating an installer, test the built exe first:

```cmd
dist\JayraldinesCatering\JayraldinesCatering.exe
```

Make sure the app opens, connects to the DB, and all pages work correctly.

---

## Step 7 — Create a Proper Installer (Optional but Recommended)

### 7a — Download Inno Setup

Download and install from: https://jrsoftware.org/isdl.php

### 7b — Create the Installer Script

Create a file named `installer.iss` in the project root:

```ini
[Setup]
AppName=Jayraldine's Catering
AppVersion=1.0
AppPublisher=Jayraldine's Catering
DefaultDirName={autopf}\JayraldinesCatering
DefaultGroupName=Jayraldine's Catering
OutputDir=installer_output
OutputBaseFilename=JayraldinesSetup
SetupIconFile=assets\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\JayraldinesCatering\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Jayraldine's Catering"; Filename: "{app}\JayraldinesCatering.exe"; IconFilename: "{app}\assets\logo.ico"
Name: "{commondesktop}\Jayraldine's Catering"; Filename: "{app}\JayraldinesCatering.exe"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\JayraldinesCatering.exe"; Description: "Launch Jayraldine's Catering"; Flags: postinstall nowait skipifsilent
```

### 7c — Compile the Installer

1. Open **Inno Setup Compiler**
2. File → Open → select `installer.iss`
3. Click **Build → Compile** (or press `F9`)
4. Output will be at `installer_output/JayraldinesSetup.exe`

This is a single `.exe` installer you can give to anyone.

---

## Important Notes

### PostgreSQL is NOT bundled
The target machine must have PostgreSQL installed separately.
- Download PostgreSQL: https://www.postgresql.org/download/windows/
- After installing, restore the database:
  ```cmd
  psql -U postgres -c "CREATE DATABASE jayraldines_catering;"
  psql -U postgres -d jayraldines_catering -f jayraldines_catering.sql
  ```

### DB Connection Settings
The app reads DB credentials from `utils/db.py`.
If you need to change the host/port/password for a different machine,
edit `utils/db.py` before running `pyinstaller`.

### If the .exe Crashes on Launch
Run from Command Prompt to see errors:
```cmd
dist\JayraldinesCatering\JayraldinesCatering.exe
```
Or temporarily set `console=True` in the spec file and rebuild to see the error output.

### UPX (Optional — smaller file size)
UPX compresses the binaries. Download from https://upx.github.io and place `upx.exe` in the project folder or system PATH. PyInstaller will use it automatically if found.

---

## Quick Summary

| Step | Command / Tool |
|------|----------------|
| 1. Activate venv | `venv\Scripts\activate` |
| 2. Install deps | `pip install -r requirements.txt pyinstaller pillow` |
| 3. Make .ico | python one-liner (Step 3 above) |
| 4. Create spec | copy `jayraldines.spec` (Step 4 above) |
| 5. Build exe | `pyinstaller jayraldines.spec` |
| 6. Test | run `dist\JayraldinesCatering\JayraldinesCatering.exe` |
| 7. Make installer | Inno Setup + `installer.iss` (Step 7 above) |
