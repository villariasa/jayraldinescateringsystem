# System Troubleshooting & Technical Diagnostic Runbook

## 1. Common Diagnostics
- **Port 8000 Conflict**: Run `netstat -ano | findstr :8000` to identify and terminate rogue processes.
- **PostgreSQL Service Down**: Execute `net start postgresql-x64-16` via Administrator command prompt.
- **Firewall Re-configuration**: Re-run `open_firewall_ports.bat` to re-authorize inbound TCP traffic.
