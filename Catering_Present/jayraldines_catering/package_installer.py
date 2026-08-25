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

    # Ensure all critical PySide6 and OpenGL runtime DLLs are present in package
    pyside_src = root / "venv" / "Lib" / "site-packages" / "PySide6"
    pyside_dst = dist_app / "_internal" / "PySide6"
    if pyside_src.exists() and pyside_dst.exists():
        CRITICAL_DLLS = [
            "Qt6OpenGL.dll", "Qt6OpenGLWidgets.dll", "opengl32sw.dll",
            "QtOpenGL.pyd", "QtOpenGLWidgets.pyd", "Qt6Charts.dll",
            "Qt6ChartsQml.dll", "QtCharts.pyd", "pyside6.abi3.dll",
            "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll",
            "Qt6Network.dll", "Qt6PrintSupport.dll", "Qt6Svg.dll",
            "PySide6.dll", "shiboken6.dll"
        ]
        for f in CRITICAL_DLLS:
            s_file = pyside_src / f
            d_file = pyside_dst / f
            if s_file.exists() and not d_file.exists():
                shutil.copy2(s_file, d_file)

        # Remove heavy unused modules (WebEngine, 3D, multimedia codecs) to keep installer lightweight
        EXCLUDE_PREFIXES = [
            "Qt6WebEngine", "Qt6Quick3D", "Qt6Designer", "Qt6Pdf",
            "Qt6SpatialAudio", "Qt6VirtualKeyboard", "Qt6Sensors",
            "Qt6SerialPort", "Qt6Positioning", "Qt6Bluetooth", "Qt63D",
            "avcodec", "avformat", "avutil", "swscale", "swresample"
        ]
        for item in os.listdir(pyside_dst):
            if any(item.startswith(p) for p in EXCLUDE_PREFIXES):
                try:
                    os.remove(pyside_dst / item)
                except Exception:
                    pass

    zip_target = root / "app_package.zip"
    print(f"[1/3] Compressing application files into {zip_target.name}...")
    
    with zipfile.ZipFile(zip_target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
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
        "--exclude-module", "reportlab",
        "--exclude-module", "openpyxl",
        "--exclude-module", "psycopg2",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "numpy",
        "--exclude-module", "unittest",
        "--exclude-module", "PySide6.QtWebEngine",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtOpenGL",
        "--exclude-module", "PySide6.QtPdf",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.Qt3DCore",
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
