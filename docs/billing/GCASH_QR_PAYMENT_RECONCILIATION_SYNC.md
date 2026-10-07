# GCash Merchant QR Payment Reconciliation & Auto-Sync

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Cashflow, GCash Digital Wallet, Billing

---

## 1. Overview
Over 65% of catering deposits are settled through GCash. To eliminate manual verification errors, the system verifies GCash merchant notification SMS and transaction reference IDs.

---

## 2. Verification Protocol
1. Cashier enters client's 12-digit GCash Reference Number (e.g. `9012 3456 7890`).
2. Regex validator checks format: `^[0-9]{12}$`.
3. System verifies against existing records to prevent duplicate reference entry reuse.
4. Transaction is committed directly to `cash_flow_transactions` under account `gcash`.\n