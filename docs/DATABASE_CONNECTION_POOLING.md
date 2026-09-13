# PostgreSQL Connection Pooling & Keep-Alive Specification

## 1. Connection Pool Parameters
- **Min Pool Size**: 5 persistent connections for core application threads.
- **Max Pool Size**: 25 concurrent connections to accommodate peak tablet kiosk bursts.
- **Connection Timeout**: 10 seconds before initiating retry sequences.

## 2. Keep-Alive Configuration
TCP keep-alive parameters are tuned for aggressive LAN failure detection:
- `keepalives_idle`: 30 seconds.
- `keepalives_interval`: 5 seconds.
- `keepalives_count`: 3 retries before marking the connection stale.
