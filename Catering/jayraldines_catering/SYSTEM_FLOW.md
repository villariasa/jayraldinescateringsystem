# Jayraldine's Catering Management System
## System Flow & Transaction Guide

---

## 1. System Overview

Jayraldine's Catering Management System is a desktop application built with PySide6 and PostgreSQL. It manages the full lifecycle of a catering business — from booking inquiries to kitchen preparation and billing.

---

## 2. Main Modules

| Module | Purpose |
|---|---|
| Dashboard | Business overview and KPIs |
| Orders & Bookings | Receive and manage event bookings |
| Customers | Client database management |
| Menu | Menu items and packages |
| Calendar | Visual event scheduling |
| Kitchen | Order preparation tracking |
| Billing | Invoices and payment tracking |
| Reports | Business performance reports |
| Settings | Business information and preferences |

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
Click ✓ (Approve) → Status: CONFIRMED
   OR
Click ✗ (Decline) → Status: CANCELLED
        ↓
CONFIRMED bookings appear in:
  - Calendar (blue event card)
  - Kitchen queue (auto-added)
  - Upcoming Events on Dashboard
  - Alert scheduler (notifications)
```

---

### STEP 3 — Calendar Scheduling
```
[Calendar] shows monthly view
        ↓
Days with bookings show:
  - Total pax count (color-coded by capacity)
  - Number of bookings
        ↓
Click a day → Side panel opens showing:
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
        ↓
Staff moves orders through stages:

  Queued → Preparing → In Progress → Ready → Delivered → Done

        ↓
Staff can also move backwards if needed:

  Preparing → Queued (if wrong)
  In Progress → Preparing (if wrong)
  etc.
        ↓
Each card shows: client name, pax, items, event name
```

---

### STEP 5 — Billing & Invoicing
```
[Billing] manages all financial transactions
        ↓
Staff creates invoice:
  - Search and select customer
  - Link to booking (optional)
  - Set event date, total amount, amount paid
        ↓
Invoice status is auto-calculated:
  - amount_paid = 0           → Unpaid
  - 0 < amount_paid < total   → Partial
  - amount_paid = total       → Paid
        ↓
Staff can record payments at any time
        ↓
Invoice reference auto-generated (e.g. INV-005)
```

---

### STEP 6 — Notifications & Reminders
```
System checks every 10 seconds for upcoming CONFIRMED events
        ↓
Automatic alerts fire:

  24 hours before  → "Reminder: {ref} Tomorrow"        [yellow toast]
  30 minutes before → "Event in 30 Minutes: {ref}"     [orange toast]
  At event time    → "Event Starting Now: {ref}"       [red toast]

        ↓
Toast appears top-right of screen (auto-dismisses after 7 seconds)
        ↓
Notification saved to DB → visible in bell icon panel
        ↓
Staff can dismiss individual notifications or mark all as read
```

---

### STEP 7 — Reports & Export
```
[Reports] shows business performance:
  - Total bookings, pax, revenue, unpaid amount
  - Filter by: Today / This Week / This Month / This Year / All Time
        ↓
Charts available on Dashboard:
  - Monthly income (bar chart)
  - Payment methods (pie chart)
  - Top menu items
  - Customer order frequency
        ↓
Export options:
  - PDF  → Professional branded report (reportlab)
  - Excel → Styled spreadsheet (openpyxl)
  - CSV  → Raw data export
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
Staff can view booking history per customer
    ↓
Status can be set to Inactive if no longer active
```

---

## 5. Menu & Inventory

```
[Menu] manages available dishes and packages
    ↓
Each item has: name, description, category, package tier, price, status
    ↓
Status options:
  Available / Unavailable / Seasonal / Out of Stock
    ↓
[Inventory] tracks raw ingredients
    ↓
Low stock items trigger alerts on Dashboard
    ↓
Staff adjusts stock (restock or usage deduction)
```

---

## 6. Capacity Rules

| Pax Range | Calendar Color | Status |
|---|---|---|
| 0 – 399 | Green | Available |
| 400 – 599 | Amber | Near Full |
| 600+ | Red | Fully Booked |

> Maximum daily capacity: **600 pax**

---

## 7. Booking Status Rules

| From | To | Allowed |
|---|---|---|
| PENDING | CONFIRMED | ✓ Yes |
| PENDING | CANCELLED | ✓ Yes |
| CONFIRMED | any | ✗ Locked |
| CANCELLED | any | ✗ Locked |

> Only PENDING bookings can be edited or transitioned.

---

## 8. Kitchen Order Status Flow

```
Queued → Preparing → In Progress → Ready → Delivered → Done
  ↑           ↑            ↑          ↑          ↑
  └───────────┴────────────┴──────────┴──────────┘
              (can move backwards if needed)
```

---

## 9. Quick Reference — Key Shortcuts

| Action | Location |
|---|---|
| New Booking | Orders page → New Booking button |
| Approve Booking | Orders page → ✓ button (PENDING only) |
| View Day Events | Calendar → click any day |
| Add Manual Event | Calendar → Manage Day Schedule |
| Move Kitchen Order | Kitchen → Forward / Back buttons on card |
| Create Invoice | Billing → New Invoice |
| Export Report | Reports → Export button → PDF / Excel / CSV |
| Mark Notifications Read | Bell icon → Mark all read |
| Toggle Theme | Sun/Moon icon in top bar |
| Fullscreen | F11 |
| Exit Fullscreen | Esc |

---

## 10. Database Quick Reference

| Table | Purpose |
|---|---|
| `bookings` | All booking records |
| `customers` | Customer profiles |
| `menu_items` | Dish/item catalog |
| `packages` | Catering packages with pricing |
| `invoices` | Billing and payment records |
| `kitchen_orders` | Kitchen preparation queue |
| `calendar_events` | Manual schedule entries |
| `inventory` | Ingredient stock levels |
| `notifications` | System alert history |
| `business_info` | Owner/business settings |

---

*Generated by Jayraldine's Catering Management System*
