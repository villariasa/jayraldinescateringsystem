"""
Local SQLite schema — Jayraldine's Catering PWA backend.

Table/column names in the shared tables below are an EXACT mirror of
Catering_Present/jayraldines_catering/utils/sqlite_schema.py and of the
original Tablet/utils/sqlite_schema.py (PySide6 kiosk app, kept in the repo
as reference). This is deliberate: it keeps this backend's database
byte-compatible with the PC app's "Merge Backup File Into This Database"
import feature, and with any historical tablet.db files already collected
from the field.
"""
import os
import sqlite3
from pathlib import Path


def _app_data_dir() -> Path:
    """Local, non-network-share app-data directory for the SQLite file.

    Deliberately NOT next to this source file: this backend's own project
    folder may itself sit on a network/SMB share (confirmed during
    development — CIFS mounts break SQLite's file locking, causing spurious
    "database is locked" errors and truncated schema creation). Same reason
    the original PySide6 Tablet app resolved its own app-data directory
    instead of writing next to its source (see Tablet/utils/logger.py::
    get_app_data_dir()).
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "JayraldinesCateringPWA" / "data"
    return Path.home() / ".jayraldines_catering_pwa" / "data"


DATA_DIR = _app_data_dir()
DB_PATH = DATA_DIR / "catering_pwa.db"

SQLITE_FULL_SCHEMA = """
PRAGMA foreign_keys = ON;

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

