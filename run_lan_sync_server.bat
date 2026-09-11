@echo off
title Jayraldine's Catering - Central LAN Sync Server Hub
cd /d "%~dp0"

echo ============================================================
echo   Jayraldine's Catering - Central LAN Sync Server Hub
echo ============================================================
echo.
echo Starting Central LAN Synchronization Server on Port 8000...
echo All tablets and remote laptops on the same Wi-Fi can connect.
echo.

if exist "%~dp0Catering_Present\jayraldines_catering\venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0Catering_Present\jayraldines_catering\venv\Scripts\python.exe"
    set "CWD=%~dp0Catering_Present\jayraldines_catering"
) else (
    set "PY_EXE=python"
    set "CWD=%~dp0"
)

cd /d "%CWD%"
"%PY_EXE%" -c "import utils.db_sync_server as s, time; print('='*50); print('Central Server Hub IP:', s.get_local_ip()); print('Port: 8000'); print('Database: PostgreSQL (jayraldines_catering)'); print('='*50); s.start_sync_server_background(); print('[READY] Server is active. Keep this window open or minimize.'); [time.sleep(3600) for _ in iter(int, 1)]"

pause
