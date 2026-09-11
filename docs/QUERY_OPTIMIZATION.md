# Database Indexing & Query Optimizations

## Indexes
- B-Tree indexes on all foreign keys (`bk_customer_id`, `pi_package_id`, etc.)
- Functional indexes on search columns (`LOWER(cus_name)`, `LOWER(ab_name)`)
- Partial indexes on active records (`status = 'online'`)
