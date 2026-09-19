# Inno Setup 6 Automated Packaging & Uninstaller Logic

## 1. Compiler Configuration
Compiled via Inno Setup 6 command-line compiler (`ISCC.exe`):
```powershell
ISCC.exe Catering_Present\jayraldines_catering\installer.iss
```

## 2. Installer Features
- Automatic detection and elevation to Administrator privileges.
- Creation of desktop icons, start menu entries, and uninstaller registry entries.
- Automated execution of firewall configuration scripts post-installation.
