# Maya Business Terminal Settlement & End-of-Day Batching

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Billing, Maya Merchant Gateway, Cashflow

---

## 1. Scope
For credit/debit card card-present swipe transactions using the Maya handheld terminal at commissary headquarters.

---

## 2. Settlement Flow
- **Batch Cut-Off Time:** 10:00 PM daily.
- Cashier performs terminal batch settlement slip printout.
- Total net proceeds are mapped to Bank Checking Account upon clearing (T+1 business day).
- Merchant fee deductions (standard 1.5% - 2.5%) are logged as `Bank Charges` under Expenses.\n