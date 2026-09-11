@echo off
title Jayraldine's Catering - Server Setup & Installer Wizard
color 0B
cls

:: Check for Administrator permissions (required for Windows Firewall & Network profile setup)
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ============================================================
    echo   [ADMINISTRATOR PERMISSION REQUIRED]
    echo   Windows Firewall and Private Network Profile setup require
    echo   Administrator privileges. Requesting elevation now...
    echo ============================================================
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"\"%~f0\"\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0Catering_Present\jayraldines_catering"

echo ============================================================
echo   Jayraldine's Catering - Setup & Installation Wizard
echo ============================================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo Starting Installer Wizard GUI with: %PY_EXE%
echo.

"%PY_EXE%" installer_wizard.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTE] Installer Wizard closed with code %ERRORLEVEL%.
    pause
)
