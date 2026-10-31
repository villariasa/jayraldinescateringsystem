# Release Notes — Jayraldine's Catering System v4.7.6
Release Date: October 31, 2026

## 1. Executive Summary
Version 4.7.6 introduces critical enhancements to the PDF receipt generation engine, ensuring native rendering across all Windows client environments without external Adobe Acrobat dependencies.

## 2. Key Highlights
- **Qt6Pdf & ImageFormats Bundling**: Fully bundled `Qt6Pdf.dll`, `Qt6PdfWidgets.dll`, and `plugins/imageformats/qpdf.dll` in the standalone package.
- **PyInstaller Specification Hardening**: Enhanced dynamic plugin inclusion covering platform backends, icon engines, and desktop styling themes.
- **Inno Setup v4.7.6 Packaging**: Streamlined setup installer with clean registry registration and automatic uninstaller generation.
- **Offline Tablet Synchronization**: Optimized vector signature and receipt canvas synchronization.
