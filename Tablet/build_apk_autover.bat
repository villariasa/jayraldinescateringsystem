@echo off
title Jayraldine's Catering - Mobile Android APK Builder
cd /d "%~dp0"

echo ============================================================
echo   Jayraldine's Catering - Android Mobile / Tablet APK Builder
echo ============================================================
echo.

REM Check for virtual environments
if exist "%~dp0..\Catering_Present\jayraldines_catering\venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0..\Catering_Present\jayraldines_catering\venv\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo [Step 1/2] Auto-incrementing Mobile APK version...
"%PY_EXE%" bump_version.py %*

echo.
echo [Step 2/2] Running Android APK Packaging...
call "%~dp0setup\build_android.bat"

echo.
pause
