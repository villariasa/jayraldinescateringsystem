@echo off
title Open All Network Access for Tablets
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [Requesting Administrator Permission...]
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   DISABLING FIREWALL BLOCKING FOR TABLETS AND LOCAL CLIENTS
echo ============================================================
echo.

netsh advfirewall firewall delete rule name="Jayraldines Sync Server 8000" >nul 2>&1
netsh advfirewall firewall add rule name="Jayraldines Sync Server 8000" dir=in action=allow protocol=TCP localport=8000 profile=any
netsh advfirewall firewall add rule name="Jayraldines Postgres 5432" dir=in action=allow protocol=TCP localport=5432 profile=any
netsh advfirewall firewall add rule name="Jayraldines Web 8085" dir=in action=allow protocol=TCP localport=8085 profile=any
netsh advfirewall firewall add rule name="Allow ICMPv4-In (Ping)" protocol=icmpv4:8,any dir=in action=allow profile=any

echo.
echo [OK] Firewall ports 8000, 5432, 8085 are completely ALLOWED.
echo.
echo You can now refresh http://192.168.1.10:8000/index.html on your tablet!
echo.
pause
