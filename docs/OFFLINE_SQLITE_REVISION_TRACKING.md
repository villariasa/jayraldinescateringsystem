# Offline SQLite Change Tracking & Tombstone Reconciliation

## 1. Change Tracking Architecture
Local SQLite tables utilize `updated_at` timestamps and a dedicated `tombstones` table for deleted records.

## 2. Conflict Resolution
In the event of a simultaneous edit between two tablet kiosks, the central server employs Last-Write-Wins (LWW) based on high-precision server receipt timestamps, logging the conflict to the audit ledger.
