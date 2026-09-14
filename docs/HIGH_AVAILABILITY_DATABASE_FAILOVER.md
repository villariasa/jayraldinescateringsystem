# PostgreSQL High-Availability Streaming Replication & Failover

## 1. Failover Topology
- **Primary Node**: Main Cashier Desktop PC hosting read/write PostgreSQL instance.
- **Standby Node**: Secondary Office Laptop receiving synchronous streaming replication.
- **Automatic Promotion**: Standby node can be promoted to primary within 30 seconds via `pg_ctl promote` in event of hardware failure.
