# Installer Executable Packaging & Code Signing Guide

## 1. Packaging Toolchain
- **PyInstaller**: Packages Python application, Qt libraries, and dependencies into standalone executable bundles.
- **Inno Setup 6**: Generates modern Windows installer wizards with UAC elevation, desktop shortcuts, and firewall setup scripts.

## 2. Security Verification
- Executables are compiled with embedded manifests requesting `requireAdministrator` privileges for system-level configuration.
- Checksum hashes (SHA-256) are published alongside release binaries for integrity verification.
