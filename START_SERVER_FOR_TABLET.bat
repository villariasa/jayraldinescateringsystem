@echo off
title Jayraldine's Catering - Central Tablet Sync Server Hub
cd /d "%~dp0Catering_Present\jayraldines_catering"
cls
echo ====================================================================
echo      JAYRALDINE'S CATERING - CENTRAL TABLET SYNC SERVER HUB
echo ====================================================================
echo.

set "PY_EXE=%~dp0Catering_Present\jayraldines_catering\venv\Scripts\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"

echo [1/3] Detecting Local Wi-Fi / Hotspot IP address...
for /f "tokens=*" %%a in ('"%PY_EXE%" -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); (s.connect(('8.8.8.8', 80)) if True else None); print(s.getsockname()[0]); s.close()"') do set "SERVER_IP=%%a"
if "%SERVER_IP%"=="" set "SERVER_IP=127.0.0.1"

echo.
echo ====================================================================
echo   STATUS: SERVER IS ACTIVE AND BROADCASTING ON YOUR HOTSPOT / WI-FI!
echo ====================================================================
echo.
echo   - Local Server IP Address : %SERVER_IP%
echo   - Hub Sync Port           : 8000
echo   - Central Database        : PostgreSQL (jayraldines_catering)
echo.
echo   ------------------------------------------------------------------
echo   HOW TO TEST FROM YOUR TABLET RIGHT NOW:
echo   ------------------------------------------------------------------
echo   1. On your tablet, open Chrome or your browser and visit:
echo        http://%SERVER_IP%:8000/test
echo      You will see a green diagnostic screen confirming connection!
echo.
echo   2. In the Tablet Kiosk App (or Android APK):
echo      - Go to Settings (passcode: 12345678) -^> "Database & Sync"
echo      - Server IP : %SERVER_IP%
echo      - Port      : 8000
echo      - Tap "Save & Sync Now"
echo.
echo   Or open the Full Web Kiosk on your tablet browser:
echo        http://%SERVER_IP%:8000/index.html
echo.
echo ====================================================================
echo   KEEP THIS WINDOW OPEN WHILE USING THE TABLETS / KIOSK!
echo ====================================================================
echo.
echo [SERVER LOGS]:
"%PY_EXE%" run_daemon_server.py
pause
