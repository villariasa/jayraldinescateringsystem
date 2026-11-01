# Query Plan Optimization for Multi-Year Sales Aggregation

## 1. Problem Statement
Aggregating 5+ years of payment transactions across thousands of catering contracts can trigger full-table sequential scans if indexes on `(pr_payment_date, pr_status)` are omitted.

## 2. Optimized SQL Execution
```sql
CREATE INDEX IF NOT EXISTS idx_payment_records_date_status 
ON payment_records (pr_payment_date, pr_status);

EXPLAIN QUERY PLAN
SELECT strftime('%Y-%m', pr_payment_date) as month, SUM(pr_amount) 
FROM payment_records 
WHERE pr_status != 'Voided' 
GROUP BY month;
```
