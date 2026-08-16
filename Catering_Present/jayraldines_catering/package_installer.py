"""
Helper script to package dist/JayraldinesCatering into a single standalone installer executable.
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

def create_installer():
    root = Path(__file__).resolve().parent
    dist_app = root / "dist" / "JayraldinesCatering"
    
    if not dist_app.exists():
        print("[Error] dist/JayraldinesCatering not found. Run PyInstaller first.")
        sys.exit(1)
        
    output_dir = root / "installer_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    zip_target = root / "app_package.zip"
    print(f"[1/3] Compressing application files into {zip_target.name}...")
    
    with zipfile.ZipFile(zip_target, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder, _, files in os.walk(dist_app):
            for f in files:
                file_path = Path(folder) / f
                arc_name = file_path.relative_to(dist_app)
                zf.write(file_path, arc_name)
                
    print(f"  Package size: {zip_target.stat().st_size / (1024*1024):.2f} MB")
    
    print("[2/3] Compiling Setup Executable with PyInstaller...")
    pyinstaller = root / "venv" / "Scripts" / "pyinstaller.exe"
    if not pyinstaller.exists():
        pyinstaller = "pyinstaller"
        
    cmd = [
        str(pyinstaller),
        "installer_wizard.py",
        "--onefile",
        "--windowed",
        "--name", "Jayraldines_Catering_Setup",
        "--icon", "assets/logo.ico",
        "--add-data", f"app_package.zip;.",
        "--add-data", f"assets;assets",
        "--distpath", str(output_dir),
        "--noconfirm"
    ]
    
    res = subprocess.run(cmd, cwd=root)
    if res.returncode != 0:
        print("[Error] PyInstaller failed to compile installer wizard.")
        sys.exit(res.returncode)
        
    try:
        from version import __version__
    except ImportError:
        __version__ = "1.3.1"

    setup_exe = output_dir / "Jayraldines_Catering_Setup.exe"
    versioned_exe = output_dir / f"Jayraldines_Catering_Setup_v{__version__}.exe"
    if setup_exe.exists():
        shutil.copy2(setup_exe, versioned_exe)

    print("=" * 60)
    print(f"[3/3] INSTALLER READY:")
    print(f"  -> {setup_exe.name} ({setup_exe.stat().st_size / (1024*1024):.2f} MB)")
    print(f"  -> {versioned_exe.name} ({versioned_exe.stat().st_size / (1024*1024):.2f} MB)")
    print("=" * 60)

if __name__ == "__main__":
    create_installer()
