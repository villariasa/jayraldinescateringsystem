# Jayraldine's Catering Management System
## System Flow & Transaction Guide

---

## 1. System Overview

Jayraldine's Catering Management System is a desktop application built with PySide6 and PostgreSQL. It manages the full lifecycle of a catering business — from booking inquiries to kitchen preparation, billing, customer loyalty, and business analytics.

---

## 2. Main Modules

| Module | Purpose |
|---|---|
| Dashboard | Business overview, KPIs, recent activity, follow-up alerts, capacity summary |
| Orders & Bookings | Receive, approve, decline, and manage event bookings |
| Customers | Client database, loyalty tiers, follow-up reminders |
| Menu | Menu items, packages, and status management |
| Calendar | Visual event scheduling with capacity indicators |
| Kitchen | Kanban order preparation tracking with per-dish task checklists |
| Billing | Invoices, payment tracking, receipt printing and emailing |
| Reports | Business performance reports, expense tracking, profit summary |
| Settings | Business info, booking policy, SMTP/SMS config, backup/restore, audit log |

---

## 3. Complete Transaction Flow

### STEP 1 — Customer Inquiry / Booking
```
Customer contacts Jayraldine's
        ↓
Staff opens [Orders & Bookings] → New Booking
        ↓
Fill in booking details:
  - Customer name (search or new)
  - Event date & time
  - Number of pax
  - Occasion & venue
  - Menu package or custom items
  - Payment mode & downpayment
        ↓
System validates:
  - Date capacity check (pax + existing bookings ≤ max_daily_pax)
  - Blocks if capacity exceeded (error dialog shown)
        ↓
Booking saved → Status: PENDING
        ↓
System auto-generates Booking Reference (e.g. BKG-005)
```

---

### STEP 2 — Booking Approval
```
[Orders & Bookings] shows PENDING bookings
        ↓
Staff reviews booking details
        ↓
Click ✓ (Approve):
  - System checks date capacity (hard block if exceeded)
  - System checks downpayment requirement:
      amount_paid ≥ (total_amount × min_downpayment_pct / 100)
      OR allow_zero_downpayment override is enabled
  - If checks pass → Status: CONFIRMED
  - Audit log entry written (actor, APPROVE, bookings)
  - Email confirmation auto-sent to customer (if email + SMTP configured)
  - SMS confirmation auto-sent to customer (if contact + Semaphore API configured)
   OR
Click ✗ (Decline):
  - Staff enters cancellation reason (optional text)
  - Status: CANCELLED
  - Cancellation reason stored and shown in booking row
  - Audit log entry written (actor, CANCEL, bookings)
        ↓
CONFIRMED bookings appear in:
  - Calendar (color-coded capacity indicator)
  - Kitchen queue (auto-added with per-dish tasks)
  - Upcoming Events on Dashboard
  - Alert scheduler (notifications)
        ↓
[Send Confirmation] button (bell icon) available on each CONFIRMED row
  → Manually resends email + SMS confirmation at any time
        ↓
When event date/time is reached:
  - Dashboard countdown shows "Event started"
  - [Mark as Completed] button appears on the upcoming event card
  - Clicking it sets Status: COMPLETED
  - Completed bookings are locked (no further status changes)
```

---

### STEP 3 — Calendar Scheduling
```
[Calendar] shows monthly view
        ↓
Days with bookings show:
  - Total pax count (color-coded by capacity vs. max_daily_pax)
  - Number of bookings
        ↓
Click a day → Side panel opens showing:
  - Capacity label: green / amber / red based on pax vs. max_daily_pax
  - All CONFIRMED bookings for that day
  - Any manually added schedule events
        ↓
Staff can click [Manage Day Schedule]
  - Add manual events (e.g. setup, teardown)
  - Delete manual events
  - Save the day schedule
```

---

### STEP 4 — Kitchen Preparation
```
[Kitchen] loads automatically from CONFIRMED bookings
        ↓
Each booking appears as a Kanban card in [Queued]
  - Tasks are auto-generated from items_desc (one task per comma-separated item)
        ↓
Staff moves orders through stages:

  Queued → Preparing → In Progress → Ready → Delivered → Done

        ↓
Staff can also move backwards if needed:

  Preparing → Queued (if wrong)
  In Progress → Preparing (if wrong)
  etc.
        ↓
Each status change is written to the audit log
        ↓
Per-dish task checklist on each card:
  - Checkbox per task (toggle done/undone)
  - Staff can add custom tasks manually
  - Staff can delete tasks
        ↓
Each card shows: client name, pax, items, event name, task progress
```

---

