@echo off
title Jayraldine's Catering - Tablet Kiosk App
cd /d "%~dp0Tablet"

echo ============================================================
echo   Jayraldine's Catering - Self-Service Tablet Kiosk
echo ============================================================
echo.

REM Check for virtual environments
if exist "%~dp0Catering_Present\jayraldines_catering\venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0Catering_Present\jayraldines_catering\venv\Scripts\python.exe"
) else if exist "%~dp0Tablet\.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0Tablet\.venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo Starting Tablet Kiosk App with: %PY_EXE%
echo.

"%PY_EXE%" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application closed with error code %ERRORLEVEL%.
    pause
)
