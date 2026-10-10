@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

:: 1. Check default Git Bash locations
if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%SCRIPT_DIR%autocommit.sh" %*
    goto :end
)

if exist "C:\Program Files\Git\usr\bin\bash.exe" (
    "C:\Program Files\Git\usr\bin\bash.exe" "%SCRIPT_DIR%autocommit.sh" %*
    goto :end
)

if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    "C:\Program Files (x86)\Git\bin\bash.exe" "%SCRIPT_DIR%autocommit.sh" %*
    goto :end
)

if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" (
    "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" "%SCRIPT_DIR%autocommit.sh" %*
    goto :end
)

:: 2. Try bash from PATH
where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
    bash "%SCRIPT_DIR%autocommit.sh" %*
    goto :end
)

:: 3. Try sh from PATH
where sh >nul 2>nul
if %ERRORLEVEL% equ 0 (
    sh "%SCRIPT_DIR%autocommit.sh" %*
    goto :end
)

echo.
echo [ERROR] Git Bash was not found on your system to run autocommit.sh.
echo Please ensure Git for Windows is installed (https://git-scm.com/download/win).
echo.
pause
exit /b 1

:end
exit /b %ERRORLEVEL%
