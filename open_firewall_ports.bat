@echo off
title Jayraldine's Catering - Open LAN Firewall Ports
echo ============================================================
echo   Jayraldine's Catering - Windows Firewall Port Configurator
echo ============================================================
echo.
echo Requesting Administrator permissions to open ports 5432 (PostgreSQL) and 8000 (Sync Hub)...
echo.

powershell -Command "Start-Process cmd -ArgumentList '/c netsh advfirewall firewall add rule name=\"Jayraldines Central DB (5432)\" dir=in action=allow protocol=TCP localport=5432 && netsh advfirewall firewall add rule name=\"Jayraldines Tablet Sync Server (8000)\" dir=in action=allow protocol=TCP localport=8000 && echo. && echo [SUCCESS] Firewall ports 5432 and 8000 successfully opened! && echo Press any key to exit... && pause' -Verb RunAs"

echo Done. Check the elevated prompt window.
pause
