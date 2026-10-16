# Actual Sales Evaluation & Package Category Breakdown Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Sales Reports, Dashboard KPIs, Revenue Analytics

---

## 1. Business Logic Rules

In catering revenue recognition, items sold are classified into primary business categories:
1. **Full Catering Service:** High-pax complete event packages with table skirting, servers, and chaffing setups.
2. **Food and Services:** Packages bundled with essential event services (waitstaff, utensils, basic styling).
3. **Food Orders:** Includes packed meals, party platters, **Food Sets**, and **Food Packs**.
4. **Equipment Rentals:** Sound system, projector, tables, Tiffany chairs, and linens.
5. **Additional Surcharges:** Corkage, ingress overtime, outside venue fees.

### 1.1 Category Mapping Alignment

To prevent misreporting of packed meal packages or food and service combos as non-food or uncategorized revenue, the classification engine strictly maps package types:

```python
def classify_booking_package(pkg_name: str, occasion: str, menu_type: str = "", is_food_service: bool = False) -> str:
    p = (pkg_name or "").strip().lower()
    occ = (occasion or "").strip().lower()
    mt = (menu_type or "").strip().lower()
    
    if is_food_service or mt == "food_service" or any(k in p for k in ["food and services", "food & services", "food and service"]):
        return "Food and Services"
    elif any(k in p for k in ["food set", "food pack", "packed meal", "bilao", "bento", "food tray"]):
        return "Food Orders"
    elif any(k in occ for k in ["food set", "food pack", "food tray"]):
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
