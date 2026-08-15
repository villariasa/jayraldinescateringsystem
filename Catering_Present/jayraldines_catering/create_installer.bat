@echo off
cd /d "%~dp0"
call venv\Scripts\activate
echo Building Standalone Executable...
python -m PyInstaller jayraldines.spec --noconfirm
echo Packaging Installer...
python package_installer.py
pause
