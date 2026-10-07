# Void Transaction Reversal & Supervisory Override Policy

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** POS Cashier, Role-Based Access Control, Security

---

## 1. Overview
Cashiers cannot unilaterally delete or void issued receipts. Reversing an entry requires authorized supervisory PIN override.

---

## 2. Reversal Steps
1. Cashier clicks **Void / Reverse Transaction**.
2. Supervisor Modal prompts for 6-digit Master PIN.
3. System verifies PIN using PBKDF2-HMAC-SHA256.
4. Transaction is marked `is_void = 1` with reason code; a compensatory opposite entry is recorded in the ledger for balanced bookkeeping.\n