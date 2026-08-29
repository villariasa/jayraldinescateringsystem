#!/usr/bin/env python3
"""
Installer builder for the Jayraldine's Catering Kiosk PWA server.

Bundles the FastAPI backend + PWA frontend into a standalone executable (via PyInstaller)
and creates a Windows installer (via Inno Setup) or a portable zip package.
Automatically increments the version number on every build run.

Usage:
  ./build_installer.py                 # Auto-increments patch (e.g., 1.0.0 -> 1.0.1)
  ./build_installer.py --bump minor    # Increments minor (e.g., 1.0.0 -> 1.1.0)
  ./build_installer.py --bump major    # Increments major (e.g., 1.0.0 -> 2.0.0)
  ./build_installer.py --version 1.5.0 # Forces explicit version
  ./build_installer.py --no-bump       # Builds with current version without incrementing
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
VERSION_FILE = BACKEND_DIR / "version.py"


def get_current_version() -> str:
    """Read the current version from backend/version.py."""
    if not VERSION_FILE.exists():
        return "1.0.0"
    text = VERSION_FILE.read_text(encoding="utf-8")
    m = re.search(r'VERSION\s*=\s*"([^"]+)"', text)
    if not m:
        return "1.0.0"
    return m.group(1)


def increment_version(version: str, bump_type: str = "patch") -> str:
    """Increment semantic version string (major.minor.patch)."""
    parts = version.split(".")
    while len(parts) < 3:
        parts.append("0")
    
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
        if match:
            major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
        else:
            major, minor, patch = 1, 0, 0

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    return f"{major}.{minor}.{patch}"


def save_version(version: str) -> None:
    """Persist new version into backend/version.py."""
    content = f'"""Version stamp for the Kiosk PWA server installer. Auto-incremented by build_installer.py."""\nVERSION = "{version}"\n'
    VERSION_FILE.write_text(content, encoding="utf-8")


def find_python() -> Path:
    """Locate the best python executable."""
    conda_prefix = os.environ.get("CONDA_PREFIX")
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
    ]
    if conda_prefix:
        candidates.append(Path(conda_prefix) / ("python.exe" if sys.platform.startswith("win") else "bin/python"))
    candidates.extend([
        Path.home() / "miniconda3" / "bin" / "python",
        Path.home() / "miniconda3" / "python.exe",
        Path(sys.executable),
    ])
    for c in candidates:
        if c.is_file():
            return c
    return Path(sys.executable)


def ensure_pyinstaller(py_exe: Path) -> Path:
    """Ensure PyInstaller is installed in the python environment."""
    pyinstaller = py_exe.parent / ("pyinstaller.exe" if sys.platform.startswith("win") else "pyinstaller")
    if pyinstaller.exists():
        return pyinstaller

    try:
        res = subprocess.run([str(py_exe), "-m", "PyInstaller", "--version"], capture_output=True, text=True)
        if res.returncode == 0:
            return py_exe
    except Exception:
        pass

    print("==> Installing PyInstaller...")
    subprocess.run([str(py_exe), "-m", "pip", "install", "pyinstaller", "-q"], check=True)
    if pyinstaller.exists():
        return pyinstaller
    return py_exe


def find_iscc() -> Path | None:
    """Find Inno Setup Compiler executable."""
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]
    which_iscc = shutil.which("iscc") or shutil.which("ISCC.exe")
    if which_iscc:
        candidates.append(Path(which_iscc))

    for c in candidates:
        if c.is_file():
            return c
    return None


def create_inno_script(version: str) -> Path:
    """Generate Inno Setup script with auto-start and desktop icons."""
    dist_dir = BACKEND_DIR / "dist" / "JayraldinesCateringKioskServer"
    output_dir = ROOT / "installer_output"
    iss_content = f"""[Setup]
AppName=Jayraldine's Catering Kiosk Server
AppVersion={version}
AppPublisher=Jayraldine's Catering Services
DefaultDirName={{autopf}}\\JayraldinesCateringKioskServer
DefaultGroupName=Jayraldine's Catering Kiosk Server
OutputDir={output_dir}
OutputBaseFilename=Jayraldines_Kiosk_Server_Setup_v{version}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"
Name: "autostart"; Description: "Start the kiosk server automatically when this PC turns on (recommended)"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "{dist_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\Jayraldine's Catering Kiosk Server"; Filename: "{{app}}\\JayraldinesCateringKioskServer.exe"
Name: "{{autodesktop}}\\Jayraldine's Catering Kiosk Server"; Filename: "{{app}}\\JayraldinesCateringKioskServer.exe"; Tasks: desktopicon
Name: "{{userstartup}}\\Jayraldine's Catering Kiosk Server"; Filename: "{{app}}\\JayraldinesCateringKioskServer.exe"; Tasks: autostart

