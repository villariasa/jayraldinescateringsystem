# Automated Schema Versioning & Forward Migration Runner Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** SQLite Database Engine, DDL Migrations, Schema Registry

---

## 1. Purpose & Goals
As system capabilities expand across versions, database schemas must safely migrate forward on client POS machines without data loss or manual developer intervention.

---

## 2. Schema Migration Table

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version_id INTEGER PRIMARY KEY,
    migration_name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT NOT NULL
);
```

---

## 3. Execution Pipeline

1. **Discovery:** On application startup, the runner inspects `schema_migrations` to determine current applied version (e.g. `PRAGMA user_version` or `MAX(version_id)`).
2. **Sequential Rollout:** Pending migrations are loaded from the migration catalog and executed sequentially inside an atomic transaction (`BEGIN IMMEDIATE`).
3. **Integrity Validation:** If any DDL statement fails, the transaction rolls back cleanly, application launch aborts, and an emergency recovery log is saved.\n