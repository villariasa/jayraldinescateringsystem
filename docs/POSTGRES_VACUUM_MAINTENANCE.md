# PostgreSQL Automated VACUUM & Database Maintenance Specification

## 1. Routine Maintenance Schedule
- **Auto-Vacuum**: Configured with `autovacuum_vacuum_scale_factor = 0.05` for high-write booking and log tables.
- **Weekly Full Analyze**: Executes off-hours query planner index statistics refresh every Sunday at 3:00 AM.

## 2. WAL Archiving
Write-Ahead Logging (WAL) files are retained for 7 days to facilitate point-in-time recovery.
