# SQLite WAL Auto-Recovery & Disk I/O Resilience Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Database Engine, Connection Manager, WAL Checkpointer

---

## 1. Problem Definition

In production deployments on Windows and Linux POS terminals, abrupt power loss or USB drive disconnections while SQLite was actively in WAL (`Write-Ahead Logging`) mode can cause orphaned `-wal` and `-shm` lock files. When restarted, naive connection attempts could encounter `sqlite3.OperationalError: disk I/O error` or stale shared-memory locks.

This specification details the **self-healing auto-repair routine** embedded into the database connection manager.

---

## 2. Auto-Recovery Architecture

```
[Connect Request]
       |
  [Try Standard Connect] -- Success --> [Verify Integrity PRAGMA] -> [OK]
       |
  (OperationalError: disk I/O or malformed)
       |
[Trigger Self-Healing Routine]
       |
  1. Close all active connection handles
  2. Backup database file to timestamped recovery file
  3. Attempt WAL Checkpoint TRUNCATE
  4. If locks stuck:
     - Check file permissions and lock holders
     - Safely remove stale .db-shm
     - Reconnect to trigger SQLite auto-journal recovery
  5. Run PRAGMA integrity_check
       |
  [Recovered] -> Log audit event & resume normal operations
```

---

## 3. Pragma Configuration Standards

Every new connection enforces strict WAL safety flags:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
PRAGMA wal_autocheckpoint = 1000;
```
