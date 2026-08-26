"""
Complete SQLite Schema and View Provisioner for Jayraldine's Catering System.
Defines all tables, views, indexes, and starter seed data identical to PostgreSQL.
"""

import sqlite3
from pathlib import Path
from utils.logger import get_logger

log = get_logger()

SQLITE_FULL_SCHEMA = """
-- Business Information & Policy Settings
CREATE TABLE IF NOT EXISTS business_info (
    bi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bi_name TEXT DEFAULT "Jayraldine's Catering",
    bi_contact TEXT DEFAULT '+63 912 345 6789',
    bi_email TEXT DEFAULT 'admin@jayraldines.com',
    bi_address TEXT DEFAULT '123 Rizal St., Manila, Metro Manila',
    bi_max_daily_pax INTEGER DEFAULT 500,
    bi_min_downpayment_pct REAL DEFAULT 30.0,
    bi_allow_zero_downpayment INTEGER DEFAULT 0,
    bi_smtp_host TEXT DEFAULT '',
    bi_smtp_port INTEGER DEFAULT 587,
    bi_smtp_user TEXT DEFAULT '',
    bi_smtp_pass TEXT DEFAULT '',
    bi_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Occasions Master Table
CREATE TABLE IF NOT EXISTS occasions (
    occ_id INTEGER PRIMARY KEY AUTOINCREMENT,
    occ_name TEXT NOT NULL UNIQUE,
    occ_description TEXT,
    occ_is_active INTEGER DEFAULT 1
);

-- Customers Master Table
CREATE TABLE IF NOT EXISTS customers (
    cus_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cus_name TEXT NOT NULL,
    cus_contact TEXT,
    cus_email TEXT,
    cus_address TEXT,
    cus_address_id INTEGER,
    cus_loyalty_tier TEXT DEFAULT 'Bronze',
    cus_total_events INTEGER DEFAULT 0,
    cus_total_spent REAL DEFAULT 0.0,
    cus_status TEXT DEFAULT 'Active',
    cus_notes TEXT,
    cus_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Address Tables
CREATE TABLE IF NOT EXISTS address_provinces (
    ap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ap_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS address_cities (
    ac_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ac_province_id INTEGER REFERENCES address_provinces(ap_id),
    ac_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS address_barangays (
    ab_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ab_city_id INTEGER REFERENCES address_cities(ac_id),
    ab_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS addresses (
    ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_street TEXT,
    ad_barangay_id INTEGER REFERENCES address_barangays(ab_id),
    ad_city_id INTEGER REFERENCES address_cities(ac_id),
    ad_province_id INTEGER REFERENCES address_provinces(ap_id),
    ad_zip_code TEXT
);

CREATE TABLE IF NOT EXISTS customer_addresses (
    ca_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ca_customer_id INTEGER REFERENCES customers(cus_id) ON DELETE CASCADE,
    ca_address_id INTEGER REFERENCES addresses(ad_id) ON DELETE CASCADE
);

-- Loyalty & Follow-ups
CREATE TABLE IF NOT EXISTS customer_loyalty_tiers (
    cl_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cl_customer_id INTEGER UNIQUE REFERENCES customers(cus_id) ON DELETE CASCADE,
    cl_tier TEXT DEFAULT 'Bronze',
    cl_event_count INTEGER DEFAULT 0,
    cl_total_spent REAL DEFAULT 0.0,
    cl_last_recalculated DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_follow_ups (
    cfu_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cf_id INTEGER,
    cfu_customer_id INTEGER REFERENCES customers(cus_id) ON DELETE CASCADE,
    cf_customer_id INTEGER,
    cfu_follow_up_date DATE DEFAULT (DATE('now')),
    cfu_date TEXT,
    cf_date TEXT,
    cfu_note TEXT,
    cf_note TEXT,
    cfu_is_done INTEGER DEFAULT 0,
    cf_is_done INTEGER DEFAULT 0,
    cfu_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Menu Items & Packages
CREATE TABLE IF NOT EXISTS menu_items (
    mi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mi_name TEXT NOT NULL,
    name TEXT,
    mi_category TEXT NOT NULL,
    category TEXT,
    mi_package_tier TEXT DEFAULT 'Standard',
    mi_package TEXT DEFAULT 'Standard',
    package_tier TEXT DEFAULT 'Standard',
    package TEXT DEFAULT 'Standard',
    mi_price REAL NOT NULL,
    price REAL,
    mi_status TEXT DEFAULT 'Available',
    status TEXT DEFAULT 'Available',
    mi_description TEXT,
    description TEXT,
    mi_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS packages (
    pkg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pkg_name TEXT NOT NULL UNIQUE,
    pkg_description TEXT,
    pkg_price_per_pax REAL NOT NULL,
    pkg_min_pax INTEGER DEFAULT 30,
    pkg_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS package_items (
    pi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pi_package_id INTEGER NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
    pi_menu_item_id INTEGER REFERENCES menu_items(mi_id),
    pi_item_name TEXT,
    pi_category TEXT,
    pi_custom_price REAL DEFAULT 0.0,
    pi_quantity INTEGER DEFAULT 1
);

-- Bookings & Orders
CREATE TABLE IF NOT EXISTS bookings (
    bk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bk_booking_ref TEXT NOT NULL UNIQUE,
    bk_customer_id INTEGER REFERENCES customers(cus_id),
    bk_customer_name TEXT NOT NULL,
    bk_address TEXT,
    bk_event_date DATE NOT NULL,
    bk_event_time TIME DEFAULT '18:00',
    bk_venue TEXT,
    bk_occasion TEXT,
    bk_pax INTEGER NOT NULL,
    bk_total_amount REAL NOT NULL,
    bk_payment_mode TEXT DEFAULT 'Cash',
    bk_amount_paid REAL DEFAULT 0.0,
    bk_menu_type TEXT DEFAULT 'package',
    bk_package_id INTEGER REFERENCES packages(pkg_id),
    bk_notes TEXT,
    bk_status TEXT DEFAULT 'PENDING',
    bk_color_theme TEXT DEFAULT '#2563EB',
    bk_cancellation_reason TEXT,
    bk_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking_menu_items (
    bmi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bmi_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    bmi_item_id INTEGER REFERENCES menu_items(mi_id),
    bmi_item_name TEXT,
    bmi_category TEXT,
    bmi_price REAL DEFAULT 0.0,
    bmi_quantity INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS booking_items (
    bi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bi_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    bi_item_name TEXT NOT NULL,
    bi_category TEXT,
    bi_price REAL DEFAULT 0.0,
    bi_quantity INTEGER DEFAULT 1
);

-- Invoices & Payments
CREATE TABLE IF NOT EXISTS invoices (
    inv_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inv_booking_id INTEGER REFERENCES bookings(bk_id) ON DELETE CASCADE,
    inv_invoice_ref TEXT UNIQUE,
    inv_invoice_number TEXT,
    inv_customer_name TEXT,
    inv_event_date DATE,
    inv_total_amount REAL,
    inv_amount_paid REAL DEFAULT 0.0,
    inv_balance REAL,
    inv_status TEXT DEFAULT 'Unpaid',
    inv_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_records (
    pr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_invoice_id INTEGER REFERENCES invoices(inv_id) ON DELETE CASCADE,
    pr_amount REAL NOT NULL,
    pr_payment_date DATE NOT NULL,
    pr_payment_method TEXT DEFAULT 'Cash',
    pr_reference_number TEXT,
    pr_notes TEXT,
    pr_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Additional Charges / Additional Items applied to an existing order
CREATE TABLE IF NOT EXISTS booking_additional_charges (
    ac_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ac_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    ac_description TEXT NOT NULL,
    ac_amount REAL NOT NULL DEFAULT 0.0,
    ac_date_added DATE NOT NULL,
    ac_added_by TEXT,
    ac_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Terms & Conditions acknowledgement, tied to an order. Populated either by
-- the PC's own booking flow or merged in from the Tablet App (Tablet-mode.md
-- #6/#7/#17) - same table/columns on both sides so it merges cleanly.
CREATE TABLE IF NOT EXISTS terms_acknowledgements (
    ta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ta_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    ta_version TEXT NOT NULL,
    ta_acknowledged INTEGER DEFAULT 0,
    ta_acknowledged_at DATETIME,
    ta_customer_name TEXT,
    ta_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Cash Flow Transactions (for Cash Flow module)
CREATE TABLE IF NOT EXISTS cash_flow_transactions (
    cft_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cft_date DATE NOT NULL,
    cft_check_no TEXT DEFAULT '',
    cft_particulars TEXT NOT NULL,
    cft_deposit REAL DEFAULT 0.0,
    cft_withdrawal REAL DEFAULT 0.0,
    cft_balance REAL DEFAULT 0.0,
    cft_actual_sales REAL DEFAULT 0.0,
    cft_notes TEXT DEFAULT '',
    cft_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Monthly Sales Targets (for Sales Report vs Settings)
CREATE TABLE IF NOT EXISTS monthly_sales_targets (
    mst_year INTEGER NOT NULL,
    mst_month INTEGER NOT NULL,
    mst_target_amount REAL DEFAULT 85000.0,
    mst_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (mst_year, mst_month)
);

-- Kitchen Orders & Tasks
CREATE TABLE IF NOT EXISTS kitchen_orders (
    ko_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ko_booking_id INTEGER REFERENCES bookings(bk_id) ON DELETE CASCADE,
    ko_order_ref TEXT NOT NULL,
    ko_client_name TEXT,
    ko_customer_name TEXT,
    ko_event_name TEXT,
    ko_items_desc TEXT,
    ko_event_date DATE DEFAULT (DATE('now')),
    ko_event_time TIME DEFAULT '18:00',
    ko_pax INTEGER DEFAULT 50,
    ko_status TEXT DEFAULT 'Queued',
    ko_notes TEXT,
    ko_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kitchen_tasks (
    kt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kt_order_id INTEGER REFERENCES kitchen_orders(ko_id) ON DELETE CASCADE,
    kt_task_label TEXT NOT NULL,
    kt_is_done INTEGER DEFAULT 0,
    kt_sort_order INTEGER DEFAULT 0,
    kt_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Expenses
CREATE TABLE IF NOT EXISTS expenses (
    exp_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exp_category TEXT NOT NULL,
    exp_description TEXT NOT NULL,
    exp_amount REAL NOT NULL,
    exp_date DATE NOT NULL,
    exp_expense_date DATE,
    exp_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Calendar Events
CREATE TABLE IF NOT EXISTS calendar_events (
    ce_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ce_event_date DATE NOT NULL,
    ce_name TEXT NOT NULL,
    ce_pax INTEGER DEFAULT 0,
    ce_event_time TEXT DEFAULT '06:00 PM',
    ce_location TEXT DEFAULT 'TBD',
    ce_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
    notif_type TEXT DEFAULT 'info',
    notif_title TEXT NOT NULL,
    notif_message TEXT NOT NULL,
    notif_color TEXT DEFAULT '#3B82F6',
    notif_link_id INTEGER,
    notif_is_read INTEGER DEFAULT 0,
    notif_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    al_id INTEGER PRIMARY KEY AUTOINCREMENT,
    al_actor TEXT DEFAULT 'System',
    al_action TEXT NOT NULL,
    al_table_name TEXT DEFAULT 'bookings',
    al_record_id INTEGER DEFAULT 1,
    al_old_value TEXT,
    al_new_value TEXT,
    al_user TEXT DEFAULT 'System',
    al_details TEXT,
    al_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Database Backups Metadata
CREATE TABLE IF NOT EXISTS database_backups (
    backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    status TEXT DEFAULT 'Completed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- SYSTEM VIEWS (Optimized for SQLite)
-- =============================================================================

DROP VIEW IF EXISTS v_dashboard_kpis;
CREATE VIEW v_dashboard_kpis AS
SELECT
    (SELECT COUNT(*) FROM bookings WHERE DATE(bk_event_date) = DATE('now')) AS todays_events,
    (SELECT COUNT(*) FROM bookings WHERE bk_status = 'PENDING') AS pending_bookings,
    (SELECT COALESCE(SUM(bk_total_amount), 0) FROM bookings
     WHERE DATE(bk_event_date) >= DATE('now', 'weekday 0', '-6 days')
       AND DATE(bk_event_date) <= DATE('now', 'weekday 0')) AS weekly_revenue,
    (SELECT COALESCE(SUM(inv_total_amount - inv_amount_paid), 0) FROM invoices WHERE inv_status != 'Paid') AS unpaid_invoices,
    (SELECT COALESCE(SUM(bk_pax), 0) FROM bookings WHERE DATE(bk_event_date) = DATE('now')) AS todays_pax;

DROP VIEW IF EXISTS v_upcoming_events;
CREATE VIEW v_upcoming_events AS
SELECT
    b.bk_id, b.bk_booking_ref, b.bk_customer_name, b.bk_occasion,
    b.bk_venue, b.bk_event_date, b.bk_event_time, b.bk_pax, b.bk_status
FROM bookings b
WHERE DATE(b.bk_event_date) >= DATE('now') AND b.bk_status IN ('CONFIRMED', 'PENDING')
ORDER BY b.bk_event_date, b.bk_event_time;

DROP VIEW IF EXISTS v_report_kpis;
CREATE VIEW v_report_kpis AS
SELECT
    (SELECT COUNT(*) FROM bookings WHERE bk_status IN ('CONFIRMED', 'COMPLETED')) AS total_bookings,
    (SELECT COALESCE(SUM(bk_pax), 0) FROM bookings WHERE bk_status IN ('CONFIRMED', 'COMPLETED')) AS total_pax,
    (SELECT COALESCE(SUM(inv_total_amount), 0) FROM invoices) AS total_revenue,
    (SELECT COALESCE(SUM(inv_total_amount - inv_amount_paid), 0) FROM invoices WHERE inv_status != 'Paid') AS unpaid_amount,
    (SELECT COUNT(*) FROM bookings WHERE DATE(bk_created_at) = DATE('now') AND bk_status IN ('CONFIRMED', 'COMPLETED')) AS today_bookings,
    (SELECT COUNT(*) FROM bookings WHERE DATE(bk_created_at) >= DATE('now', '-7 days') AND bk_status IN ('CONFIRMED', 'COMPLETED')) AS week_bookings;

DROP VIEW IF EXISTS v_monthly_income;
CREATE VIEW v_monthly_income AS
SELECT
    strftime('%m', inv_event_date) AS month_num,
    CASE strftime('%m', inv_event_date)
        WHEN '01' THEN 'Jan' WHEN '02' THEN 'Feb' WHEN '03' THEN 'Mar' WHEN '04' THEN 'Apr'
        WHEN '05' THEN 'May' WHEN '06' THEN 'Jun' WHEN '07' THEN 'Jul' WHEN '08' THEN 'Aug'
        WHEN '09' THEN 'Sep' WHEN '10' THEN 'Oct' WHEN '11' THEN 'Nov' WHEN '12' THEN 'Dec'
        ELSE 'Other'
    END AS month_label,
    COALESCE(SUM(inv_total_amount), 0) AS total_revenue,
    COALESCE(SUM(inv_amount_paid), 0) AS total_paid
FROM invoices
WHERE strftime('%Y', inv_event_date) = strftime('%Y', 'now')
GROUP BY month_num
ORDER BY month_num;

DROP VIEW IF EXISTS v_payment_methods;
CREATE VIEW v_payment_methods AS
SELECT bk_payment_mode AS method, COUNT(*) AS total
FROM bookings
WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
GROUP BY bk_payment_mode;

DROP VIEW IF EXISTS v_top_menu_items;
CREATE VIEW v_top_menu_items AS
SELECT mi.mi_name AS item, COUNT(*) AS order_count
FROM booking_menu_items bmi
JOIN menu_items mi ON mi.mi_id = bmi.bmi_item_id
JOIN bookings b ON b.bk_id = bmi.bmi_booking_id
WHERE b.bk_status IN ('CONFIRMED', 'COMPLETED')
GROUP BY mi.mi_name
ORDER BY order_count DESC
LIMIT 10;

DROP VIEW IF EXISTS v_customer_order_frequency;
CREATE VIEW v_customer_order_frequency AS
SELECT bk_customer_name AS name, COUNT(*) AS booking_count
FROM bookings
WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
GROUP BY bk_customer_name
ORDER BY booking_count DESC
LIMIT 10;

DROP VIEW IF EXISTS v_recent_activity;
CREATE VIEW v_recent_activity AS
SELECT
    CASE bk_status
        WHEN 'CONFIRMED' THEN 'Booking Confirmed'
        WHEN 'CANCELLED' THEN 'Booking Cancelled'
        ELSE 'New Booking Request'
    END AS title,
    bk_customer_name || ' — ' || bk_occasion || ' (' || bk_pax || ' pax)' AS description,
    CASE bk_status
        WHEN 'CONFIRMED' THEN '#22C55E'
        WHEN 'CANCELLED' THEN '#EF4444'
        ELSE '#3B82F6'
    END AS color,
    bk_created_at AS created_at
FROM bookings
ORDER BY bk_created_at DESC
LIMIT 10;

DROP VIEW IF EXISTS v_audit_log_recent;
CREATE VIEW v_audit_log_recent AS
SELECT
    al_id AS id,
    al_id,
    al_actor AS actor,
    al_actor,
    al_action AS action,
    al_action,
    al_table_name AS table_name,
    al_table_name,
    al_record_id AS record_id,
    al_record_id,
    al_details AS description,
    al_details,
    al_created_at AS created_at,
    al_created_at
FROM audit_logs
ORDER BY al_created_at DESC
LIMIT 50;

DROP VIEW IF EXISTS v_profit_summary;
CREATE VIEW v_profit_summary AS
WITH months(m_num, m_label) AS (
    VALUES
    (1, 'Jan'), (2, 'Feb'), (3, 'Mar'), (4, 'Apr'),
    (5, 'May'), (6, 'Jun'), (7, 'Jul'), (8, 'Aug'),
    (9, 'Sep'), (10, 'Oct'), (11, 'Nov'), (12, 'Dec')
),
rev AS (
    SELECT CAST(strftime('%m', bk_event_date) AS INTEGER) AS m_num, SUM(bk_total_amount) AS revenue
    FROM bookings
    WHERE bk_status IN ('CONFIRMED', 'COMPLETED') AND strftime('%Y', bk_event_date) = strftime('%Y', 'now')
    GROUP BY m_num
),
exp AS (
    SELECT CAST(strftime('%m', exp_date) AS INTEGER) AS m_num, SUM(exp_amount) AS total_expense
    FROM expenses
    WHERE strftime('%Y', exp_date) = strftime('%Y', 'now')
    GROUP BY m_num
)
SELECT
    months.m_num AS month_num,
    months.m_label AS month_label,
    COALESCE(rev.revenue, 0.0) AS revenue,
    COALESCE(exp.total_expense, 0.0) AS total_expense,
    (COALESCE(rev.revenue, 0.0) - COALESCE(exp.total_expense, 0.0)) AS net_profit
FROM months
LEFT JOIN rev ON rev.m_num = months.m_num
LEFT JOIN exp ON exp.m_num = months.m_num
ORDER BY months.m_num;
DROP VIEW IF EXISTS v_customer_ledger;
CREATE VIEW v_customer_ledger AS
SELECT
    c.cus_id AS customer_id,
    c.cus_name AS customer_name,
    'Booking' AS entry_type,
    DATE(b.bk_created_at) AS recorded_date,
    b.bk_event_date AS event_date,
    b.bk_booking_ref AS reference,
    b.bk_occasion AS description,
    0.0 AS debit,
    0.0 AS credit,
    b.bk_status AS entry_status,
    b.bk_id AS source_id
FROM customers c
JOIN bookings b ON b.bk_customer_id = c.cus_id

UNION ALL

SELECT
    c.cus_id AS customer_id,
    c.cus_name AS customer_name,
    'Invoice' AS entry_type,
    DATE(i.inv_created_at) AS recorded_date,
    i.inv_event_date AS event_date,
    i.inv_invoice_ref AS reference,
    'Invoice issued' AS description,
    i.inv_total_amount AS debit,
    0.0 AS credit,
    i.inv_status AS entry_status,
    i.inv_id AS source_id
FROM customers c
JOIN bookings b ON b.bk_customer_id = c.cus_id
JOIN invoices i ON i.inv_booking_id = b.bk_id

UNION ALL

SELECT
    c.cus_id AS customer_id,
    c.cus_name AS customer_name,
    'Payment' AS entry_type,
    pr.pr_payment_date AS recorded_date,
    i.inv_event_date AS event_date,
    ('PMT-' || pr.pr_id) AS reference,
    COALESCE(pr.pr_note, pr.pr_notes, pr.pr_method, pr.pr_payment_method, 'Payment') AS description,
    0.0 AS debit,
    pr.pr_amount AS credit,
    'Paid' AS entry_status,
    pr.pr_id AS source_id
FROM customers c
JOIN bookings b ON b.bk_customer_id = c.cus_id
JOIN invoices i ON i.inv_booking_id = b.bk_id
JOIN payment_records pr ON pr.pr_invoice_id = i.inv_id

ORDER BY recorded_date DESC, entry_type;
"""


