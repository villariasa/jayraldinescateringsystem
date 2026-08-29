@echo off
REM Shortcut to build Jayraldine's Catering Kiosk PWA Server Installer with auto-increment
setlocal
cd /d "%~dp0Tablet_PWA"
call "build_installer.bat" %*
endlocal
