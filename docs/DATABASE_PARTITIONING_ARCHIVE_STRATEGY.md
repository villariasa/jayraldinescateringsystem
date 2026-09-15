# PostgreSQL Declarative Table Partitioning & Archiving Strategy

## 1. Partitioning Hierarchy
To ensure high query speeds over multi-year operational histories, the `bookings` table implements range partitioning by year:

- `bookings_2025`: Range `[2025-01-01, 2026-01-01)`
- `bookings_2026`: Range `[2026-01-01, 2027-01-01)`
- `bookings_2027`: Range `[2027-01-01, 2028-01-01)`

## 2. Benefits
- **Query Pruning**: Queries filtering by event date scan only relevant partitions.
- **Maintenance**: Historical partitions can be archived or detached without impacting live tables.