### STEP 5 — Billing & Invoicing
```
[Billing] manages all financial transactions
        ↓
Staff creates invoice:
  - Search and select customer
  - Set event date, total amount, amount paid
        ↓
Invoice status is auto-calculated:
  - amount_paid = 0           → Unpaid
  - 0 < amount_paid < total   → Partial
  - amount_paid = total       → Paid
        ↓
Invoice create and update actions written to audit log
        ↓
Staff can record payments at any time (via Edit Invoice)
        ↓
Invoice reference auto-generated (e.g. INV-005)
        ↓
Receipt actions:
  [Print Receipt] → Generates branded PDF receipt → save to disk
  [Email Receipt] → Prompts for customer email → sends PDF via SMTP
  Both actions logged to receipt_log (invoice_id, method, timestamp)
```

---

### STEP 6 — Notifications & Reminders
```
System checks every 10 seconds for upcoming CONFIRMED events
        ↓
Automatic alerts fire:

  24 hours before   → "Reminder: {ref} Tomorrow"        [yellow toast]
  30 minutes before → "Event in 30 Minutes: {ref}"      [orange toast]
  At event time     → "Event Starting Now: {ref}"       [red toast]

        ↓
Toast appears top-right of screen (auto-dismisses after 7 seconds)
        ↓
Notification saved to DB → visible in bell icon panel
        ↓
Staff can dismiss individual notifications or mark all as read
        ↓
Dashboard [Follow-ups Due Today] card:
  - Shows customers with a follow-up reminder due today
  - Refreshes every 60 seconds with the dashboard
```

---

### STEP 7 — Reports & Export
```
[Reports] shows business performance:
  - Total bookings, pax, revenue, unpaid amount
  - Filter by: Today / This Week / This Month / This Year / All Time
        ↓
Expense Tracking (Reports → Expenses tab):
  - Log expenses by category: Food Cost / Labor / Transport /
    Utilities / Equipment / Other
  - View total expenses vs. revenue
        ↓
Charts available on Dashboard:
  - Monthly income (bar chart)
  - Payment methods (pie chart)
  - Top menu items
  - Customer order frequency
  - Net Profit (YTD) KPI card
        ↓
Export options:
  - PDF   → Professional branded report (reportlab)
  - Excel → Styled spreadsheet (openpyxl)
  - CSV   → Raw data export
```

---

## 4. Customer Lifecycle

```
New Inquiry
    ↓
Added to [Customers] (manually or auto on booking)
    ↓
Status: Pending → Active (after first confirmed booking)
    ↓
total_events count increments on each confirmed booking
    ↓
Loyalty tier auto-updated by trigger:
  Bronze: 1–2 events
  Silver: 3–5 events
  Gold:   6–9 events
  VIP:    10+ events
    ↓
Loyalty tier badge displayed on customer row
    ↓
Staff can add follow-up reminders (date + note)
    ↓
Follow-ups due today appear on Dashboard alert card
    ↓
Status can be set to Inactive if no longer active
```

---

## 5. Email & SMS Notification Flow

```
Trigger: Booking approved (CONFIRMED)
    ↓
System reads SMTP config from business_info
  → If smtp_host + smtp_user set:
      Send HTML booking confirmation email with event details
      Log to confirmation_log (booking_id, method='email', sent_at)
    ↓
System reads Semaphore API key from business_info
  → If sms_api_key set and booking has contact number:
      Send SMS via Semaphore API with booking summary
      Log to confirmation_log (booking_id, method='sms', sent_at)

Manual resend:
  [Send Confirmation] bell button on CONFIRMED booking row
  → Repeats email + SMS send, logs each attempt

Configure in [Settings] → Email (SMTP) Configuration
                        → SMS Configuration (Semaphore)
```

---

## 6. Menu Management

```
[Menu] manages available dishes and packages
    ↓
Each item has: name, description, category, package tier, price, status
    ↓
Status options:
  Available / Unavailable / Seasonal / Out of Stock
    ↓
Unavailable / Seasonal / Out of Stock items flagged in v_menu_alerts
```

---

## 7. Capacity Rules

| Pax Range | Calendar Color | Capacity Status |
|---|---|---|
| 0 – 66% of max | Green | Available |
| 67% – 99% of max | Amber | Near Full |
| 100%+ of max | Red | Full |

> Default maximum daily capacity: **600 pax** — configurable in Settings → Booking & Capacity Policy.

> Calendar side panel capacity label reflects the same color thresholds in real time.

---

## 8. Booking Status Rules

| From | To | Allowed | Condition |
|---|---|---|---|
| PENDING | CONFIRMED | ✓ Yes | Downpayment met + capacity available |
| PENDING | CANCELLED | ✓ Yes | Cancellation reason recorded |
| CONFIRMED | COMPLETED | ✓ Yes | Event has started (via dashboard "Mark as Completed" button) |
| CONFIRMED | CANCELLED | ✗ Locked | — |
| COMPLETED | any | ✗ Locked | — |
| CANCELLED | any | ✗ Locked | — |

