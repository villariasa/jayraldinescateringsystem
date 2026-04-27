# PRD — Jayraldine's Catering Management System
## Detailed Feature Checklist & Task Breakdown

> Items marked ~~strikethrough~~ are already implemented.
> Items marked **[ ]** are pending implementation.

---

## CATEGORY A — Operationally Important

### Feature 2 — Receipt Printing / Invoice Export to Customer
> *"No receipt printing — after payment, there's no way to print or email a receipt/invoice to the customer — lets apply this give me what credentials you need"*

**Credentials / Config needed:**
- SMTP email: host, port, username, password (or use Gmail App Password)
- Stored in `business_info` table (new columns: `smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass`)

**Tasks:**
- [x] Add SMTP config columns to `business_info` table (`sp_save_smtp_config` SP)
- [x] Add SMTP settings fields to Settings page UI
- [x] Create `utils/mailer.py` — sends email via `smtplib` with HTML body + PDF attachment
- [x] Generate receipt PDF via `utils/exporter.py` (new `export_receipt_pdf()` method)
- [x] Add "Print Receipt" button on Billing page (opens PDF preview / save dialog)
- [x] Add "Email Receipt" button on Billing page (sends PDF to customer email)
- [x] `sp_log_receipt_sent` SP — records that receipt was sent (timestamp + method)

---

### Feature 3 — Booking Confirmation Notification to Customer (SMS/Email)
> *"No booking confirmation sent to customer — no SMS or email notification goes out when a booking is approved — lets apply this give me what credentials you need"*

**Credentials / Config needed:**
- Email: same SMTP config as Feature 2
- SMS (optional): Semaphore or Vonage API key (stored in `business_info`)

**Tasks:**
- [x] Add SMS API key column to `business_info` (`sp_save_sms_config` SP)
- [x] Add SMS config fields to Settings page UI
- [x] Create `utils/sms_sender.py` — sends SMS via Semaphore API (POST request)
- [x] On booking approval (`sp_update_booking_status`): trigger email + SMS to customer contact
- [x] Add "Send Confirmation" button on Booking detail view (manual resend)
- [x] `sp_log_confirmation_sent` SP — records confirmation sent (booking_id, method, timestamp)

---

### Feature 4 — Downpayment Enforcement Before Confirming Booking
> *"No downpayment enforcement — system doesn't block confirming a booking if no downpayment was received — ok apply also this"*

**Tasks:**
- [x] Add `min_downpayment_pct` column to `business_info` (default 30%) — configurable
- [x] Add "Minimum Downpayment %" field to Settings page UI
- [x] Update `sp_update_booking_status` — raise exception if `amount_paid < (total_amount * min_downpayment_pct / 100)` when transitioning to CONFIRMED
- [x] Show blocking error dialog in `booking_page.py` when downpayment is insufficient
- [x] Allow override by admin (bypass flag) — add `allow_zero_downpayment` toggle in Settings

---

### Feature 5 — Event Date Conflict / Capacity Hard Block
> *"No event date conflict check — can book 10 events on the same day beyond 600 pax with no hard block — apply this"*

**Tasks:**
- [x] Add `max_daily_pax` column to `business_info` (default 600)
- [x] Add "Max Daily Capacity" field to Settings page UI
- [x] Create `sp_check_date_capacity` SP — returns current pax booked for a given date
- [x] Update `sp_create_booking` and `sp_update_booking` — call capacity check, raise exception if exceeded
- [x] Show blocking error dialog in `booking_page.py` when date is over capacity
- [x] Update `v_calendar_day_summary` — include capacity warning flag

---

### Feature 6 — Kitchen Per-Dish Task Checklist
> *"Kitchen has no per-dish task breakdown — just shows a description string, no checklist for kitchen staff — apply this"*

**Tasks:**
- [x] Create `kitchen_tasks` table — `id, order_id (FK), task_label, is_done, sort_order, updated_at`
- [x] Create `sp_add_kitchen_task` SP — insert a task row
- [x] Create `sp_toggle_kitchen_task` SP — toggle `is_done` for a task
- [x] Create `sp_delete_kitchen_task` SP — delete a task row
- [x] Update Kitchen page UI — expand Kanban card to show task checklist
- [x] Add "Add Task" input on each kitchen card
- [x] Auto-generate default tasks from `items_desc` on kitchen order creation

---

### Feature 7 — Cancellation Reason Tracking
> *"When a booking is cancelled, no reason is recorded — apply this"*

**Tasks:**
- [x] Add `cancellation_reason` TEXT column to `bookings` table (nullable)
- [x] Update `sp_update_booking_status` — accept `p_reason TEXT` parameter, store when cancelling
- [x] Show reason input dialog in `booking_page.py` when staff clicks cancel (Decline) button
- [x] Display cancellation reason in booking detail view

---

## CATEGORY B — Business Intelligence

### Feature 8 — Profit / Expense Tracking
> *"Revenue is tracked but no cost of goods, no net profit calculation — apply this"*

