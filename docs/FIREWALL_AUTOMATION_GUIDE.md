# Windows Firewall Automation Guide

## 1. Purpose & Scope
To enable seamless communication between the main catering workstation, Android tablets, and PWA kiosks, network firewall rules must be explicitly provisioned for inbound traffic.

## 2. Managed Ports
- **Port 8000 (TCP)**: Jayraldine's HTTP Sync & Static Web Server for tablet kiosks.
- **Port 5432 (TCP)**: PostgreSQL database engine listener for LAN clients.
- **Port 8085 (TCP)**: Internal event streaming and WebSocket notification hub.
- **ICMPv4 (Ping)**: Network diagnostic reachability testing.

## 3. Execution Script
The deployment is automated via `DISABLE_FIREWALL_AND_ALLOW_ALL.bat`, which requests Administrator UAC elevation and executes idempotent `netsh advfirewall` rules.
