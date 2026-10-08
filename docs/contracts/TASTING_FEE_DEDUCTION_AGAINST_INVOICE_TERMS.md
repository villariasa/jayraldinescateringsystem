# Food Tasting Fee Deductions & Accounting Credit Reconciliation

> **Target Version:** v4.2.5  
> **Status:** Billing Accounting Spec  
> **Date:** October 8, 2026  
> **Audience:** Cashier, Sales, Accounting

---

## 1. Tasting Session Pricing & Credit Rules
- Prospective clients pay a standard tasting fee of **₱1,500.00** for up to 4 persons.
- If the client signs an event contract with total contract value exceeding **₱30,000.00**, the full ₱1,500.00 tasting fee is credited as an advance payment on the final invoice.

## 2. Ledger Posting Procedure
In the Desktop Billing module:
1. Credit entry: `Tasting Fee Credit (Receipt Ref: TASTE-XXXX)`.
2. Reduce gross payable balance while maintaining correct VATable gross totals.
