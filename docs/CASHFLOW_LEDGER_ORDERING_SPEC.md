# Cashflow Ledger Chronological Ordering & Real-time Reverse Indexing Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Cash Flow Management, Desktop UI, Ledger Repository

---

## 1. Overview

In Jayraldine's Catering System, financial transactions (downpayments, balance settlements, vendor payments, ingredient purchases, petty cash disbursements) must be easily audited by cashiers and business managers.

Previously, default ledger queries fetched records in ascending chronological order (`ORDER BY transaction_date ASC, id ASC`), causing new entries to append at the bottom of lengthy tables. Operators were forced to scroll through hundreds of rows to confirm newly added receipts.

This document formalizes the requirement for **newest-first ordering** across all cashflow tables and UI views.

---

## 2. Technical Requirements

### 2.1 SQL Query Specification

All data retrieval routines for cashflow entries must sort descending by date and insertion timestamp:

```sql
SELECT 
    id,
    transaction_date,
    category,
    account_type,
    amount,
    flow_type, -- INFLOW / OUTFLOW
    reference_no,
    notes,
    created_at
FROM cash_flow_transactions
ORDER BY 
    transaction_date DESC,
    id DESC;
```

### 2.2 Table View Integration

1. **Table Widget Positioning:**
   - Newly inserted transactions must immediately appear at `row index 0` upon creation.
   - When refreshed or populated, `QTableWidget` or `QTableView` rows are loaded with newest record at index 0.
2. **Smooth Highlighting:**
   - On manual entry creation, the UI momentarily flashes row 0 with a soft emerald accent (`rgba(16, 185, 129, 0.2)`) before settling to standard alternating row colors.
3. **Running Balance Calculation:**
   - While rows are displayed descending, running balances are calculated forward chronologically from opening balances, ensuring that row-by-row balance indicators remain mathematically sound.
