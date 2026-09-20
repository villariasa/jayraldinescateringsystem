# Offline-First LAN Topology Specification

## 1. Physical Architecture
- **Central Station**: Windows 10/11 Workstation acting as local database and HTTP server.
- **Local Access Point**: Dual-band 2.4GHz/5GHz wireless router.
- **Client Terminals**: 5-10 Android tablets or mobile devices connecting via local IP (`192.168.x.x`).
- **External WAN**: Optional. The system does not depend on cloud uptime or ISP connectivity.

## 2. Port Allocations
- `8000/TCP`: HTTP Sync REST API & Web Kiosk PWA Server.
- `5432/TCP`: PostgreSQL Engine (or embedded SQLite engine).
- `8085/TCP`: Local WebSocket push notification channel.
