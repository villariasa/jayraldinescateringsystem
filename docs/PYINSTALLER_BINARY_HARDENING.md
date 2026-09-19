# Standalone PySide6 Windows Executable Packaging Specification

## 1. PyInstaller Build Options
- **Windowed Mode (`-w`)**: Suppresses background console terminal.
- **UPX Compression**: Compresses compiled binary payload by ~30%.
- **Excluded Modules**: Strips unused Qt modules (`QtWebEngine`, `QtQuick`, `Qt3D`) to minimize final installer size.

## 2. Target Executable
Produces `jayraldines_catering.exe` in `dist/` with high-resolution 256x256 embedded application icon.
