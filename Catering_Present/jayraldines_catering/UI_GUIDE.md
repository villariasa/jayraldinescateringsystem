# Jayraldine's Catering — UI & CSS Modification Guide

This guide covers every module, their key files, CSS classes, colors, and how to modify them without breaking the app.

---

## Table of Contents
1. [Project Structure](#1-project-structure)
2. [Theme System](#2-theme-system)
3. [CSS / QSS Reference](#3-css--qss-reference)
4. [Color Palette](#4-color-palette)
5. [Shared objectName Classes](#5-shared-objectname-classes)
6. [Module-by-Module Guide](#6-module-by-module-guide)
   - [Sidebar](#sidebar--componentssidebarpy)
   - [Topbar](#topbar--componentstopbarpy)
   - [Dashboard](#dashboard--uidashboard_pagepy)
   - [Bookings / Orders](#bookings--orders--uibooking_pagepy--componentsbooking_modalpy)
   - [Kitchen](#kitchen--uikitchen_pagepy)
   - [Billing](#billing--uibilling_pagepy)
   - [Customers](#customers--uicustomers_pagepy)
   - [Menu](#menu--uimenu_pagepy)
   - [Inventory](#inventory--uiinventory_pagepy)
   - [Reports](#reports--uireports_pagepy)
   - [Settings](#settings--uisettings_pagepy)
7. [How to Add a New Page](#7-how-to-add-a-new-page)
8. [Common UI Modifications](#8-common-ui-modifications)

---

## 1. Project Structure

```
jayraldines_catering/
├── main.py                         # App entry point
├── ui/
│   ├── main_window.py              # Root window, navigation, sidebar + topbar wiring
│   ├── dashboard_page.py           # Dashboard KPIs, charts, activity feed
│   ├── booking_page.py             # Bookings table + approve/decline/confirm
│   ├── kitchen_page.py             # Kitchen Kanban board (order statuses)
│   ├── billing_page.py             # Invoices table + new/edit/print/email
│   ├── customers_page.py           # Customers table + add/edit/follow-ups
│   ├── menu_page.py                # Menu items table + add/edit
│   ├── inventory_page.py           # Inventory stock table + adjust
│   ├── reports_page.py             # Charts + KPIs + expense tracker
│   └── settings_page.py            # Business info, SMTP, SMS, theme, backup
├── components/
│   ├── booking_modal.py            # Multi-step New Booking / Edit Booking dialog
│   ├── sidebar.py                  # Left navigation sidebar
│   ├── topbar.py                   # Top bar (search, clock, theme toggle, notifications)
│   ├── dialogs.py                  # Shared confirm() and success() dialogs
│   └── notifications.py            # Notification popover
├── styles/
│   ├── main.qss                    # Dark theme stylesheet (default)
│   └── light.qss                   # Light theme stylesheet
├── utils/
│   ├── db.py                       # PostgreSQL connection
│   ├── repository.py               # All database queries / stored proc calls
│   ├── theme.py                    # ThemeManager singleton (dark/light toggle)
│   ├── exporter.py                 # PDF / Excel / CSV export helpers
│   ├── mailer.py                   # SMTP email sender
│   ├── sms_sender.py               # Semaphore SMS sender
│   ├── scheduler.py                # Background notification scheduler
│   ├── session.py                  # Current logged-in user session
│   ├── icons.py                    # Icon helpers (btn_icon_primary, etc.)
│   └── menu_store.py               # In-memory menu item cache
└── jayraldines_catering.sql        # Full PostgreSQL schema + stored procedures
```

---

## 2. Theme System

**File:** `utils/theme.py`

The app has two themes — **Dark** (default) and **Light**. The `ThemeManager` is a singleton.

```python
from utils.theme import ThemeManager

tm = ThemeManager()
tm.is_dark()        # True / False
tm.toggle()         # switches theme, emits theme_changed signal
```

**Signal:** `ThemeManager().theme_changed.connect(my_func)`  
Connect to this signal in any widget that needs to repaint when the theme changes.

**How theme loads stylesheets:**
- Dark  → loads `styles/main.qss`
- Light → loads `styles/light.qss`

Both QSS files use the **same objectName selectors** — only the color values differ.

---

## 3. CSS / QSS Reference

QSS (Qt Style Sheets) works like CSS but uses objectName as the selector:

```css
/* Target by objectName */
QFrame#card { background-color: #111827; }

/* Target widget type globally */
QPushButton { border-radius: 8px; }

/* Target child widgets */
QFrame#card QLabel { color: #F9FAFB; }
```

**Set objectName in Python:**
```python
widget.setObjectName("card")
```

**Apply inline style (overrides QSS — use sparingly):**
```python
widget.setStyleSheet("background: #111827; color: #F9FAFB;")
```

> ⚠️ Inline `setStyleSheet()` overrides QSS completely for that widget.
> If a widget looks wrong after a theme switch, check if it has an inline `setStyleSheet()` with hardcoded colors.

---

## 4. Color Palette

### Dark Theme (`styles/main.qss`)

| Name         | Hex       | Used For                        |
|--------------|-----------|---------------------------------|
| Background   | `#0B1220` | App window, page background     |
| Surface      | `#111827` | Cards, inputs, table rows       |
| Hover        | `#1F2937` | Hovered rows, menu items        |
| Border       | `#243244` | Card borders, dividers, inputs  |
| Primary      | `#E11D48` | Buttons, active states, accents |
| Text         | `#F9FAFB` | Main labels and headings        |
| Muted        | `#9CA3AF` | Subtitles, placeholder text     |
| Success      | `#22C55E` | Status: Confirmed, Active       |
| Warning      | `#F59E0B` | Status: Pending, warnings       |
| Danger       | `#EF4444` | Status: Cancelled, errors       |
| Info         | `#3B82F6` | Status: Queued, info badges     |
| Gold         | `#F59E0B` | VIP/Gold tier, prices           |
| Purple       | `#A855F7` | VIP loyalty tier                |

### Light Theme (`styles/light.qss`)

| Name         | Hex       | Used For                        |
|--------------|-----------|---------------------------------|
| Background   | `#F8FAFC` | App window, page background     |
| Surface      | `#FFFFFF` | Cards, inputs, table rows       |
| Hover        | `#F1F5F9` | Hovered rows, dropdowns         |
| Border       | `#E2E8F0` | Card borders, dividers, inputs  |
| Primary      | `#E11D48` | Buttons, active states (same)   |
| Text         | `#0F172A` | Main labels and headings        |
| Muted        | `#64748B` | Subtitles, placeholder text     |

---

## 5. Shared objectName Classes

These are defined in `main.qss` / `light.qss` and can be used on any widget:

### Layout / Containers

| objectName     | Widget   | Description                      |
|----------------|----------|----------------------------------|
| `card`         | QFrame   | Rounded panel / card block       |
| `cardElevated` | QFrame   | Card with stronger shadow        |
| `kpiCard`      | QFrame   | Dashboard KPI stat box           |
| `accentCard`   | QFrame   | Card with colored left border    |
| `divider`      | QFrame   | Horizontal line separator        |
| `costBox`      | QFrame   | Booking payment breakdown box    |

### Typography

| objectName  | Widget | Description              |
|-------------|--------|--------------------------|
| `pageTitle` | QLabel | Top-left page heading    |
| `h1`        | QLabel | Large heading            |
| `h2`        | QLabel | Medium heading           |
| `h3`        | QLabel | Small section heading    |
| `subtitle`  | QLabel | Gray caption below title |
| `kpiValue`  | QLabel | Large KPI number         |
| `kpiLabel`  | QLabel | Small label under KPI    |
| `muted`     | QLabel | Very light gray text     |

### Buttons

| objectName        | Description                     |
|-------------------|---------------------------------|
| `primaryButton`   | Red filled button               |
| `secondaryButton` | Outlined / ghost button         |
| `ghostButton`     | Transparent button              |
| `dangerButton`    | Red danger action button        |
| `goldButton`      | Gold/amber button               |
| `pageButton`      | Pagination inactive button      |
| `pageButtonActive`| Pagination active button        |
| `segmentLeft`     | Left half of segmented control  |
| `segmentRight`    | Right half of segmented control |

### Badges

| objectName     | Color  | Usage              |
|----------------|--------|--------------------|
| `badgeSuccess` | Green  | Active, Confirmed  |
| `badgeWarning` | Amber  | Pending, Partial   |
| `badgeDanger`  | Red    | Cancelled, Unpaid  |
| `badgeInfo`    | Blue   | Info, Queued       |
| `badgeGold`    | Gold   | VIP, Gold tier     |

### Navigation / Shell

| objectName        | Widget  | Location       |
|-------------------|---------|----------------|
| `sidebar`         | QFrame  | Left sidebar   |
| `logoArea`        | QFrame  | Logo section   |
| `logoText`        | QLabel  | Business name  |
| `sidebarSection`  | QLabel  | Section header |
| `collapseBtn`     | QPushButton | Collapse arrow |
| `userProfileArea` | QFrame  | Bottom user section |
| `userAvatar`      | QLabel  | User circle avatar |
| `topBar`          | QFrame  | Top bar        |
| `searchBox`       | QLineEdit | Search input  |
| `notifBtn`        | QPushButton | Bell button  |
| `notifBadge`      | QLabel  | Red count badge |

---

## 6. Module-by-Module Guide

---

### Sidebar — `components/sidebar.py`

**Class:** `Sidebar` (line 27)

**Key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `__init__` | 30 | Builds sidebar, nav buttons, user section |
| `handle_click` | 143 | Highlights active nav item |
| `_on_nav_clicked` | 150 | Emits navigation signal |
| `toggle_collapse` | 157 | Expand / collapse sidebar |

**To change nav items:** Edit the list in `__init__` — each item is a tuple of `(icon_name, label, page_key)`.

**To change sidebar width:** Look for `setFixedWidth(220)` (expanded) and `setFixedWidth(64)` (collapsed).

**To change logo text:** Find `logoText` QLabel and change its `setText()`.

---

### Topbar — `components/topbar.py`

**Class:** `TopBar` (line 23)

**Key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `__init__` | 25 | Builds search, clock, theme toggle, notif bell |
| `_toggle_theme` | 112 | Switches dark/light theme |
| `_update_theme_icon` | 116 | Updates icon after toggle |
| `_tick_clock` | 132 | Updates the clock label every second |
| `set_page` | 136 | Updates the page title shown in topbar |

**To remove the clock:** Delete the `QTimer` and clock `QLabel` in `__init__`.

**To change search placeholder:** Find `searchBox.setPlaceholderText(...)`.

---

### Dashboard — `ui/dashboard_page.py`

**Classes:**
| Class | Line | Description |
|-------|------|-------------|
| `AnimatedCard` | 16 | Card with hover animation |
| `KPICard` | 22 | Stat box (value + label + icon) |
| `ActivityItem` | 63 | Single row in recent activity feed |
| `EventItem` | 94 | Upcoming event row |
| `MenuAlertItem` | 144 | Low-stock menu alert row |
| `DashboardPage` | 161 | Main dashboard widget |

**Key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_load_data` | 419 | Fetches all KPI/chart data from DB |
| `_rebuild_events` | 472 | Redraws upcoming events section |
| `_rebuild_activity` | 520 | Redraws recent activity feed |
| `_rebuild_menu_alerts` | 538 | Redraws low-stock alerts |
| `_export_pdf` | 389 | Exports dashboard summary to PDF |
| `_export_excel` | 404 | Exports dashboard summary to Excel |

**To add a new KPI card:** In `_build_ui`, find where `KPICard(...)` is called and add a new one with your label/icon.

**To change KPI colors:** Edit the color argument in each `KPICard(...)` call — color options: `#22C55E`, `#F59E0B`, `#3B82F6`, `#E11D48`.

---

### Bookings / Orders — `ui/booking_page.py` + `components/booking_modal.py`

**Classes:**
| Class | File | Line | Description |
|-------|------|------|-------------|
| `BookingPage` | booking_page.py | 83 | Bookings table with filter tabs |
| `StepIndicator` | booking_modal.py | 101 | Step progress dots (1-2-3-4) |
| `BookingModal` | booking_modal.py | 166 | Multi-step new/edit booking dialog |

**BookingPage key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_build_ui` | 97 | Builds table + filter tabs + action buttons |
| `_populate_table` | 177 | Fills rows from `self._bookings` list |
| `_approve_booking` | 262 | Changes status to CONFIRMED, sends SMS |
| `_decline_booking` | 297 | Changes status to CANCELLED |
| `_send_confirmation` | 341 | Re-sends SMS confirmation |
| `_delete_booking` | 387 | Deletes booking after confirm dialog |
| `_edit_booking` | 401 | Opens BookingModal in edit mode |
| `_open_modal` | 421 | Opens BookingModal for new booking |
| `_export_csv` | 457 | Exports bookings to CSV |

**BookingModal steps:**
| Step | Method | Line | Contents |
|------|--------|------|----------|
| 0 | `_build_step0` | 253 | Customer selector + readonly contact/email/address |
| 1 | `_build_step1` | 331 | Occasion, venue, date, time, pax, notes |
| 2 | `_build_step2` | 410 | Package selector OR custom menu items |
| 3 | `_build_step3` | 519 | Payment mode, amount paid, cost breakdown |

**To add a new field to the booking form:** Add it in the appropriate `_build_stepX` method, then save it in `_save()` at line 628.

**To change package prices/names:** Edit `_PACKAGES` list at the top of `booking_modal.py`:
```python
_PACKAGES = [
    ("Standard Package", "₱1,500/pax", "description", 1500),
    ("Premium Package",  "₱2,500/pax", "description", 2500),
    ("VIP Package",      "₱3,500/pax", "description", 3500),
]
```

**Step indicator colors:**
- Active step: `#E11D48` (red)
- Completed step: `#22C55E` (green with ✓)
- Inactive step: `#6B7280` (gray)
- Connector line: `#E2E8F0` light / `#243244` dark

---

### Kitchen — `ui/kitchen_page.py`

**Class:** `KitchenPage` (line 90)

**Key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `__init__` | 91 | Init, loads orders, connects theme signal |
| `_build_ui` | 104 | Builds the 6-column Kanban board |
| `_apply_column_styles` | (added) | Re-applies column bg/border on theme change |
| `_refresh_columns` | 167 | Clears and rebuilds all order cards |
| `_build_order_card` | 180 | Builds one order card widget |
| `_add_task_row` | 287 | Adds a task/subtask row inside a card |
| `_advance_order` | 326 | Moves order to next status column |
| `_cancel_order` | 351 | Cancels an order |

**Column status colors** (`_COL_COLORS` dict at top of file):
| Status | Color |
|--------|-------|
| Queued | `#F59E0B` (amber) |
| Preparing | `#A855F7` (purple) |
| In Progress | `#3B82F6` (blue) |
| Ready | `#22C55E` (green) |
| Delivered | `#10B981` (teal) |
| Cancelled | `#EF4444` (red) |

**To add a new column:** Add the status to `_DISPLAY_COLS` list and `_COL_COLORS` dict at the top of the file.

**To change order card appearance:** Edit `_card_style()` and `_id_color()` helper functions.

---

### Billing — `ui/billing_page.py`

**Classes:**
| Class | Line | Description |
|-------|------|-------------|
| `InvoiceDialog` | 39 | New / Edit invoice dialog |
| `BillingPage` | 205 | Invoices table + actions |

**BillingPage key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_build_ui` | 213 | Builds table with 10 columns |
| `_populate_table` | 267 | Fills invoice rows |
| `_edit_invoice` | 328 | Opens InvoiceDialog in edit mode |
| `_delete_invoice` | 358 | Deletes invoice |
| `_print_receipt` | 373 | Saves PDF receipt |
| `_email_receipt` | 395 | Emails PDF receipt via SMTP |
| `_open_new_invoice` | 431 | Opens InvoiceDialog for new invoice |
| `export_csv` | 459 | Exports to CSV |

**Invoice status colors:**
```python
_STATUS_COLORS = {
    "Paid":    "#22C55E",   # green
    "Partial": "#F59E0B",   # amber
    "Unpaid":  "#EF4444",   # red
}
```

**Table columns:** Invoice #, Customer, Event Date, Amount, Paid, Status, Edit, Delete, Print, Email

**To change invoice statuses:** Edit `_STATUSES` list and `_STATUS_COLORS` dict at top of file.

---

### Customers — `ui/customers_page.py`

**Classes:**
| Class | Line | Description |
|-------|------|-------------|
| `AddCustomerDialog` | 52 | Add new customer dialog (with country code selector) |
| `CustomersPage` | 210 | Customers table |

**AddCustomerDialog fields:**
| Field | Widget | Description |
|-------|--------|-------------|
| Name | QLineEdit | Full name or company |
| Country Code | QComboBox | 25 country codes, +63 default |
| Contact | QLineEdit | Phone number (without country code) |
| Email | QLineEdit | Email address |
| Address | QTextEdit | Street, Barangay, City, Province |
| Status | QComboBox | Active / Pending / Inactive |

**To add more country codes:** Edit `_COUNTRY_CODES` list at top of file:
```python
_COUNTRY_CODES = [
    ("+63", "PH  +63"),   # (actual_code, display_label)
    ("+1",  "US  +1"),
    ...
]
```

**CustomersPage key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_populate_table` | 276 | Fills rows with customer data |
| `_open_follow_ups` | 337 | Opens follow-up reminders dialog |
| `_open_add_dialog` | 433 | Opens AddCustomerDialog |
| `_filter_table` | 447 | Live search filter |

**Loyalty tier colors:**
```python
_TIER_COLORS = {
    "Bronze": ("#CD7F32", "rgba(205,127,50,.15)"),
    "Silver": ("#C0C0C0", "rgba(192,192,192,.15)"),
    "Gold":   ("#F59E0B", "rgba(245,158,11,.15)"),
    "VIP":    ("#A855F7", "rgba(168,85,247,.15)"),
}
```

**Table columns:** Name, Contact, Email, Events, Tier, Status, Actions

---

### Menu — `ui/menu_page.py`

**Classes:**
| Class | Line | Description |
|-------|------|-------------|
| `MenuItemDialog` | 19 | Edit existing menu item |
| `AddMenuItemDialog` | 162 | Add new menu item |
| `MenuPage` | 280 | Menu items table |

**Key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_populate_table` | 333 | Fills menu item rows |
| `_edit_item` | 371 | Opens edit dialog |
| `_delete_item` | 386 | Deletes item after confirm |
| `_open_add_dialog` | 403 | Opens add dialog |
| `filter_search` | 412 | Search filter (called from topbar) |

**Menu item status colors:**
```python
{
    "Available":    "#22C55E",   # green
    "Unavailable":  "#EF4444",   # red
    "Seasonal":     "#F59E0B",   # amber
    "Out of Stock": "#F97316",   # orange
}
```

**Table columns:** Name, Category, Package Tier, Price, Status, Edit, Delete

---

### Inventory — `ui/inventory_page.py`

**Classes:**
| Class | Line | Description |
|-------|------|-------------|
| `AddInventoryDialog` | 16 | Add new stock item |
| `AdjustStockDialog` | 128 | Adjust stock quantity |
| `InventoryPage` | 218 | Inventory table |

**Key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_populate_table` | 270 | Fills inventory rows, colors low-stock red |
| `_open_add_dialog` | 308 | Opens AddInventoryDialog |
| `_adjust_stock` | 321 | Opens AdjustStockDialog |
| `_delete_item` | 335 | Deletes inventory item |
| `filter_search` | 347 | Search filter |

**Low stock indicator:** If `quantity <= reorder_level`, row quantity cell turns `#EF4444` (red). Otherwise `#22C55E` (green).

**Table columns:** Item, Category, Qty, Unit, Reorder Level, Expiry Date, Adjust, Delete

---

### Reports — `ui/reports_page.py`

**Classes:**
| Class | Line | Description |
|-------|------|-------------|
| `HoverCard` | 42 | Animated KPI card for reports |
| `IncomeAreaChart` | 84 | Area chart — revenue over time |
| `PaymentDonutChart` | 172 | Donut chart — payment method split |
| `MonthlyRevenueChart` | 226 | Bar chart — monthly revenue |
| `TopMenuItemsChart` | 289 | Horizontal bars — top menu items |
| `CustomerFrequencyChart` | 342 | Bar chart — customer frequency |
| `ReportsPage` | 383 | Main reports page |

**Key methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_on_period` | 618 | Handles period filter change (7d/30d/90d/year) |
| `_reload_kpis` | 647 | Refreshes KPI values from DB |
| `_load_expenses` | 720 | Loads expense tracker table |
| `_open_add_expense` | 754 | Opens add expense dialog |
| `_export_pdf` | 834 | Exports full report to PDF |
| `_export_excel` | 848 | Exports to Excel |
| `_export_csv` | 862 | Exports to CSV |

**Chart colors:**
```python
# Used across all charts
Primary:  #E11D48   # red
Gold:     #F59E0B   # amber
Blue:     #3B82F6   # info
Green:    #22C55E   # success
Purple:   #8B5CF6   # accent
Gray:     #6B7280   # muted
```

---

### Settings — `ui/settings_page.py`

**Class:** `SettingsPage` (line 24)

**Sections and their builder methods:**
| Section | Method | Line | Description |
|---------|--------|------|-------------|
| Business Info | `_build_business_card` | 62 | Name, contact, email, address |
| Policy | `_build_policy_card` | 108 | Downpayment %, max pax |
| SMTP Email | `_build_smtp_card` | 157 | Host, port, user, password |
| SMS | `_build_sms_card` | 214 | Semaphore API key |
| Appearance | `_build_theme_card` | 256 | Dark/Light toggle |
| Backup | `_build_backup_card` | 287 | pg_dump backup / psql restore |
| Audit Log | `_build_audit_card` | 325 | Last 50 audit log entries |

**To add a new settings section:** Create a new `_build_xxx_card(self)` method that returns a `QFrame` with `setObjectName("card")`, then call it in `_build_ui` with `lay.addWidget(self._build_xxx_card())`.

---

## 7. How to Add a New Page

1. **Create the page file** in `ui/` — e.g. `ui/my_page.py`:
```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        title = QLabel("My Page")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
```

2. **Register it in `ui/main_window.py`** — import the class and add to the `_PAGES` dict and `QStackedWidget`.

3. **Add a nav item in `components/sidebar.py`** — add a tuple to the nav items list: `("icon-name", "Label", "my_page_key")`.

---

## 8. Common UI Modifications

### Change the primary/accent color (red → another color)

In `styles/main.qss` and `styles/light.qss`, find and replace all `#E11D48` with your new color.

### Change button style

In `main.qss`, find `QPushButton#primaryButton` and edit:
```css
QPushButton#primaryButton {
    background-color: #E11D48;   /* button fill color */
    color: #F9FAFB;              /* text color */
    border-radius: 8px;          /* corner roundness */
    padding: 8px 18px;           /* size */
    font-size: 13px;
    font-weight: 600;
}
```

### Change card appearance

In `main.qss`, find `QFrame#card`:
```css
QFrame#card {
    background-color: #111827;   /* card background */
    border-radius: 14px;          /* corner roundness */
    border: 1px solid #243244;   /* border color */
}
```

### Change table header color

In `main.qss`, find `QHeaderView::section`:
```css
QHeaderView::section {
    background-color: #1F2937;
    color: #9CA3AF;
    font-size: 11px;
    font-weight: 700;
    padding: 10px 12px;
    border: none;
}
```

### Change font size globally

In `main.qss`, find the `QWidget` or `QLabel` base rule and change `font-size`.

### Fix a widget stuck in dark mode in light theme

If a widget looks dark after switching to light, it has an inline `setStyleSheet()` with hardcoded dark colors. Find the widget in the relevant `.py` file and either:
- Remove the inline style so QSS takes over
- Replace hardcoded hex values with theme-aware calls:
```python
from utils.theme import ThemeManager
bg = "#FFFFFF" if not ThemeManager().is_dark() else "#111827"
widget.setStyleSheet(f"background: {bg};")
```
Then connect `ThemeManager().theme_changed` to re-apply the style.

### Add a divider line between sections

```python
div = QFrame()
div.setObjectName("divider")
div.setFixedHeight(1)
layout.addWidget(div)
```

### Add a badge/pill label

```python
badge = QLabel("Active")
badge.setObjectName("badgeSuccess")   # or badgeWarning, badgeDanger, badgeInfo
```
