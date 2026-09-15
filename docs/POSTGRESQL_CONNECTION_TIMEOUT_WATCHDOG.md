# PostgreSQL Connection Pool Idle Reaper Watchdog

## 1. Reaper Logic
- **Idle Timeout**: Automatically closes pooled connections idle for $>10\text{ minutes}$.
- **Connection Health Probe**: Tests connection validity with zero-overhead socket checks before delivering connections to calling threads.
