# Reports & Analytics Multi-Period Filtering Architecture

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Reports Module, Expenses Page, Sales Analytics

---

## 1. Overview

Accurate financial reporting requires rapid date aggregation presets so catering managers can quickly assess operations across standard reporting horizons:
- **This Date / Today:** Immediate daily cash and kitchen deliveries.
- **This Week:** Monday through Sunday cycle covering upcoming weekend bookings.
- **This Month:** 1st day of current month to last calendar day.
- **This Year:** January 1 through December 31 of active calendar year.
- **Custom Date Range:** Granular `start_date` and `end_date` date picker inputs.

---

## 2. Filter Calculation Logic

All filter calculations use timezone-aware local date intervals (Asia/Manila):

```python
from datetime import date, timedelta

def get_period_bounds(preset: str, custom_start: str = None, custom_end: str = None):
    today = date.today()
    
    if preset == "today":
        return today, today
        
    elif preset == "this_week":
        start_week = today - timedelta(days=today.weekday()) # Monday
        end_week = start_week + timedelta(days=6)           # Sunday
        return start_week, end_week
        
    elif preset == "this_month":
        start_month = today.replace(day=1)
        # Last day of month
        next_month = (start_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_month = next_month - timedelta(days=1)
        return start_month, end_month
        
    elif preset == "this_year":
        start_year = date(today.year, 1, 1)
        end_year = date(today.year, 12, 31)
        return start_year, end_year
        
    elif preset == "custom":
        return date.fromisoformat(custom_start), date.fromisoformat(custom_end)
        
    raise ValueError(f"Unknown filter preset: {preset}")
```

---

## 3. SQL Query Parametrization

Queries across `bookings`, `invoices`, and `expenses` apply consistent date boundaries:

```sql
SELECT 
    category,
    COUNT(id) AS transaction_count,
    SUM(amount) AS total_amount
FROM expenses
WHERE expense_date >= :start_date 
  AND expense_date <= :end_date
GROUP BY category
ORDER BY total_amount DESC;
```
