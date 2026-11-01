# Concurrent Booking Transaction Isolation Specification

## 1. Conflict Prevention
To prevent two sales agents from reserving the same premier venue hall simultaneously:
- PostgreSQL: `ISOLATION LEVEL SERIALIZABLE` with retry backoff loop.
- SQLite: `BEGIN IMMEDIATE` transaction lock, preventing phantom writes before booking validation.
