# Automated PostgreSQL & SQLite Database Backup S3 Rotation

> **Target Version:** v2.7.5  
> **Status:** DevOps Standard  
> **Date:** October 29, 2026  
> **Audience:** DevOps Engineers, System Administrators

---

## 1. Cron Backup Schedule (03:00 AM Daily)
- Dump PostgreSQL database using `pg_dump -Fc` compressed custom binary format.
- Stream encrypted backup tarball to secure Amazon S3 / Cloudflare R2 bucket.

## 2. Retention Lifecycle Policy
- **Daily Backups:** Retained for 14 days.
- **Weekly Backups:** Retained for 8 weeks.
- **Monthly Backups:** Retained indefinitely for annual tax auditing and business analytics.
