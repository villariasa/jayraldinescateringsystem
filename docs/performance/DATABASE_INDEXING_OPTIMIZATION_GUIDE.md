# Database Indexing & Query Optimization Guide

## 1. High-Priority Indexes
- `idx_bookings_date_status`: `(bk_event_date, bk_status)` for rapid calendar queries.
- `idx_payments_date`: `(pr_payment_date)` for sales evaluation aggregation.
- `idx_customers_phone`: `(cust_phone)` for instantaneous phone lookups during customer calls.
