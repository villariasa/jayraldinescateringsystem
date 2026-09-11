# Disaster Recovery & Restore Procedures

## Restoration Steps
1. Stop application instances.
2. Restore PostgreSQL dump using `pg_restore` or `psql -f backup.sql`.
3. Verify sequence alignments and integrity checks.
