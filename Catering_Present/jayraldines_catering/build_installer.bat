@echo off
title Jayraldine's Catering - Installer Builder
color 0A
cls
echo ======================================================================
echo           JAYRALDINE'S CATERING - CUSTOM INSTALLER BUILDER
echo ======================================================================
echo.

cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" build_installer.py

echo.
echo ======================================================================
echo Press any key to open the output folder and exit...
echo ======================================================================
pause >nul
if exist "installer_output" explorer "installer_output"
