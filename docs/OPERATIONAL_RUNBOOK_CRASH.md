# Operational Runbook: Emergency Crash Recovery & System Failover

## 1. Crash Triage Steps
1. **Identify Failure Source**: Determine if outage is hardware, network switch, or database engine related.
2. **Inspect Windows Event Logs**: Check for system error codes or abrupt power loss markers.
3. **Database Consistency Verification**: Run PostgreSQL `pg_waldump` and check table integrity.
4. **Local Fallback Mode**: If network connectivity is severed, switch tablet clients to offline SQLite mode immediately.

## 2. Post-Recovery Reconciliation
Execute batch sync verification to ensure all buffered offline orders are acknowledged by the primary server.
