# Kiosk Food Set Selection & Customization Workflow

> **Target Version:** v2.7.5  
> **Status:** Technical Specification  
> **Date:** October 29, 2026  
> **Audience:** Frontend Developers, UX Designers

---

## 1. Workflow Architecture
When a customer selects a predefined food set (e.g., Set Menu A - Filipino Classic) instead of a custom buffet tier, the wizard dynamically adapts the menu step:

```
[ Step 1: Package Selection ] ──► Choose Set Menu (min_pax: 20)
               │
               ▼
[ Step 2: Date & Occasion ]   ──► Venue, Date, Guest Count
               │
               ▼
[ Step 3: Menu Customization] ──► View Set Inclusions
                                  ├── Keep Default Set Dishes
                                  └── Swap/Remove Dish (Triggers Replacement Counter)
```

## 2. State Retention & Data Model
- `d.setSelections`: An array of objects tracking active set instances, selected dishes, and excluded item IDs.
- `removedCount`: Evaluated dynamically to prevent customers from advancing without either accepting defaults or selecting approved replacements.