CREATE TABLE IF NOT EXISTS menu_categories (
    mc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mc_name TEXT NOT NULL UNIQUE,
    mc_is_active INTEGER DEFAULT 1,
    mc_sort INTEGER DEFAULT 0
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
    pkg_is_set INTEGER DEFAULT 0,
    pkg_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS package_items (
    pi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pi_package_id INTEGER NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
    pi_menu_item_id INTEGER REFERENCES menu_items(mi_id),
    pi_item_name TEXT,
    pi_category TEXT,
    pi_custom_price REAL DEFAULT 0.0,
    pi_quantity INTEGER DEFAULT 1,
    pi_bucket_id INTEGER
);

CREATE TABLE IF NOT EXISTS package_buckets (
    pb_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pb_package_id INTEGER NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
    pb_name TEXT NOT NULL,
    pb_limit INTEGER NOT NULL DEFAULT 1,
    pb_categories TEXT NOT NULL DEFAULT '[]',
    pb_sort INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bookings (
    bk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bk_booking_ref TEXT NOT NULL UNIQUE,
    bk_customer_id INTEGER REFERENCES customers(cus_id),
    bk_customer_name TEXT NOT NULL,
    bk_address TEXT,
    bk_event_date DATE NOT NULL,
    bk_event_time TIME DEFAULT '18:00',
    bk_pickup_time TEXT,
    bk_dropoff_time TEXT,
    bk_venue TEXT,
    bk_occasion TEXT,
    bk_pax INTEGER NOT NULL,
    bk_num_sets INTEGER DEFAULT 0,
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

-- Food Set selections per booking: supports MULTIPLE sets and REPEATING the
-- same set (e.g. 2x Set A + 1x Set C). Each row is one chosen set + quantity.
-- Mirrors Catering_Present/jayraldines_catering/utils/sqlite_schema.py exactly.
CREATE TABLE IF NOT EXISTS booking_sets (
    bs_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bs_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    bs_set_id INTEGER REFERENCES packages(pkg_id),
    bs_set_name TEXT,
    bs_quantity INTEGER NOT NULL DEFAULT 1,
    bs_unit_price REAL DEFAULT 0.0,
    bs_sort INTEGER DEFAULT 0
);

-- Per-set customized dishes (each chosen/repeated set can be customized
-- independently). bsi_set_row_id ties a dish to one booking_sets row.
CREATE TABLE IF NOT EXISTS booking_set_items (
    bsi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bsi_set_row_id INTEGER NOT NULL REFERENCES booking_sets(bs_id) ON DELETE CASCADE,
    bsi_item_name TEXT,
    bsi_category TEXT,
    bsi_price REAL DEFAULT 0.0,
    bsi_quantity INTEGER DEFAULT 1
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

CREATE TABLE IF NOT EXISTS terms_acknowledgements (
    ta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ta_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    ta_version TEXT NOT NULL,
    ta_acknowledged INTEGER DEFAULT 0,
    ta_acknowledged_at DATETIME,
    ta_customer_name TEXT,
    ta_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tablet_master_sync (
    tms_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tms_source_export_version TEXT,
    tms_imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    tms_packages_count INTEGER DEFAULT 0,
    tms_menu_items_count INTEGER DEFAULT 0,
    tms_customers_count INTEGER DEFAULT 0
);
"""

_CEBU_CITIES = [
    ("Cebu City", [
        "Apas", "Banilad", "Basak San Nicolas", "Busay", "Camputhaw", "Capitol Site",
        "Guadalupe", "Kasambagan", "Lahug", "Mabolo", "Pardo", "Punta Princesa",
        "Sambag I", "Sambag II", "Talamban", "Tisa", "Zapatera",
    ]),
    ("Mandaue City", [
        "Alang-alang", "Bakilid", "Banilad", "Cabancalan", "Centro", "Guizo",
        "Ibabao-Estancia", "Maguikay", "Paknaan", "Subangdaku", "Tipolo",
    ]),
    ("Lapu-Lapu City", [
        "Basak", "Gun-ob", "Ibo", "Mactan", "Maribago", "Marigondon",
        "Pajac", "Pajo", "Poblacion", "Pusok", "Subabasbas",
    ]),
    ("Talisay City", [
        "Bulacao", "Cansojong", "Dumlog", "Lawaan I", "Lawaan II",
        "Mohon", "Poblacion", "San Roque", "Tabunok", "Tangke",
    ]),
    ("Consolacion", [
        "Casili", "Cansaga", "Danlag", "Jugan", "Nangka", "Pitogo", "Poblacion", "Tayud",
    ]),
    ("Liloan", [
        "Catarman", "Cotcot", "Jubay", "Poblacion", "San Roque", "San Vicente", "Yati",
    ]),
]

# Default seed packages/menu so the kiosk isn't empty on first launch,
# before an owner has imported real master data.
_DEFAULT_PACKAGES = [
    ("Silver Buffet", "Basic buffet package — 4 main dishes, rice, drinks.", 350.0, 60),
    ("Gold Buffet", "Premium buffet package — 6 main dishes, dessert, drinks.", 450.0, 60),
    ("Platinum Buffet", "Deluxe buffet package with VIP table service.", 600.0, 100),
]
_DEFAULT_MENU_CATEGORIES = [
    "Beef", "Pork", "Chicken", "Fish & Seafood", "Pasta & Noodles",
    "Vegetables", "Dessert", "Beverage", "Add-on",
]
_DEFAULT_MENU_ITEMS = [
    ("Beef Caldereta", "Beef", 0.0, "Available", ""),
    ("Pork Sisig", "Pork", 0.0, "Available", ""),
    ("Chicken Inasal", "Chicken", 0.0, "Available", ""),
    ("Sweet & Sour Fish Fillet", "Fish & Seafood", 0.0, "Available", ""),
    ("Buttered Shrimp", "Fish & Seafood", 150.0, "Available", "Add-on"),
    ("Carbonara", "Pasta & Noodles", 0.0, "Available", ""),
    ("Chopsuey", "Vegetables", 0.0, "Available", ""),
    ("Leche Flan", "Dessert", 0.0, "Available", ""),
    ("Buko Salad", "Dessert", 0.0, "Available", ""),
    ("Iced Tea Station", "Beverage", 0.0, "Available", ""),
]


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize schema. Idempotent — safe to call on every startup."""
    cur = conn.cursor()
    cur.executescript(SQLITE_FULL_SCHEMA)

    try:
        cur.execute("ALTER TABLE tablet_master_sync ADD COLUMN tms_customers_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    for table in ["bookings", "customers"]:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN sync_status TEXT DEFAULT 'pending'")
        except sqlite3.OperationalError:
            pass

    try:
        cur.execute("ALTER TABLE package_items ADD COLUMN pi_bucket_id INTEGER")
    except sqlite3.OperationalError:
        pass

    # New fields (client request): pickup/drop-off time + number of sets,
    # and pkg_is_set to flag predefined Food Sets A-E. Idempotent — guarded.
    _new_cols = [
        ("packages", "pkg_is_set", "INTEGER DEFAULT 0"),
        ("bookings", "bk_pickup_time", "TEXT"),
        ("bookings", "bk_dropoff_time", "TEXT"),
        ("bookings", "bk_num_sets", "INTEGER DEFAULT 0"),
    ]
    for table, col, col_def in _new_cols:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass

    cur.execute("SELECT COUNT(*) FROM address_provinces")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT OR IGNORE INTO address_provinces (ap_name) VALUES ('Cebu')")
        prov_id = cur.lastrowid or 1
        for city_name, barangays in _CEBU_CITIES:
            cur.execute("INSERT INTO address_cities (ac_province_id, ac_name) VALUES (?, ?)", (prov_id, city_name))
            city_id = cur.lastrowid
            for b in barangays:
                cur.execute("INSERT INTO address_barangays (ab_city_id, ab_name) VALUES (?, ?)", (city_id, b))

    # Seed predefined Food Sets A-E locally so the tablet has them even before
    # its first sync with the PC (mirrors Catering_Present's seeding; the PC's
    # copies will also arrive via sync and are matched by pkg_name so no dupes).
    cur.execute("SELECT COUNT(*) FROM packages WHERE COALESCE(pkg_is_set, 0) = 1")
    if cur.fetchone()[0] == 0:
        FOOD_SET_PRICE = 4800.0
        FOOD_SET_MIN_PAX = 20
        food_sets = [
            ("Set A", ["Humba", "Lumpia Shanghai", "Chopsuey", "Bam-i"]),
            ("Set B", ["Pork Steak", "Chicken Cordon Bleu", "Bam-i", "Fish Fillet w/ Lemon Sauce"]),
            ("Set C", ["Beef Kalderita", "Buttered Chicken", "Fish Fillet w/ Tartar Sauce", "Pancit Guisado"]),
            ("Set D", ["Pork Spareribs", "Crab Relleno", "Bam-i", "Korean Chicken"]),
            ("Set E", ["Beef Steak", "Fried Chicken", "Spaghetti", "Lumpia Shanghai"]),
        ]
        for set_name, dishes in food_sets:
            cur.execute(
                "INSERT OR IGNORE INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax, pkg_is_set) "
                "VALUES (?, ?, ?, ?, 1)",
                (set_name, "Predefined Food Set (" + ", ".join(dishes) + ")", FOOD_SET_PRICE, FOOD_SET_MIN_PAX),
            )
            cur.execute("SELECT pkg_id FROM packages WHERE pkg_name = ?", (set_name,))
            row = cur.fetchone()
            if row:
                set_pkg_id = row[0]
                for dish in dishes:
                    cur.execute(
                        "INSERT INTO package_items (pi_package_id, pi_item_name, pi_category, pi_quantity) "
                        "VALUES (?, ?, 'Main Dish', 1)",
                        (set_pkg_id, dish),
                    )

    # Clean up any stale categories that have no dishes
    try:
        cur.execute("SELECT COUNT(*) FROM menu_items")
        if cur.fetchone()[0] > 0:
            cur.execute("""
                DELETE FROM menu_categories
                WHERE LOWER(TRIM(mc_name)) NOT IN (
                    SELECT DISTINCT LOWER(TRIM(mi_category))
                    FROM menu_items
                    WHERE mi_category IS NOT NULL AND TRIM(mi_category) != ''
                )
            """)
    except Exception:
        pass

    conn.commit()
