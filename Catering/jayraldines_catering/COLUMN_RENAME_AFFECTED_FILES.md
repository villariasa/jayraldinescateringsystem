# Column Rename Plan — Jayraldines Catering System

## Naming Convention

Every column is prefixed with a table abbreviation:
`<table_abbreviation>_<original_column_name>`

---

## Table → Prefix Mapping

| Table | Prefix |
|---|---|
| `business_info` | `bi_` |
| `customers` | `cus_` |
| `packages` | `pkg_` |
| `menu_items` | `mi_` |
| `package_items` | `pi_` |
| `bookings` | `bk_` |
| `booking_menu_items` | `bmi_` |
| `invoices` | `inv_` |
| `payment_records` | `pr_` |
| `kitchen_orders` | `ko_` |
| `kitchen_tasks` | `kt_` |
| `expenses` | `exp_` |
| `customer_follow_ups` | `cfu_` |
| `communication_logs` | `cl_` |
| `audit_logs` | `al_` |
| `notifications` | `notif_` |
| `calendar_events` | `ce_` |
| `occasions` | `occ_` |
| `addresses` | `addr_` |
| `address_regions` | `ar_` |
| `address_provinces` | `ap_` |
| `address_cities` | `ac_` |
| `address_barangays` | `ab_` |

---

## Column Renames per Table

### business_info
| Old | New |
|---|---|
| `id` | `bi_id` |
| `name` | `bi_name` |
| `address` | `bi_address` |
| `contact` | `bi_contact` |
| `email` | `bi_email` |
| `logo_path` | `bi_logo_path` |
| `updated_at` | `bi_updated_at` |

### customers
| Old | New |
|---|---|
| `id` | `cus_id` |
| `name` | `cus_name` |
| `contact` | `cus_contact` |
| `email` | `cus_email` |
| `address` | `cus_address` |
| `occasion_preference` | `cus_occasion_preference` |
| `notes` | `cus_notes` |
| `loyalty_tier` | `cus_loyalty_tier` |
| `status` | `cus_status` |
| `address_id` | `cus_address_id` |
| `created_at` | `cus_created_at` |
| `updated_at` | `cus_updated_at` |

### packages
| Old | New |
|---|---|
| `id` | `pkg_id` |
| `name` | `pkg_name` |
| `description` | `pkg_description` |
| `base_price` | `pkg_base_price` |
| `per_head_price` | `pkg_per_head_price` |
| `min_pax` | `pkg_min_pax` |
| `is_active` | `pkg_is_active` |
| `created_at` | `pkg_created_at` |
| `updated_at` | `pkg_updated_at` |

### menu_items
| Old | New |
|---|---|
| `id` | `mi_id` |
| `name` | `mi_name` |
| `description` | `mi_description` |
| `category` | `mi_category` |
| `price` | `mi_price` |
| `package_tier` | `mi_package_tier` |
| `is_active` | `mi_is_active` |
| `created_at` | `mi_created_at` |
| `updated_at` | `mi_updated_at` |

### package_items
| Old | New |
|---|---|
| `id` | `pi_id` |
| `package_id` | `pi_package_id` |
| `item_id` | `pi_item_id` |

### bookings
| Old | New |
|---|---|
| `id` | `bk_id` |
| `booking_ref` | `bk_booking_ref` |
| `customer_id` | `bk_customer_id` |
| `customer_name` | `bk_customer_name` |
| `contact` | `bk_contact` |
| `email` | `bk_email` |
| `address` | `bk_address` |
| `occasion` | `bk_occasion` |
| `venue` | `bk_venue` |
| `event_date` | `bk_event_date` |
| `event_time` | `bk_event_time` |
| `pax` | `bk_pax` |
| `special_notes` | `bk_special_notes` |
| `menu_type` | `bk_menu_type` |
| `package_id` | `bk_package_id` |
| `total_amount` | `bk_total_amount` |
| `payment_mode` | `bk_payment_mode` |
| `amount_paid` | `bk_amount_paid` |
| `balance` | `bk_balance` |
| `status` | `bk_status` |
| `payment_status` | `bk_payment_status` |
| `created_at` | `bk_created_at` |
| `updated_at` | `bk_updated_at` |

### booking_menu_items
| Old | New |
|---|---|
| `id` | `bmi_id` |
| `booking_id` | `bmi_booking_id` |
| `item_id` | `bmi_item_id` |
| `quantity` | `bmi_quantity` |
| `unit_price` | `bmi_unit_price` |
| `subtotal` | `bmi_subtotal` |

### invoices
| Old | New |
|---|---|
| `id` | `inv_id` |
| `invoice_ref` | `inv_invoice_ref` |
| `booking_id` | `inv_booking_id` |
| `total_amount` | `inv_total_amount` |
| `amount_paid` | `inv_amount_paid` |
| `balance` | `inv_balance` |
| `status` | `inv_status` |
| `due_date` | `inv_due_date` |
| `notes` | `inv_notes` |
| `created_at` | `inv_created_at` |
| `updated_at` | `inv_updated_at` |

