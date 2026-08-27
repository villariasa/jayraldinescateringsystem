@echo off
setlocal
set ADB="%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"

echo ============================================================
echo   Jayraldine's Catering - Live Device Crash Log Capture
echo ============================================================
echo.

%ADB% devices
echo.
echo Checking for Python / PySide / Qt crash logs on your device...
echo.
%ADB% logcat -d -s python:V Python:V python-for-android:V Qt:V AndroidRuntime:E DEBUG:E
echo.
echo ============================================================
echo If you see 'unauthorized' above, please unlock your phone
echo and tap 'Always allow from this computer' then run this again.
echo ============================================================
pause
