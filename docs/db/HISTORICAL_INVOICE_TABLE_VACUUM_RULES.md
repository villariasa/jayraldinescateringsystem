# Historical Invoice Table Vacuum and Reindex Rules

## Table Maintenance
- `invoices` table analyzed and fragmented pages compacted monthly.
- Database integrity check `PRAGMA integrity_check` executed prior to vacuum.
- Keeps desktop database filesize under 25MB for lightning-fast cold boot.