### payment_records
| Old | New |
|---|---|
| `id` | `pr_id` |
| `invoice_id` | `pr_invoice_id` |
| `amount` | `pr_amount` |
| `payment_date` | `pr_payment_date` |
| `method` | `pr_method` |
| `reference_no` | `pr_reference_no` |
| `notes` | `pr_notes` |
| `created_at` | `pr_created_at` |

### kitchen_orders
| Old | New |
|---|---|
| `id` | `ko_id` |
| `order_ref` | `ko_order_ref` |
| `booking_id` | `ko_booking_id` |
| `client_name` | `ko_client_name` |
| `event_name` | `ko_event_name` |
| `pax` | `ko_pax` |
| `items_desc` | `ko_items_desc` |
| `status` | `ko_status` |
| `created_at` | `ko_created_at` |
| `updated_at` | `ko_updated_at` |

### kitchen_tasks
| Old | New |
|---|---|
| `id` | `kt_id` |
| `order_id` | `kt_order_id` |
| `task_label` | `kt_task_label` |
| `is_done` | `kt_is_done` |
| `sort_order` | `kt_sort_order` |
| `updated_at` | `kt_updated_at` |

### expenses
| Old | New |
|---|---|
| `id` | `exp_id` |
| `category` | `exp_category` |
| `description` | `exp_description` |
| `amount` | `exp_amount` |
| `expense_date` | `exp_expense_date` |
| `created_at` | `exp_created_at` |
| `updated_at` | `exp_updated_at` |

### customer_follow_ups
| Old | New |
|---|---|
| `id` | `cfu_id` |
| `customer_id` | `cfu_customer_id` |
| `follow_up_date` | `cfu_follow_up_date` |
| `note` | `cfu_note` |
| `is_done` | `cfu_is_done` |
| `created_at` | `cfu_created_at` |
| `updated_at` | `cfu_updated_at` |

### communication_logs
| Old | New |
|---|---|
| `id` | `cl_id` |
| `log_type` | `cl_log_type` |
| `method` | `cl_method` |
| `recipient` | `cl_recipient` |
| `booking_id` | `cl_booking_id` |
| `invoice_id` | `cl_invoice_id` |
| `status` | `cl_status` |
| `note` | `cl_note` |
| `created_at` | `cl_created_at` |

### audit_logs
| Old | New |
|---|---|
| `id` | `al_id` |
| `actor` | `al_actor` |
| `action` | `al_action` |
| `table_name` | `al_table_name` |
| `record_id` | `al_record_id` |
| `old_value` | `al_old_value` |
| `new_value` | `al_new_value` |
| `created_at` | `al_created_at` |

### notifications
| Old | New |
|---|---|
| `id` | `notif_id` |
| `type` | `notif_type` |
| `title` | `notif_title` |
| `message` | `notif_message` |
| `color` | `notif_color` |
| `is_read` | `notif_is_read` |
| `created_at` | `notif_created_at` |

### calendar_events
| Old | New |
|---|---|
| `id` | `ce_id` |
| `event_date` | `ce_event_date` |
| `name` | `ce_name` |
| `pax` | `ce_pax` |
| `event_time` | `ce_event_time` |
| `location` | `ce_location` |
| `created_at` | `ce_created_at` |

### occasions
| Old | New |
|---|---|
| `id` | `occ_id` |
| `name` | `occ_name` |
| `created_at` | `occ_created_at` |

### addresses
| Old | New |
|---|---|
| `id` | `addr_id` |
| `region_id` | `addr_region_id` |
| `province_id` | `addr_province_id` |
| `city_id` | `addr_city_id` |
| `barangay_id` | `addr_barangay_id` |
| `street` | `addr_street` |
| `created_at` | `addr_created_at` |

### address_regions
| Old | New |
|---|---|
| `id` | `ar_id` |
| `name` | `ar_name` |

### address_provinces
| Old | New |
|---|---|
| `id` | `ap_id` |
| `region_id` | `ap_region_id` |
| `name` | `ap_name` |

### address_cities
| Old | New |
|---|---|
| `id` | `ac_id` |
| `province_id` | `ac_province_id` |
| `name` | `ac_name` |

### address_barangays
| Old | New |
|---|---|
| `id` | `ab_id` |
| `city_id` | `ab_city_id` |
| `name` | `ab_name` |

---

## Affected Files

### DIRECTLY IMPACTED — Must be fully updated

| File | Reason |
|---|---|
| `jayraldines_catering_clean.sql` | All table DDLs, indexes, FKs, views, stored procedures — every column reference must be renamed |
| `confirmed_only_views_migration.sql` | 4 views referencing `payment_mode`, `status`, `pax`, `total_amount`, `amount_paid`, `created_at`, `customer_name`, `name` (bookings/menu_items) |
| `occasions_migration.sql` | `occasions` table DDL + `INSERT INTO occasions (name)` — `name` → `occ_name` |
| `cebu_address_migration.sql` | All 5 address lookup table DDLs + FK on `customers.address_id` → `cus_address_id` |
| `utils/repository.py` | All raw SQL strings — every column reference must use new prefixed names; **output aliases must be preserved** so UI layer dict keys remain unchanged |
| `ui/reports_page.py` | `_period_sql_filter()` method contains inline SQL referencing `event_date` directly → must change to `bk_event_date` |

