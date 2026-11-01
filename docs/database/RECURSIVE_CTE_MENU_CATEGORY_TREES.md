# Recursive CTE Queries for Hierarchical Menu Category Trees

## 1. Schema Hierarchy
Menu categories support multi-level nested groupings (e.g. *Beverages* -> *Mocktails* -> *Tropical Coolers*).

```sql
WITH RECURSIVE CategoryTree AS (
    SELECT mc_id, mc_name, mc_parent_id, 1 as level
    FROM menu_categories
    WHERE mc_parent_id IS NULL
    UNION ALL
    SELECT c.mc_id, c.mc_name, c.mc_parent_id, ct.level + 1
    FROM menu_categories c
    INNER JOIN CategoryTree ct ON c.mc_parent_id = ct.mc_id
)
SELECT * FROM CategoryTree ORDER BY level, mc_name;
```
