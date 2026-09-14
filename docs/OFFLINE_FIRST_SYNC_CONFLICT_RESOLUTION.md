# Offline-First Synchronization & Conflict Resolution

## 1. Concurrency Model
Jayraldine's Catering employs an optimistic mutation model with deterministic conflict resolution:

- **Client Authority**: Offline order submissions generate unique UUID/timestamp-based booking references (`TB-YYYYMMDD-XXXXX`).
- **Server Upsert Strategy**: The central server utilizes `ON CONFLICT (bk_booking_ref) DO NOTHING` to guarantee idempotent execution.
- **Master Data Supremacy**: Server-side dish prices, packages, and categories take precedence over client-local master data caches during synchronization cycles.