[Run]
Filename: "{{app}}\\JayraldinesCateringKioskServer.exe"; Description: "Start the kiosk server now"; Flags: nowait postinstall skipifsilent
"""
    iss_path = ROOT / "kiosk_server_installer.iss"
    iss_path.write_text(iss_content, encoding="utf-8")
    return iss_path


def make_zip_archive(zip_filepath_without_ext: Path, source_dir: Path) -> Path:
    """Create a zip archive of source_dir with automatic fallbacks."""
    target_zip = Path(f"{zip_filepath_without_ext}.zip")
    
    # 1. Try zipfile module
    try:
        import zipfile
        compression = zipfile.ZIP_STORED
        try:
            import zlib
            compression = zipfile.ZIP_DEFLATED
        except Exception:
            pass

        with zipfile.ZipFile(target_zip, "w", compression=compression) as zf:
            for file in source_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, arcname=file.relative_to(source_dir))
        return target_zip
    except Exception:
        pass

    # 2. Try shutil.make_archive
    try:
        shutil.make_archive(str(zip_filepath_without_ext), "zip", source_dir)
        return target_zip
    except Exception:
        pass

    # 3. Try system zip CLI
    try:
        subprocess.run(["zip", "-rq", str(target_zip), "."], cwd=source_dir, check=True)
        return target_zip
    except Exception:
        pass

    # 4. Fallback to tar.gz
    shutil.make_archive(str(zip_filepath_without_ext), "gztar", source_dir)
    return Path(f"{zip_filepath_without_ext}.tar.gz")


def run_build(version: str):
    print("=" * 70)
    print(f"  JAYRALDINE'S CATERING KIOSK SERVER — BUILDING INSTALLER v{version}")
    print("=" * 70)

    py_exe = find_python()
    pyinstaller_target = ensure_pyinstaller(py_exe)
    print(f"Using Python interpreter: {py_exe}")
    print(f"Target Version:           {version}")

    print("\n[Step 1/2] Compiling Kiosk Server with PyInstaller...")
    spec_file = BACKEND_DIR / "pwa_server.spec"
    
    if pyinstaller_target.name.startswith("python"):
        cmd = [str(pyinstaller_target), "-m", "PyInstaller", str(spec_file), "--noconfirm"]
    else:
        cmd = [str(pyinstaller_target), str(spec_file), "--noconfirm"]

    res = subprocess.run(cmd, cwd=BACKEND_DIR)
    if res.returncode != 0:
        print(f"\n[ERROR] PyInstaller compilation failed with code {res.returncode}")
        sys.exit(res.returncode)

    output_dir = ROOT / "installer_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n[Step 2/2] Creating Installer Package...")
    iscc = find_iscc()
    if iscc:
        iss_script = create_inno_script(version)
        print(f"Found Inno Setup Compiler: {iscc}")
        res_inno = subprocess.run([str(iscc), str(iss_script)], cwd=ROOT)
        if res_inno.returncode == 0:
            setup_exe = output_dir / f"Jayraldines_Kiosk_Server_Setup_v{version}.exe"
            print("\n" + "=" * 70)
            print(f"  🎉 SUCCESS! Windows Installer Created: v{version}")
            print(f"  Path: {setup_exe}")
            print("=" * 70)
            print("  This installer can be run on the counter PC to install the server,")
            print("  create Start Menu & Desktop shortcuts, and set up auto-start on boot.")
            return setup_exe

    # Fallback to portable zip
    zip_base = output_dir / f"Jayraldines_Kiosk_Server_Portable_v{version}"
    dist_folder = BACKEND_DIR / "dist" / "JayraldinesCateringKioskServer"
    print(f"Creating portable archive: {zip_base}.zip")
    zip_path = make_zip_archive(zip_base, dist_folder)

    print("\n" + "=" * 70)
    print(f"  🎉 SUCCESS! Portable Package Created: v{version}")
    print(f"  Path: {zip_path}")
    print(f"  Distribution folder: {dist_folder}")
    print("=" * 70)
    return zip_path


def main():
    parser = argparse.ArgumentParser(description="Jayraldine's Catering Kiosk Server Installer Builder")
    parser.add_argument("--version", type=str, default=None, help="Explicit version number (e.g. 1.2.0)")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch", help="Version bump level (default: patch)")
    parser.add_argument("--no-bump", action="store_true", help="Do not increment version; keep current version")
    args = parser.parse_args()

    current_ver = get_current_version()

    if args.version:
        new_version = args.version
        save_version(new_version)
        print(f"==> Set explicit version: {new_version}")
    elif args.no_bump:
        new_version = current_ver
        print(f"==> Keeping current version: {new_version}")
    else:
        new_version = increment_version(current_ver, bump_type=args.bump)
        save_version(new_version)
        print(f"==> Auto-incremented version: {current_ver} -> {new_version} ({args.bump} bump)")

    run_build(new_version)


if __name__ == "__main__":
    main()
