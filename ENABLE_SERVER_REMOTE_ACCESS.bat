@echo off
title Jayraldine's Catering - Enable Server Remote Access
setlocal enabledelayedexpansion

:: Check for Administrator elevation
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [Requesting Administrator Permission...]
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

echo ============================================================
echo   ENABLING REMOTE WORKSTATION ACCESS ON PC SERVER
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0enable_server_remote_access.ps1"

echo.
pause
