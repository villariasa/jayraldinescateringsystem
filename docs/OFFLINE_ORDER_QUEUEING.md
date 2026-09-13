# FIFO Offline Order Queueing & Synchronization Specification

## 1. Queue Architecture
- When the tablet detects lack of server heartbeat, new bookings and order modifications append to a persistent FIFO queue.
- Items contain a unique UUID, client timestamp, payload, and status (`QUEUED`, `SYNCING`, `FAILED`).

## 2. Transmission & Replay
- When network connectivity returns, a background worker consumes the queue in chronological order.
- Failed requests employ exponential backoff (1s, 2s, 4s, 8s, max 30s) to avoid flooding the server.
