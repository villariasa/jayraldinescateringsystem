@echo off
REM Jayraldine's Catering — Tablet App — Android APK build script (Windows).
REM
REM Wraps PySide6's official `pyside6-android-deploy` tool. This produces an
REM installable .apk you can side-load onto an Android tablet, built entirely
REM from a Windows machine (no Linux/WSL required).
REM
REM ── One-time prerequisites (outside this script, on the build machine) ──
REM   1. Android SDK + NDK installed (Android Studio's SDK Manager is the
REM      easiest way, or the standalone `sdkmanager.bat` command-line tools).
REM   2. A JDK (Java 17 recommended for recent Android Gradle Plugin versions).
REM   3. Environment variables set before running this script, e.g.:
REM        set ANDROID_SDK_ROOT=C:\Users\you\AppData\Local\Android\Sdk
REM        set ANDROID_NDK_ROOT=%ANDROID_SDK_ROOT%\ndk\<version>
REM        set JAVA_HOME=C:\Program Files\Java\jdk-17
REM   4. setup\setup_windows.bat already run at least once (this script
REM      reuses whichever environment it created — conda env or .venv).
REM
REM Consult Qt's official "Deploying to Android" documentation for the exact
REM PySide6 version you have installed — the deploy tool's CLI flags have
REM changed between minor Qt releases, so treat the flags below as a
REM starting point and adjust to match `pyside6-android-deploy --help` output
REM for your installed version.

setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%.."
set "VENV_DIR=%APP_DIR%\.venv"
set "CONDA_ENV_NAME=jayraldines_tablet"

cd /d "%APP_DIR%"

REM Unlike bash's ${VAR:-}, an undefined %VAR% expands to the literal text
REM "%VAR%" in cmd.exe rather than an empty string — define these explicitly
REM so the --wheel-pyside/--wheel-shiboken args below come out empty, not
REM garbage, when the caller hasn't set them.
if not defined PYSIDE6_ANDROID_WHEEL set "PYSIDE6_ANDROID_WHEEL="
if not defined SHIBOKEN6_ANDROID_WHEEL set "SHIBOKEN6_ANDROID_WHEEL="

if "%ANDROID_SDK_ROOT%"=="" (
    if exist "%LOCALAPPDATA%\Android\Sdk" set "ANDROID_SDK_ROOT=%LOCALAPPDATA%\Android\Sdk"
)
if "%ANDROID_NDK_ROOT%"=="" if not "%ANDROID_SDK_ROOT%"=="" (
    for /d %%D in ("%ANDROID_SDK_ROOT%\ndk\*") do set "ANDROID_NDK_ROOT=%%D"
)

if "%ANDROID_SDK_ROOT%"=="" (
    echo ERROR: ANDROID_SDK_ROOT must be set. See the prerequisites comment
    echo        block at the top of this script.
    exit /b 1
)
if "%ANDROID_NDK_ROOT%"=="" (
    echo ERROR: ANDROID_NDK_ROOT must be set. See the prerequisites comment
    echo        block at the top of this script.
    exit /b 1
)

REM Locate the same interpreter setup_windows.bat would have created —
REM prefer the conda env if present, else the plain venv. Always call the
REM interpreter by its full path (never a bare "python"/"pip" on PATH),
REM for the same shadowing reasons documented in setup_windows.bat.
set "PY="
where conda >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "delims=" %%B in ('conda info --base') do set "CONDA_BASE=%%B"
    set "CANDIDATE=!CONDA_BASE!\envs\%CONDA_ENV_NAME%\python.exe"
    if exist "!CANDIDATE!" set "PY=!CANDIDATE!"
)
if "!PY!"=="" (
    if exist "%VENV_DIR%\Scripts\python.exe" set "PY=%VENV_DIR%\Scripts\python.exe"
)
if "!PY!"=="" (
    echo ERROR: no environment found. Run setup\setup_windows.bat first.
    exit /b 1
)
echo ==^> Using interpreter: !PY!

echo ==^> Installing Android-deploy Python dependencies
for /f "delims=" %%R in ('"!PY!" -c "import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), 'scripts', 'requirements-android.txt'))"') do set "ANDROID_REQS=%%R"
"!PY!" -m pip install -r "!ANDROID_REQS!"

REM pyside6-android-deploy is a console-script entry point installed into
REM the same env's Scripts\ folder as python.exe (mirrors how build_android.sh
REM calls it from the venv's bin\ on Linux) — call it by full path, same
REM shadowing rationale as above.
for %%I in ("!PY!") do set "ENV_SCRIPTS=%%~dpI"
set "DEPLOY_EXE=!ENV_SCRIPTS!pyside6-android-deploy.exe"
if not exist "!DEPLOY_EXE!" (
    echo ERROR: pyside6-android-deploy.exe not found at !DEPLOY_EXE!.
    echo        The requirements-android.txt install above may have failed.
    exit /b 1
)

echo ==^> Building Android APK (this can take a long time on first run —
echo     it downloads/builds a Python-for-Android toolchain)
"!DEPLOY_EXE!" ^
    --name "JayraldinesCateringTablet" ^
    --wheel-pyside="%PYSIDE6_ANDROID_WHEEL%" ^
    --wheel-shiboken="%SHIBOKEN6_ANDROID_WHEEL%" ^
    --ndk-path="%ANDROID_NDK_ROOT%" ^
    --sdk-path="%ANDROID_SDK_ROOT%" ^
    -c "%APP_DIR%\pysidedeploy.spec"

echo ==^> Done. Look for the generated .apk under %APP_DIR% (path reported above).
echo     Install on a tablet with: adb install -r ^<path-to-apk^>

endlocal
