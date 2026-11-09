# Customer Address Barangay Lookup Index Tuning

## SQLite Performance
- Composite index `idx_customer_city_barangay` on `customers(city, barangay)`.
- Drops query latency on customer autocomplete from 45ms to 2ms.
- Reindexed automatically during weekly vacuum maintenance.
