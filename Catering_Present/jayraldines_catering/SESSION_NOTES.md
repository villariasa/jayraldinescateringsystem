# Session Notes — Jayraldines Catering

## Status Summary

### DONE ✅
1. **`notifications_panel.py` — eventFilter crash fixed**
   - File: `components/notifications_panel.py:270`
   - Added type guard: `if not hasattr(event, 'type') or not callable(event.type): return False`
   - Error was: `AttributeError: 'PySide6.QtWidgets.QWidgetItem' object has no attribute 'type'`

2. **`jayraldines_catering_clean.sql` — `sp_update_booking_status` fixed in file**
   - Removed downpayment validation block from status transition procedure
   - Removed unused DECLARE vars: `v_amount_paid`, `v_total`, `v_min_pct`, `v_allow_zero`
   - Changed `SELECT status, amount_paid, total_amount` → `SELECT status` only
   - **SQL file is correct** but live DB is NOT yet patched

---

### PENDING ❌

#### 1. Apply `sp_update_booking_status` fix to live PostgreSQL DB
- **DB config**: `host=localhost`, `port=5432`, `dbname=jayraldines_catering`, `user=postgres`, `password=12345678`
- **Problem**: `sp_update_booking_status` still has the broken downpayment check in the live DB
- **Error in app**: `[DB] callproc_void(sp_update_booking_status) failed: Downpayment insufficient. Required: 36600.00 pct. Paid: 0.00.`

**Fix SQL to run:**
```sql
CREATE OR REPLACE PROCEDURE sp_update_booking_status(
    IN  p_booking_id            INT,
    IN  p_new_status            TEXT,
    IN  p_cancellation_reason   TEXT DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
    v_current       booking_status;
    v_customer_id   INT;
BEGIN
    SELECT status
    INTO v_current
    FROM bookings WHERE id = p_booking_id;

    IF v_current = 'CANCELLED' THEN
        RAISE EXCEPTION 'Cancelled bookings cannot be changed.';
    END IF;

    IF v_current = 'COMPLETED' THEN
        RAISE EXCEPTION 'Completed bookings cannot be changed.';
    END IF;

    IF v_current NOT IN ('PENDING', 'CONFIRMED') THEN
        RAISE EXCEPTION 'Only PENDING or CONFIRMED bookings can be transitioned.';
    END IF;

    IF p_new_status = 'COMPLETED' AND v_current != 'CONFIRMED' THEN
        RAISE EXCEPTION 'Only CONFIRMED bookings can be marked as COMPLETED.';
    END IF;

    UPDATE bookings
    SET status              = p_new_status::booking_status,
        cancellation_reason = CASE WHEN p_new_status = 'CANCELLED'
                                   THEN p_cancellation_reason
                                   ELSE cancellation_reason END,
        updated_at          = NOW()
    WHERE id = p_booking_id;

    IF p_new_status = 'CONFIRMED' THEN
        SELECT customer_id INTO v_customer_id FROM bookings WHERE id = p_booking_id;

        IF v_customer_id IS NOT NULL THEN
            UPDATE customers
            SET total_events = (
                SELECT COUNT(*) FROM bookings
                WHERE customer_id = v_customer_id
                  AND status IN ('CONFIRMED', 'COMPLETED')
            ), updated_at = NOW()
            WHERE id = v_customer_id;
        END IF;
    END IF;
END;
$$;
```

**How to apply**: Open pgAdmin / DBeaver / any PostgreSQL client, connect to `jayraldines_catering` DB, and run the SQL above.

Alternatively, once `psql` or `psycopg2` is available:
```bash
# Option A — psql
psql -U postgres -d jayraldines_catering -c "<paste SQL above>"

# Option B — python3
python3 -m pip install psycopg2-binary
# then run the fix script
```

---

#### 2. `Unknown property transform` Qt warnings
- Repeated stylesheet warnings on startup
- Caused by a CSS `transform` property in `.qss` stylesheet (not supported by Qt)
- **Not yet investigated** — check `styles/main.qss` and `styles/light.qss` for `transform:` rules and remove them
