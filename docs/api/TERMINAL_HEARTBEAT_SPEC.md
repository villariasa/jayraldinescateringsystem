# Terminal Heartbeat & State Tracking Specification

## 1. Heartbeat Interval
Tablet kiosks dispatch a lightweight HTTP `POST /api/heartbeat` ping every 10 seconds containing:
- `device_id`: Unique persistent UUID.
- `device_name`: Human-readable label (e.g., "Tablet Kiosk 1").
- `battery_level`: Operational power status.
- `last_sync_timestamp`: Local vector clock.

## 2. Stale Detection
The desktop server flags any terminal with no ping for > 30 seconds as **Offline** in the device monitor tray.
