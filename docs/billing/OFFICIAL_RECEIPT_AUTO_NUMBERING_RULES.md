# Official Receipt (OR) Sequential Auto-Numbering Engine

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Invoicing, BIR Compliance, Database Engine

---

## 1. Compliance Mandate
BIR registered receipts require strictly sequential, unskipped numerical series.

---

## 2. Auto-Numbering Implementation

```sql
BEGIN IMMEDIATE;
UPDATE invoice_series 
SET current_number = current_number + 1 
WHERE series_code = 'OR-2026';

SELECT printf('OR-2026-%06d', current_number) 
FROM invoice_series 
WHERE series_code = 'OR-2026';
COMMIT;
```

Locks ensure concurrent transactions across multiple cashier terminals never duplicate or skip numbers.\n