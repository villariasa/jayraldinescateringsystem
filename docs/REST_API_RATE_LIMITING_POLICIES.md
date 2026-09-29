> **Note:** Reviewed & updated 2026-09-29 — Jayraldine's Catering System.

# REST API Rate Limiting & Denial-of-Service Safeguards

## 1. Rate Limiting Parameters
- **LAN Local Requests**: Up to 120 requests/minute per client device.
- **Remote Tunnel Requests**: 60 requests/minute with exponential backoff triggers.
- **Connection Queuing**: Thread pool worker queues handle bursts during simultaneous multi-tablet order placements.
