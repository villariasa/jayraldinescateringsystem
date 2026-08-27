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

REM Auto-detect previously-downloaded Android wheels in the usual cache spot
REM or directly inside this Tablet folder, same convention build_android.sh
REM uses on Linux.
set "WHEEL_CACHE_DIR=%USERPROFILE%\.cache\pyside6_wheels"
if "%PYSIDE6_ANDROID_WHEEL%"=="" (
    for %%F in ("%WHEEL_CACHE_DIR%\PySide6*android*.whl" "%APP_DIR%\PySide6*android*.whl") do (
        if exist "%%F" if "%PYSIDE6_ANDROID_WHEEL%"=="" set "PYSIDE6_ANDROID_WHEEL=%%F"
    )
)
if "%SHIBOKEN6_ANDROID_WHEEL%"=="" (
    for %%F in ("%WHEEL_CACHE_DIR%\shiboken6*android*.whl" "%APP_DIR%\shiboken6*android*.whl") do (
        if exist "%%F" if "%SHIBOKEN6_ANDROID_WHEEL%"=="" set "SHIBOKEN6_ANDROID_WHEEL=%%F"
    )
)

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

REM python-for-android/buildozer refuses to run on Python 3.12+ ("Android
REM deployment requires Python version 3.11 or lower"). setup_windows.bat
REM creates the venv from whatever "python" resolves to on PATH, which on a
REM fresh Windows machine is often the latest installed version — check
REM here with a clear error instead of failing deep inside a buildozer stack
REM trace after the SDK/NDK download has already run.
REM
REM NOTE: values are captured via a temp .py file + temp output file, NOT
REM `for /f ('"!PY!" -c "...")')`. That pattern silently breaks in cmd.exe
REM whenever the Python one-liner contains parentheses/brackets (which
REM print(...) and list indexing always do) — cmd's parser mistakes them
REM for its own command-grouping syntax and truncates the command. Writing
REM a real .py file sidesteps quoting entirely.
set "TMP_PY=%TEMP%\jc_check_%RANDOM%.py"
set "TMP_OUT=%TEMP%\jc_out_%RANDOM%.txt"
>"%TMP_PY%" echo import sys
>>"%TMP_PY%" echo print(sys.version_info[0]*100+sys.version_info[1])
"!PY!" "%TMP_PY%" > "%TMP_OUT%"
set /p PYVER=<"%TMP_OUT%"
del "%TMP_PY%" "%TMP_OUT%" >nul 2>&1
if !PYVER! GTR 311 (
    echo ERROR: this environment's Python is too new for the Android build
    echo        ^(python-for-android requires Python 3.11 or lower^). Install
    echo        Python 3.11 from python.org, then delete "%VENV_DIR%" and
    echo        re-run setup\setup_windows.bat so it picks up 3.11, or point
    echo        it at a 3.11 interpreter explicitly.
    exit /b 1
)

set "TMP_PY=%TEMP%\jc_pyside_%RANDOM%.py"
set "TMP_OUT=%TEMP%\jc_out_%RANDOM%.txt"
>"%TMP_PY%" echo import PySide6
>>"%TMP_PY%" echo print(PySide6.__version__)
"!PY!" "%TMP_PY%" > "%TMP_OUT%"
set /p PYSIDE_VER=<"%TMP_OUT%"
del "%TMP_PY%" "%TMP_OUT%" >nul 2>&1

REM Self-heal a partial/corrupted PySide6 install (seen cause: antivirus
REM silently stripping files during pip's wheel extraction) — if the
REM deploy-tool's actual Python module or its requirements file are
REM missing, force a clean reinstall automatically instead of erroring out
REM and telling the user to run pip by hand.
REM
REM NOTE: pyside6-android-deploy.exe (the console-script .exe wrapper) is
REM deliberately NOT checked here — confirmed on a real machine that it's
REM simply absent from Windows PySide6 wheels even after a totally clean
REM reinstall. That's handled separately below by falling back to running
REM the module directly via `-m`, not treated as corruption.
for %%I in ("!PY!") do set "ENV_SCRIPTS=%%~dpI"
for %%I in ("!PY!") do set "ENV_SITEPKGS=%%~dpILib\site-packages"

if not exist "!ENV_SITEPKGS!\PySide6" (
    echo ==^> PySide6 is not installed. Installing...
    "!PY!" -m pip install "PySide6==%PYSIDE_VER%"
)

REM Auto-download the two Android target wheels if not already cached —
REM these are cross-compiled wheels (same file regardless of host OS), safe
REM to fetch automatically instead of making the user run curl by hand.
REM curl.exe ships built into Windows 10 1803+ / Windows 11.
set "WHEEL_ARCH=android_aarch64"
if /i "%TABLET_TARGET_ARCH%"=="x86_64" set "WHEEL_ARCH=android_x86_64"

if "%PYSIDE6_ANDROID_WHEEL%"=="" (
    if not exist "%WHEEL_CACHE_DIR%" mkdir "%WHEEL_CACHE_DIR%"
    set "PYSIDE6_ANDROID_WHEEL=%WHEEL_CACHE_DIR%\pyside6-%PYSIDE_VER%-%WHEEL_ARCH%.whl"
    echo ==^> Downloading PySide6 %PYSIDE_VER% Android wheel ^(~80MB, one-time^)...
    curl.exe -sL --fail -o "!PYSIDE6_ANDROID_WHEEL!" "https://download.qt.io/official_releases/QtForPython/pyside6/pyside6-%PYSIDE_VER%-%PYSIDE_VER%-cp311-cp311-%WHEEL_ARCH%.whl"
    if errorlevel 1 (
        del "!PYSIDE6_ANDROID_WHEEL!" >nul 2>&1
        echo ERROR: download failed. Check your internet connection, or manually
        echo        grab it from https://download.qt.io/official_releases/QtForPython/pyside6/
        echo        and save it into %WHEEL_CACHE_DIR%.
        exit /b 1
    )
)
if "%SHIBOKEN6_ANDROID_WHEEL%"=="" (
    if not exist "%WHEEL_CACHE_DIR%" mkdir "%WHEEL_CACHE_DIR%"
    set "SHIBOKEN6_ANDROID_WHEEL=%WHEEL_CACHE_DIR%\shiboken6-%PYSIDE_VER%-%WHEEL_ARCH%.whl"
    echo ==^> Downloading shiboken6 %PYSIDE_VER% Android wheel ^(one-time^)...
    curl.exe -sL --fail -o "!SHIBOKEN6_ANDROID_WHEEL!" "https://download.qt.io/official_releases/QtForPython/shiboken6/shiboken6-%PYSIDE_VER%-%PYSIDE_VER%-cp311-cp311-%WHEEL_ARCH%.whl"
    if errorlevel 1 (
        del "!SHIBOKEN6_ANDROID_WHEEL!" >nul 2>&1
        echo ERROR: download failed. Check your internet connection, or manually
        echo        grab it from https://download.qt.io/official_releases/QtForPython/shiboken6/
        echo        and save it into %WHEEL_CACHE_DIR%.
        exit /b 1
    )
)
echo ==^> Using PySide6 Android wheel: %PYSIDE6_ANDROID_WHEEL%
echo ==^> Using shiboken6 Android wheel: %SHIBOKEN6_ANDROID_WHEEL%

echo ==^> Installing Android-deploy Python dependencies
set "TMP_PY=%TEMP%\jc_reqs_%RANDOM%.py"
set "TMP_OUT=%TEMP%\jc_out_%RANDOM%.txt"
>"%TMP_PY%" echo import PySide6, os
>>"%TMP_PY%" echo print(os.path.join(os.path.dirname(PySide6.__file__), "scripts", "requirements-android.txt"))
"!PY!" "%TMP_PY%" > "%TMP_OUT%"
set /p ANDROID_REQS=<"%TMP_OUT%"
del "%TMP_PY%" "%TMP_OUT%" >nul 2>&1
if exist "!ANDROID_REQS!" (
    "!PY!" -m pip install -r "!ANDROID_REQS!"
) else (
    echo ==^> Installing buildozer and cython fallback dependencies...
    "!PY!" -m pip install "buildozer>=1.5.0" "cython<3.0.0"
)

REM pyside6-android-deploy is normally a console-script .exe wrapper in the
REM env's Scripts\ folder — but Windows PySide6 wheels don't reliably ship
REM that entry point (confirmed: still missing after a clean reinstall).
REM The actual tool is just a regular Python module underneath, so fall
REM back to running it directly via -m, which works regardless of whether
REM pip generated the .exe wrapper.
for %%I in ("!PY!") do set "ENV_SCRIPTS=%%~dpI"
set "DEPLOY_EXE=!ENV_SCRIPTS!pyside6-android-deploy.exe"
if not exist "!DEPLOY_EXE!" set "DEPLOY_EXE=!ENV_SCRIPTS!pyside6-deploy.exe"
set DEPLOY_CMD="!DEPLOY_EXE!"
if not exist "!DEPLOY_EXE!" (
    echo ==^> pyside6-android-deploy.exe not found — running python deploy module instead.
    set DEPLOY_CMD="!PY!" -m PySide6.scripts.deploy
)

echo ==^> Building Android APK (this can take a long time on first run —
echo     it downloads/builds a Python-for-Android toolchain)
REM Deliberately NOT passing -c pysidedeploy.spec here: that file in this
REM project has been hand-edited with another developer's machine-specific
REM absolute paths (wheel locations, a conda env path) that don't exist on
REM this machine. Passing all values explicitly via CLI flags avoids
REM silently falling back to those stale paths.
REM --name must NOT contain a space — it becomes the p4a distribution's
REM directory name, and a space in that path breaks the autotools chain
REM used to cross-compile libffi ("configure: error: C compiler cannot
REM create executables" — confirmed by reproducing it with a spaced name).
!DEPLOY_CMD! ^
    --name "JayraldinesCateringTablet" ^
    -f ^
    --local-libs="python3.11,plugins_platforms_qtforandroid" ^
    --wheel-pyside="%PYSIDE6_ANDROID_WHEEL%" ^
    --wheel-shiboken="%SHIBOKEN6_ANDROID_WHEEL%" ^
    --ndk-path="%ANDROID_NDK_ROOT%" ^
    --sdk-path="%ANDROID_SDK_ROOT%"

echo ==^> Done. Look for the generated .apk under %APP_DIR% (path reported above).
echo     Install on a tablet with: adb install -r ^<path-to-apk^>

endlocal