def _ensure_columns(conn: sqlite3.Connection):
    """Ensure all required columns exist in tables even if created earlier."""
    cur = conn.cursor()
    cols_to_add = [
        ("customers", "cus_loyalty_tier", "TEXT DEFAULT 'Bronze'"),
        ("customers", "cus_address_id", "INTEGER"),
        ("customers", "cus_total_events", "INTEGER DEFAULT 0"),
        ("customers", "cus_total_spent", "REAL DEFAULT 0.0"),
        ("customer_follow_ups", "cfu_follow_up_date", "DATE DEFAULT (DATE('now'))"),
        ("customer_follow_ups", "cf_id", "INTEGER"),
        ("customer_follow_ups", "cf_customer_id", "INTEGER"),
        ("customer_follow_ups", "cfu_date", "TEXT"),
        ("customer_follow_ups", "cf_date", "TEXT"),
        ("customer_follow_ups", "cfu_note", "TEXT"),
        ("customer_follow_ups", "cf_note", "TEXT"),
        ("customer_follow_ups", "cfu_is_done", "INTEGER DEFAULT 0"),
        ("customer_follow_ups", "cf_is_done", "INTEGER DEFAULT 0"),
        ("kitchen_orders", "ko_client_name", "TEXT"),
        ("kitchen_orders", "ko_customer_name", "TEXT"),
        ("kitchen_orders", "ko_event_name", "TEXT"),
        ("kitchen_orders", "ko_items_desc", "TEXT"),
        ("kitchen_orders", "ko_event_date", "DATE DEFAULT (DATE('now'))"),
        ("kitchen_orders", "ko_event_time", "TIME DEFAULT '18:00'"),
        ("kitchen_orders", "ko_pax", "INTEGER DEFAULT 50"),
        ("kitchen_orders", "ko_status", "TEXT DEFAULT 'Queued'"),
        ("kitchen_orders", "ko_notes", "TEXT"),
        ("kitchen_tasks", "kt_order_id", "INTEGER"),
        ("kitchen_tasks", "kt_task_label", "TEXT"),
        ("kitchen_tasks", "kt_is_done", "INTEGER DEFAULT 0"),
        ("kitchen_tasks", "kt_sort_order", "INTEGER DEFAULT 0"),
        ("notifications", "notif_color", "TEXT DEFAULT '#3B82F6'"),
        ("notifications", "notif_link_id", "INTEGER"),
        ("business_info", "bi_max_daily_pax", "INTEGER DEFAULT 500"),
        ("business_info", "bi_min_downpayment_pct", "REAL DEFAULT 30.0"),
        ("business_info", "bi_allow_zero_downpayment", "INTEGER DEFAULT 0"),
        ("bookings", "bk_address", "TEXT"),
        ("bookings", "bk_package_id", "INTEGER"),
        ("expenses", "exp_expense_date", "DATE"),
        ("invoices", "inv_invoice_ref", "TEXT"),
        ("invoices", "inv_customer_name", "TEXT"),
        ("invoices", "inv_event_date", "DATE"),
        ("payment_records", "pr_method", "TEXT DEFAULT 'Cash'"),
        ("payment_records", "pr_payment_method", "TEXT DEFAULT 'Cash'"),
        ("payment_records", "pr_note", "TEXT"),
        ("payment_records", "pr_notes", "TEXT"),
        ("payment_records", "pr_is_verified", "INTEGER DEFAULT 0"),
        ("payment_records", "pr_is_downpayment", "INTEGER DEFAULT 0"),
        ("bookings", "bk_down_payment", "REAL DEFAULT 0.0"),
        ("bookings", "bk_down_payment_status", "TEXT DEFAULT 'PENDING'"),
        ("invoices", "inv_down_payment", "REAL DEFAULT 0.0"),
        ("invoices", "inv_payment_verified", "INTEGER DEFAULT 0"),
        ("cash_flow_transactions", "cft_actual_sales", "REAL DEFAULT 0.0"),
        ("bookings", "bk_base_total", "REAL"),
    ]
    for table, col, col_def in cols_to_add:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except Exception:
            pass
    conn.commit()

    # Backfill bk_base_total for rows created before this column existed:
    # base = current total minus any additional charges already recorded.
    try:
        cur.execute("""
            UPDATE bookings
            SET bk_base_total = bk_total_amount - COALESCE(
                (SELECT SUM(ac_amount) FROM booking_additional_charges WHERE ac_booking_id = bookings.bk_id), 0.0
            )
            WHERE bk_base_total IS NULL
        """)
        conn.commit()
    except Exception:
        pass


