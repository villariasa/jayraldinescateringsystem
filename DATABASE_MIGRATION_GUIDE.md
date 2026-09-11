# SQLite to PostgreSQL Automated Migration Guide

## Overview
The v4.1.15 setup wizard automatically detects existing SQLite databases (`catering.db`, `database.db`) and transfers all records to the central PostgreSQL database server.

### Migration Pipeline Steps
1. Scan candidate paths in `%LOCALAPPDATA%` and `%APPDATA%`.
2. Validate table schemas and normalize types (booleans, timestamps).
3. Bulk insert rows using conflict resolution (`ON CONFLICT DO NOTHING`).
4. Synchronize PostgreSQL `SERIAL` sequences (`setval`).