**Tasks:**
- [x] Create `expenses` table — `id, category (ENUM), description, amount, expense_date, created_at`
- [x] Create `expense_category` ENUM — `('Food Cost','Labor','Transport','Utilities','Equipment','Other')`
- [x] Create `sp_add_expense` SP — insert expense record
- [x] Create `sp_update_expense` SP — update expense record
- [x] Create `sp_delete_expense` SP — delete expense record
- [x] Create `v_profit_summary` view — revenue vs expenses per month, net profit
- [x] Add Expenses sub-tab to Reports page
- [x] Add Expense entry form (date, category, description, amount)
- [x] Show Net Profit KPI card on Dashboard

---

### Feature 9 — Customer Loyalty Tracking
> *"total_events exists but no repeat customer rewards or follow-up reminders — apply this"*

**Tasks:**
- [x] Add `loyalty_tier` column to `customers` — `ENUM ('Bronze','Silver','Gold','VIP')` auto-updated by trigger
- [x] Create `sp_recalculate_loyalty` SP — updates tier based on `total_events` count
  - Bronze: 1–2 events, Silver: 3–5, Gold: 6–9, VIP: 10+
- [x] Create `customer_follow_ups` table — `id, customer_id (FK), follow_up_date, note, is_done, created_at`
- [x] Create `sp_add_follow_up` SP — insert a follow-up reminder
- [x] Create `sp_complete_follow_up` SP — mark follow-up done
- [x] Add Follow-Up Reminders section in Customers page
- [x] Show loyalty tier badge on customer card/row
- [x] Dashboard alert: customers with follow-up due today

---

### Feature 10 — Audit Log
> *"No record of who changed what and when (e.g. who approved a booking) — apply this"*

**Tasks:**
- [x] Create `audit_logs` table — `id, actor TEXT, action TEXT, table_name TEXT, record_id INT, old_value JSONB, new_value JSONB, created_at`
- [x] Create `sp_write_audit_log` SP — insert audit log row
- [x] Call `sp_write_audit_log` from: booking approve/cancel
- [x] Call `sp_write_audit_log` from: invoice create/payment, kitchen status change
- [x] Add current user/actor to app session (minimal: store `current_user` in a singleton)
- [x] Add Audit Log view in Settings page — last 50 entries, refreshable
- [x] `v_audit_log_recent` view — last 50 entries with human-readable description

---

## CATEGORY C — Minor but Useful

### Feature 12 — Database Backup / Restore
> *"No built-in way to backup the database from within the app — apply this"*

**Tasks:**
- [x] Add "Backup Database" button in Settings page
- [x] Run `pg_dump` via `subprocess` to export `.sql` file to user-chosen folder
- [x] Add "Restore Database" button — run `psql` via `subprocess` to restore from `.sql` file
- [x] Show confirmation dialog before restore (warns it will overwrite current data)
- [x] Display progress/completion toast notification on backup/restore success

---

## ALREADY IMPLEMENTED (from previous sessions)

- [x] Booking CRUD (create, edit, approve, cancel, delete)
- [x] Customer management (add, edit, delete, search)
- [x] Menu items management (add, edit, delete, search, filter by status)
- [x] Package management
- [x] Calendar with monthly view, day bookings, manual schedule events
- [x] Kitchen Kanban board (Queued → Preparing → In Progress → Ready → Delivered → Done)
- [x] Kitchen auto-populate from CONFIRMED bookings
- [x] Billing / Invoicing (create, edit, record payment, delete)
- [x] Invoice status auto-calculation (Unpaid / Partial / Paid)
- [x] Reports with period filters (Today / This Week / This Month / This Year / All Time)
- [x] PDF export (reportlab) — professional branded report
- [x] Excel export (openpyxl) — styled spreadsheet
- [x] CSV export
- [x] Dashboard KPI cards (today's events, pending bookings, weekly revenue, unpaid)
- [x] Dashboard charts (monthly income bar, payment methods pie, top menu items, customer frequency)
- [x] Notification system — toast alerts (24h, 30min, at event time)
- [x] Notification bell panel with unread badge
- [x] Inventory tracking with low-stock alerts
- [x] Business info settings page
- [x] Dark/Light theme toggle
- [x] F11 fullscreen / Esc exit fullscreen
- [x] Global search bar (filters current page)
- [x] Booking approval/cancel with booking_ref as unique key
- [x] Calendar "Manage Day Schedule" persistent button
- [x] Calendar "Today" button preserves booked schedules

---

## IMPLEMENTATION PRIORITY ORDER

| Priority | Feature | Complexity | Impact |
|----------|---------|------------|--------|
| 1 | Feature 5 — Capacity Hard Block | Low | High |
| 2 | Feature 4 — Downpayment Enforcement | Low | High |
| 3 | Feature 7 — Cancellation Reason | Low | Medium |
| 4 | Feature 6 — Kitchen Task Checklist | Medium | High |
| 5 | Feature 8 — Expense / Profit Tracking | Medium | High |
| 6 | Feature 9 — Customer Loyalty | Medium | Medium |
| 7 | Feature 10 — Audit Log | Medium | Medium |
| 8 | Feature 2 — Receipt Printing/Email | Medium | High |
| 9 | Feature 3 — Booking SMS/Email Confirm | Medium | High |
| 10 | Feature 12 — DB Backup/Restore | Low | Medium |

---

*Updated: 2026-04-27 — Based on owner review and PRD annotations*
