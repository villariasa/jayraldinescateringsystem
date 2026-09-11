@echo off
title Jayraldine's Catering — Standalone Tablet APK Builder
color 0A
cls

set "SCRIPT_DIR=%~dp0"
set "APK_PROJECT_DIR=%SCRIPT_DIR%Tablet_Android_APK"
set "PWA_FRONTEND_DIR=%SCRIPT_DIR%Tablet_PWA\frontend"

REM 1. Check for Python to use enhanced interactive builder
if exist "%SCRIPT_DIR%Catering_Present\jayraldines_catering\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%Catering_Present\jayraldines_catering\venv\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%Tablet\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%Tablet\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

REM Test Python availability
"%PYTHON_EXE%" -c "import sys" >nul 2>&1
if not errorlevel 1 (
    if exist "%SCRIPT_DIR%build_tablet_installer.py" (
        "%PYTHON_EXE%" "%SCRIPT_DIR%build_tablet_installer.py" %*
        pause
        exit /b 0
    )
)

REM ── Fallback Pure Batch Build ──────────────────────────────
echo =======================================================
echo    Jayraldine's Catering - Standalone APK Builder     
echo =======================================================
echo.

REM Extract current version from build.gradle
set "TABLET_VER=1.26.0"
if exist "%APK_PROJECT_DIR%\app\build.gradle" (
    for /f "tokens=2 delims=^"^" %%v in ('findstr /i "versionName" "%APK_PROJECT_DIR%\app\build.gradle"') do (
        set "TABLET_VER=%%v"
    )
)

if not "%~1"=="" set "TABLET_VER=%~1"
set "OUTPUT_APK_VER=%SCRIPT_DIR%jayraldines_catering_v%TABLET_VER%.apk"
set "OUTPUT_APK_UNI=%SCRIPT_DIR%jayraldines_catering.apk"

REM Setup Android SDK Environment
if "%ANDROID_HOME%"=="" (
    if exist "%LOCALAPPDATA%\Android\Sdk" (
        set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
    ) else if exist "%USERPROFILE%\AppData\Local\Android\Sdk" (
        set "ANDROID_HOME=%USERPROFILE%\AppData\Local\Android\Sdk"
    ) else (
        echo Error: Android SDK not found in %LOCALAPPDATA%\Android\Sdk
        pause
        exit /b 1
    )
)

echo ==^> Using Android SDK: %ANDROID_HOME%
echo ==^> Building Tablet Version: v%TABLET_VER%

REM Sync latest frontend files to APK assets
echo ==^> Syncing latest PWA frontend assets into APK...
if exist "%APK_PROJECT_DIR%\app\src\main\assets" (
    rd /s /q "%APK_PROJECT_DIR%\app\src\main\assets"
)
mkdir "%APK_PROJECT_DIR%\app\src\main\assets"
xcopy "%PWA_FRONTEND_DIR%\*" "%APK_PROJECT_DIR%\app\src\main\assets\" /s /e /y /q >nul

REM Remove previous build outputs to prevent stale files
if exist "%APK_PROJECT_DIR%\app\build\outputs\apk\debug\app-debug.apk" (
    del /f /q "%APK_PROJECT_DIR%\app\build\outputs\apk\debug\app-debug.apk" >nul 2>&1
)

REM Build APK with Gradle (clean assembleDebug guarantees fresh compilation)
echo ==^> Compiling fresh APK with Gradle...
cd /d "%APK_PROJECT_DIR%"
call "%APK_PROJECT_DIR%\gradlew.bat" clean assembleDebug --no-daemon

if errorlevel 1 (
    echo.
    echo ERROR: Gradle APK build failed. Check the error messages above.
    pause
    exit /b 1
)

REM Copy output APK to versioned and universal filenames
if exist "%APK_PROJECT_DIR%\app\build\outputs\apk\debug\app-debug.apk" (
    copy /y "%APK_PROJECT_DIR%\app\build\outputs\apk\debug\app-debug.apk" "%OUTPUT_APK_VER%" >nul
    copy /y "%APK_PROJECT_DIR%\app\build\outputs\apk\debug\app-debug.apk" "%OUTPUT_APK_UNI%" >nul
    echo.
    echo =======================================================
    echo   SUCCESS! APK Generated Successfully: 
    echo   Versioned File : %OUTPUT_APK_VER%
    echo   Universal File : %OUTPUT_APK_UNI%
    echo =======================================================
) else (
    echo Error: APK output file not found.
    pause
    exit /b 1
)

echo.
echo Done! You can now install %OUTPUT_APK_VER% onto your tablet.
pause
