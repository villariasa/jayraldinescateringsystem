# PostgreSQL Threaded Connection Pool Management

## 1. Pool Architecture
The database manager utilizes `psycopg2.pool.ThreadedConnectionPool` configured for concurrent multi-terminal transaction processing:

- **Minimum Pool Connections**: `5`
- **Maximum Pool Connections**: `32`
- **Connection Acquisition**: Context-managed `get_cursor()` pattern guaranteeing return of connections to the pool upon block exit.
- **TCP Keep-Alive**: Configured with `keepalives=1`, `keepalives_idle=30`, and `keepalives_interval=10` to prevent firewall idle timeouts.
