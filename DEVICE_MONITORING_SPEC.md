# Device Sessions & Terminal Monitoring Specification

## Heartbeat & Activity Protocol
- Each terminal generates a persistent machine identifier: `DEV-XXXX-XXXX`.
- Terminals emit active page heartbeats every 30 seconds to the `device_sessions` table.
- Status transitions:
  - 🟢 **Online**: Last heartbeat within 90 seconds.
  - 🟡 **Idle**: Last heartbeat between 90 seconds and 5 minutes.
  - ⚪ **Offline**: App closed or inactive for more than 5 minutes.
