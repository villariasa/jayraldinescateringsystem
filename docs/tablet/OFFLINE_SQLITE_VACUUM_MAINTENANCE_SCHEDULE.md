# Tablet Offline SQLite WASM Vacuum & Storage Optimization

> **Target Version:** v4.2.5  
> **Status:** Database Engineering Spec  
> **Date:** October 8, 2026  
> **Audience:** Tablet Engine Developers, Database Admin

---

## 1. SQLite WebAssembly (WASM) Fragment Accumulation
Heavy order revisions and booking snapshot updates in browser `sql-wasm` create database file fragmentation and bloated browser IndexedDB footprints.

## 2. Scheduled VACUUM Routine
- **Trigger:** Automated during night sync or when database freespace exceeds 30%.
- **Command:** Execute `PRAGMA incremental_vacuum(500);` during idle timers.
- **Full Vacuum:** On app startup if `page_count * page_size > 15MB`, execute `VACUUM;` to reclaim unused memory blocks.
