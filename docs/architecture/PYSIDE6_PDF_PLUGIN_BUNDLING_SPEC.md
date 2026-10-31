# PySide6 PDF Plugin Bundling & Runtime Isolation Specification

## 1. Architectural Challenge
In standalone PySide6 desktop packaging, dynamic PDF rasterizers frequently fail when `qpdf.dll` or `Qt6Pdf.dll` are stripped by aggressive PyInstaller binary pruning.

## 2. Solution Strategy
`package_installer.py` enforces explicit white-listing of the `Qt6Pdf` subsystem and ensures `imageformats/qpdf.dll` is preserved in the application runtime root.