### CONDITIONALLY IMPACTED — Only if repository output aliases change

> **If `utils/repository.py` maintains the same output aliases (e.g., `SELECT bk_event_date AS event_date ...`), these files require NO changes.**

| File | Dict keys used |
|---|---|
| `ui/billing_page.py` | `invoice_ref`, `customer_name`, `total_amount`, `amount_paid`, `balance`, `status`, `due_date`, `id`, `booking_id`, `method`, `reference_no`, `payment_date` |
| `ui/booking_page.py` | `id`, `booking_ref`, `customer_name`, `occasion`, `event_date`, `pax`, `status`, `contact`, `email`, `venue`, `total_amount`, `amount_paid`, `balance` |
| `ui/customers_page.py` | `id`, `name`, `contact`, `email`, `address`, `loyalty_tier`, `status`, `notes`, `booking_count` |
| `ui/dashboard_page.py` | `total_bookings`, `confirmed`, `pending`, `cancelled`, `total_revenue`, `upcoming` |
| `ui/kitchen_page.py` | `id`, `order_ref`, `client_name`, `event_name`, `pax`, `status`, `items_desc`, `tasks` |
| `ui/menu_page.py` | `id`, `name`, `description`, `category`, `price`, `package_tier`, `is_active` |
| `ui/calendar_page.py` | `event_date`, `name`, `pax`, `event_time`, `location` |
| `ui/settings_page.py` | `name`, `address`, `contact`, `email`, `logo_path` (business_info); `id`, `name` (occasions) |
| `ui/inventory_page.py` | `ingredient`, `unit`, `stock`, `min_stock` — ⚠️ **WARNING: inventory table not found in any SQL schema file** |
| `components/booking_modal.py` | `id`, `name`, `per_head_price`, `min_pax`, `base_price` (packages); `id`, `name`, `contact`, `email` (customers) |
| `components/customer_search.py` | `name`, `contact` (from customers query alias) |
| `components/notifications_panel.py` | `id`, `type`, `title`, `message`, `color`, `created_at` (from notifications query alias) |

### NOT IMPACTED

| File | Reason |
|---|---|
| `utils/db.py` | Pure connection/execution layer — no SQL column names |
| `main.py` | Application entry point — no SQL column names |
| `ui/main_window.py` | Window shell only — no SQL column names |
| `utils/icons.py` | SVG icon helpers — no SQL |
| `utils/theme.py` | Theme management — no SQL |
| `utils/exporter.py` | Export logic — uses repo-returned dicts; only conditionally impacted if aliases change |
| `utils/signals.py` | Qt signal definitions — no SQL |
| `utils/paths.py` | Path utilities — no SQL |
| `utils/notif_scheduler.py` | Scheduler — calls repo functions; conditionally impacted if aliases change |
| `components/toast.py` | UI toast widget — no SQL |
| `components/splash.py` | Splash screen — no SQL |
| `components/sidebar.py` | Navigation sidebar — no SQL |
| `components/topbar.py` | Top bar — no SQL |
| `components/filter_popover.py` | Filter popover widget — no SQL |
| `components/address_search.py` | Address search widget — uses repo aliases |
| `components/charts.py` | Chart widgets — uses repo-returned dicts |
| `styles/main.qss` | Qt stylesheet — no SQL |
| `styles/light.qss` | Qt stylesheet — no SQL |

---

## Recommended Execution Order

1. **Back up the database** before any changes
2. **Update `jayraldines_catering_clean.sql`** — rename all columns in DDL, update all indexes, FKs, views, and stored procedures
3. **Update `occasions_migration.sql`** — `name` → `occ_name` in DDL and INSERT
4. **Update `confirmed_only_views_migration.sql`** — update all 4 view definitions
5. **Update `cebu_address_migration.sql`** — rename all address table columns, update FK reference
6. **Run migration SQL on the live database** using `ALTER TABLE ... RENAME COLUMN`
7. **Update `utils/repository.py`** — update all SQL column references, preserve output aliases
8. **Update `ui/reports_page.py`** — change `event_date` → `bk_event_date` in `_period_sql_filter()`
9. **Investigate `ui/inventory_page.py`** — locate missing inventory table schema and include in rename plan
10. **Re-run all migrations** on a fresh database to validate the new schema
11. **Test all pages** in the application to confirm no broken dict key lookups

---

## Notes

- **Strategy**: Preserve all repository output aliases so UI layer requires minimal changes.
  Example: `SELECT bk_event_date AS event_date FROM bookings` keeps `event_date` as the dict key.
- **ENUMs** (`booking_status`, `invoice_status`, `customer_status`, `loyalty_tier`, etc.) do **not** need renaming — they are type names, not column names.
- **Sequences** (`seq_booking_ref`, `seq_invoice_ref`, `seq_order_ref`) do **not** need renaming.
- **`ui/inventory_page.py`** references columns (`ingredient`, `unit`, `stock`, `min_stock`) from a table absent from all SQL schema files — this must be resolved before this file can be included in the rename.
