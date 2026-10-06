# Receipt Downpayment Status Evaluation Rules

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Billing Module, Exporter Engine, Tablet PWA

---

## 1. Context

On receipt printouts, displaying `(Cash - Partial)` or `(Cash - Pending)` when a client has successfully paid their downpayment caused customer inquiries. In catering operations, the initial payment transaction specifically fulfills the **Downpayment requirement**.

Therefore, if any downpayment amount has been tendered (`amount_paid > 0` or `down_payment > 0`), the status badge for the downpayment row must state **PAID**, not Partial or Pending.

---

## 2. Evaluation Rules Matrix

| Condition | Downpayment Badge | Balance Due Status | Overall Booking Status |
|---|---|---|---|
| `amount_paid == 0` and `down_payment == 0` | `PENDING` | `UNPAID` | `Pending / Unconfirmed` |
| `amount_paid > 0` and `amount_paid < total` | `PAID` | `BALANCE DUE` | `Confirmed / Partial` |
| `amount_paid >= total` | `PAID` | `CLEARED (0.00)` | `Fully Paid` |

---

## 3. Algorithm Implementation

```python
def resolve_downpayment_badge(inv: dict, booking: dict) -> str:
    # Explicit status override if specified
    explicit_status = (booking.get("down_payment_status") 
                       or booking.get("bk_down_payment_status") 
                       or inv.get("down_payment_status"))
    if explicit_status:
        return str(explicit_status).upper()
        
    paid = float(inv.get("amount_paid") or inv.get("paid") or booking.get("paid") or 0.0)
    dp = float(inv.get("down_payment") or booking.get("down_payment") or 0.0)
    
    if paid > 0 or dp > 0:
        return "PAID"
    return "PENDING"
```
