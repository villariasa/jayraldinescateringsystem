# Central Audit Log & Tamper-Evident Security Journal Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Security, Audit Trail, Compliance Engine

---

## 1. Requirement Overview
In commercial catering management, cashier discounts, price overrides, booking cancellations, and cash drawer reconciliations must be logged into an append-only, tamper-evident audit journal.

---

## 2. Data Structure & Hash Chaining

Each audit record includes a cryptographic SHA-256 hash linking it to the previous record:

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    target_id TEXT NOT NULL,
    details_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Verification Algorithm
$$	ext{record\_hash} = 	ext{SHA256}(	ext{id} \parallel 	ext{prev\_hash} \parallel 	ext{action\_type} \parallel 	ext{details\_json} \parallel 	ext{created\_at})$$

Any manual alteration in the database file breaks the cryptographic chain and triggers an alert upon system audit check.\n