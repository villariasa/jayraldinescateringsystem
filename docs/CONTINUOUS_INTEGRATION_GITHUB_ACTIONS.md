# Continuous Integration & Automated Release Packaging

## 1. GitHub Actions Workflows
- `build-windows-installer.yml`: Compiles PyInstaller executable bundles and Inno Setup `.exe` installers on `windows-latest` runners.
- `build-tablet-apk.yml`: Compiles Android APK packages with embedded PWA assets using Gradle on `ubuntu-latest` runners.
