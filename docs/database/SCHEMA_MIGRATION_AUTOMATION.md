# Automated Schema Migration Execution Guide

## 1. Migration Pipeline
When the application initializes, `utils/db.py` checks `schema_version` in the database.
Pending migrations are executed in sequence:
1. `jayraldines_catering_clean.sql`: Core baseline tables.
2. `cebu_address_migration.sql`: Barangay and municipality tables.
3. `occasions_migration.sql`: Standard event types and templates.
4. `confirmed_only_views_migration.sql`: Financial view definitions.
5. `analytics_functions_migration.sql`: Stored procedures and reporting views.
