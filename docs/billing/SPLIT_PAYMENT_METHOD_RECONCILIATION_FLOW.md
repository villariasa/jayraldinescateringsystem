# Multi-Method Split Payment Ledger Reconciliation Workflow

> **Target Version:** v2.7.5  
> **Status:** Accounting Specification  
> **Date:** October 29, 2026  
> **Audience:** Cashiers, Accounting Staff, Developers

---

## 1. Architecture & Split Mechanics
Clients frequently settle large catering contracts across multiple payment channels:
- Cash deposit + GCash QR transaction + Bank Wire (BDO / BPI).
- In `billing_page.py`, each payment entry generates an isolated immutable ledger transaction tied to `booking_id`.

```
[ Booking Invoice: ₱85,000 ]
     ├── Payment 1: Cash (₱20,000) ──► OR# 10452
     ├── Payment 2: GCash (₱35,000) ──► Ref# 900241049281
     └── Payment 3: Bank Transfer (₱30,000) ──► BDO Auth# 819203
```

## 2. Automatic Balance Audit
Invoice balance dynamically updates to `₱0.00` upon receipt of all confirmed tranches, releasing final release permit for dispatch.
