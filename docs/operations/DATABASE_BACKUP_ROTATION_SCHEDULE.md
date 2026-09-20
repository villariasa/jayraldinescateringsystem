# Automated Database Backup Retention Schedule

## 1. Schedule
- **Hourly Snapshot**: Maintained for the last 24 hours.
- **Daily Archive**: Compressed at midnight and retained for 30 days.
- **Monthly Rollup**: Maintained indefinitely in `backups/monthly/`.
