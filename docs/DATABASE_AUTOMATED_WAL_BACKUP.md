# PostgreSQL Automated Backup & WAL Archiving Policy

## 1. Backup Strategies
- **Continuous Archiving**: Write-Ahead Logging (WAL) archiving enabled for point-in-time recovery (PITR).
- **Daily Full Snapshot**: Automated `pg_dump -Fc` execution at 02:00 AM daily with 30-day local retention.
- **Disaster Mirroring**: Encrypted backup archives mirrored to external storage drives and cloud vaults.
