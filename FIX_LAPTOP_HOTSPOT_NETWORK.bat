@echo off
:: Batch script to configure Windows Network & Firewall for iPhone Hotspot and Tablet Sync
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [REQUESTING ADMINISTRATOR PERMISSION...]
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

title Jayraldine's Catering - Hotspot Network & Firewall Setup
cls
echo ====================================================================
echo   CONFIGURING LAPTOP FOR IPHONE HOTSPOT & TABLET COMMUNICATION
echo ====================================================================
echo.

echo [1/3] Setting iPhone Hotspot network profile to PRIVATE...
powershell -Command "Get-NetConnectionProfile | Where-Object { $_.Name -like '*iPhone*' -or $_.IPv4Connectivity -eq 'Internet' } | Set-NetConnectionProfile -NetworkCategory Private"

echo.
echo [2/3] Adding Windows Firewall Inbound Rule for Port 8000...
netsh advfirewall firewall delete rule name="Jayraldines LAN Sync Server (8000)" >nul 2>&1
netsh advfirewall firewall add rule name="Jayraldines LAN Sync Server (8000)" dir=in action=allow protocol=TCP localport=8000 profile=any

echo.
echo [3/3] Allowing ICMP Ping so devices can detect each other...
netsh advfirewall firewall delete rule name="Allow ICMPv4-In (Ping)" >nul 2>&1
netsh advfirewall firewall add rule name="Allow ICMPv4-In (Ping)" protocol=icmpv4:8,any dir=in action=allow profile=any

echo.
echo ====================================================================
echo   SUCCESS: Laptop is now open for tablet connection on port 8000!
echo ====================================================================
echo.
echo Current Network Profile:
powershell -Command "Get-NetConnectionProfile | Select-Object Name, NetworkCategory, IPv4Connectivity"
echo.
echo You can now test on your tablet browser: http://10.105.101.120:8000/test
echo.
pause
