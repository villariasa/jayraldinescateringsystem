# Systemd Service Unit Configuration for Kiosk Auto-Start

## 1. Unit File: `/etc/systemd/system/jayraldines-kiosk.service`
```ini
[Unit]
Description=Jayraldine's Catering Tablet Kiosk Server
After=network.target

[Service]
Type=simple
User=villarias
WorkingDirectory=/opt/jayraldinescateringsystem/Tablet_PWA/backend
ExecStart=/opt/jayraldinescateringsystem/Tablet_PWA/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
