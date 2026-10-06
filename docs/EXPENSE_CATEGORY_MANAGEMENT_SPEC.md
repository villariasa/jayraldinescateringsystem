# Expense Category Customization & Batch Reassignment Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Expense Tracking, Category Management Dialog, Database Schema

---

## 1. Feature Purpose

In catering operations, expense tracking requirements evolve dynamically. Businesses incur expenses ranging from daily market produce (meat, seafood, vegetables) to kitchen utilities, vehicle fuel, staff wages, and equipment rentals.

Hardcoded category lists limit bookkeeping agility. The Expense Category Management subsystem introduces:
1. **Dynamic Category Creation:** Administrators can add custom expense categories with custom color badges.
2. **Category Renaming & Merging:** If a category name is updated, existing records are automatically migrated.
3. **Batch Reassignment:** Users can select multiple expense items and reassign their category in a single operation.

---

## 2. Data Model

```sql
CREATE TABLE IF NOT EXISTS expense_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    badge_color TEXT NOT NULL DEFAULT '#64748B',
    icon TEXT DEFAULT 'tag',
    is_system_default INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.1 Default Category Seed

- `Meat & Poultry` (`#EF4444`)
- `Seafood` (`#0EA5E9`)
- `Vegetables & Fruits` (`#10B981`)
- `Dry Goods & Spices` (`#F59E0B`)
- `Kitchen Equipment & Gas` (`#8B5CF6`)
- `Transportation & Fuel` (`#EC4899`)
- `Staff Wages & Honoraria` (`#3B82F6`)
- `Utilities & Miscellaneous` (`#64748B`)
