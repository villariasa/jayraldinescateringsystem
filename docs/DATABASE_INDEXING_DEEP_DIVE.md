# Relational Database Indexing Strategy & Optimization

## 1. Key Indexes
- `idx_bookings_event_date`: B-tree index on `bookings(event_date)` for fast calendar range queries.
- `idx_bookings_status`: Partial index on active bookings (`WHERE status IN ('Confirmed', 'Pending')`).
- `idx_customers_phone`: Unique B-tree index on customer contact numbers.
- `idx_inventory_par`: Functional index on items below minimum par levels.

## 2. Query Optimization Guidelines
Avoid `SELECT *` in high-frequency polling endpoints; utilize indexed cover queries to reduce disk I/O.
