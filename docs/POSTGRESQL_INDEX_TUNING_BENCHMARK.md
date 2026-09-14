# PostgreSQL Query Optimization & Index Benchmarks

## 1. Index Strategy
- `idx_bookings_event_date`: B-tree index on `bk_event_date` for instantaneous monthly calendar rendering.
- `idx_customers_name_trgm`: GIN trigram index on `LOWER(cus_name)` for millisecond autocomplete fuzzy searching.
- `idx_invoices_status_balance`: Composite index on `(inv_status, inv_balance)` for high-speed receivables reports.
