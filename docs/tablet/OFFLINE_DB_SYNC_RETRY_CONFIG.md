# Offline Database Sync Retry Configuration

## Queue Parameters
- Maximum retry attempts capped at 8 per booking payload.
- Jittered exponential delay between sync pings (3s, 6s, 12s, 24s).
- Failed payloads logged to local IndexedDB dead-letter store for manual export.
