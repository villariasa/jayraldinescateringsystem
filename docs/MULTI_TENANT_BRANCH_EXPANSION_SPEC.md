# Multi-Branch Commissary Architecture & Partitioning

## 1. Regional Hierarchy
Enables multi-branch expansion across regional catering commissaries:

```
[ Central Commissary Headquarters ]
        │
        ├── [ Branch A: Cebu City Commissary ]
        ├── [ Branch B: Mandaue Satellite Kitchen ]
        └── [ Branch C: Lapu-Lapu Resort Hub ]
```

- **Partition Key**: `branch_id` embedded across all bookings, expenses, and inventory transactions.
- **Centralized Aggregation**: Real-time roll-up of branch revenues and cash flow into executive dashboard reports.
