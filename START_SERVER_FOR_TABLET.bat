@echo off
title Jayraldine's Catering - Central Tablet Sync Server Hub
cd /d "%~dp0Catering_Present\jayraldines_catering"
cls

set "PY_EXE=%~dp0Catering_Present\jayraldines_catering\venv\Scripts\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"

"%PY_EXE%" run_daemon_server.py
pause
