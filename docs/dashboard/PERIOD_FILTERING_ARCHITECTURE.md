# Dashboard Dynamic Period Filtering Architecture

## 1. Overview
The dashboard filter bar allows users to dynamically scope analytics metrics:
- **All Time**: Resets start and end date bounds to `None`.
- **Today**: Binds queries from `00:00:00` to `23:59:59` of the current calendar day.
- **This Week**: Calculates Monday through Sunday of the active calendar week.
- **This Month**: Dynamically bounds the 1st of the month through the final day.

## 2. Dynamic Component Updates
- `KPICard.update_title()` dynamically updates card labels (e.g., "Today's Events", "This Week's Revenue").
- Upcoming event table queries apply `BETWEEN :date_start AND :date_end` clauses.
