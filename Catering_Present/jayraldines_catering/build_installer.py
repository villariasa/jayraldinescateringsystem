"""
Interactive Installer Builder for Jayraldine's Catering System.
Allows entering a custom version number and builds the complete standalone setup installer executable.

Usage:
  Interactive:
    python build_installer.py
  Direct:
    python build_installer.py --version 4.1.2
"""

import sys
import os
import shutil
import argparse
import datetime
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def get_current_version() -> str:
    version_file = ROOT / "version.py"
    if version_file.exists():
        for line in version_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "4.1.1"


def set_version(new_version: str):
    new_version = new_version.strip()
    if not new_version:
        new_version = get_current_version()
    
    # 1. Update version.py
    today_str = datetime.date.today().strftime("%Y.%m.%d")
    version_content = f'''"""
Centralized Version and Application Metadata for Jayraldine's Catering.
"""

__version__ = "{new_version}"
APP_NAME = "Jayraldine's Catering"
BUILD_ID = "{today_str}-v{new_version}"
'''
    (ROOT / "version.py").write_text(version_content, encoding="utf-8")
    print(f"  [OK] Updated version.py -> v{new_version}")

    # 2. Update installer.iss if present
    iss_file = ROOT / "installer.iss"
    if iss_file.exists():
        lines = []
        for line in iss_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("AppVersion="):
                lines.append(f"AppVersion={new_version}")
            elif line.startswith("OutputBaseFilename="):
                lines.append(f"OutputBaseFilename=Jayraldines_Catering_Setup_v{new_version}")
            else:
                lines.append(line)
        iss_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  [OK] Updated installer.iss -> v{new_version}")

    return new_version


def run_build(version: str):
    print("=" * 65)
    print(f"  JAYRALDINE'S CATERING — COMPILING INSTALLER v{version}")
    print("=" * 65)

    py_exe = ROOT / "venv" / "Scripts" / "python.exe"
    if not py_exe.exists():
        py_exe = Path(sys.executable)

    pyinstaller_exe = ROOT / "venv" / "Scripts" / "pyinstaller.exe"
    if not pyinstaller_exe.exists():
        pyinstaller_exe = Path("pyinstaller")

    # Step 1: Build Application Distribution
    print("\n[Step 1/2] Compiling Application Core via PyInstaller...")
    spec_file = ROOT / "jayraldines.spec"
    if not spec_file.exists():
        print(f"[ERROR] Spec file not found: {spec_file}")
        sys.exit(1)

    cmd_app = [str(pyinstaller_exe), str(spec_file), "--noconfirm"]
    res1 = subprocess.run(cmd_app, cwd=ROOT)
    if res1.returncode != 0:
        print("\n[ERROR] Failed to compile application.")
        sys.exit(res1.returncode)
    print("  [OK] Application Core built successfully.")

    # Step 2: Package Installer Wizard & Single-File Exe
    print("\n[Step 2/2] Packaging Standalone Setup Executable...")
    pkg_script = ROOT / "package_installer.py"
    if not pkg_script.exists():
        print(f"[ERROR] package_installer.py not found: {pkg_script}")
        sys.exit(1)

    cmd_pkg = [str(py_exe), str(pkg_script)]
    res2 = subprocess.run(cmd_pkg, cwd=ROOT)
    if res2.returncode != 0:
        print("\n[ERROR] Failed to package installer executable.")
        sys.exit(res2.returncode)

    output_dir = ROOT / "installer_output"
    target_exe = output_dir / f"Jayraldines_Catering_Setup_v{version}.exe"
    universal_exe = output_dir / "Jayraldines_Catering_Setup.exe"

    if universal_exe.exists() and not target_exe.exists():
        shutil.copy2(universal_exe, target_exe)

    print("\n" + "=" * 65)
    print("  INSTALLER BUILD COMPLETE!")
    print("=" * 65)
    if target_exe.exists():
        size_mb = target_exe.stat().st_size / (1024 * 1024)
        print(f"\n  Executable : {target_exe.name}")
        print(f"  Full Path  : {target_exe}")
        print(f"  File Size  : {size_mb:.2f} MB")
        print(f"  Universal  : {universal_exe}")
    print("=" * 65)


def auto_increment_version(curr: str) -> str:
    """
    Auto-increments the build / patch number of a version string.
    Example: 4.1.2 -> 4.1.3, 4.1.9 -> 4.1.10, 4.1 -> 4.2
    """
    parts = curr.strip().split(".")
    if not parts:
        return "4.1.1"
    try:
        last_num = int(parts[-1])
        parts[-1] = str(last_num + 1)
        return ".".join(parts)
    except ValueError:
        return f"{curr}.1"


def main():
    parser = argparse.ArgumentParser(description="Auto-Version Installer Builder for Jayraldine's Catering")
    parser.add_argument("-v", "--version", type=str, help="Override version string (e.g. 4.2.0)", default=None)
    parser.add_argument("--major", action="store_true", help="Bump 1st digit (Major)")
    parser.add_argument("--module", action="store_true", help="Bump 2nd digit (Module)")
    parser.add_argument("--even", "--db", action="store_true", help="Bump 3rd digit to next EVEN (DB/data model)")
    parser.add_argument("--odd", "--fix", action="store_true", help="Bump 3rd digit to next ODD (Bug fix)")
    args = parser.parse_args()

    curr = get_current_version()

    # Try office 3-digit version detector
    root_proj = ROOT.parent.parent
    sys.path.insert(0, str(root_proj))
    try:
        from bump_version import compute_new_version, detect_change_type, run_git
        last_commit = run_git(["log", "-n", "1", "--pretty=format:%H", "--", str(ROOT / "version.py")])
        if args.major:
            b_type = "major"
        elif args.module:
            b_type = "module"
        elif getattr(args, "even", False) or getattr(args, "db", False):
            b_type = "even"
        elif getattr(args, "odd", False) or getattr(args, "fix", False):
            b_type = "odd"
        else:
            b_type, _ = detect_change_type(last_commit, "Catering_Present")
        next_ver = compute_new_version(curr, b_type)
    except Exception:
        next_ver = auto_increment_version(curr)

    if args.version:
        ver = args.version.strip()
    else:
        ver = next_ver
        print("\n=============================================================")
        print("  JAYRALDINE'S CATERING — OFFICE 3-DIGIT INSTALLER BUILDER")
        print("=============================================================")
        print(f"  Previous Version : v{curr}")
        print(f"  Target Version   : v{ver} (Auto-Incremented)")
        print("=============================================================")

    final_ver = set_version(ver)
    run_build(final_ver)


if __name__ == "__main__":
    main()
