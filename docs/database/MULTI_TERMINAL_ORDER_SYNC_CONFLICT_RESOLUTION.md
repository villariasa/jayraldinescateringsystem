# Multi-Terminal Order Collision Detection & Conflict Resolution

> **Target Version:** v2.7.5  
> **Status:** Database Engineering Spec  
> **Date:** October 29, 2026  
> **Audience:** Backend Architects, Database Admins

---

## 1. Concurrency Scenario
Two sales terminals concurrently modify the same event booking (e.g., Terminal 1 updates menu items while Terminal 2 adjusts table layout).

## 2. Resolution Hierarchy: Last-Write-Wins with Field-Level Merging
- Primary records store granular column-level timestamps:
  - `menu_last_modified_at`
  - `logistics_last_modified_at`
  - `billing_last_modified_at`
- If modifications affect orthogonal domains, both edits merge automatically.
- If conflicting modifications target identical fields, the server-side PostgreSQL timestamp takes precedence and records an audit log row into `booking_conflict_history`.
