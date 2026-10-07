# Split-Tender Payment Multi-Account Transaction Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Payment Processing, POS Cashier, Billing Engine

---

## 1. Overview
Clients frequently settle large catering balances across multiple payment channels simultaneously (e.g. paying PHP 20,000 via GCash and the remaining PHP 15,000 in Cash on Hand).

---

## 2. Transaction Data Model

```json
{
  "invoice_id": 1042,
  "total_settlement": 35000.00,
  "splits": [
    {
      "method": "gcash",
      "amount": 20000.00,
      "reference_no": "GC-20261007-8891",
      "target_account": "gcash"
    },
    {
      "method": "cash",
      "amount": 15000.00,
      "reference_no": "CASH-DRAWER-01",
      "target_account": "cash"
    }
  ],
  "balance_remaining": 0.00
}
```

---

## 3. Atomicity & Integrity
All splits are committed in a single database transaction. If any payment method validation fails, the entire settlement aborts.\n