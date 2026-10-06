# Cashflow Account Classification & Filter Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Financial Ledger, Account Classification, Cash Flow Page

---

## 1. Background & Scope

Jayraldine's Catering receives payments and disburses expenses across specific financial accounts:
- **Cash in Drawer / Cash on Hand** (Physical commissary drawer and event cashbox)
- **GCash** (Digital wallet payments for booking deposits and final balances)
- **Maya** (Alternative e-wallet channel)
- **Bank Checking Account** (Official business operations account)

### 1.1 Deprecation of "BDO Savings"
Historical versions included "BDO Savings" in the classification options. Business management has standardized all corporate banking under the primary checking operations account. Consequently, "BDO Savings" is deprecated and removed from active classification selectors.

---

## 2. Classification Architecture

### 2.1 Supported Account Types

The active enumeration for accounts is defined as follows:

```json
[
  { "id": "cash", "label": "Cash on Hand", "icon": "money-bill-wave", "badge_color": "#10B981" },
  { "id": "gcash", "label": "GCash", "icon": "mobile-alt", "badge_color": "#007DFE" },
  { "id": "maya", "label": "Maya", "icon": "wallet", "badge_color": "#16A34A" },
  { "id": "bank_checking", "label": "Bank Checking (Main)", "icon": "university", "badge_color": "#6366F1" }
]
```

### 2.2 Account-Specific Balance Dynamic Display

When an operator selects an account filter (e.g., selecting **GCash**):
1. **Dynamic Balance Metric Card:** The top summary card dynamically pivots from "Total System Cashflow" to display:
   - **Current Account Balance:** Total inflows minus outflows specifically tied to `account_type = 'gcash'`.
   - **Monthly Inflow for GCash:** Cumulative downpayments and settlements collected via GCash this month.
   - **Pending Transfers:** Amounts scheduled for settlement or transfer to the main account.
2. **Table Filtering:** The ledger table immediately refines rows to show only transactions affecting the chosen account.
