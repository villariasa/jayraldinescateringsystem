# Offline Sync Mutation Journal & Idempotency Tokens

## 1. Journaling Architecture
All offline client mutations append an immutable record to the local `sync_journal` table:

- **Mutation Token**: `UUIDv4` uniquely identifying the transactional payload.
- **State Sequence**: Ordered integer sequence ensuring mutations replay in chronological order upon server reconnect.
- **Ack Confirmation**: Marked as committed upon receiving server HTTP 200 responses.
