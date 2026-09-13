@echo off
title Setup Central PostgreSQL Server and Migrate Data
cd /d "%~dp0"

echo ============================================================
echo   JAYRALDINE'S CATERING - SETUP CENTRAL POSTGRESQL SERVER
echo ============================================================
echo.
echo Running automated server configurator with Administrator rights...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0SETUP_POSTGRES_SERVER_AND_MIGRATE.ps1"

pause