def init_sqlite_db(conn: sqlite3.Connection):
    """Initialize SQLite tables, indexes, views, and essential seed data."""
    cursor = conn.cursor()
    cursor.executescript(SQLITE_FULL_SCHEMA)
    _ensure_columns(conn)

    # Backfill: any invoice whose booking is already CANCELLED but was cancelled
    # before this fix existed must not keep showing as outstanding Unpaid/Partial.
    cursor.execute("""
        UPDATE invoices
        SET inv_status = 'CANCELLED', inv_balance = 0
        WHERE inv_status != 'CANCELLED'
          AND inv_booking_id IN (SELECT bk_id FROM bookings WHERE bk_status = 'CANCELLED')
    """)

    # Seed Business Info if empty
    cursor.execute("SELECT COUNT(*) FROM business_info")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO business_info (bi_name) VALUES ('Jayraldine''s Catering')")

    # Seed Occasions if empty
    cursor.execute("SELECT COUNT(*) FROM occasions")
    if cursor.fetchone()[0] == 0:
        occasions = ["Wedding", "Birthday", "Debut", "Corporate Event", "Anniversary", "Christening", "Graduation", "Holiday Party"]
        for occ in occasions:
            cursor.execute("INSERT OR IGNORE INTO occasions (occ_name) VALUES (?)", (occ,))

    # Seed Address Data if empty
    cursor.execute("SELECT COUNT(*) FROM address_provinces")
    if cursor.fetchone()[0] == 0:
        log.info("Seeding standard Cebu address hierarchy...")
        cursor.execute("INSERT OR IGNORE INTO address_provinces (ap_name) VALUES ('Cebu')")
        prov_id = cursor.lastrowid or 1

        cities = [
            ("Cebu City", [
                "Apas", "Banilad", "Basak San Nicolas", "Busay", "Camputhaw", "Capitol Site",
                "Guadalupe", "Kasambagan", "Lahug", "Mabolo", "Pardo", "Punta Princesa",
                "Sambag I", "Sambag II", "Talamban", "Tisa", "Zapatera"
            ]),
            ("Mandaue City", [
                "Alang-alang", "Bakilid", "Banilad", "Cabancalan", "Centro", "Guizo",
                "Ibabao-Estancia", "Maguikay", "Paknaan", "Subangdaku", "Tipolo"
            ]),
            ("Lapu-Lapu City", [
                "Basak", "Gun-ob", "Ibo", "Mactan", "Maribago", "Marigondon",
                "Pajac", "Pajo", "Poblacion", "Pusok", "Subabasbas"
            ]),
            ("Talisay City", [
                "Bulacao", "Cansojong", "Dumlog", "Lawaan I", "Lawaan II",
                "Mohon", "Poblacion", "San Roque", "Tabunok", "Tangke"
            ]),
        ]
        for c_name, brgys in cities:
            cursor.execute("INSERT INTO address_cities (ac_province_id, ac_name) VALUES (?, ?)", (prov_id, c_name))
            c_id = cursor.lastrowid
            for b_name in brgys:
                cursor.execute("INSERT INTO address_barangays (ab_city_id, ab_name) VALUES (?, ?)", (c_id, b_name))

    # Seed Default Packages if empty
    cursor.execute("SELECT COUNT(*) FROM packages")
    if cursor.fetchone()[0] == 0:
        log.info("Seeding default catering packages...")
        pkgs = [
            ("Classic Celebration Package", "Standard catering buffet package with 4 main dishes, rice, dessert, and drinks.", 350.0, 30),
            ("Premium Grand Feast", "Deluxe buffet with 6 main dishes, roast pork lechon belly, 2 desserts, and beverage bar.", 550.0, 50),
            ("Executive VIP Buffet", "Top-tier package with live carving station, 7 signature mains, seafood, and full dessert table.", 850.0, 50),
        ]
        for name, desc, price, min_pax in pkgs:
            cursor.execute(
                "INSERT OR IGNORE INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax) VALUES (?, ?, ?, ?)",
                (name, desc, price, min_pax)
            )

    # Seed Default Occasions if empty
    cursor.execute("SELECT COUNT(*) FROM occasions")
    if cursor.fetchone()[0] == 0:
        log.info("Seeding default occasions...")
        default_occasions = [
            "Wedding", "Birthday", "Debut", "Corporate Event", "Anniversary",
            "Christening", "Graduation", "Holiday Party"
        ]
        for occ in default_occasions:
            cursor.execute(
                "INSERT OR IGNORE INTO occasions (occ_name, occ_is_active) VALUES (?, 1)",
                (occ,)
            )

    # Seed Default Menu Items if empty
    cursor.execute("SELECT COUNT(*) FROM menu_items")
    if cursor.fetchone()[0] == 0:
        log.info("Seeding default menu items...")
        items = [
            ("Special Pork Humba", "Pork", "Standard", 450.0, "Available", "Slow cooked pork belly with banana blossoms"),
            ("Lechon Belly Roast", "Pork", "Premium", 1200.0, "Available", "Crispy rolled pork belly with herbs"),
            ("Chicken Pandan", "Poultry", "Standard", 380.0, "Available", "Wrapped savory fried chicken"),
            ("Garlic Butter Buttered Shrimp", "Seafood", "Premium", 550.0, "Available", "Fresh prawns in savory garlic butter"),
            ("Sweet & Sour Fish Fillet", "Seafood", "Standard", 360.0, "Available", "Crispy fish fillet in pineapple sweet sauce"),
            ("Beef with Broccoli", "Beef", "Standard", 480.0, "Available", "Tender beef slices in oyster glaze"),
            ("Biko with Latik", "Dessert", "Standard", 250.0, "Available", "Traditional sweet sticky rice"),
            ("Mango Tapioca", "Dessert", "Standard", 220.0, "Available", "Chilled mango cubes with sago pearls"),
            ("Refillable Iced Tea", "Beverage", "Standard", 150.0, "Available", "House blend lemon iced tea"),
        ]
        for name, cat, pkg, price, status, desc in items:
            cursor.execute(
                "INSERT INTO menu_items (mi_name, name, mi_category, category, mi_package_tier, mi_package, package_tier, package, mi_price, price, mi_status, status, mi_description, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, name, cat, cat, pkg, pkg, pkg, pkg, price, price, status, status, desc, desc)
            )

    # Seed Default Monthly Sales Targets for 2026 (Ref Image 1: 85,000 / mo)
    cursor.execute("SELECT COUNT(*) FROM monthly_sales_targets WHERE mst_year = 2026")
    if cursor.fetchone()[0] == 0:
        log.info("Seeding default 2026 monthly sales targets (₱85,000/mo)...")
        for m in range(1, 13):
            cursor.execute(
                "INSERT INTO monthly_sales_targets (mst_year, mst_month, mst_target_amount) VALUES (2026, ?, 85000.0)",
                (m,)
            )

    # Ensure app_settings table exists for tracking initialization states
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed Starter Cash Flow Transactions ONLY on initial setup (never re-seed if user deleted records)
    cursor.execute("SELECT setting_value FROM app_settings WHERE setting_key = 'cash_flow_initial_seed_done'")
    cf_seeded_row = cursor.fetchone()
    if not cf_seeded_row:
        cursor.execute("SELECT COUNT(*) FROM cash_flow_transactions")
        if cursor.fetchone()[0] == 0:
            log.info("Seeding starter cash flow transactions (first-time setup)...")
            cf_data = [
                ("2026-05-01", "CHK-001", "BDO Jayraldine's Catering (Initial capital deposit)", 100000.0, 0.0, "Initial working capital"),
                ("2026-05-03", "CHK-002", "Cash on Hand (Ingredients market withdrawal)", 0.0, 25000.0, "Fresh pork and market ingredients"),
                ("2026-05-05", "GCASH-101", "GCash (Customer down payment)", 15000.0, 0.0, "Booking DP received"),
                ("2026-05-08", "MAYA-202", "Maya (Customer down payment)", 20000.0, 0.0, "Debut party DP received"),
                ("2026-05-10", "CHK-003", "Cash on Hand (Service staff payroll)", 0.0, 12000.0, "Assistant cook & server pay"),
                ("2026-05-12", "UB-303", "UnionBank (Equipment rental deposit)", 0.0, 8500.0, "Chafing dish and table rentals"),
                ("2026-05-15", "BPI-404", "BPI Personal Savings (Client booking settlement)", 35000.0, 0.0, "Full payment wedding banquet"),
                ("2026-05-18", "CHK-004", "Cash on Hand (Gasul & van diesel transport)", 0.0, 4500.0, "Delivery van diesel"),
                ("2026-05-20", "BDO-505", "BDO Jayraldine's Catering (Corporate banquet settlement)", 55000.0, 0.0, "Corporate seminar catering"),
            ]
            running_bal = 0.0
            for dt, chk, part, dep, withd, notes in cf_data:
                running_bal = running_bal + dep - withd
                cursor.execute("""
                    INSERT INTO cash_flow_transactions (cft_date, cft_check_no, cft_particulars, cft_deposit, cft_withdrawal, cft_balance, cft_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (dt, chk, part, dep, withd, running_bal, notes))
        cursor.execute("INSERT OR REPLACE INTO app_settings (setting_key, setting_value) VALUES ('cash_flow_initial_seed_done', '1')")

    # Seed Starter Expenses ONLY on initial setup (never re-seed if user deleted records)
    cursor.execute("SELECT setting_value FROM app_settings WHERE setting_key = 'expenses_initial_seed_done'")
    exp_seeded_row = cursor.fetchone()
    if not exp_seeded_row:
        cursor.execute("SELECT COUNT(*) FROM expenses")
        if cursor.fetchone()[0] == 0:
            log.info("Seeding starter expenses (first-time setup)...")
            exps = [
                ("Food Cost", "Fresh Pork Lechon & Pork Belly", 18500.0, "2026-05-02"),
                ("Transport", "Gas and Diesel for Delivery Van", 2400.0, "2026-05-04"),
                ("Labor", "Part-time Service Crew & Waiters", 6000.0, "2026-05-08"),
                ("Equipment", "Chafing Dish & Glassware Rental", 3500.0, "2026-05-10"),
                ("Utilities", "LPG Gasul & Kitchen Water Utility", 2800.0, "2026-05-14"),
                ("Food Cost", "Fresh Seafood & Vegetable Ingredients", 12500.0, "2026-05-16"),
            ]
            for cat, desc, amt, dt in exps:
                cursor.execute(
                    "INSERT INTO expenses (exp_category, exp_description, exp_amount, exp_date, exp_expense_date) VALUES (?, ?, ?, ?, ?)",
                    (cat, desc, amt, dt, dt)
                )
        cursor.execute("INSERT OR REPLACE INTO app_settings (setting_key, setting_value) VALUES ('expenses_initial_seed_done', '1')")

    # Ensure bk_color_theme column exists in bookings table
    try:
        cursor.execute("PRAGMA table_info(bookings)")
        bk_cols = [r[1] for r in cursor.fetchall()]
        if "bk_color_theme" not in bk_cols:
            cursor.execute("ALTER TABLE bookings ADD COLUMN bk_color_theme TEXT DEFAULT '#2563EB'")
    except Exception as exc:
        log.warning(f"Error checking/adding bk_color_theme column: {exc}")

    # Automatically and silently merge any duplicate customers and remove duplicate bookings
    try:
        _auto_deduplicate_database(conn)
    except Exception as exc:
        log.warning(f"Auto-deduplication check error: {exc}")

    conn.commit()
    log.info("SQLite Database Schema and Views verified successfully.")


def _auto_deduplicate_database(conn: sqlite3.Connection):
    """Automatically merges duplicate customer records and removes duplicate booking records
    completely in the background on startup or upgrade."""
    import re
    cur = conn.cursor()

    # 1. Customer deduplication
    cur.execute("SELECT cus_id, cus_name, cus_contact, cus_email, cus_total_events, cus_total_spent FROM customers ORDER BY cus_id ASC")
    rows = cur.fetchall()
    if rows:
        seen_groups = {}
        for r in rows:
            cid, name, contact, email, ev_cnt, spent = r[0], r[1] or "", r[2] or "", r[3] or "", r[4] or 0, r[5] or 0.0
            norm_name = re.sub(r"[^\w]", "", name.lower())
            norm_contact = re.sub(r"\D", "", contact)
            key = norm_name or norm_contact
            if not key:
                continue
            seen_groups.setdefault(key, []).append({
                "id": cid, "name": name, "contact": contact, "email": email, "events": ev_cnt, "spent": spent
            })

        for key, group in seen_groups.items():
            if len(group) > 1:
                group.sort(key=lambda x: (int(x["events"]), -int(x["id"])), reverse=True)
                master = group[0]
                master_id = master["id"]

                for dup in group[1:]:
                    dup_id = dup["id"]
                    try:
                        cur.execute("UPDATE bookings SET bk_customer_id = ?, bk_customer_name = ? WHERE bk_customer_id = ?",
                                    (master_id, master["name"], dup_id))
                        cur.execute("UPDATE customer_follow_ups SET cfu_customer_id = ? WHERE cfu_customer_id = ?",
                                    (master_id, dup_id))
                        cur.execute("DELETE FROM customers WHERE cus_id = ?", (dup_id,))
                    except Exception:
                        pass

                cur.execute("""
                    SELECT COUNT(*), COALESCE(SUM(bk_total_amount), 0.0)
                    FROM bookings WHERE bk_customer_id = ? AND bk_status != 'CANCELLED'
                """, (master_id,))
                stats = cur.fetchone()
                if stats:
                    cnt, sp = stats[0], stats[1]
                    tier = "Gold" if (cnt >= 5 or sp >= 100000) else ("Silver" if (cnt >= 3 or sp >= 50000) else "Bronze")
                    cur.execute("UPDATE customers SET cus_total_events = ?, cus_total_spent = ?, cus_loyalty_tier = ? WHERE cus_id = ?",
                                (cnt, sp, tier, master_id))

    # 2. Duplicate bookings deduplication
    cur.execute("""
        SELECT bk_id, bk_customer_name, bk_event_date, bk_occasion, bk_total_amount
        FROM bookings
        ORDER BY bk_id ASC
    """)
    b_rows = cur.fetchall()
    if b_rows:
        seen_b = {}
        dup_b_ids = []
        for b in b_rows:
            bid = b[0]
            bname = (b[1] or "").strip().lower()
            bdate = str(b[2] or "")
            bocc = (b[3] or "").strip().lower()
            bkey = (bname, bdate, bocc)
            if bkey in seen_b:
                dup_b_ids.append(bid)
            else:
                seen_b[bkey] = bid

        for dbid in dup_b_ids:
            cur.execute("DELETE FROM bookings WHERE bk_id = ?", (dbid,))
            cur.execute("DELETE FROM invoices WHERE inv_booking_id = ?", (dbid,))
            cur.execute("DELETE FROM kitchen_orders WHERE ko_booking_id = ?", (dbid,))

    conn.commit()
    cur.close()
