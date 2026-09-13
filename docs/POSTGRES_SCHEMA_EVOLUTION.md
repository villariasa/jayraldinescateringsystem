# Database Schema Migration Pipeline Specification

## 1. Migration Architecture
The system supports zero-downtime schema evolution between SQLite legacy deployments and PostgreSQL 16+ enterprise instances.

## 2. Schema Conventions
- Table and column names use lower_snake_case.
- Primary keys utilize `SERIAL` or `BIGSERIAL` auto-incrementing integers.
- Foreign keys enforce `ON DELETE RESTRICT` or `ON DELETE CASCADE` explicitly.
- Timestamps default to `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'`.
