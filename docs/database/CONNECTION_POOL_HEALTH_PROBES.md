# Database Connection Pool Health Probes & Eviction Rules

## 1. Health Probe Cycle
- Keepalive ping: `SELECT 1` dispatched every 45 seconds for idle pool connections.
- Stale connection max lifetime: 600 seconds.
- Automatically discards socket connections broken by Wi-Fi sleep states on mobile laptops.
