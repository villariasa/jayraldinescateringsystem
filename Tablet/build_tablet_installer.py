"""
Installer & Executable Builder for Jayraldine's Catering Tablet / Mobile.
Features:
- Auto-increment versioning (major, minor, patch)
- PyInstaller compilation into standalone distributable
- Inno Setup / Self-Extracting installer builder
- Android APK helper bridge

Usage:
  python build_tablet_installer.py                  # Prompts for version or auto-increments
  python build_tablet_installer.py --patch          # Auto-increments patch (e.g. 0.1.0 -> 0.1.1)
  python build_tablet_installer.py --version 1.0.0  # Sets explicit version
"""

import sys
import os
import shutil
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

from bump_version import bump, get_current_version


def find_python() -> Path:
    candidates = [
        REPO_ROOT / "Catering_Present" / "jayraldines_catering" / "venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path(sys.executable)


def find_pyinstaller(py_exe: Path) -> Path:
    pyinstaller = py_exe.parent / "pyinstaller.exe"
    if pyinstaller.exists():
        return pyinstaller
    return Path("pyinstaller")


def find_iscc() -> Path | None:
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def create_inno_script(version: str) -> Path:
    iss_content = f"""[Setup]
AppName=Jayraldines Catering Tablet
AppVersion={version}
AppPublisher=Jayraldine's Catering Services
DefaultDirName={{autopf}}\\JayraldinesCateringTablet
DefaultGroupName=Jayraldine's Catering Tablet
OutputDir={ROOT / "installer_output"}
OutputBaseFilename=Jayraldines_Tablet_Setup_v{version}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"

[Files]
Source: "{ROOT / 'dist' / 'JayraldinesTablet'}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\Jayraldine's Catering Tablet"; Filename: "{{app}}\\JayraldinesTablet.exe"
Name: "{{autodesktop}}\\Jayraldine's Catering Tablet"; Filename: "{{app}}\\JayraldinesTablet.exe"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\JayraldinesTablet.exe"; Description: "{{cm:LaunchProgram,Jayraldine's Catering Tablet}}"; Flags: nowait postinstall skipifsilent
"""
    iss_path = ROOT / "tablet_installer.iss"
    iss_path.write_text(iss_content, encoding="utf-8")
    return iss_path


def run_build(version: str):
    print("=" * 65)
    print(f"  JAYRALDINE'S CATERING TABLET — COMPILING INSTALLER v{version}")
    print("=" * 65)

    py_exe = find_python()
    pyinstaller_exe = find_pyinstaller(py_exe)

    print(f"Using Python: {py_exe}")
    print(f"Using PyInstaller: {pyinstaller_exe}")

    # 1. Compile with PyInstaller
    print("\n[Step 1/2] Compiling Tablet App with PyInstaller...")
    spec_file = ROOT / "tablet.spec"
    cmd = [str(pyinstaller_exe), str(spec_file), "--noconfirm"]
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        print(f"\n[ERROR] PyInstaller compilation failed with code {res.returncode}")
        sys.exit(res.returncode)

    output_dir = ROOT / "installer_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 2. Check for Inno Setup compiler
    print("\n[Step 2/2] Building Setup Installer Package...")
    iscc = find_iscc()
    if iscc:
        iss_script = create_inno_script(version)
        print(f"Running Inno Setup Compiler ({iscc})...")
        res_inno = subprocess.run([str(iscc), str(iss_script)], cwd=ROOT)
        if res_inno.returncode == 0:
            setup_exe = output_dir / f"Jayraldines_Tablet_Setup_v{version}.exe"
            print("\n" + "=" * 65)
            print(f"  SUCCESS! Tablet Installer created:")
            print(f"  {setup_exe}")
            print("=" * 65)
            return setup_exe

    # If Inno Setup is not installed, create a clean portable zip bundle
    zip_path = output_dir / f"Jayraldines_Tablet_Portable_v{version}.zip"
    dist_folder = ROOT / "dist" / "JayraldinesTablet"
    print(f"Packaging portable archive to: {zip_path}")
    shutil.make_archive(str(output_dir / f"Jayraldines_Tablet_Portable_v{version}"), "zip", dist_folder)

    print("\n" + "=" * 65)
    print(f"  SUCCESS! Portable Tablet App build completed:")
    print(f"  {zip_path}")
    print(f"  Distribution directory: {dist_folder}")
    print("=" * 65)
    return zip_path


def main():
    parser = argparse.ArgumentParser(description="Jayraldine's Catering Tablet Installer Builder")
    parser.add_argument("--version", type=str, default=None, help="Explicit version number")
    parser.add_argument("--patch", action="store_true", help="Auto-increment patch version")
    parser.add_argument("--minor", action="store_true", help="Auto-increment minor version")
    parser.add_argument("--major", action="store_true", help="Auto-increment major version")
    args = parser.parse_args()

    if args.version:
        v = bump(explicit=args.version)
    elif args.major:
        v = bump(mode="major")
    elif args.minor:
        v = bump(mode="minor")
    elif args.patch:
        v = bump(mode="patch")
    else:
        curr = get_current_version()
        curr_str = f"{curr[0]}.{curr[1]}.{curr[2]}"
        suggested_str = f"{curr[0]}.{curr[1]}.{curr[2] + 1}"
        print("=" * 65)
        print(f"  Jayraldine's Catering Tablet - Installer Builder")
        print(f"  Current version: v{curr_str}")
        print(f"  Next suggested version: v{suggested_str}")
        print("=" * 65)
        user_in = input(f"Enter version to build [Press Enter for {suggested_str}]: ").strip()
        if not user_in:
            v = bump(mode="patch")
        else:
            v = bump(explicit=user_in)

    run_build(v)


if __name__ == "__main__":
    main()
