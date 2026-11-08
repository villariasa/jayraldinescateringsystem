# SQLite Database Archiving for Closed Year Bookings

## Data Retention
- Bookings older than 3 fiscal years archived into `catering_archive_YYYY.db`.
- Preserves live production database lean for fast desktop startup.
- Historical queries routed to archive databases on read-only basis.
