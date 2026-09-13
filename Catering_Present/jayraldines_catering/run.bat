@echo off
cd /d "%~dp0"
call venv\Scripts\activate
rem Uses database engine configured in Settings (default: SQLite embedded)
rem set DB_ENGINE=postgres
python main.py
pause
