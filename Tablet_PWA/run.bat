@echo off
REM Jayraldine's Catering — Kiosk PWA — local dev/run launcher (Windows).
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%backend"

if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo ==^> Creating venv and installing dependencies ^(first run only^)
    python -m venv "%SCRIPT_DIR%.venv"
    "%SCRIPT_DIR%.venv\Scripts\pip.exe" install --upgrade pip -q
    "%SCRIPT_DIR%.venv\Scripts\pip.exe" install -r requirements.txt -q
)

if "%HOST%"=="" set "HOST=0.0.0.0"
if "%PORT%"=="" set "PORT=8000"
echo ==^> Starting Jayraldine's Catering Kiosk on http://%HOST%:%PORT%
echo     On the same Wi-Fi, open http://^<this-machine's-LAN-IP^>:%PORT% on a tablet's Chrome and Install.
"%SCRIPT_DIR%.venv\Scripts\python.exe" -m uvicorn app:app --host %HOST% --port %PORT%
endlocal
