@echo off
title Jayraldine's Catering - Tablet Installer Builder
cd /d "%~dp0"

echo ============================================================
echo   Jayraldine's Catering - Tablet Installer Builder
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

"%PY_EXE%" build_tablet_installer.py %*

echo.
pause
