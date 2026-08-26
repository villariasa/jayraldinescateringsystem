@echo off
REM Jayraldine's Catering — Tablet App — Windows setup/run script.
REM Creates an isolated environment, installs dependencies, and launches the
REM app so you can test the tablet workflow on a Windows PC before deploying
REM to an actual Android tablet.
REM
REM Prefers a conda env when conda is available on PATH, because
REM "python -m venv" frequently fails on conda's Python with an ensurepip
REM error. Falls back to a plain venv otherwise.
REM
REM IMPORTANT: we call the target interpreter by its *full path*, never via
REM "conda run ... python" or a bare "python"/"pip" on PATH — both can
REM resolve to a different python.exe that shadows the one actually inside
REM the env we just created, silently installing packages the app can never
REM see. A full path can't be shadowed.

setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%.."
set "VENV_DIR=%APP_DIR%\.venv"
set "CONDA_ENV_NAME=jayraldines_tablet"

cd /d "%APP_DIR%"

where conda >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ==^> Conda detected — using a conda environment

    for /f "delims=" %%B in ('conda info --base') do set "CONDA_BASE=%%B"
    set "ENV_PREFIX=!CONDA_BASE!\envs\%CONDA_ENV_NAME%"
    set "PY=!ENV_PREFIX!\python.exe"

    if not exist "!PY!" (
        echo ==^> Creating conda environment '%CONDA_ENV_NAME%'
        conda create -n %CONDA_ENV_NAME% python=3.11 -y
    )

    if not exist "!PY!" (
        echo ERROR: expected interpreter not found at !PY!
        exit /b 1
    )
    echo ==^> Using interpreter: !PY!

    echo ==^> Installing dependencies
    "!PY!" -m pip install --upgrade pip >nul
    "!PY!" -m pip install -r requirements.txt

    echo ==^> Verifying PySide6 is importable in the target environment
    "!PY!" -c "import PySide6"
    if errorlevel 1 (
        echo ERROR: PySide6 installed but is not importable via !PY!.
        exit /b 1
    )

    echo ==^> Launching Tablet App
    "!PY!" main.py %*
    goto :eof
)

set "PY=%VENV_DIR%\Scripts\python.exe"
if not exist "!PY!" (
    if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
    echo ==^> Creating virtual environment at %VENV_DIR%
    python -m venv "%VENV_DIR%"
    if not exist "!PY!" (
        echo ERROR: venv creation failed. If you have conda/Anaconda installed,
        echo        run this from an "Anaconda Prompt" instead so it is detected above.
        exit /b 1
    )
)

echo ==^> Using interpreter: !PY!

echo ==^> Installing dependencies
"!PY!" -m pip install --upgrade pip >nul
"!PY!" -m pip install -r requirements.txt

echo ==^> Verifying PySide6 is importable in the target environment
"!PY!" -c "import PySide6"
if errorlevel 1 (
    echo ERROR: PySide6 installed but is not importable via !PY!.
    exit /b 1
)

echo ==^> Launching Tablet App
"!PY!" main.py %*

endlocal
