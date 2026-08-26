@echo off
REM Jayraldine's Catering - Tablet Installer Builder
REM
REM This builds the Android APK (the actual mobile/tablet installer) via
REM setup\build_android.bat. It used to run build_tablet_installer.py, a
REM PyInstaller + Inno Setup pipeline that produced a Windows DESKTOP .exe
REM installer instead — that's not usable on an Android tablet, so it has
REM been retired from this entrypoint. If you specifically want a Windows
REM desktop build of the Tablet app (e.g. for testing on a Windows laptop
REM with no physical tablet), run build_tablet_installer.py directly.
title Jayraldine's Catering - Tablet (Android) Installer Builder
cd /d "%~dp0"

echo ============================================================
echo   Jayraldine's Catering - Tablet Installer Builder (Android APK)
echo ============================================================
echo.

call "%~dp0setup\build_android.bat" %*

echo.
pause
