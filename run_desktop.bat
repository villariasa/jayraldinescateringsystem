@echo off
title Jayraldine's Catering - Desktop Application
color 0A
cls

cd /d "%~dp0Catering_Present\jayraldines_catering"

echo ============================================================
echo   Jayraldine's Catering - Management System (Desktop)
echo ============================================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo Starting application using: %PY_EXE%
echo.
echo Login Credentials:
echo   Username: admin
echo   Password: Admin1234!
echo.

"%PY_EXE%" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTE] Application exited with code %ERRORLEVEL%.
    pause
)
