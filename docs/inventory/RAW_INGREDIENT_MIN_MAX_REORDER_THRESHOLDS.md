# Raw Ingredient Min-Max Stock Levels & Automatic Reorder Triggers

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Inventory Engine, Procurement, Automated Reordering

---

## 1. Threshold Configuration

```json
{
  "SKU-RICE-JASMINE": {
    "name": "Jasmine Rice 50kg Sack",
    "min_stock": 5,
    "reorder_point": 10,
    "max_stock": 25,
    "unit": "sacks"
  },
  "SKU-OIL-PALM-20L": {
    "name": "Cooking Oil 20L Tin",
    "min_stock": 4,
    "reorder_point": 8,
    "max_stock": 20,
    "unit": "tins"
  }
}
```

Whenever inventory level drops to or below `reorder_point`, the desktop system prompts the commissary purchaser with a draft PO.\n