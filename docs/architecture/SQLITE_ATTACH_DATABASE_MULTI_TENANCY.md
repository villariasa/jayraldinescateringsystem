# SQLite ATTACH DATABASE Multi-Branch Isolation Architecture

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Database Engine, Multi-Tenant Branch Partitioning

---

## 1. Executive Summary
As Jayraldine's Catering expands commissary branches (e.g. Cebu Central Commissary vs. Mandaue Satellite Dispatch), data isolation is required while preserving cross-branch reporting capabilities on the central owner dashboard.

This document outlines using SQLite's native `ATTACH DATABASE` feature for multi-branch operation without heavy server infrastructure.

---

## 2. Connection Topology

```sql
-- Attach satellite commissary database on demand
ATTACH DATABASE '/var/data/jayraldines_mandaue.db' AS mandaue;
ATTACH DATABASE '/var/data/jayraldines_cebu_central.db' AS cebu_central;

-- Cross-branch consolidated sales projection
SELECT 
    'Cebu Central' AS branch,
    SUM(total_amount) AS gross_sales
FROM cebu_central.invoices
WHERE event_date >= '2026-10-01'

UNION ALL

SELECT 
    'Mandaue' AS branch,
    SUM(total_amount) AS gross_sales
FROM mandaue.invoices
WHERE event_date >= '2026-10-01';
```

---

## 3. Security & Transaction Isolation
- Each branch maintains a detached, self-contained SQLite file with WAL journaling.
- Branch terminals mount only their local database, preventing accidental write leaks.\n