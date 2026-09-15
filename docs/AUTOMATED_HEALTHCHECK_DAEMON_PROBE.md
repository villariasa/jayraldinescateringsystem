# Automated Health-Check Heartbeat Daemon & Recovery

## 1. Daemon Watchdog Architecture
A background thread periodically ($15\text{ seconds}$) probes critical system components:

- **PostgreSQL Connection**: Executes `SELECT 1` query.
- **Memory Footprint**: Monitors Python process RSS memory; triggers garbage collection if threshold exceeds $800\text{MB}$.
- **Storage Availability**: Alerts operator if host drive space drops below $2\text{GB}$.
