# Installer Packaging Pipeline

## Build Steps
1. `package_installer.py` compresses application files into `app_package.zip`.
2. PyInstaller builds standalone `installer_wizard.py` executable with embedded zip.
3. Output saved to `installer_output/Jayraldines_Catering_Setup_v4.1.15.exe`.
