"""
Tablet local SQLite schema — Jayraldine's Catering Tablet App.

IMPORTANT: table and column names in the shared tables below are an EXACT
mirror of Catering_Present/jayraldines_catering/utils/sqlite_schema.py. This
is deliberate, not incidental — it is what lets a tablet's local .db file be
fed directly into the PC app's Settings -> "Merge Backup File Into This
Database" feature (utils/importer.py: merge_database_file) without any
translation step. Do not rename or restructure these tables without making
the matching change on the PC side.

Tables NOT needed on the tablet (cash_flow_transactions, audit_logs,
notifications, kitchen_orders, expenses, etc.) are intentionally omitted -
the tablet is an order-entry device, not a management system (see
Tablet-mode.md section 8/16).
"""
import sqlite3
import tempfile
from pathlib import Path
from utils.logger import get_logger, get_app_data_dir

log = get_logger()

SQLITE_FULL_SCHEMA = """
PRAGMA foreign_keys = ON;

-- ── Shared with PC (schema-identical — required for merge compatibility) ──

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
    bk_base_total REAL,
    bk_payment_mode TEXT DEFAULT 'Cash',
    bk_amount_paid REAL DEFAULT 0.0,
    bk_down_payment REAL DEFAULT 0.0,
    bk_down_payment_status TEXT DEFAULT 'PENDING',
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
    inv_down_payment REAL DEFAULT 0.0,
    inv_payment_verified INTEGER DEFAULT 0,
    inv_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_records (
    pr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_invoice_id INTEGER REFERENCES invoices(inv_id) ON DELETE CASCADE,
    pr_amount REAL NOT NULL,
    pr_payment_date DATE NOT NULL,
    pr_payment_method TEXT DEFAULT 'Cash',
    pr_method TEXT DEFAULT 'Cash',
    pr_reference_number TEXT,
    pr_notes TEXT,
    pr_note TEXT,
    pr_is_downpayment INTEGER DEFAULT 0,
    pr_is_verified INTEGER DEFAULT 0,
    pr_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking_additional_charges (
    ac_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ac_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    ac_description TEXT NOT NULL,
    ac_amount REAL NOT NULL DEFAULT 0.0,
    ac_date_added DATE NOT NULL,
    ac_added_by TEXT,
    ac_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Terms & Conditions acknowledgement, tied to the order (Tablet-mode.md #6/#7).
-- This table is ALSO added to the PC schema (same name/columns) so it merges
-- cleanly via the existing import path instead of becoming an orphaned record.
CREATE TABLE IF NOT EXISTS terms_acknowledgements (
    ta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ta_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    ta_version TEXT NOT NULL,
    ta_acknowledged INTEGER DEFAULT 0,
    ta_acknowledged_at DATETIME,
    ta_customer_name TEXT,
    ta_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Tablet-only (local operational state, never exported/merged) ──

-- Tracks when master data (packages/menu) was last imported from the PC, and
-- which PC-side export version it came from, so a re-import can tell whether
-- the file being opened is newer than what's already loaded.
CREATE TABLE IF NOT EXISTS tablet_master_sync (
    tms_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tms_source_export_version TEXT,
    tms_imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    tms_packages_count INTEGER DEFAULT 0,
    tms_menu_items_count INTEGER DEFAULT 0
);
"""


def get_sqlite_db_path() -> Path:
    try:
        data_dir = get_app_data_dir() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "tablet.db"
    except Exception:
        target = Path(tempfile.gettempdir()) / "jayraldines_catering_tablet_data"
        target.mkdir(parents=True, exist_ok=True)
        return target / "tablet.db"


def init_sqlite_db(conn: sqlite3.Connection):
    """Initialize the tablet's local SQLite schema. Idempotent — safe to call
    every app startup."""
    cursor = conn.cursor()
    cursor.executescript(SQLITE_FULL_SCHEMA)
    conn.commit()
    log.info("Tablet SQLite schema verified successfully.")