> Only PENDING bookings can be edited or transitioned.
> Only CONFIRMED bookings can be marked as COMPLETED (via Dashboard upcoming event card).
> Admin can bypass downpayment check via `allow_zero_downpayment` toggle in Settings.

---

## 9. Kitchen Order Status Flow

```
Queued → Preparing → In Progress → Ready → Delivered → Done
  ↑           ↑            ↑          ↑          ↑
  └───────────┴────────────┴──────────┴──────────┘
              (can move backwards if needed)
```

> Every status change is written to the audit log with actor, old status, and new status.

---

## 10. Audit Log

```
Actions logged automatically:
  - Booking approved   → actor, APPROVE, bookings, record_id
  - Booking cancelled  → actor, CANCEL, bookings, record_id + reason
  - Invoice created    → actor, CREATE, invoices, record_id
  - Invoice updated    → actor, UPDATE, invoices, old/new status+paid
  - Kitchen advance    → actor, STATUS_CHANGE, kitchen_orders, old→new
  - Kitchen return     → actor, STATUS_CHANGE, kitchen_orders, old→new
  - Kitchen cancelled  → actor, CANCEL, kitchen_orders, old→new

View in [Settings] → Audit Log (last 50 entries, refreshable)

Actor defaults to "staff" — changeable via utils/session.py set_actor()
```

---

## 11. Database Backup & Restore

```
[Settings] → Database Backup & Restore
    ↓
[Backup Database]:
  - Prompts for save location (.sql file)
  - Runs pg_dump -U postgres -d jayraldines_catering
  - Success: toast notification with file path
    ↓
[Restore Database]:
  - Prompts to select a .sql backup file
  - Confirmation dialog warns data will be overwritten
  - Runs psql -U postgres -d jayraldines_catering
  - Success: toast notification + restart reminder
```

---

## 12. Quick Reference — Key Shortcuts & Actions

| Action | Location |
|---|---|
| New Booking | Orders page → New Booking button |
| Approve Booking | Orders page → ✓ button (PENDING only) |
| Decline Booking | Orders page → ✗ button → enter reason |
| Resend Confirmation | Orders page → bell button (CONFIRMED only) |
| View Day Events | Calendar → click any day |
| Add Manual Event | Calendar → Manage Day Schedule |
| Add Kitchen Task | Kitchen card → type in task field → + button |
| Move Kitchen Order | Kitchen → Forward / Back buttons on card |
| Create Invoice | Billing → New Invoice |
| Print Receipt | Billing → printer icon on invoice row |
| Email Receipt | Billing → bell icon on invoice row |
| Log Expense | Reports → Expenses tab → Add Expense |
| View Audit Log | Settings → Audit Log section |
| Configure SMTP | Settings → Email (SMTP) Configuration |
| Configure SMS | Settings → SMS Configuration (Semaphore) |
| Backup Database | Settings → Backup Database button |
| Restore Database | Settings → Restore Database button |
| Export Report | Reports → Export button → PDF / Excel / CSV |
| Mark Notifications Read | Bell icon → Mark all read |
| Toggle Theme | Sun/Moon icon in top bar |
| Fullscreen | F11 |
| Exit Fullscreen | Esc |

---

## 13. Database Quick Reference

| Table | Purpose |
|---|---|
| `bookings` | All booking records with cancellation reason |
| `customers` | Customer profiles with loyalty tier |
| `customer_follow_ups` | Follow-up reminders per customer |
| `menu_items` | Dish/item catalog |
| `packages` | Catering packages with pricing |
| `invoices` | Billing and payment records |
| `kitchen_orders` | Kitchen preparation queue |
| `kitchen_tasks` | Per-dish task checklist for each kitchen order |
| `calendar_events` | Manual schedule entries |
| `notifications` | System alert history |
| `expenses` | Business expense records |
| `audit_logs` | Full change history with actor, action, old/new values |
| `receipt_log` | Receipt send history (print/email) |
| `confirmation_log` | Booking confirmation send history (email/SMS) |
| `business_info` | Owner/business settings, SMTP, SMS, policy config |

---

## 14. Settings Reference

| Setting | Location | Default |
|---|---|---|
| Business name / contact / email / address | Business Information | — |
| Minimum downpayment % | Booking & Capacity Policy | 30% |
| Allow confirming without downpayment | Booking & Capacity Policy | Off |
| Maximum daily pax | Booking & Capacity Policy | 600 pax |
| SMTP host / port / user / password | Email (SMTP) Configuration | — |
| Semaphore SMS API key | SMS Configuration | — |
| Theme (Dark / Light) | Appearance | Dark |
| Database backup | Database Backup & Restore | — |
| Database restore | Database Backup & Restore | — |
| Audit log viewer | Audit Log | last 50 entries |

---

*Updated: 2026-04-27 — Reflects all implemented features. Inventory module removed; system does not track raw ingredient stock.*
