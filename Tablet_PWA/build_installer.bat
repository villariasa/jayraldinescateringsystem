@echo off
REM ============================================================================
REM Jayraldine's Catering — Kiosk PWA — Installer Builder (Windows)
REM Automatically creates .venv, installs dependencies, bumps version,
REM and builds the standalone installer package.
REM ============================================================================
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ============================================================================
echo   JAYRALDINE'S CATERING KIOSK SERVER - AUTO-INCREMENT INSTALLER BUILDER
echo ============================================================================

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

REM Setup Virtual Environment if missing
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo ==^> Creating Python virtual environment in .venv...
    python -m venv "%SCRIPT_DIR%.venv"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo ==^> Checking and installing dependencies...
"%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install --upgrade pip -q
"%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install -r "%SCRIPT_DIR%backend\requirements.txt" -q
"%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install pyinstaller -q

echo.
echo ==^> Running auto-increment installer build...
"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%build_installer.py" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed! Check the output above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ==^> Build completed successfully! Check the "installer_output" folder.
echo ============================================================================
pause
endlocal
