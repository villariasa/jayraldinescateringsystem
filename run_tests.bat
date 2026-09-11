@echo off
title Jayraldine's Catering - Automated Test Suite
color 0E
cls

cd /d "%~dp0Catering_Present\jayraldines_catering"

echo ============================================================
echo   Jayraldine's Catering - Running Automated Test Suite
echo ============================================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo Running unit tests with: %PY_EXE%
echo.

"%PY_EXE%" -m unittest tests/unit/test_centralized_server_and_sync.py tests/unit/test_auth_and_config.py

echo.
echo ============================================================
echo Tests complete.
echo ============================================================
pause
