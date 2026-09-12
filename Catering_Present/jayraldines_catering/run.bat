@echo off
cd /d "%~dp0"
call venv\Scripts\activate
set DB_PASSWORD=12345678
set DB_ENGINE=postgres
python main.py
pause
