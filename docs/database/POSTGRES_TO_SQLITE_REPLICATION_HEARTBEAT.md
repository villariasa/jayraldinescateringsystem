# Central PostgreSQL to Tablet SQLite Replication & Heartbeat Protocol

> **Target Version:** v2.7.5  
> **Status:** Systems Architecture Spec  
> **Date:** October 29, 2026  
> **Audience:** Backend Engineers, System Administrators

---

## 1. Heartbeat Architecture
Field tablets maintain live connection to central PostgreSQL backend via lightweight HTTP polling daemon:
- Interval: **30 seconds**.
- Payload: Device serial, active software version (`v2.7.5`), local SQLite max change sequence ID.

## 2. Incremental Delta Synchronization
- If backend sequence exceeds tablet sequence, server returns JSON changeset containing only modified rows since sequence timestamp.
- Applied locally within SQLite `BEGIN IMMEDIATE TRANSACTION` block to ensure zero dirty reads during active kiosk booking sessions.
