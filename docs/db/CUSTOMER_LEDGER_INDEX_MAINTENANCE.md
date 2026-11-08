# Customer Ledger Index Maintenance & Vacuum Schedule

## SQLite Maintenance
- `idx_ledger_customer_date` rebuilt monthly via scheduled cron script.
- `VACUUM` executed on database file every first Sunday at 2:00 AM.
- Keeps query latency under 15ms even with 50,000 transaction rows.
