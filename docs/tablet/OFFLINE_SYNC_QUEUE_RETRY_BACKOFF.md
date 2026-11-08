# Offline Sync Queue Retry Backoff

## Sync Queue Strategy
- Failed sync payloads retry with exponential backoff: 2s, 4s, 8s, 16s, max 60s.
- Offline transactions remain persistent in IndexedDB until server ACK received.
- Checksum verified before removing queue entries.
