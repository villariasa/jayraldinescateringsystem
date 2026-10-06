# Actual Sales Evaluation & Package Category Breakdown Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Sales Reports, Dashboard KPIs, Revenue Analytics

---

## 1. Business Logic Rules

In catering revenue recognition, items sold are classified into primary business categories:
1. **Full Catering Service:** High-pax complete event packages with table skirting, servers, and chaffing setups.
2. **Food Orders:** Includes packed meals, party platters, **Food Sets**, and **Food Packs**.
3. **Equipment Rentals:** Sound system, projector, tables, Tiffany chairs, and linens.
4. **Additional Surcharges:** Corkage, ingress overtime, outside venue fees.

### 1.1 Category Mapping Alignment

To prevent misreporting of packed meal packages as non-food or uncategorized revenue, the classification engine strictly maps package types:

```python
def classify_booking_package(pkg_name: str, occasion: str) -> str:
    p = (pkg_name or "").strip().lower()
    occ = (occasion or "").strip().lower()
    
    if any(k in p for k in ["food set", "food pack", "packed meal", "bilao", "bento"]):
        return "Food Orders"
    elif any(k in occ for k in ["food set", "food pack"]):
        return "Food Orders"
    elif any(k in p for k in ["wedding", "debut", "birthday", "buffet", "catering"]):
        return "Full Catering"
    elif any(k in p for k in ["rental", "chair", "table", "sound"]):
        return "Rentals"
    return "General Catering"
```

---

## 2. Actual Sales Math

- **Total Contract Value:** `Gross Amount = Package Total + Addons - Discounts`
- **Recognized Sales (Accrual):** Fully confirmed events within period regardless of final collection status.
- **Cash Basis Sales:** `Collected Sales = Downpayments Collected + Balance Settlements Collected`.
