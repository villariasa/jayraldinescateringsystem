@echo off
:: ==============================================================================
:: Jayraldine's Catering System — Windows Launcher
:: Double-click to run application on Windows
:: ==============================================================================
cd /d "%~dp0"

:: Activate virtual environment if present
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Set default PostgreSQL connection variables if not already set
if not defined DB_HOST set DB_HOST=localhost
if not defined DB_PORT set DB_PORT=5432
if not defined DB_USER set DB_USER=postgres
if not defined DB_PASSWORD set DB_PASSWORD=12345678

:: Launch main GUI application
python main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%.
    pause
)
