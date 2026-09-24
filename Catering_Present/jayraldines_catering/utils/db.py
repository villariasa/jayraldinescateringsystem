"""
Unified Database Module for Jayraldine's Catering.
Provides ultra-fast embedded SQLite database support with WAL mode by default,
and optional PostgreSQL fallback if explicitly configured.
"""

import os
import re
import time
import sqlite3
import threading
import contextlib
import uuid
from pathlib import Path
from datetime import date, datetime, time as time_type
from typing import Any, Optional, Dict, List, Tuple

from utils.logger import get_logger
from utils.sqlite_schema import init_sqlite_db

log = get_logger()


def compute_invoice_status(total_amount: float, amount_paid: float) -> str:
    """Single source of truth for deriving a billing status from totals.

    Never trust a stored/imported status string - always recompute from the
    actual total vs. actual valid payments so cancelled/edited/imported
    records can't drift into a stale Paid/Partial/Unpaid label.
    """
    total_amount = total_amount or 0.0
    amount_paid = amount_paid or 0.0
    remaining = total_amount - amount_paid
    if total_amount > 0 and remaining <= 0.0:
        return "Paid"
    if amount_paid > 0:
        return "Partial"
    return "Unpaid"

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False

_db_lock = threading.RLock()          # Used for SQLite and pool init only
_engine_type: str = "sqlite"          # 'sqlite' or 'postgres'
_sqlite_conn: Optional[sqlite3.Connection] = None
_pg_pool: Optional[Any] = None        # psycopg2.pool.ThreadedConnectionPool
_pg_conn: Optional[Any] = None        # Legacy alias — points to first pool conn for compat
_sqlite_path: Optional[Path] = None
_keepalive_started: bool = False

_POOL_MIN_CONNS = 5
_POOL_MAX_CONNS = 32
_pg_pool_semaphore: Optional[threading.BoundedSemaphore] = None


def get_sqlite_db_path() -> Path:
    """Get standard SQLite database file path in AppData or local fallback."""
    global _sqlite_path
    if _sqlite_path is not None:
        return _sqlite_path

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        data_dir = Path(local_app_data) / "JayraldinesCatering" / "data"
    else:
        data_dir = Path.home() / ".jayraldines_catering" / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        _sqlite_path = data_dir / "catering.db"
    except Exception:
        fallback = Path(__file__).resolve().parent.parent / "data"
        fallback.mkdir(parents=True, exist_ok=True)
        _sqlite_path = fallback / "catering.db"

    return _sqlite_path


def set_sqlite_db_path(custom_path: Path):
    """Override SQLite database location (useful for testing)."""
    global _sqlite_path, _sqlite_conn
    close()
    _sqlite_path = custom_path


def get_engine_type() -> str:
    """Return active database engine ('sqlite' or 'postgres')."""
    _ensure_connected()
    return _engine_type


def get_connection():
    """Return active connection handle, ensuring connection is initialized.

    NOTE: For PostgreSQL, callers should prefer using _pg_getconn()/_pg_putconn()
    directly so connections are returned to the pool. This function is kept for
    backwards-compatibility with the db_sync_server health-check only.
    """
    with _db_lock:
        if not _ensure_connected():
            return None
        if _engine_type == "postgres" and _pg_pool is not None:
            try:
                return _pg_pool.getconn()
            except Exception:
                return None
        return _sqlite_conn


def _pg_getconn(timeout: float = 5.0):
    """Borrow a connection from the PostgreSQL pool with semaphore wait (thread-safe, graceful queuing)."""
    if _pg_pool is None:
        return None
    global _pg_pool_semaphore
    if _pg_pool_semaphore is not None:
        acquired = _pg_pool_semaphore.acquire(timeout=timeout)
        if not acquired:
            log.warning(f"[Postgres] Connection pool semaphore timed out after {timeout}s.")
            return None
    try:
        return _pg_pool.getconn()
    except Exception as exc:
        if _pg_pool_semaphore is not None:
            try:
                _pg_pool_semaphore.release()
            except ValueError:
                pass
        log.error(f"[Postgres] Failed to borrow connection from pool: {exc}")
        return None


def _pg_putconn(conn) -> None:
    """Return a borrowed connection back to the pool."""
    if _pg_pool is not None and conn is not None:
        try:
            _pg_pool.putconn(conn)
        except Exception:
            pass
        finally:
            global _pg_pool_semaphore
            if _pg_pool_semaphore is not None:
                try:
                    _pg_pool_semaphore.release()
                except ValueError:
                    pass



def is_available() -> bool:
    """Return True if a database connection is active."""
    return _ensure_connected()


def _sanitize_param(val: Any) -> Any:
    """Normalize date/time objects to ISO strings for SQLite compatibility across Python versions."""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, time_type):
        return val.strftime("%H:%M:%S")
    return val


def _sanitize_params(params: tuple) -> tuple:
    if not params:
        return ()
    return tuple(_sanitize_param(p) for p in params)


def _translate_pg_to_sqlite(sql: str) -> str:
    """Translate PostgreSQL-specific syntax (typecasts, %s placeholders, ILIKE, intervals, functions) to SQLite."""
    # 1. Function table calls: SELECT ... FROM fn_profit_summary(%s) -> SELECT ... FROM v_profit_summary
    clean_sql = re.sub(r"FROM\s+fn_profit_summary\s*\([^)]*\)", "FROM v_profit_summary", sql, flags=re.IGNORECASE)

    # 2. Date intervals: e.g. CURRENT_DATE + INTERVAL '1 day' -> DATE('now', '+1 day')
    clean_sql = re.sub(r"CURRENT_DATE\s*\+\s*INTERVAL\s*'(\d+)\s*(day|days)'", r"DATE('now', '+\1 day')", clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"CURRENT_DATE\s*-\s*INTERVAL\s*'(\d+)\s*(day|days)'", r"DATE('now', '-\1 day')", clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"\+\s*INTERVAL\s*'(\d+)\s*(day|days)'", r", '+\1 day'", clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"-\s*INTERVAL\s*'(\d+)\s*(day|days)'", r", '-\1 day'", clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"\bCURRENT_DATE\b", "DATE('now')", clean_sql, flags=re.IGNORECASE)

    # 3. Date truncation: date_trunc('week', CURRENT_DATE) -> DATE('now', 'weekday 0', '-6 days')
    clean_sql = re.sub(r"date_trunc\s*\(\s*'week'\s*,\s*DATE\('now'\)\s*\)", "DATE('now', 'weekday 0', '-6 days')", clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"date_trunc\s*\(\s*'week'\s*,\s*CURRENT_DATE\s*\)", "DATE('now', 'weekday 0', '-6 days')", clean_sql, flags=re.IGNORECASE)

    # 4. Remove Postgres typecasts like ::TEXT, ::int, ::customer_status, ::FLOAT, ::DATE, ::expense_category
    clean_sql = re.sub(r"::[a-zA-Z0-9_]+", "", clean_sql)

    # 5. Replace ILIKE with LIKE
    clean_sql = re.sub(r"\bILIKE\b", "LIKE", clean_sql, flags=re.IGNORECASE)

    # 6. Replace NOW() with CURRENT_TIMESTAMP
    clean_sql = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", clean_sql, flags=re.IGNORECASE)

    # 7. Replace %s placeholders with ?
    clean_sql = clean_sql.replace("%s", "?")
    return clean_sql


def _sqlite_split_part(string: Any, delimiter: Any, part: Any) -> str:
    if string is None:
        return ""
    parts = str(string).split(str(delimiter))
    try:
        idx = int(part) - 1
        if 0 <= idx < len(parts):
            return parts[idx].strip()
    except (ValueError, TypeError):
        pass
    return ""


def connect_sqlite() -> bool:
    """Initialize and connect to embedded SQLite database in WAL mode."""
    global _sqlite_conn, _engine_type
    with _db_lock:
        try:
            db_path = get_sqlite_db_path()
            log.info(f"Connecting to SQLite Database at: {db_path}")

            _sqlite_conn = sqlite3.connect(
                str(db_path),
                timeout=15.0,
                check_same_thread=False,
                isolation_level=None  # autocommit mode managed manually
            )
            _sqlite_conn.row_factory = sqlite3.Row

            # Register PostgreSQL-compatible SQL functions in SQLite
            _sqlite_conn.create_function("SPLIT_PART", 3, _sqlite_split_part)
            _sqlite_conn.create_function("split_part", 3, _sqlite_split_part)
            _sqlite_conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            _sqlite_conn.create_function("CURRENT_DATE", 0, lambda: date.today().strftime("%Y-%m-%d"))
            _sqlite_conn.create_function("TO_CHAR", 2, lambda val, fmt: str(val))

            # Configure ultra-fast WAL mode and memory settings
            cur = _sqlite_conn.cursor()
            cur.execute("PRAGMA journal_mode = WAL;")
            cur.execute("PRAGMA synchronous = NORMAL;")
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute("PRAGMA temp_store = MEMORY;")
            cur.execute("PRAGMA cache_size = -32000;")  # 32MB cache
            cur.close()

            # Initialize schema and seed data
            init_sqlite_db(_sqlite_conn)
            try:
                _sqlite_conn.execute("""
                    CREATE TABLE IF NOT EXISTS deleted_records (
                        dr_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dr_table TEXT NOT NULL,
                        dr_ref TEXT NOT NULL UNIQUE,
                        dr_record_id INTEGER,
                        dr_deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                _sqlite_conn.commit()
            except Exception:
                pass
            _engine_type = "sqlite"
            log.info("SQLite Database initialized and ready.")
            return True
        except Exception as exc:
            log.error(f"Failed to connect to SQLite database: {exc}", exc_info=True)
            _sqlite_conn = None
            return False


_tls = threading.local()


def _init_sqlite_read_conn(conn: sqlite3.Connection) -> None:
    """Configure PostgreSQL compatibility functions on thread-local read connection."""
    conn.row_factory = sqlite3.Row
    conn.create_function("SPLIT_PART", 3, _sqlite_split_part)
    conn.create_function("split_part", 3, _sqlite_split_part)
    conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    conn.create_function("CURRENT_DATE", 0, lambda: date.today().strftime("%Y-%m-%d"))
    conn.create_function("TO_CHAR", 2, lambda val, fmt: str(val))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA query_only = ON;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        cur.close()
    except Exception:
        pass


def _get_sqlite_read_conn() -> Optional[sqlite3.Connection]:
    """Return a thread-local SQLite connection for concurrent non-blocking reads in WAL mode."""
    global _sqlite_conn
    if _sqlite_conn is None:
        return None
    # Main thread can use the primary connection
    if threading.current_thread() is threading.main_thread():
        return _sqlite_conn

    conn = getattr(_tls, "read_conn", None)
    if conn is not None:
        return conn

    db_path = get_sqlite_db_path()
    try:
        conn = sqlite3.connect(
            str(db_path),
            timeout=15.0,
            check_same_thread=False,
            isolation_level=None
        )
        _init_sqlite_read_conn(conn)
        _tls.read_conn = conn
        return conn
    except Exception as e:
        log.debug(f"[db] Thread-local SQLite read conn fallback: {e}")
        return _sqlite_conn


try:
    from utils.db_config import load_db_config, test_postgres_connection, save_db_config, get_db_config
except ImportError:
    def load_db_config(): return {}
    def test_postgres_connection(*args, **kwargs): return False, "db_config not available"
    def save_db_config(*args, **kwargs): pass
    def get_db_config(): return {}

load_config = load_db_config

_pg_schema_verified = False


def _ensure_pg_places_and_auth(conn) -> None:
    """Verifies that Cebu places dropdown and basic auth tables exist in PostgreSQL, auto-inserting if empty."""
    global _pg_schema_verified
    if _pg_schema_verified:
        return
    try:
        # 1. Ensure audit_logs table exists
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id              SERIAL PRIMARY KEY,
                        user_id         INT,
                        username        VARCHAR(100),
                        action          VARCHAR(100) NOT NULL,
                        target_type     VARCHAR(50),
                        target_id       VARCHAR(50),
                        details         TEXT,
                        ip_address      VARCHAR(50),
                        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS al_device VARCHAR(100) DEFAULT 'Desktop / Server';
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 2. Check address_cities
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='address_cities'")
                has_table = cur.fetchone() is not None
                has_rows = False
                if has_table:
                    cur.execute("SELECT count(*) FROM address_cities")
                    has_rows = (cur.fetchone()[0] or 0) > 0

                if not has_rows:
                    log.info("Auto-inserting Cebu places dropdown hierarchy into PostgreSQL...")
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS address_regions (
                            ar_id   SERIAL PRIMARY KEY,
                            ar_name VARCHAR(120) NOT NULL
                        );
                        CREATE TABLE IF NOT EXISTS address_provinces (
                            ap_id        SERIAL PRIMARY KEY,
                            ap_region_id INT NOT NULL REFERENCES address_regions(ar_id) ON DELETE CASCADE,
                            ap_name      VARCHAR(120) NOT NULL
                        );
                        CREATE TABLE IF NOT EXISTS address_cities (
                            ac_id          SERIAL PRIMARY KEY,
                            ac_province_id INT NOT NULL REFERENCES address_provinces(ap_id) ON DELETE CASCADE,
                            ac_name        VARCHAR(120) NOT NULL
                        );
                        CREATE TABLE IF NOT EXISTS address_barangays (
                            ab_id      SERIAL PRIMARY KEY,
                            ab_city_id INT NOT NULL REFERENCES address_cities(ac_id) ON DELETE CASCADE,
                            ab_name    VARCHAR(120) NOT NULL
                        );
                        CREATE INDEX IF NOT EXISTS idx_address_barangays_name ON address_barangays (LOWER(ab_name));
                        CREATE INDEX IF NOT EXISTS idx_address_cities_name    ON address_cities    (LOWER(ac_name));

                        CREATE TABLE IF NOT EXISTS addresses (
                            addr_id          SERIAL PRIMARY KEY,
                            addr_street      VARCHAR(255)    NOT NULL,
                            addr_barangay_id INT REFERENCES address_barangays(ab_id),
                            addr_city_id     INT REFERENCES address_cities(ac_id),
                            addr_province_id INT REFERENCES address_provinces(ap_id),
                            addr_zip_code    VARCHAR(10),
                            addr_created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );

                        INSERT INTO address_regions (ar_name) VALUES ('Region VII - Central Visayas')
                            ON CONFLICT DO NOTHING;

                        INSERT INTO address_provinces (ap_region_id, ap_name)
                        SELECT r.ar_id, 'Cebu'
                        FROM address_regions r WHERE r.ar_name = 'Region VII - Central Visayas'
                        ON CONFLICT DO NOTHING;
                    """)
                    cur.execute("SELECT ap_id FROM address_provinces WHERE ap_name = 'Cebu' LIMIT 1")
                    prov_res = cur.fetchone()
                    if prov_res:
                        prov_id = prov_res[0]
                        cebu_cities_data = [
                            ("Cebu City", ["Apas", "Banilad", "Basak San Nicolas", "Busay", "Camputhaw", "Capitol Site", "Guadalupe", "Kasambagan", "Lahug", "Mabolo", "Pardo", "Punta Princesa", "Sambag I", "Sambag II", "Talamban", "Tisa", "Zapatera"]),
                            ("Mandaue City", ["Alang-alang", "Bakilid", "Banilad", "Cabancalan", "Centro", "Guizo", "Ibabao-Estancia", "Maguikay", "Paknaan", "Subangdaku", "Tipolo"]),
                            ("Lapu-Lapu City", ["Basak", "Gun-ob", "Ibo", "Mactan", "Maribago", "Marigondon", "Pajac", "Pajo", "Poblacion", "Pusok", "Subabasbas"]),
                            ("Talisay City", ["Bulacao", "Cansojong", "Dumlog", "Lawaan I", "Lawaan II", "Mohon", "Poblacion", "San Roque", "Tabunok", "Tangke"]),
                            ("Consolacion", ["Casili", "Cansaga", "Danlag", "Jugan", "Nangka", "Pitogo", "Poblacion", "Tayud"]),
                            ("Liloan", ["Catarman", "Cotcot", "Jubay", "Poblacion", "San Roque", "San Vicente", "Yati"]),
                            ("Minglanilla", ["Cadulawan", "Calajo-an", "Camp 7", "Camp 8", "Cuanos", "Guindaruhan", "Linao", "Manduang", "Pakigne", "Poblacion Ward 1", "Poblacion Ward 2", "Tubod", "Tulay", "Tungkop", "Tungkil", "Vito", "Ward I", "Ward II", "Ward III", "Ward IV"]),
                            ("Carcar City", ["Bolinawan", "Buenavista", "Calidngan", "Can-asujan", "Guadalupe", "Liburon", "Napu", "Ocana", "Perrelos", "Poblacion I", "Poblacion II", "Poblacion III", "Tuyom", "Valencia", "Valladolid"]),
                            ("Danao City", ["Baliang", "Bayabas", "Binaliw", "Cabungahan", "Cahumayan", "Cambanay", "Cambubho", "Cogon-Cruz", "Danasan", "Dungga", "Guinsay", "Ibo", "Lawaan", "Licos", "Looc", "Magtagobtob", "Malapoc", "Manlayag", "Mantija", "Maslog", "Nangka", "Oguis", "Pili", "Poblacion", "Quisol", "Sabang", "Sacsac", "Sandayong Norte", "Sandayong Sur", "Santa Rosa", "Santican", "Sibacan", "Suba", "Taboc", "Taytay", "Togonon", "Tuburan Sur"]),
                            ("Naga City", ["Alfaco", "Bairan", "Balirong", "Cabungahan", "Cantao-an", "Central Poblacion", "Cogon", "Colon", "Inayagan", "Inoburan", "Kinasang-an", "Lutac", "Mainit", "Mayana", "Naalad", "North Poblacion", "Pangdan", "Patag", "South Poblacion", "Tagjaguimit", "Tangke", "Tinaan", "Tuyan", "Uling"]),
                            ("Toledo City", ["Awihao", "Bagakay", "Bato", "Biga", "Bulongan", "Bunga", "Cabitoonan", "Calongcalong", "Cambang-ug", "Camp 8", "Canlumampao", "Cantabaco", "Capitan Claudio", "Carmen", "Daanglungsod", "Don Andres Soriano", "Dumlog", "Gen. Climaco", "Ibo", "Ilihan", "Landahan", "Loay", "Luray II", "Matab-ang", "Media Once", "Pangamihan", "Poog", "Poblacion", "Putingbato", "Sagay", "Sam-ang", "Sangi", "Santo Nino", "Subayon", "Talavera", "Tubod", "Tungkay"]),
                        ]
                        for c_name, brgys in cebu_cities_data:
                            cur.execute("INSERT INTO address_cities (ac_province_id, ac_name) VALUES (%s, %s) RETURNING ac_id", (prov_id, c_name))
                            c_id = cur.fetchone()[0]
                            for b_name in brgys:
                                cur.execute("INSERT INTO address_barangays (ab_city_id, ab_name) VALUES (%s, %s)", (c_id, b_name))
            conn.commit()
        except Exception:
            conn.rollback()

        # 3. Ensure bookings table has all expected columns
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_down_payment NUMERIC(12, 2) DEFAULT 0.00;
                    ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_down_payment_status VARCHAR(50) DEFAULT 'PENDING';
                    ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_base_total NUMERIC(12, 2) DEFAULT 0.00;
                    ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_color_theme VARCHAR(100) DEFAULT '#2563EB';
                    ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_notes TEXT DEFAULT '';
                    ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_cancellation_reason TEXT DEFAULT '';
                    ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_event_end_time TIME NULL;
                    ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS mi_image TEXT DEFAULT '';
                    ALTER TABLE packages ADD COLUMN IF NOT EXISTS pkg_image TEXT DEFAULT '';
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS cus_notes TEXT DEFAULT '';
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 4. Ensure occasions table & occ_is_active column
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS occasions (
                        occ_id SERIAL PRIMARY KEY,
                        occ_name VARCHAR(100) NOT NULL UNIQUE,
                        occ_is_active INT DEFAULT 1
                    );
                    ALTER TABLE occasions ADD COLUMN IF NOT EXISTS occ_is_active INT DEFAULT 1;
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 5. Ensure monthly_sales_targets table
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS monthly_sales_targets (
                        mst_year INT NOT NULL,
                        mst_month INT NOT NULL,
                        mst_target_amount NUMERIC(12, 2) DEFAULT 85000.0,
                        mst_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (mst_year, mst_month)
                    );
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 6. Ensure cash_flow_transactions table
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cash_flow_transactions (
                        cft_id SERIAL PRIMARY KEY,
                        cft_date DATE NOT NULL,
                        cft_check_no VARCHAR(100) DEFAULT '',
                        cft_particulars VARCHAR(255) NOT NULL,
                        cft_deposit NUMERIC(12, 2) DEFAULT 0.0,
                        cft_withdrawal NUMERIC(12, 2) DEFAULT 0.0,
                        cft_balance NUMERIC(12, 2) DEFAULT 0.0,
                        cft_actual_sales NUMERIC(12, 2) DEFAULT 0.0,
                        cft_notes TEXT DEFAULT '',
                        cft_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 7. Ensure expenses table & columns
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS expenses (
                        exp_id SERIAL PRIMARY KEY,
                        exp_category VARCHAR(100) NOT NULL,
                        exp_description VARCHAR(255) NOT NULL,
                        exp_amount NUMERIC(12, 2) NOT NULL,
                        exp_date DATE NOT NULL,
                        exp_expense_date DATE,
                        exp_notes TEXT DEFAULT '',
                        exp_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    ALTER TABLE expenses ADD COLUMN IF NOT EXISTS exp_date DATE;
                    ALTER TABLE expenses ADD COLUMN IF NOT EXISTS exp_expense_date DATE;
                    ALTER TABLE expenses ADD COLUMN IF NOT EXISTS exp_notes TEXT DEFAULT '';
                    UPDATE expenses SET exp_date = exp_expense_date WHERE exp_date IS NULL AND exp_expense_date IS NOT NULL;
                    UPDATE expenses SET exp_expense_date = exp_date WHERE exp_expense_date IS NULL AND exp_date IS NOT NULL;
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 8. Ensure booking_additional_charges table
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS booking_additional_charges (
                        ac_id SERIAL PRIMARY KEY,
                        ac_booking_id INT NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
                        ac_description TEXT NOT NULL,
                        ac_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                        ac_date_added DATE NOT NULL DEFAULT CURRENT_DATE,
                        ac_added_by TEXT DEFAULT '',
                        ac_created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 9. Ensure device_sessions table for monitoring connected client devices
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS device_sessions (
                        device_id VARCHAR(64) PRIMARY KEY,
                        hostname VARCHAR(128) NOT NULL,
                        ip_address VARCHAR(45),
                        os_info VARCHAR(128),
                        app_version VARCHAR(32),
                        username VARCHAR(64),
                        user_role VARCHAR(32),
                        active_module VARCHAR(64) DEFAULT 'Dashboard',
                        status VARCHAR(20) DEFAULT 'online',
                        first_connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_device_sessions_status ON device_sessions(status);
                    CREATE INDEX IF NOT EXISTS idx_device_sessions_heartbeat ON device_sessions(last_heartbeat);
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 10. Ensure invoices & payment_records columns
        for stmt in [
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS inv_balance NUMERIC(12, 2) DEFAULT 0.00;",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS inv_down_payment NUMERIC(12, 2) DEFAULT 0.00;",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS inv_payment_verified INT DEFAULT 0;",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS inv_invoice_number VARCHAR(50);",
            "ALTER TABLE payment_records ADD COLUMN IF NOT EXISTS pr_is_downpayment INT DEFAULT 0;",
            "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_down_payment NUMERIC(12, 2) DEFAULT 0.00;",
            "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_color_theme VARCHAR(50) DEFAULT '#2563EB';",
            "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_event_end_time TIME;",
            "ALTER TABLE package_items ADD COLUMN IF NOT EXISTS pi_item_name VARCHAR(255) DEFAULT '';",
            "ALTER TABLE package_items ADD COLUMN IF NOT EXISTS pi_category VARCHAR(100) DEFAULT '';",
            "ALTER TABLE package_items ADD COLUMN IF NOT EXISTS pi_quantity INT DEFAULT 1;",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS cus_total_spent NUMERIC(12, 2) DEFAULT 0.00;",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS exp_date DATE;",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS exp_expense_date DATE;",
            "ALTER TABLE packages DROP CONSTRAINT IF EXISTS packages_pkg_price_per_pax_check;",
            "ALTER TABLE packages ADD CONSTRAINT packages_pkg_price_per_pax_check CHECK (pkg_price_per_pax >= 0);"
        ]:
            try:
                with conn.cursor() as cur:
                    cur.execute(stmt)
                conn.commit()
            except Exception:
                conn.rollback()

        # Ensure invoice_status enum values
        try:
            old_iso = conn.isolation_level
            conn.set_isolation_level(0)
            with conn.cursor() as cur_enum:
                cur_enum.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'CANCELLED';")
                cur_enum.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'Cancelled';")
            conn.set_isolation_level(old_iso)
        except Exception as e_enum:
            log.warning(f"Could not add CANCELLED to invoice_status enum: {e_enum}")

        # 11. Ensure helper tables
        for create_stmt in [
            """CREATE TABLE IF NOT EXISTS customer_loyalty_tiers (
                cl_id SERIAL PRIMARY KEY,
                cl_customer_id INT NOT NULL REFERENCES customers(cus_id) ON DELETE CASCADE,
                cl_tier VARCHAR(50) DEFAULT 'Bronze',
                cl_points INT DEFAULT 0,
                cl_last_recalculated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS inventory (
                inv_id SERIAL PRIMARY KEY,
                inv_ingredient VARCHAR(150) NOT NULL,
                inv_category VARCHAR(100) DEFAULT '',
                inv_stock NUMERIC(12, 2) DEFAULT 0.0,
                inv_unit VARCHAR(50) DEFAULT 'kg',
                inv_cost_per_unit NUMERIC(12, 2) DEFAULT 0.0,
                inv_min_stock NUMERIC(12, 2) DEFAULT 5.0,
                inv_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS customer_addresses (
                ca_id SERIAL PRIMARY KEY,
                ca_customer_id INT NOT NULL,
                ca_address_id INT NOT NULL
            );"""
        ]:
            try:
                with conn.cursor() as cur:
                    cur.execute(create_stmt)
                conn.commit()
            except Exception:
                conn.rollback()

        # 12. PostgreSQL strftime compatibility functions
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE OR REPLACE FUNCTION strftime(format text, d date) RETURNS text AS $$
                    BEGIN
                        IF format = '%Y' THEN RETURN TO_CHAR(d, 'YYYY');
                        ELSIF format = '%m' THEN RETURN TO_CHAR(d, 'MM');
                        ELSIF format = '%d' THEN RETURN TO_CHAR(d, 'DD');
                        ELSE RETURN TO_CHAR(d, 'YYYY-MM-DD');
                        END IF;
                    END;
                    $$ LANGUAGE plpgsql IMMUTABLE;

                    CREATE OR REPLACE FUNCTION strftime(format text, ts timestamp) RETURNS text AS $$
                    BEGIN
                        IF format = '%Y' THEN RETURN TO_CHAR(ts, 'YYYY');
                        ELSIF format = '%m' THEN RETURN TO_CHAR(ts, 'MM');
                        ELSIF format = '%d' THEN RETURN TO_CHAR(ts, 'DD');
                        ELSE RETURN TO_CHAR(ts, 'YYYY-MM-DD');
                        END IF;
                    END;
                    $$ LANGUAGE plpgsql IMMUTABLE;

                    CREATE OR REPLACE FUNCTION strftime(format text, ts timestamptz) RETURNS text AS $$
                    BEGIN
                        IF format = '%Y' THEN RETURN TO_CHAR(ts, 'YYYY');
                        ELSIF format = '%m' THEN RETURN TO_CHAR(ts, 'MM');
                        ELSIF format = '%d' THEN RETURN TO_CHAR(ts, 'DD');
                        ELSE RETURN TO_CHAR(ts, 'YYYY-MM-DD');
                        END IF;
                    END;
                    $$ LANGUAGE plpgsql IMMUTABLE;
                """)
            conn.commit()
        except Exception:
            conn.rollback()

        # 13. Ensure unified v_customer_ledger timeline view & enhanced sp_create_booking
        try:
            with conn.cursor() as cur:
                cur.execute("DROP VIEW IF EXISTS v_customer_ledger CASCADE;")
                cur.execute("""
                    CREATE OR REPLACE VIEW v_customer_ledger AS
                    SELECT
                        c.cus_id AS customer_id, c.cus_name AS customer_name,
                        'Booking' AS entry_type,
                        b.bk_created_at::DATE AS recorded_date,
                        b.bk_event_date AS event_date, b.bk_booking_ref AS reference,
                        COALESCE(b.bk_occasion, 'Event') AS description,
                        0.00 AS debit, 0.00 AS credit,
                        b.bk_status::TEXT AS entry_status, b.bk_id AS source_id
                    FROM customers c
                    JOIN bookings b ON b.bk_customer_id = c.cus_id

                    UNION ALL

                    SELECT
                        c.cus_id, c.cus_name, 'Invoice',
                        i.inv_created_at::DATE, i.inv_event_date, i.inv_invoice_ref,
                        'Invoice issued', i.inv_total_amount, 0.00,
                        i.inv_status::TEXT, i.inv_id
                    FROM customers c
                    JOIN bookings b ON b.bk_customer_id = c.cus_id
                    JOIN invoices i ON i.inv_booking_id = b.bk_id

                    UNION ALL

                    SELECT
                        c.cus_id, c.cus_name, 'Payment',
                        COALESCE(pr.pr_payment_date, i.inv_created_at::DATE), i.inv_event_date,
                        CONCAT('PMT-', pr.pr_id::TEXT),
                        COALESCE(NULLIF(pr.pr_note, ''), NULLIF(pr.pr_method, ''), 'Payment received'),
                        0.00, pr.pr_amount, 'Paid', pr.pr_id
                    FROM customers c
                    JOIN bookings b ON b.bk_customer_id = c.cus_id
                    JOIN invoices i ON i.inv_booking_id = b.bk_id
                    JOIN payment_records pr ON pr.pr_invoice_id = i.inv_id

                    ORDER BY recorded_date DESC, entry_type;
                """)
            conn.commit()
        except Exception as e_v:
            log.warning(f"[db.py] v_customer_ledger view update note: {e_v}")
            conn.rollback()

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE OR REPLACE PROCEDURE sp_create_booking(
                        IN  p_customer_name  TEXT,
                        IN  p_contact        TEXT,
                        IN  p_email          TEXT,
                        IN  p_address        TEXT,
                        IN  p_occasion       TEXT,
                        IN  p_venue          TEXT,
                        IN  p_event_date     DATE,
                        IN  p_event_time     TIME,
                        IN  p_pax            INT,
                        IN  p_special_notes  TEXT,
                        IN  p_menu_type      TEXT,
                        IN  p_package_id     INT,
                        IN  p_custom_items   TEXT,
                        IN  p_total_amount   NUMERIC,
                        IN  p_payment_mode   TEXT,
                        IN  p_amount_paid    NUMERIC,
                        OUT p_booking_id     INT,
                        OUT p_booking_ref    TEXT
                    )
                    LANGUAGE plpgsql AS $$
                    DECLARE
                        v_cid INT;
                        v_inv_id INT;
                        v_inv_ref TEXT;
                        v_inv_st invoice_status;
                        v_bal NUMERIC;
                        v_paid NUMERIC;
                    BEGIN
                        CALL sp_next_booking_ref(p_booking_ref);

                        SELECT cus_id INTO v_cid FROM customers WHERE LOWER(cus_name) = LOWER(p_customer_name) LIMIT 1;
                        IF v_cid IS NULL AND p_customer_name IS NOT NULL AND TRIM(p_customer_name) <> '' THEN
                            INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_loyalty_tier, cus_status, cus_total_events, cus_total_spent)
                            VALUES (TRIM(p_customer_name), COALESCE(p_contact, ''), COALESCE(p_email, ''), COALESCE(p_address, ''), 'Bronze', 'Active', 0, 0.00)
                            RETURNING cus_id INTO v_cid;
                        END IF;

                        v_paid := COALESCE(p_amount_paid, 0.00);

                        INSERT INTO bookings (
                            bk_booking_ref, bk_customer_id, bk_customer_name, bk_contact, bk_email, bk_address,
                            bk_occasion, bk_venue, bk_event_date, bk_event_time, bk_pax, bk_special_notes,
                            bk_menu_type, bk_package_id, bk_custom_items,
                            bk_total_amount, bk_base_total, bk_payment_mode, bk_amount_paid, bk_down_payment,
                            bk_down_payment_status, bk_status
                        ) VALUES (
                            p_booking_ref, v_cid, p_customer_name, p_contact, p_email, p_address,
                            p_occasion, p_venue, p_event_date, p_event_time, p_pax, p_special_notes,
                            p_menu_type, p_package_id, p_custom_items,
                            p_total_amount, p_total_amount, p_payment_mode::payment_method, v_paid, v_paid,
                            CASE WHEN v_paid > 0 THEN 'ACCEPTED' ELSE 'PENDING' END, 'PENDING'
                        )
                        RETURNING bk_id INTO p_booking_id;

                        -- Auto generate linked invoice
                        CALL sp_auto_create_invoice(p_booking_id, v_inv_id, v_inv_ref);

                        v_bal := GREATEST(0.00, p_total_amount - v_paid);
                        IF v_paid >= p_total_amount AND p_total_amount > 0 THEN
                            v_inv_st := 'Paid'::invoice_status;
                        ELSIF v_paid > 0 THEN
                            v_inv_st := 'Partial'::invoice_status;
                        ELSE
                            v_inv_st := 'Unpaid'::invoice_status;
                        END IF;

                        UPDATE invoices
                        SET inv_total_amount = p_total_amount,
                            inv_amount_paid = v_paid,
                            inv_balance = v_bal,
                            inv_down_payment = v_paid,
                            inv_status = v_inv_st,
                            inv_payment_verified = CASE WHEN v_paid > 0 THEN 1 ELSE 0 END
                        WHERE inv_id = v_inv_id;

                        -- Record payment entry if paid
                        IF v_paid > 0 THEN
                            INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_method, pr_note, pr_is_downpayment)
                            VALUES (v_inv_id, v_paid, p_event_date, p_payment_mode, 'Initial payment on booking', 1);
                        END IF;

                        IF v_cid IS NOT NULL THEN
                            UPDATE customers
                            SET cus_total_events = cus_total_events + 1,
                                cus_total_spent = cus_total_spent + p_total_amount,
                                cus_updated_at = NOW()
                            WHERE cus_id = v_cid;
                            CALL sp_recalculate_loyalty(v_cid);
                        END IF;
                    END;
                    $$;
                """)
            conn.commit()
        except Exception as e_sp:
            log.warning(f"[db.py] sp_create_booking procedure update note: {e_sp}")
            conn.rollback()

        # 14. Ensure default packages and menu items if empty
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM packages;")
                if cur.fetchone()[0] == 0:
                    for name, desc, price, min_pax in [
                        ('Classic Celebration Package', 'Standard catering buffet package with 4 main dishes, rice, dessert, and drinks.', 350.0, 30),
                        ('Premium Grand Feast', 'Deluxe buffet with 6 main dishes, roast pork lechon belly, 2 desserts, and beverage bar.', 550.0, 50),
                        ('Executive VIP Buffet', 'Top-tier package with live carving station, 7 signature mains, seafood, and full dessert table.', 850.0, 50),
                    ]:
                        cur.execute("""
                            INSERT INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (pkg_name) DO NOTHING;
                        """, (name, desc, price, min_pax))

                cur.execute("SELECT COUNT(*) FROM menu_items;")
                if cur.fetchone()[0] == 0:
                    for name, cat, price, status, desc in [
                        ('Special Pork Humba', 'Main Course', 450.0, 'Available', 'Slow cooked pork belly with banana blossoms'),
                        ('Lechon Belly Roast', 'Main Course', 1200.0, 'Available', 'Crispy rolled pork belly with herbs'),
                        ('Chicken Pandan', 'Main Course', 380.0, 'Available', 'Wrapped savory fried chicken'),
                        ('Garlic Butter Buttered Shrimp', 'Main Course', 550.0, 'Available', 'Fresh prawns in savory garlic butter'),
                        ('Sweet & Sour Fish Fillet', 'Main Course', 360.0, 'Available', 'Crispy fish fillet in pineapple sweet sauce'),
                        ('Beef with Broccoli', 'Main Course', 480.0, 'Available', 'Tender beef slices in oyster glaze'),
                        ('Biko with Latik', 'Dessert', 250.0, 'Available', 'Traditional sweet sticky rice'),
                        ('Mango Tapioca', 'Dessert', 220.0, 'Available', 'Chilled mango cubes with sago pearls'),
                        ('Refillable Iced Tea', 'Drinks', 150.0, 'Available', 'House blend lemon iced tea'),
                    ]:
                        cur.execute("""
                            INSERT INTO menu_items (mi_name, mi_category, mi_price, mi_status, mi_description)
                            VALUES (%s, %s::menu_category, %s, %s::menu_status, %s)
                            ON CONFLICT (mi_name) DO NOTHING;
                        """, (name, cat, price, status, desc))

                cur.execute("SELECT COUNT(*) FROM package_items;")
                if cur.fetchone()[0] == 0:
                    cur.execute("""
                        INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_item_name, pi_category, pi_quantity)
                        SELECT p.pkg_id, m.mi_id, m.mi_name, m.mi_category::TEXT, 1
                        FROM packages p CROSS JOIN menu_items m
                        ON CONFLICT DO NOTHING;
                    """)
            conn.commit()
        except Exception as e_seed:
            log.warning(f"[db.py] Package / menu item auto-seed note: {e_seed}")
            conn.rollback()

        # 14b. Admin-controlled menu category display order (drag-and-drop in
        # Settings > Menu Categories). Backfill existing rows with their current
        # mc_id order so nothing shuffles until an admin actually reorders them.
        try:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE menu_categories ADD COLUMN IF NOT EXISTS mc_sort INT DEFAULT 0;")
                cur.execute("""
                    UPDATE menu_categories SET mc_sort = sub.rn
                    FROM (SELECT mc_id, ROW_NUMBER() OVER (ORDER BY mc_id) AS rn FROM menu_categories) sub
                    WHERE menu_categories.mc_id = sub.mc_id AND menu_categories.mc_sort = 0;
                """)
            conn.commit()
        except Exception as e_mcsort:
            log.warning(f"[db.py] menu_categories.mc_sort migration note: {e_mcsort}")
            conn.rollback()

        # 15. Package selection buckets (dish/dessert quotas) + one-time backfill
        # ------------------------------------------------------------------
        # A bucket = a named selection limit on a package (e.g. "Dishes" max 4,
        # "Dessert" max 1) scoped to a set of menu categories. This is purely
        # additive: a package with no buckets keeps the old unlimited behavior,
        # so existing data and orders are unaffected.
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS package_buckets (
                        pb_id         SERIAL PRIMARY KEY,
                        pb_package_id INT NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
                        pb_name       VARCHAR(100) NOT NULL,
                        pb_limit      INT NOT NULL DEFAULT 1,
                        pb_categories TEXT NOT NULL DEFAULT '[]',
                        pb_sort       INT DEFAULT 0
                    );
                    CREATE INDEX IF NOT EXISTS idx_package_buckets_pkg ON package_buckets(pb_package_id);
                    ALTER TABLE package_items ADD COLUMN IF NOT EXISTS pi_bucket_id INT;
                """)
            conn.commit()
        except Exception as e_pb:
            log.warning(f"[db.py] package_buckets schema note: {e_pb}")
            conn.rollback()

        # One-time auto-backfill so the client never re-enters package data.
        # For every package that has NO buckets yet, we derive buckets from the
        # dishes it already has: categories that look like desserts become a
        # "Dessert" bucket, everything else a "Dishes" bucket, each with its
        # limit defaulted to the current default-dish count. Guarded per bucket
        # name so re-running on later startups is a no-op (idempotent). If this
        # fails for any reason, packages simply stay unlimited (safe fallback).
        try:
            with conn.cursor() as cur:
                # -- Dishes buckets --------------------------------------------
                cur.execute("""
                    INSERT INTO package_buckets (pb_package_id, pb_name, pb_limit, pb_categories, pb_sort)
                    SELECT q.pkg_id, 'Dishes', COUNT(*), COALESCE(to_jsonb(array_agg(DISTINCT q.cat))::text, '[]'), 0
                    FROM (
                        SELECT pi.pi_package_id AS pkg_id,
                               COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category::text, 'General') AS cat,
                               (COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category::text, '') ILIKE '%dessert%'
                                OR COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category::text, '') ILIKE '%sweet%'
                                OR COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category::text, '') ILIKE '%panghimagas%') AS is_dessert
                        FROM package_items pi
                        LEFT JOIN menu_items mi ON mi.mi_id = pi.pi_menu_item_id
                    ) q
                    WHERE q.is_dessert = FALSE
                      AND NOT EXISTS (SELECT 1 FROM package_buckets b
                                      WHERE b.pb_package_id = q.pkg_id AND b.pb_name = 'Dishes')
                    GROUP BY q.pkg_id;
                """)
                # -- Dessert buckets -------------------------------------------
                cur.execute("""
                    INSERT INTO package_buckets (pb_package_id, pb_name, pb_limit, pb_categories, pb_sort)
                    SELECT q.pkg_id, 'Dessert', COUNT(*), COALESCE(to_jsonb(array_agg(DISTINCT q.cat))::text, '[]'), 1
                    FROM (
                        SELECT pi.pi_package_id AS pkg_id,
                               COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category::text, 'General') AS cat,
                               (COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category::text, '') ILIKE '%dessert%'
                                OR COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category::text, '') ILIKE '%sweet%'
                                OR COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category::text, '') ILIKE '%panghimagas%') AS is_dessert
                        FROM package_items pi
                        LEFT JOIN menu_items mi ON mi.mi_id = pi.pi_menu_item_id
                    ) q
                    WHERE q.is_dessert = TRUE
                      AND NOT EXISTS (SELECT 1 FROM package_buckets b
                                      WHERE b.pb_package_id = q.pkg_id AND b.pb_name = 'Dessert')
                    GROUP BY q.pkg_id;
                """)
                # -- Tag each default dish with the bucket it belongs to -------
                cur.execute("""
                    UPDATE package_items pi
                    SET pi_bucket_id = (SELECT b.pb_id FROM package_buckets b
                                        WHERE b.pb_package_id = pi.pi_package_id AND b.pb_name = 'Dessert')
                    WHERE pi.pi_bucket_id IS NULL
                      AND EXISTS (SELECT 1 FROM package_buckets b
                                  WHERE b.pb_package_id = pi.pi_package_id AND b.pb_name = 'Dessert')
                      AND (COALESCE(NULLIF(pi.pi_category, ''),
                                    (SELECT mi.mi_category::text FROM menu_items mi WHERE mi.mi_id = pi.pi_menu_item_id),
                                    '') ILIKE '%dessert%'
                           OR COALESCE(NULLIF(pi.pi_category, ''),
                                    (SELECT mi.mi_category::text FROM menu_items mi WHERE mi.mi_id = pi.pi_menu_item_id),
                                    '') ILIKE '%sweet%'
                           OR COALESCE(NULLIF(pi.pi_category, ''),
                                    (SELECT mi.mi_category::text FROM menu_items mi WHERE mi.mi_id = pi.pi_menu_item_id),
                                    '') ILIKE '%panghimagas%');
                """)
                cur.execute("""
                    UPDATE package_items pi
                    SET pi_bucket_id = (SELECT b.pb_id FROM package_buckets b
                                        WHERE b.pb_package_id = pi.pi_package_id AND b.pb_name = 'Dishes')
                    WHERE pi.pi_bucket_id IS NULL
                      AND EXISTS (SELECT 1 FROM package_buckets b
                                  WHERE b.pb_package_id = pi.pi_package_id AND b.pb_name = 'Dishes');
                """)
            conn.commit()
        except Exception as e_bf:
            log.warning(f"[db.py] package_buckets backfill note: {e_bf}")
            conn.rollback()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        log.warning(f"Note verifying PostgreSQL places/auth/schema: {exc}")
    finally:
        _pg_schema_verified = True


def connect_postgres(force: bool = False) -> bool:
    """Connect to PostgreSQL using a ThreadedConnectionPool."""
    global _pg_pool, _pg_conn, _engine_type, _keepalive_started, _pg_pool_semaphore
    if not _PSYCOPG2_AVAILABLE:
        return False

    with _db_lock:
        if not force and _engine_type == "postgres" and _pg_pool is not None:
            return True

        load_db_config()

        import getpass
        env_user = os.environ.get("DB_USER")
        user = env_user if env_user else getpass.getuser()
        cfg = {
            "host":            os.environ.get("DB_HOST", "localhost"),
            "port":            int(os.environ.get("DB_PORT", "5432")),
            "dbname":          os.environ.get("DB_NAME", "jayraldines_catering"),
            "user":            user,
            "password":        os.environ.get("DB_PASSWORD", "12345678"),
            "connect_timeout": 4,
        }

        try:
            # Close any existing pool cleanly
            if _pg_pool is not None:
                try:
                    _pg_pool.closeall()
                except Exception:
                    pass
                _pg_pool = None

            _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=_POOL_MIN_CONNS,
                maxconn=_POOL_MAX_CONNS,
                **cfg
            )
            _pg_pool_semaphore = threading.BoundedSemaphore(_POOL_MAX_CONNS)
            # Verify pool works and run schema bootstrap on one connection
            _boot_conn = _pg_pool.getconn()
            try:
                _boot_conn.autocommit = False
                _ensure_pg_places_and_auth(_boot_conn)
            finally:
                _pg_pool.putconn(_boot_conn)

            _engine_type = "postgres"
            log.info(f"Connected to PostgreSQL via ThreadedConnectionPool ({_POOL_MIN_CONNS}–{_POOL_MAX_CONNS} connections).")

            # Start keepalive daemon (only once per process)
            if not _keepalive_started:
                _keepalive_started = True
                _start_pg_keepalive()

            return True
        except Exception as exc:
            log.warning(f"PostgreSQL connection pool failed: {exc}. Using SQLite embedded database.")
            _pg_pool = None
            return False


def _start_pg_keepalive() -> None:
    """Daemon thread that pings the pool every 45 s to prevent idle-timeout disconnects."""
    def _keepalive_worker():
        while True:
            try:
                threading.Event().wait(45)
            except Exception:
                pass
            if _pg_pool is None or _engine_type != "postgres":
                return
            conn = None
            try:
                conn = _pg_getconn(timeout=2.0)
                if conn is not None:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                    conn.commit()
            except Exception:
                pass
            finally:
                if conn is not None:
                    _pg_putconn(conn)

    t = threading.Thread(target=_keepalive_worker, daemon=True, name="PGKeepalive")
    t.start()


def connect(force: bool = False) -> bool:
    """Connect to preferred database (checks db_config.json and DB_ENGINE)."""
    with _db_lock:
        if not force:
            if _engine_type == "postgres" and _pg_pool is not None:
                return True
            if _engine_type == "sqlite" and _sqlite_conn is not None:
                return True
        load_db_config()
        pref = os.environ.get("DB_ENGINE", "sqlite").lower().strip()
        if pref == "postgres" and _PSYCOPG2_AVAILABLE:
            if connect_postgres(force=force):
                return True
        return connect_sqlite()


def _ensure_connected() -> bool:
    global _engine_type, _sqlite_conn, _pg_pool
    if _engine_type == "sqlite" and _sqlite_conn is not None:
        return True
    elif _engine_type == "postgres" and _pg_pool is not None:
        return True
    with _db_lock:
        if _engine_type == "sqlite" and _sqlite_conn is not None:
            return True
        elif _engine_type == "postgres" and _pg_pool is not None:
            return True
        return connect()


@contextlib.contextmanager
def transaction():
    with _db_lock:
        if not _ensure_connected():
            raise RuntimeError("No database connection")
        if _engine_type == "sqlite":
            try:
                _sqlite_conn.execute("BEGIN;")
                yield
                _sqlite_conn.execute("COMMIT;")
            except Exception:
                try:
                    _sqlite_conn.execute("ROLLBACK;")
                except Exception:
                    pass
                raise
        else:
            try:
                yield
                _pg_conn.commit()
            except Exception:
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass
                raise


def _prepare_pg_sql(sql: str, params: Any = ()) -> str:
    """Ensure raw PostgreSQL queries don't break when parameters are passed alongside literal % characters."""
    if not params or "%" not in sql:
        return sql
    # Don't escape %s, %d, %f, or %(name)s placeholders or %%
    return re.sub(r"%(?!s|d|f|\([a-zA-Z0-9_]+\)s|%)", "%%", sql)


def _bump_server_version_if_applicable(sql: str = "") -> None:
    """After a successful LOCAL write, tell the LAN sync hub's version
    counter to advance - but only on the machine actually running the
    server (or a standalone install).
    Filters out background heartbeat/session/log tables so routine status
    checks never trigger artificial version bumps or UI reload loops.
    """
    if sql:
        s = sql.lower()
        if any(ignored in s for ignored in ("device_sessions", "audit_logs", "login_attempts", "user_sessions", "app_logs", "deleted_records")):
            return
    try:
        from utils.client_sync import is_client_mode
        if is_client_mode():
            return
        from utils import db_sync_server
        db_sync_server.bump_db_version()
    except Exception:
        pass


def execute(sql: str, params: tuple = ()) -> None:
    # ── Client Workstation Write-Through Proxy ──
    # When this machine is a client, send the write to the server first,
    # then also apply locally so the UI stays responsive.
    proxied_ok = False
    try:
        from utils.client_sync import is_client_mode, proxy_write, get_server_url
        if is_client_mode():
            sql_upper = sql.strip().upper()
            is_write = any(sql_upper.startswith(k) for k in ("INSERT", "UPDATE", "DELETE", "REPLACE"))
            # Skip schema/pragma statements — those only run locally
            if is_write:
                proxied_ok = proxy_write(sql, params, server_url=get_server_url())
    except Exception as _proxy_err:
        log.debug(f"[db.execute] Client proxy error (non-fatal): {_proxy_err}")

    if not _ensure_connected():
        # The write already reached the server (source of truth for clients) —
        # don't hard-fail just because this workstation has no local cache
        # connection yet (e.g. right after a fresh client install/login).
        if proxied_ok:
            return
        raise RuntimeError("No database connection")
    if _engine_type == "sqlite":
        with _db_lock:
            try:
                clean_sql = _translate_pg_to_sqlite(sql)
                sanitized_params = _sanitize_params(params)
                cur = _sqlite_conn.cursor()
                cur.execute(clean_sql, sanitized_params)
                _sqlite_conn.commit()
                cur.close()
            except Exception as exc:
                log.error(f"[SQLite] execute failed on SQL: {sql[:100]} | Error: {exc}")
                raise
    else:
        conn = _pg_getconn()
        if conn is None:
            raise RuntimeError("No PostgreSQL connection available from pool")
        try:
            pg_sql = _prepare_pg_sql(sql, params)
            with conn.cursor() as cur:
                if params:
                    cur.execute(pg_sql, params)
                else:
                    cur.execute(pg_sql)
            conn.commit()
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            log.error(f"[Postgres] execute failed on SQL: {sql[:160]} | Error: {exc}")
            raise
        finally:
            _pg_putconn(conn)

    if sql.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE")):
        _bump_server_version_if_applicable(sql)


def fetchall(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    # ── Client Workstation Read Handling ──
    # For device telemetry (live server state), proxy to server.
    # For business tables, query local SQLite cache for instantaneous response (<1ms)
    # without hammering the PC server with HTTP round-trips.
    try:
        from utils.client_sync import is_client_mode, proxy_fetchall, get_server_url
        if is_client_mode():
            sql_upper = sql.strip().upper()
            if sql_upper.startswith("SELECT") or sql_upper.startswith("WITH"):
                if "DEVICE_SESSIONS" in sql_upper or not _ensure_connected():
                    server_rows = proxy_fetchall(sql, params, server_url=get_server_url())
                    if server_rows is not None:
                        return server_rows
    except Exception as _pe:
        log.debug(f"[db.fetchall] Client check note: {_pe}")

    if not _ensure_connected():
        return []
    if _engine_type == "sqlite":
        conn = _get_sqlite_read_conn() or _sqlite_conn
        lock_ctx = _db_lock if conn is _sqlite_conn else contextlib.nullcontext()
        with lock_ctx:
            try:
                clean_sql = _translate_pg_to_sqlite(sql)
                actual_placeholders = clean_sql.count("?")
                sanitized_params = _sanitize_params(params[:actual_placeholders]) if params else ()
                cur = conn.cursor()
                cur.execute(clean_sql, sanitized_params)
                rows = cur.fetchall()
                result = [dict(r) for r in rows]
                cur.close()
                return result
            except Exception as exc:
                log.error(f"[SQLite] fetchall failed on SQL: {sql[:100]} | Error: {exc}")
                try:
                    from utils.client_sync import is_client_mode, proxy_fetchall, get_server_url
                    if is_client_mode():
                        fallback_rows = proxy_fetchall(sql, params, server_url=get_server_url())
                        if fallback_rows is not None:
                            return fallback_rows
                except Exception:
                    pass
                return []
    else:
        conn = _pg_getconn()
        if conn is None:
            return []
        try:
            pg_sql = _prepare_pg_sql(sql, params)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if params:
                    cur.execute(pg_sql, params)
                else:
                    cur.execute(pg_sql)
                rows = [dict(row) for row in cur.fetchall()]
            conn.commit()
            return rows
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            log.error(f"[Postgres] fetchall failed on SQL: {sql[:160]} | Error: {exc}")
            return []
        finally:
            _pg_putconn(conn)


def fetchone(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    # ── Client Workstation Read Handling ──
    try:
        from utils.client_sync import is_client_mode, proxy_fetchone, get_server_url
        if is_client_mode():
            sql_upper = sql.strip().upper()
            if sql_upper.startswith("SELECT") or sql_upper.startswith("WITH"):
                if "DEVICE_SESSIONS" in sql_upper or not _ensure_connected():
                    server_row = proxy_fetchone(sql, params, server_url=get_server_url())
                    if server_row is not None:
                        return server_row
    except Exception as _pe:
        log.debug(f"[db.fetchone] Client check note: {_pe}")

    if not _ensure_connected():
        return None
    if _engine_type == "sqlite":
        conn = _get_sqlite_read_conn() or _sqlite_conn
        lock_ctx = _db_lock if conn is _sqlite_conn else contextlib.nullcontext()
        with lock_ctx:
            try:
                clean_sql = _translate_pg_to_sqlite(sql)
                actual_placeholders = clean_sql.count("?")
                sanitized_params = _sanitize_params(params[:actual_placeholders]) if params else ()
                cur = conn.cursor()
                cur.execute(clean_sql, sanitized_params)
                row = cur.fetchone()
                result = dict(row) if row else None
                cur.close()
                return result
            except Exception as exc:
                log.error(f"[SQLite] fetchone failed on SQL: {sql[:100]} | Error: {exc}")
                try:
                    from utils.client_sync import is_client_mode, proxy_fetchone, get_server_url
                    if is_client_mode():
                        fallback_row = proxy_fetchone(sql, params, server_url=get_server_url())
                        if fallback_row is not None:
                            return fallback_row
                except Exception:
                    pass
                return None
    else:
        conn = _pg_getconn()
        if conn is None:
            return None
        try:
            pg_sql = _prepare_pg_sql(sql, params)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if params:
                    cur.execute(pg_sql, params)
                else:
                    cur.execute(pg_sql)
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            log.error(f"[Postgres] fetchone failed on SQL: {sql[:160]} | Error: {exc}")
            return None
        finally:
            _pg_putconn(conn)


def callproc_cursor(proc: str, cursor_name: str = None, in_params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a PostgreSQL stored procedure returning a REFCURSOR, or return empty list on SQLite."""
    if not _ensure_connected():
        return []
    if _engine_type == "sqlite":
        return []
    if not cursor_name or cursor_name == "cursor":
        cursor_name = f"c_{uuid.uuid4().hex[:12]}"
    conn = _pg_getconn()
    if conn is None:
        return []
    try:
        all_params = in_params + (cursor_name,)
        placeholders = ", ".join(["%s"] * len(all_params))
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("BEGIN;")
            cur.execute(f"CALL {proc}({placeholders})", all_params)
            cur.execute(f'FETCH ALL IN "{cursor_name}"')
            rows = [dict(r) for r in cur.fetchall()]
        conn.commit()
        return rows
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        log.warning(f"[Postgres] callproc_cursor({proc}) failed: {exc}")
        return []
    finally:
        _pg_putconn(conn)


def callproc_out(proc: str, in_params: tuple = (), out_names: list = None) -> Optional[Dict[str, Any]]:
    """Emulate stored procedure execution with OUT parameters for SQLite, or run PostgreSQL procedure."""
    # ── Client Workstation Write-Through Proxy ──
    # Mirrors execute()'s proxy, which only ever covered raw SQL - this was
    # missing entirely for stored-procedure calls (sp_create_booking,
    # sp_pay_invoice, etc.), so those writes never reached the server from a
    # client workstation. Best-effort: local emulation still runs regardless
    # so the UI stays responsive even if the server is unreachable.
    proxy_result = None
    try:
        from utils.client_sync import is_client_mode, proxy_callproc, get_server_url
        if is_client_mode():
            proxy_result = proxy_callproc(proc, in_params=in_params, out_names=out_names, void=False, server_url=get_server_url())
    except Exception as _proxy_err:
        log.debug(f"[db.callproc_out] Client proxy error (non-fatal): {_proxy_err}")

    if not _ensure_connected():
        # Server already applied the call — return its result instead of
        # failing outright when this workstation has no local cache yet.
        if proxy_result:
            return proxy_result.get("result") or {}
        return None

    if _engine_type == "sqlite":
        with _db_lock:
            try:
                result = _emulate_sqlite_procedure_out(proc, in_params, out_names)
            except Exception as exc:
                log.error(f"[SQLite] Procedure emulation failed for {proc}: {exc}")
                return None
        _bump_server_version_if_applicable()

        # ── Reconcile a client's locally-emulated id with the SERVER's ──
        # The server is the single source of truth every client eventually
        # syncs from. A client's local SQLite autoincrement sequence can
        # drift from the server's (other clients/writes in between), so the
        # id `_emulate_sqlite_procedure_out` just assigned here may not match
        # what the server actually assigned for the "same" row. If any child
        # rows get written using the WRONG (locally-diverged) id, the next
        # server-snapshot pull sees no server row at that local id and
        # deletes it as "stale" — the exact bug behind a freshly-added
        # package vanishing on the next sync. When the proxy call to the
        # server succeeded and returned a different id, adopt the server's
        # id as canonical: repoint the just-inserted local row's primary key
        # to match, and return the server's id so callers write any child
        # rows (package_items, package_buckets, ...) against the correct id.
        if result and proxy_result and proxy_result.get("ok"):
            srv_result = proxy_result.get("result") or {}
            patch = _RECONCILE_PK_MAP.get(proc)
            if patch and srv_result:
                table, pk_col, out_name = patch
                local_id = result.get(out_name)
                server_id = srv_result.get(out_name)
                if local_id is not None and server_id is not None and local_id != server_id:
                    try:
                        with _db_lock:
                            cur = _sqlite_conn.cursor()
                            cur.execute(f"UPDATE {table} SET {pk_col} = ? WHERE {pk_col} = ?", (server_id, local_id))
                            _sqlite_conn.commit()
                        result[out_name] = server_id
                        log.info(f"[db.callproc_out] Reconciled {proc} id {local_id} -> server id {server_id}")
                    except Exception as exc:
                        log.warning(f"[db.callproc_out] Failed to reconcile {proc} id {local_id}->{server_id}: {exc}")
        return result

    # PostgreSQL Execution
    conn = _pg_getconn()
    if conn is None:
        return None
    placeholders = ", ".join(["%s"] * len(in_params))
    if out_names:
        out_placeholders = ", ".join(["NULL"] * len(out_names))
        sql = f"CALL {proc}({placeholders}, {out_placeholders})" if in_params else f"CALL {proc}({out_placeholders})"
    else:
        sql = f"CALL {proc}({placeholders})" if in_params else f"CALL {proc}()"
    try:
        with conn.cursor() as cur:
            cur.execute(sql, in_params if in_params else ())
            row = cur.fetchone()
            conn.commit()
            if row is None:
                result = {}
            elif out_names:
                result = dict(zip(out_names, row))
            else:
                result = {}
        _bump_server_version_if_applicable()
        return result
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        log.error(f"[Postgres] callproc_out({proc}) failed: {exc}")
        return None
    finally:
        _pg_putconn(conn)


def callproc_void(proc: str, in_params: tuple = ()) -> bool:
    """Emulate void stored procedure execution for SQLite, or run PostgreSQL procedure."""
    # ── Client Workstation Write-Through Proxy ── (see callproc_out for why)
    proxy_result = None
    try:
        from utils.client_sync import is_client_mode, proxy_callproc, get_server_url
        if is_client_mode():
            proxy_result = proxy_callproc(proc, in_params=in_params, void=True, server_url=get_server_url())
    except Exception as _proxy_err:
        log.debug(f"[db.callproc_void] Client proxy error (non-fatal): {_proxy_err}")

    if not _ensure_connected():
        # Server already applied the call — treat as success rather than
        # failing outright when this workstation has no local cache yet.
        return bool(proxy_result)

    if _engine_type == "sqlite":
        with _db_lock:
            try:
                ok = _emulate_sqlite_procedure_void(proc, in_params)
            except Exception as exc:
                log.error(f"[SQLite] Void procedure emulation failed for {proc}: {exc}")
                return False
        if ok:
            _bump_server_version_if_applicable()
        return ok

    conn = _pg_getconn()
    if conn is None:
        return False
    placeholders = ", ".join(["%s"] * len(in_params))
    sql = f"CALL {proc}({placeholders})" if in_params else f"CALL {proc}()"
    try:
        with conn.cursor() as cur:
            cur.execute(sql, in_params if in_params else ())
        conn.commit()
        _bump_server_version_if_applicable()
        return True
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        log.error(f"[Postgres] callproc_void({proc}) failed: {exc}")
        return False
    finally:
        _pg_putconn(conn)


def _gen_unique_booking_ref(cur) -> str:
    """Generate a collision-proof unique booking reference (BK-XXXX)."""
    cur.execute("SELECT bk_booking_ref, bk_id FROM bookings")
    rows = cur.fetchall()
    max_n = 0
    for r in rows:
        ref_str = str(r[0] or "")
        digits = "".join(c for c in ref_str if c.isdigit())
        if digits:
            try:
                val = int(digits)
                if val > max_n:
                    max_n = val
            except ValueError:
                pass
        b_id = r[1]
        if isinstance(b_id, int) and b_id > max_n:
            max_n = b_id
    next_n = max(max_n + 1, len(rows) + 1, 1)
    while True:
        cand = f"BK-{next_n:04d}"
        cur.execute("SELECT 1 FROM bookings WHERE bk_booking_ref = ? LIMIT 1", (cand,))
        if not cur.fetchone():
            return cand
        next_n += 1


def _gen_unique_kitchen_order_ref(cur) -> str:
    """Generate a collision-proof unique kitchen order reference (ORD-XXXX)."""
    cur.execute("SELECT ko_order_ref, ko_id FROM kitchen_orders")
    rows = cur.fetchall()
    max_n = 0
    for r in rows:
        ref_str = str(r[0] or "")
        digits = "".join(c for c in ref_str if c.isdigit())
        if digits:
            try:
                val = int(digits)
                if val > max_n:
                    max_n = val
            except ValueError:
                pass
        k_id = r[1]
        if isinstance(k_id, int) and k_id > max_n:
            max_n = k_id
    next_n = max(max_n + 1, len(rows) + 1, 1)
    while True:
        cand = f"ORD-{next_n:04d}"
        cur.execute("SELECT 1 FROM kitchen_orders WHERE ko_order_ref = ? LIMIT 1", (cand,))
        if not cur.fetchone():
            return cand
        next_n += 1


def _gen_unique_invoice_ref(cur, booking_id=None) -> str:
    """Generate a collision-proof unique invoice reference (INV-XXXX)."""
    cur.execute("SELECT inv_invoice_ref, inv_invoice_number, inv_id FROM invoices")
    rows = cur.fetchall()
    max_n = 0
    for r in rows:
        for val in (r[0], r[1]):
            digits = "".join(c for c in str(val or "") if c.isdigit())
            if digits:
                try:
                    num = int(digits)
                    if num > max_n:
                        max_n = num
                except ValueError:
                    pass
        i_id = r[2]
        if isinstance(i_id, int) and i_id > max_n:
            max_n = i_id
    start_n = max(max_n + 1, (booking_id or 0), len(rows) + 1, 1)
    while True:
        cand = f"INV-{start_n:04d}"
        cur.execute("SELECT 1 FROM invoices WHERE inv_invoice_ref = ? OR inv_invoice_number = ? LIMIT 1", (cand, cand))
        if not cur.fetchone():
            return cand
        start_n += 1


def _format_time_ampm(t_raw) -> str:
    """Format any time representation into 12-hour AM/PM format (e.g. '6:00 PM', '11:30 AM')."""
    if not t_raw:
        return "6:00 PM"
    if hasattr(t_raw, "strftime"):
        return t_raw.strftime("%I:%M %p").lstrip("0")
    s = str(t_raw).strip()
    from datetime import datetime as _dt
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            parsed = _dt.strptime(s, fmt).time()
            return parsed.strftime("%I:%M %p").lstrip("0")
        except ValueError:
            continue
    return s


# Which (table, primary-key column, out-param name) a client-mode id needs
# reconciling against once the server's own id for the same insert is known
# (see the reconciliation block in callproc_out). Only covers single-row
# INSERT-and-return-id procs where a locally-diverged id can later cause
# child rows (e.g. package_items/package_buckets) to be orphaned and the
# parent row purged as "stale" by the next server-snapshot pull.
_RECONCILE_PK_MAP = {
    "sp_add_package": ("packages", "pkg_id", "p_package_id"),
}


def _emulate_sqlite_procedure_out(proc: str, in_params: tuple, out_names: list) -> Optional[Dict[str, Any]]:
    """Native SQLite execution mapping for legacy stored procedure names."""
    cur = _sqlite_conn.cursor()
    out_dict = {}
    p = _sanitize_params(in_params)

    if proc == "sp_add_customer":
        # in_params: (name, contact, email, address, status)
        name = str(p[0]).strip()
        contact = str(p[1] or "").strip()
        email = str(p[2] or "").strip()
        address = str(p[3] or "").strip()
        status = str(p[4] if len(p) > 4 and p[4] else 'Active').strip()

        # Check existing customer by name or contact
        existing = None
        if contact:
            cur.execute("SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(?) OR (cus_contact = ? AND cus_contact != '') LIMIT 1", (name, contact))
            existing = cur.fetchone()
        else:
            cur.execute("SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1", (name,))
            existing = cur.fetchone()

        if existing:
            cust_id = existing[0]
            cur.execute("""
                UPDATE customers
                SET cus_name = ?,
                    cus_contact = COALESCE(NULLIF(?, ''), cus_contact),
                    cus_email = COALESCE(NULLIF(?, ''), cus_email),
                    cus_address = COALESCE(NULLIF(?, ''), cus_address),
                    cus_status = ?
                WHERE cus_id = ?
            """, (name, contact, email, address, status, cust_id))
            _sqlite_conn.commit()
            out_dict["p_customer_id"] = cust_id
        else:
            cur.execute("""
                INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status, cus_loyalty_tier)
                VALUES (?, ?, ?, ?, ?, 'Bronze')
            """, (name, contact, email, address, status))
            _sqlite_conn.commit()
            out_dict["p_customer_id"] = cur.lastrowid

    elif proc == "sp_add_menu_item":
        # in_params: (item, description, category, package, price, status)
        cur.execute("""
            INSERT INTO menu_items (mi_name, name, mi_description, description, mi_category, category, mi_package_tier, mi_package, package_tier, package, mi_price, price, mi_status, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p[0], p[0], p[1], p[1], p[2], p[2], p[3], p[3], p[3], p[3], p[4], p[4], p[5], p[5]))
        _sqlite_conn.commit()
        out_dict["p_item_id"] = cur.lastrowid
        out_dict["p_menu_item_id"] = cur.lastrowid

    elif proc == "sp_add_expense":
        # in_params: (category, description, amount, date)
        s_date = _sanitize_param(p[3])
        cur.execute("""
            INSERT INTO expenses (exp_category, exp_description, exp_amount, exp_date, exp_expense_date)
            VALUES (?, ?, ?, ?, ?)
        """, (p[0], p[1], p[2], s_date, s_date))
        _sqlite_conn.commit()
        out_dict["p_expense_id"] = cur.lastrowid

    elif proc == "sp_add_package":
        # in_params: (name, price_per_pax, min_pax, description, [image])
        img = str(p[4]) if len(p) > 4 and p[4] is not None else ""
        cur.execute("""
            INSERT INTO packages (pkg_name, pkg_price_per_pax, pkg_min_pax, pkg_description, pkg_image)
            VALUES (?, ?, ?, ?, ?)
        """, (p[0], p[1], p[2], p[3], img))
        _sqlite_conn.commit()
        out_dict["p_package_id"] = cur.lastrowid

    elif proc == "sp_save_address":
        # in_params: (street, barangay_id, city_id, province_id, zip_code)
        cur.execute("""
            INSERT INTO addresses (ad_street, ad_barangay_id, ad_city_id, ad_province_id, ad_zip_code)
            VALUES (?, ?, ?, ?, ?)
        """, p)
        _sqlite_conn.commit()
        out_dict["p_address_id"] = cur.lastrowid

    elif proc == "sp_save_calendar_event":
        # in_params: (event_date, name, pax, event_time, location)
        cal_p = list(p)
        if len(cal_p) > 3:
            cal_p[3] = _format_time_ampm(cal_p[3])
        cur.execute("""
            INSERT INTO calendar_events (ce_event_date, ce_name, ce_pax, ce_event_time, ce_location)
            VALUES (?, ?, ?, ?, ?)
        """, tuple(cal_p))
        _sqlite_conn.commit()
        out_dict["p_id"] = cur.lastrowid

    elif proc == "sp_push_notification":
        # in_params: (type, title, message, color)
        cur.execute("""
            INSERT INTO notifications (notif_type, notif_title, notif_message, notif_color, notif_is_read)
            VALUES (?, ?, ?, ?, 0)
        """, p)
        _sqlite_conn.commit()
        out_dict["p_id"] = cur.lastrowid

    elif proc == "sp_create_kitchen_order":
        # in_params: (booking_id, client_name, event_name, pax, items_desc)
        order_ref = _gen_unique_kitchen_order_ref(cur)
        cur.execute("""
            INSERT INTO kitchen_orders (ko_booking_id, ko_order_ref, ko_customer_name, ko_event_date, ko_event_time, ko_pax, ko_status, ko_notes)
            VALUES (?, ?, ?, DATE('now'), '6:00 PM', ?, 'PREPARING', ?)
        """, (p[0], order_ref, p[1], p[3], p[4]))
        _sqlite_conn.commit()
        out_dict["p_order_id"] = cur.lastrowid
        out_dict["p_order_ref"] = order_ref

    elif proc == "sp_create_booking":
        # in_params: (name, contact, email, address, occasion, venue, event_date, event_time, pax, notes, menu_type, package_id, menu_value, total, payment_mode, amount_paid)
        cust_name = str(p[0]).strip()
        total_amt = float(p[13] or 0.0)
        # BUGFIX: Never auto-default amt_paid to total. Zero down payment = Unpaid.
        # Only trust what was actually entered by the user/system.
        amt_paid = max(0.0, float(p[15] or 0.0))

        pay_mode = str(p[14] or "Cash").strip()
        event_d = _sanitize_param(p[6])
        cust_contact = str(p[1] or "").strip()

        # Deduplicate: Check existing customer
        if cust_contact:
            cur.execute("SELECT cus_id, cus_total_events, cus_total_spent FROM customers WHERE LOWER(cus_name) = LOWER(?) OR (cus_contact = ? AND cus_contact != '') LIMIT 1", (cust_name, cust_contact))
        else:
            cur.execute("SELECT cus_id, cus_total_events, cus_total_spent FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1", (cust_name,))
        c_row = cur.fetchone()
        if c_row:
            cust_id = c_row[0]
        else:
            tier = "Gold" if total_amt >= 100000 else ("Silver" if total_amt >= 50000 else "Bronze")
            cur.execute("""
                INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status, cus_total_events, cus_total_spent, cus_loyalty_tier)
                VALUES (?, ?, ?, ?, 'Active', 0, 0.0, ?)
            """, (cust_name, p[1], p[2], p[3], tier))
            cust_id = cur.lastrowid

        # Deduplicate: Prevent double booking of same event on same day for same customer
        cur.execute("""
            SELECT bk_id, bk_booking_ref FROM bookings
            WHERE (bk_customer_id = ? OR LOWER(bk_customer_name) = LOWER(?))
              AND bk_event_date = ?
              AND LOWER(bk_occasion) = LOWER(?)
              AND bk_status != 'CANCELLED'
            LIMIT 1
        """, (cust_id, cust_name, event_d, str(p[4] or '')))
        dup_bk = cur.fetchone()
        if dup_bk:
            out_dict["p_booking_id"] = dup_bk[0]
            out_dict["p_booking_ref"] = dup_bk[1]
            return out_dict

        booking_ref = _gen_unique_booking_ref(cur)

        pkg_id = p[11]
        if pkg_id:
            cur.execute("SELECT pkg_id FROM packages WHERE pkg_id = ? LIMIT 1", (pkg_id,))
            if not cur.fetchone():
                pkg_id = None
        event_t = _format_time_ampm(p[7])

        # Status is ALWAYS PENDING for new bookings until manually confirmed by staff/admin
        cur.execute("""
            INSERT INTO bookings (
                bk_booking_ref, bk_customer_id, bk_customer_name, bk_address, bk_event_date, bk_event_time,
                bk_venue, bk_occasion, bk_pax, bk_notes, bk_menu_type, bk_package_id, bk_total_amount, bk_base_total,
                bk_payment_mode, bk_amount_paid, bk_down_payment, bk_down_payment_status, bk_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 'PENDING')
        """, (
            booking_ref, cust_id, cust_name, p[3], event_d, event_t,
            p[5], p[4], p[8], p[9], p[10], pkg_id, total_amt, total_amt,
            pay_mode, amt_paid, amt_paid
        ))
        booking_id = cur.lastrowid

        # Recalculate customer total events and total spent directly from bookings table
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(bk_total_amount), 0.0)
            FROM bookings
            WHERE (bk_customer_id = ? OR LOWER(bk_customer_name) = LOWER(?))
              AND bk_status != 'CANCELLED'
        """, (cust_id, cust_name))
        c_stats = cur.fetchone()
        real_events = int(c_stats[0] if c_stats else 1)
        real_spent = float(c_stats[1] if c_stats else total_amt)
        tier = "Gold" if (real_events >= 5 or real_spent >= 100000) else ("Silver" if (real_events >= 3 or real_spent >= 50000) else "Bronze")
        cur.execute("""
            UPDATE customers
            SET cus_total_events = ?, cus_total_spent = ?, cus_loyalty_tier = ?
            WHERE cus_id = ?
        """, (real_events, real_spent, tier, cust_id))

        # Auto create invoice (Unpaid or Partial if down payment recorded)
        bal = max(0.0, total_amt - amt_paid)
        inv_status = compute_invoice_status(total_amt, amt_paid)
        inv_num = _gen_unique_invoice_ref(cur, booking_id)
        cur.execute("""
            INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name, inv_event_date, inv_total_amount, inv_amount_paid, inv_balance, inv_down_payment, inv_payment_verified, inv_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (booking_id, inv_num, inv_num, cust_name, event_d, total_amt, amt_paid, bal, amt_paid, inv_status))
        inv_id = cur.lastrowid

        # Auto create payment record if down payment > 0
        # Dated to today (when the cash was actually collected), NOT the
        # event date — sales/evaluation reports bucket by pr_payment_date,
        # so dating this to a future event date silently moves the payment
        # out of the month it was actually received in.
        if amt_paid > 0:
            cur.execute("""
                INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_method, pr_is_downpayment, pr_is_verified, pr_notes, pr_note)
                VALUES (?, ?, ?, ?, ?, 1, 0, 'Initial down payment on booking request', 'Initial down payment on booking request')
            """, (inv_id, amt_paid, date.today().strftime("%Y-%m-%d"), pay_mode, pay_mode))

        # Auto create kitchen order
        cur.execute("""
            INSERT INTO kitchen_orders (ko_booking_id, ko_order_ref, ko_customer_name, ko_event_date, ko_event_time, ko_pax, ko_status, ko_notes)
            VALUES (?, ?, ?, ?, ?, ?, 'PREPARING', ?)
        """, (booking_id, booking_ref, cust_name, event_d, event_t, p[8], p[9]))

        _sqlite_conn.commit()
        out_dict["p_booking_id"] = booking_id
        out_dict["p_booking_ref"] = booking_ref

    elif proc == "sp_pay_invoice":
        # in_params: (booking_id, payment_amount, payment_date, method, note)
        b_id = p[0]
        pay_amt = float(p[1] or 0.0)
        pay_date = _sanitize_param(p[2])
        method = p[3] or "Cash"
        note = p[4] or ""

        # Fetch invoice for booking
        cur.execute("SELECT inv_id, inv_invoice_ref, inv_total_amount, inv_amount_paid FROM invoices WHERE inv_booking_id = ? LIMIT 1", (b_id,))
        inv_row = cur.fetchone()
        if not inv_row:
            # Auto create invoice if missing
            cur.execute("SELECT bk_customer_name, bk_event_date, bk_total_amount FROM bookings WHERE bk_id = ? LIMIT 1", (b_id,))
            bk_row = cur.fetchone()
            if not bk_row:
                raise Exception(f"No booking found with ID {b_id}")
            inv_ref = _gen_unique_invoice_ref(cur, b_id)
            cur.execute("""
                INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name, inv_event_date, inv_total_amount, inv_amount_paid, inv_balance, inv_status)
                VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, 'Unpaid')
            """, (b_id, inv_ref, inv_ref, bk_row[0], bk_row[1], float(bk_row[2]), float(bk_row[2])))
            inv_id = cur.lastrowid
            v_total = float(bk_row[2])
            v_paid = 0.0
        else:
            inv_id = inv_row[0]
            inv_ref = inv_row[1]
            v_total = float(inv_row[2] or 0.0)
            v_paid = float(inv_row[3] or 0.0)

        # Insert payment record
        cur.execute("""
            INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_notes)
            VALUES (?, ?, ?, ?, ?)
        """, (inv_id, pay_amt, pay_date, method, note))

        new_paid = v_paid + pay_amt
        remaining = max(0.0, v_total - new_paid)
        new_inv_status = compute_invoice_status(v_total, new_paid)

        # Booking status: any payment/downpayment confirms the booking unless completed or cancelled
        cur.execute("SELECT bk_status FROM bookings WHERE bk_id = ? LIMIT 1", (b_id,))
        cur_bk = cur.fetchone()
        cur_bk_stat = cur_bk[0] if cur_bk else "PENDING"
        if cur_bk_stat in ("COMPLETED", "CANCELLED"):
            new_bk_status = cur_bk_stat
        else:
            new_bk_status = "CONFIRMED"

        cur.execute("UPDATE invoices SET inv_amount_paid = ?, inv_status = ?, inv_balance = ? WHERE inv_id = ?", (new_paid, new_inv_status, remaining, inv_id))
        cur.execute("UPDATE bookings SET bk_amount_paid = ?, bk_status = ? WHERE bk_id = ?", (new_paid, new_bk_status, b_id))

        _sqlite_conn.commit()
        out_dict["p_invoice_id"] = inv_id
        out_dict["p_invoice_ref"] = inv_ref
        out_dict["p_new_invoice_status"] = new_inv_status
        out_dict["p_new_booking_status"] = new_bk_status
        out_dict["p_new_paid"] = new_paid
        out_dict["p_remaining"] = remaining

    elif proc == "sp_auto_create_invoice":
        b_id = p[0]
        cur.execute("SELECT inv_id, inv_invoice_ref FROM invoices WHERE inv_booking_id = ? LIMIT 1", (b_id,))
        row = cur.fetchone()
        if row:
            out_dict["p_invoice_id"] = row[0]
            out_dict["p_invoice_ref"] = row[1]
        else:
            cur.execute("SELECT bk_customer_name, bk_event_date, bk_total_amount FROM bookings WHERE bk_id = ? LIMIT 1", (b_id,))
            bk = cur.fetchone()
            if not bk:
                raise Exception(f"No booking found with ID {b_id}")
            inv_ref = _gen_unique_invoice_ref(cur, b_id)
            cur.execute("""
                INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name, inv_event_date, inv_total_amount, inv_amount_paid, inv_balance, inv_status)
                VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, 'Unpaid')
            """, (b_id, inv_ref, inv_ref, bk[0], bk[1], float(bk[2]), float(bk[2])))
            _sqlite_conn.commit()
            out_dict["p_invoice_id"] = cur.lastrowid
            out_dict["p_invoice_ref"] = inv_ref

    elif proc == "sp_add_payment_record":
        inv_id = p[0]
        amt = float(p[1] or 0.0)
        p_date = _sanitize_param(p[2])
        method = p[3] or "Cash"
        note = p[4] or ""

        cur.execute("""
            INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_notes)
            VALUES (?, ?, ?, ?, ?)
        """, (inv_id, amt, p_date, method, note))
        rec_id = cur.lastrowid

        cur.execute("SELECT inv_total_amount, inv_amount_paid, inv_booking_id FROM invoices WHERE inv_id = ? LIMIT 1", (inv_id,))
        inv_row = cur.fetchone()
        if inv_row:
            tot = float(inv_row[0] or 0.0)
            paid = float(inv_row[1] or 0.0) + amt
            rem = max(0.0, tot - paid)
            status = compute_invoice_status(tot, paid)
            cur.execute("UPDATE invoices SET inv_amount_paid = ?, inv_balance = ?, inv_status = ? WHERE inv_id = ?", (paid, rem, status, inv_id))
            if inv_row[2]:
                cur.execute("UPDATE bookings SET bk_amount_paid = ? WHERE bk_id = ?", (paid, inv_row[2]))
        else:
            status = "Paid"
            paid = amt

        _sqlite_conn.commit()
        out_dict["p_record_id"] = rec_id
        out_dict["p_new_status"] = status
        out_dict["p_new_paid"] = paid

    elif proc == "sp_write_audit_log":
        # in_params: (actor, action, table_name, record_id, old_value_json, new_value_json, [device])
        dev = str(p[6]) if len(p) > 6 and p[6] else "Desktop / Server"
        cur.execute("""
            INSERT INTO audit_logs (al_actor, al_action, al_table_name, al_record_id, al_old_value, al_new_value, al_device)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (p[0], p[1], p[2], p[3], str(p[4]) if p[4] is not None else None, str(p[5]) if p[5] is not None else None, dev))
        _sqlite_conn.commit()
        out_dict["p_log_id"] = cur.lastrowid

    cur.close()
    return out_dict


def _emulate_sqlite_procedure_void(proc: str, in_params: tuple) -> bool:
    """Native SQLite execution mapping for void stored procedure names."""
    cur = _sqlite_conn.cursor()
    p = _sanitize_params(in_params)

    if proc == "sp_update_customer":
        # (customer_id, name, contact, email, address, status)
        cur.execute("""
            UPDATE customers
            SET cus_name = ?, cus_contact = ?, cus_email = ?, cus_address = ?, cus_status = ?
            WHERE cus_id = ?
        """, (p[1], p[2], p[3], p[4], p[5], p[0]))

    elif proc == "sp_delete_customer":
        # bookings.bk_customer_id has NO "ON DELETE CASCADE" (unlike every
        # other customer-referencing table), so deleting a customer with any
        # booking on record used to fail outright with a raw FK constraint
        # error. Per explicit request: deleting a customer must also delete
        # their orders/billing history so the delete can actually succeed.
        # Bookings can be linked either by the real FK (bk_customer_id) or,
        # for older/walk-in rows, only by a matching customer name - delete
        # both cases so nothing is left silently orphaned. Everything below
        # bookings (booking_menu_items, booking_items, invoices, and via
        # invoices payment_records) already cascades automatically once the
        # booking row itself is gone.
        cur.execute("SELECT cus_name FROM customers WHERE cus_id = ?", (p[0],))
        cust_row = cur.fetchone()
        cust_name = cust_row[0] if cust_row else None
        if cust_name:
            cur.execute(
                "DELETE FROM bookings WHERE bk_customer_id = ? OR LOWER(bk_customer_name) = LOWER(?)",
                (p[0], cust_name),
            )
        else:
            cur.execute("DELETE FROM bookings WHERE bk_customer_id = ?", (p[0],))
        cur.execute("DELETE FROM customers WHERE cus_id = ?", (p[0],))

    elif proc == "sp_update_menu_item":
        # (item_id, item, description, category, package, price, status)
        cur.execute("""
            UPDATE menu_items
            SET mi_name = ?, name = ?, mi_description = ?, description = ?, mi_category = ?, category = ?,
                mi_package_tier = ?, mi_package = ?, package_tier = ?, package = ?,
                mi_price = ?, price = ?, mi_status = ?, status = ?
            WHERE mi_id = ?
        """, (p[1], p[1], p[2], p[2], p[3], p[3], p[4], p[4], p[4], p[4], p[5], p[5], p[6], p[6], p[0]))

    elif proc == "sp_delete_menu_item":
        cur.execute("DELETE FROM menu_items WHERE mi_id = ?", (p[0],))

    elif proc == "sp_update_package":
        # (db_id, name, price_per_pax, min_pax, description, [image])
        img = str(p[5]) if len(p) > 5 and p[5] is not None else ""
        cur.execute("""
            UPDATE packages
            SET pkg_name = ?, pkg_price_per_pax = ?, pkg_min_pax = ?, pkg_description = ?, pkg_image = ?
            WHERE pkg_id = ?
        """, (p[1], p[2], p[3], p[4], img, p[0]))

    elif proc == "sp_delete_package":
        cur.execute("DELETE FROM packages WHERE pkg_id = ?", (p[0],))

    elif proc == "sp_update_expense":
        # (expense_id, category, description, amount, date)
        s_date = _sanitize_param(p[4])
        cur.execute("""
            UPDATE expenses
            SET exp_category = ?, exp_description = ?, exp_amount = ?, exp_date = ?, exp_expense_date = ?
            WHERE exp_id = ?
        """, (p[1], p[2], p[3], s_date, s_date, p[0]))

    elif proc == "sp_delete_expense":
        cur.execute("DELETE FROM expenses WHERE exp_id = ?", (p[0],))

    elif proc == "sp_update_booking":
        # (db_id, name, contact, email, address, occasion, venue, event_date, event_time, pax, notes, menu_type, package_id, menu_value, total, payment_mode, amount_paid)
        bk_id = p[0]
        c_name = str(p[1] or '').strip()
        c_contact = str(p[2] or '').strip()
        c_email = str(p[3] or '').strip()
        c_address = str(p[4] or '').strip()
        occasion = str(p[5] or '').strip()
        venue = str(p[6] or '').strip()
        event_d = _sanitize_param(p[7])
        event_t = _format_time_ampm(p[8])
        pax = int(p[9] or 100)
        notes = str(p[10] or '').strip()
        m_type = str(p[11] or 'package').strip()
        pkg_id = p[12]
        m_val = str(p[13] or '').strip()
        base_tot = float(p[14] or 0.0)
        pay_mode = str(p[15] or 'Cash').strip()
        amt_paid = float(p[16] or 0.0)

        # The edited "Total" field is the base order amount; additional charges
        # already recorded for this booking layer on top of it (never silently
        # absorbed into a flat total).
        cur.execute("SELECT COALESCE(SUM(ac_amount), 0.0) FROM booking_additional_charges WHERE ac_booking_id = ?", (bk_id,))
        charges_sum = float(cur.fetchone()[0] or 0.0)
        tot = base_tot + charges_sum

        # Update bookings row
        cur.execute("""
            UPDATE bookings
            SET bk_customer_name = ?, bk_address = ?, bk_occasion = ?, bk_venue = ?,
                bk_event_date = ?, bk_event_time = ?, bk_pax = ?, bk_notes = ?,
                bk_menu_type = ?, bk_package_id = ?, bk_total_amount = ?, bk_base_total = ?,
                bk_payment_mode = ?, bk_amount_paid = ?, bk_down_payment = ?
            WHERE bk_id = ?
        """, (c_name, c_address, occasion, venue, event_d, event_t, pax, notes, m_type, pkg_id, tot, base_tot, pay_mode, amt_paid, amt_paid, bk_id))

        # Update invoices row — recalculate amount_paid from actual payment_records (source of truth)
        cur.execute("SELECT inv_id FROM invoices WHERE inv_booking_id = ? LIMIT 1", (bk_id,))
        inv_row = cur.fetchone()
        if inv_row:
            inv_id_upd = inv_row[0]
            # Sum all real payment records to get the accurate paid amount
            cur.execute("SELECT COALESCE(SUM(pr_amount), 0.0) FROM payment_records WHERE pr_invoice_id = ?", (inv_id_upd,))
            sum_row = cur.fetchone()
            logged_paid = float(sum_row[0] if sum_row else 0.0)

            # If this edit raised the amount paid beyond what's already logged,
            # log the increase as a real payment_records row (dated today) so
            # it's counted as actual cash collected this month — otherwise the
            # increase only lands on bookings.bk_amount_paid, which sales/
            # evaluation reports never read, and the cash silently disappears
            # from those reports.
            if amt_paid > logged_paid + 0.01:
                diff = amt_paid - logged_paid
                cur.execute("""
                    INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (inv_id_upd, diff, date.today().strftime("%Y-%m-%d"), pay_mode, "Recorded via booking edit"))
                new_paid = amt_paid
            else:
                new_paid = logged_paid

            rem = max(0.0, tot - new_paid)
            inv_stat = compute_invoice_status(tot, new_paid)
            cur.execute("""
                UPDATE invoices
                SET inv_customer_name = ?, inv_event_date = ?, inv_total_amount = ?,
                    inv_amount_paid = ?, inv_balance = ?, inv_status = ?
                WHERE inv_id = ?
            """, (c_name, event_d, tot, new_paid, rem, inv_stat, inv_id_upd))
        else:
            inv_num = f"INV-{bk_id:04d}"
            rem = max(0.0, tot - amt_paid)
            inv_stat = compute_invoice_status(tot, amt_paid)
            cur.execute("""
                INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name, inv_event_date, inv_total_amount, inv_amount_paid, inv_balance, inv_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (bk_id, inv_num, inv_num, c_name, event_d, tot, amt_paid, rem, inv_stat))
            inv_id_new = cur.lastrowid
            if amt_paid > 0:
                cur.execute("""
                    INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (inv_id_new, amt_paid, date.today().strftime("%Y-%m-%d"), pay_mode, "Recorded via booking edit"))

        # Update customer table
        cur.execute("SELECT bk_customer_id FROM bookings WHERE bk_id = ?", (bk_id,))
        c_id_row = cur.fetchone()
        if c_id_row and c_id_row[0]:
            cur.execute("""
                UPDATE customers
                SET cus_name = ?,
                    cus_contact = COALESCE(NULLIF(?, ''), cus_contact),
                    cus_email = COALESCE(NULLIF(?, ''), cus_email),
                    cus_address = COALESCE(NULLIF(?, ''), cus_address)
                WHERE cus_id = ?
            """, (c_name, c_contact, c_email, c_address, c_id_row[0]))

    elif proc == "sp_confirm_booking":
        cur.execute("UPDATE bookings SET bk_status = 'CONFIRMED' WHERE bk_id = ?", (p[0],))

    elif proc == "sp_verify_payment":
        if len(p) >= 1 and p[0]:
            cur.execute("UPDATE invoices SET inv_payment_verified = 1 WHERE inv_id = ?", (p[0],))
        if len(p) >= 2 and p[1]:
            cur.execute("UPDATE payment_records SET pr_is_verified = 1 WHERE pr_id = ?", (p[1],))

    elif proc == "sp_update_booking_status":
        # (booking_id, new_status)
        cur.execute("UPDATE bookings SET bk_status = ? WHERE bk_id = ?", (p[1], p[0]))
        if p[1] == "CANCELLED":
            # A cancelled order must not keep showing as active unpaid/partial
            # billing - zero out the outstanding balance and tag the invoice
            # CANCELLED so Billing/Ledger no longer treat it as pending.
            cur.execute(
                "UPDATE invoices SET inv_status = 'CANCELLED', inv_balance = 0 WHERE inv_booking_id = ?",
                (p[0],),
            )

    elif proc == "sp_delete_booking":
        try:
            cur.execute("SELECT bk_booking_ref FROM bookings WHERE bk_id = ?", (p[0],))
            b_row = cur.fetchone()
            if b_row and b_row[0]:
                cur.execute("INSERT OR REPLACE INTO deleted_records (dr_table, dr_ref, dr_record_id) VALUES ('bookings', ?, ?)", (str(b_row[0]), p[0]))
        except Exception:
            pass
        cur.execute("DELETE FROM bookings WHERE bk_id = ?", (p[0],))
        cur.execute("DELETE FROM invoices WHERE inv_booking_id = ?", (p[0],))
        cur.execute("DELETE FROM kitchen_orders WHERE ko_booking_id = ?", (p[0],))

    elif proc == "sp_complete_booking":
        cur.execute("UPDATE bookings SET bk_status = 'COMPLETED' WHERE bk_id = ?", (p[0],))

    elif proc == "sp_update_invoice":
        # (p_invoice_id, p_customer_name, p_event_date, p_total_amount, p_amount_paid, p_status)
        s_date = _sanitize_param(p[2])
        cur.execute("""
            UPDATE invoices
            SET inv_customer_name = ?, inv_event_date = ?, inv_total_amount = ?, inv_amount_paid = ?, inv_status = ?
            WHERE inv_id = ?
        """, (p[1], s_date, p[3], p[4], p[5], p[0]))

    elif proc == "sp_delete_invoice":
        cur.execute("DELETE FROM invoices WHERE inv_id = ?", (p[0],))

    elif proc == "sp_delete_calendar_events_for_date":
        cur.execute("DELETE FROM calendar_events WHERE ce_event_date = ?", (p[0],))

    elif proc == "sp_dismiss_notification":
        cur.execute("UPDATE notifications SET notif_is_read = 1 WHERE notif_id = ?", (p[0],))

    elif proc == "sp_mark_all_notifications_read":
        cur.execute("UPDATE notifications SET notif_is_read = 1 WHERE notif_is_read = 0")

    elif proc == "sp_save_business_info":
        cur.execute("""
            UPDATE business_info
            SET bi_name = ?, bi_contact = ?, bi_email = ?, bi_address = ?, bi_updated_at = CURRENT_TIMESTAMP
            WHERE bi_id = 1
        """, p)

    elif proc == "sp_save_booking_policy":
        cur.execute("""
            UPDATE business_info
            SET bi_min_downpayment_pct = ?, bi_allow_zero_downpayment = ?, bi_updated_at = CURRENT_TIMESTAMP
            WHERE bi_id = 1
        """, p)

    elif proc == "sp_save_capacity_policy":
        cur.execute("""
            UPDATE business_info
            SET bi_max_daily_pax = ?, bi_updated_at = CURRENT_TIMESTAMP
            WHERE bi_id = 1
        """, (p[0],))

    elif proc == "sp_save_smtp_config":
        cur.execute("""
            UPDATE business_info
            SET bi_smtp_host = ?, bi_smtp_port = ?, bi_smtp_user = ?, bi_smtp_pass = ?, bi_updated_at = CURRENT_TIMESTAMP
            WHERE bi_id = 1
        """, p)

    elif proc == "sp_update_kitchen_order_status":
        cur.execute("UPDATE kitchen_orders SET ko_status = ? WHERE ko_id = ?", (p[1], p[0]))

    elif proc == "sp_delete_kitchen_order":
        cur.execute("DELETE FROM kitchen_orders WHERE ko_id = ?", (p[0],))

    elif proc == "sp_delete_kitchen_task":
        cur.execute("DELETE FROM kitchen_orders WHERE ko_id = ?", (p[0],))

    elif proc == "sp_recalculate_loyalty":
        cur.execute("UPDATE customer_loyalty_tiers SET cl_last_recalculated = CURRENT_TIMESTAMP WHERE cl_customer_id = ?", (p[0],))

    elif proc == "sp_write_audit_log":
        cur.execute("""
            INSERT INTO audit_logs (al_actor, al_action, al_table_name, al_record_id, al_old_value, al_new_value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (p[0], p[1], p[2], p[3], str(p[4]), str(p[5])))

    elif proc == "sp_mark_follow_up_done" or proc == "sp_complete_follow_up":
        cur.execute("UPDATE customer_follow_ups SET cfu_is_done = 1 WHERE cfu_id = ?", (p[0],))

    elif proc == "sp_delete_follow_up":
        cur.execute("DELETE FROM customer_follow_ups WHERE cfu_id = ?", (p[0],))

    _sqlite_conn.commit()
    cur.close()
    return True


def close() -> None:
    """Close active database connections and the connection pool."""
    global _sqlite_conn, _pg_conn, _pg_pool
    with _db_lock:
        if _sqlite_conn is not None:
            try:
                _sqlite_conn.close()
            except Exception:
                pass
            _sqlite_conn = None
        if hasattr(_tls, "read_conn") and _tls.read_conn is not None:
            try:
                _tls.read_conn.close()
            except Exception:
                pass
            _tls.read_conn = None
        if _pg_pool is not None:
            try:
                _pg_pool.closeall()
            except Exception:
                pass
            _pg_pool = None
        _pg_conn = None


# ---------------------------------------------------------------------------
# Device & Server Session Monitoring
# ---------------------------------------------------------------------------

def upsert_device_session(
    device_id: str,
    hostname: str,
    ip_address: str = "",
    os_info: str = "",
    app_version: str = "",
    username: str = "",
    user_role: str = "",
    active_module: str = "Dashboard",
    status: str = "online"
) -> bool:
    """Register or update a connected client device session in the database."""
    _ensure_connected()
    if _engine_type == "postgres":
        sql = """
            INSERT INTO device_sessions (
                device_id, hostname, ip_address, os_info, app_version,
                username, user_role, active_module, status, first_connected_at, last_heartbeat
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (device_id) DO UPDATE SET
                hostname = EXCLUDED.hostname,
                ip_address = EXCLUDED.ip_address,
                os_info = EXCLUDED.os_info,
                app_version = EXCLUDED.app_version,
                username = COALESCE(NULLIF(EXCLUDED.username, ''), device_sessions.username),
                user_role = COALESCE(NULLIF(EXCLUDED.user_role, ''), device_sessions.user_role),
                active_module = EXCLUDED.active_module,
                status = EXCLUDED.status,
                last_heartbeat = NOW()
        """
        params = (device_id, hostname, ip_address, os_info, app_version, username, user_role, active_module, status)
    else:
        sql = """
            INSERT INTO device_sessions (
                device_id, hostname, ip_address, os_info, app_version,
                username, user_role, active_module, status, first_connected_at, last_heartbeat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (device_id) DO UPDATE SET
                hostname = excluded.hostname,
                ip_address = excluded.ip_address,
                os_info = excluded.os_info,
                app_version = excluded.app_version,
                username = COALESCE(NULLIF(excluded.username, ''), device_sessions.username),
                user_role = COALESCE(NULLIF(excluded.user_role, ''), device_sessions.user_role),
                active_module = excluded.active_module,
                status = excluded.status,
                last_heartbeat = CURRENT_TIMESTAMP
        """
        params = (device_id, hostname, ip_address, os_info, app_version, username, user_role, active_module, status)

    try:
        execute(sql, params)
        return True
    except Exception as e:
        log.warning(f"[DB] upsert_device_session failed: {e}")
        return False


def update_device_heartbeat(
    device_id: str,
    username: Optional[str] = None,
    user_role: Optional[str] = None,
    active_module: Optional[str] = None,
    status: str = "online",
    hostname: str = "",
    ip_address: str = "",
    os_info: str = "",
    app_version: str = ""
) -> bool:
    """Update active heartbeat ping and current screen from a connected client device.

    hostname/ip_address/os_info/app_version are optional and only used to
    self-heal (see below) — pass them from the caller's cached values when
    available (device_tracker already has these on hand for every heartbeat).
    """
    _ensure_connected()
    if _engine_type == "postgres":
        sql = """
            UPDATE device_sessions SET
                last_heartbeat = NOW(),
                status = %s,
                username = COALESCE(%s, username),
                user_role = COALESCE(%s, user_role),
                active_module = COALESCE(%s, active_module)
            WHERE device_id = %s
        """
        exists_sql = "SELECT device_id FROM device_sessions WHERE device_id = %s"
    else:
        sql = """
            UPDATE device_sessions SET
                last_heartbeat = CURRENT_TIMESTAMP,
                status = ?,
                username = COALESCE(?, username),
                user_role = COALESCE(?, user_role),
                active_module = COALESCE(?, active_module)
            WHERE device_id = ?
        """
        exists_sql = "SELECT device_id FROM device_sessions WHERE device_id = ?"
    params = (status, username, user_role, active_module, device_id)
    try:
        execute(sql, params)

        # Self-heal: on a client workstation, the row this UPDATE targets
        # only exists because an earlier upsert_device_session() write made
        # it to the server — and that write is fire-and-forget with no
        # retry (utils/db.py execute()'s proxy_write result is never
        # checked). If that one write was lost (e.g. fired before the
        # network was fully up at startup), this device's row never
        # existed server-side and every heartbeat since has been silently
        # updating zero rows, forever, with no error anywhere. Detect that
        # and recreate the row instead of failing silently.
        try:
            from utils.client_sync import is_client_mode
            if is_client_mode():
                row = fetchone(exists_sql, (device_id,))
                if not row:
                    upsert_device_session(
                        device_id=device_id,
                        hostname=hostname or device_id,
                        ip_address=ip_address,
                        os_info=os_info,
                        app_version=app_version,
                        username=username or "",
                        user_role=user_role or "",
                        active_module=active_module or "Dashboard",
                        status=status
                    )
        except Exception as heal_err:
            log.debug(f"[DB] update_device_heartbeat self-heal check failed: {heal_err}")

        return True
    except Exception as e:
        log.warning(f"[DB] update_device_heartbeat failed: {e}")
        return False


def set_device_offline(device_id: str) -> bool:
    """Mark a client device as disconnected / offline immediately without updating heartbeat."""
    _ensure_connected()
    if _engine_type == "postgres":
        sql = "UPDATE device_sessions SET status = 'offline' WHERE device_id = %s"
    else:
        sql = "UPDATE device_sessions SET status = 'offline' WHERE device_id = ?"
    try:
        execute(sql, (device_id,))
        return True
    except Exception as e:
        log.warning(f"[DB] set_device_offline failed: {e}")
        return False


_CONNECTED_DEVICES_SQLITE_SQL = """
    SELECT
        device_id, hostname, ip_address, os_info, app_version,
        username, user_role, active_module,
        CASE
            WHEN status = 'offline' THEN 'offline'
            WHEN (julianday('now') - julianday(last_heartbeat)) * 86400 <= 35 THEN 'online'
            WHEN (julianday('now') - julianday(last_heartbeat)) * 86400 <= 90 THEN 'idle'
            ELSE 'offline'
        END AS live_status,
        status AS raw_status,
        first_connected_at,
        last_heartbeat,
        CAST((julianday('now') - julianday(last_heartbeat)) * 86400 AS INTEGER) AS seconds_since_ping
    FROM device_sessions
    ORDER BY last_heartbeat DESC
"""


def get_connected_devices() -> List[Dict[str, Any]]:
    """Retrieve list of all monitored devices with computed live status."""
    devices, _ok, _err = get_connected_devices_with_status()
    return devices


def get_connected_devices_with_status() -> "Tuple[List[Dict[str, Any]], bool, Optional[str]]":
    """Like get_connected_devices(), but also reports whether THIS specific
    call reached the server in client mode, instead of the shared
    'most recent proxy call' flag in client_sync (get_last_proxy_status),
    which any unrelated concurrent write/read elsewhere in the app can
    overwrite between this call and the caller checking it — leading to a
    stale/empty device list with no visible warning. Returns
    (devices, proxy_ok, proxy_error); proxy_ok/proxy_error are always
    (True, None) when this machine is not in client mode.
    """
    try:
        from utils.client_sync import is_client_mode, proxy_fetchall, get_server_url
        if is_client_mode():
            server_rows = proxy_fetchall(_CONNECTED_DEVICES_SQLITE_SQL, (), server_url=get_server_url())
            if server_rows is None:
                from utils.client_sync import get_last_proxy_status
                _ok, err = get_last_proxy_status()
                return [], False, (err or "Server unreachable")
            return server_rows, True, None
    except Exception as e:
        log.debug(f"[DB] get_connected_devices_with_status client-mode check failed: {e}")

    _ensure_connected()
    if _engine_type == "postgres":
        # Auto-discover any active remote PostgreSQL client connections
        try:
            direct_conns = fetchall("""
                SELECT DISTINCT client_addr::text AS c_ip, usename, application_name
                FROM pg_stat_activity
                WHERE client_addr IS NOT NULL
                  AND client_addr != '127.0.0.1'::inet
                  AND datname = current_database()
            """)
            for dc in direct_conns:
                ip = dc.get("c_ip") if isinstance(dc, dict) else str(dc[0])
                if ip:
                    clean_ip = ip.replace(":", "_").replace(".", "_")
                    upsert_device_session(
                        device_id=f"direct-db-{clean_ip}",
                        hostname=f"📱 Remote Mobile / Client ({ip})",
                        ip_address=ip,
                        os_info="PostgreSQL Direct Client Connection",
                        app_version="v1.26.12",
                        username="Mobile Client",
                        user_role="Database Client",
                        active_module="Live Database",
                        status="online"
                    )
        except Exception:
            pass

        sql = """
            SELECT 
                device_id, hostname, ip_address, os_info, app_version,
                username, user_role, active_module,
                CASE 
                    WHEN status = 'offline' THEN 'offline'
                    WHEN last_heartbeat >= NOW() - INTERVAL '35 seconds' THEN 'online'
                    WHEN last_heartbeat >= NOW() - INTERVAL '90 seconds' THEN 'idle'
                    ELSE 'offline'
                END AS live_status,
                status AS raw_status,
                first_connected_at,
                last_heartbeat,
                ROUND(EXTRACT(EPOCH FROM (NOW() - last_heartbeat))) AS seconds_since_ping
            FROM device_sessions
            ORDER BY last_heartbeat DESC
        """
    else:
        sql = _CONNECTED_DEVICES_SQLITE_SQL
    try:
        rows = fetchall(sql)
        devices = []
        for r in rows:
            if isinstance(r, dict):
                devices.append(r)
            else:
                # tuple/list conversion
                devices.append({
                    "device_id": r[0], "hostname": r[1], "ip_address": r[2], "os_info": r[3],
                    "app_version": r[4], "username": r[5], "user_role": r[6], "active_module": r[7],
                    "live_status": r[8], "raw_status": r[9], "first_connected_at": r[10],
                    "last_heartbeat": r[11], "seconds_since_ping": r[12]
                })
        return devices, True, None
    except Exception as e:
        log.warning(f"[DB] get_connected_devices failed: {e}")
        return [], False, str(e)


def get_server_connection_stats() -> Dict[str, Any]:
    """Return live database server stats including active PG connections and pool status."""
    _ensure_connected()
    stats = {
        "engine": _engine_type,
        "active_devices_count": 0,
        "pg_active_connections": 1,
        "pool_min": _POOL_MIN_CONNS if _engine_type == "postgres" else 1,
        "pool_max": _POOL_MAX_CONNS if _engine_type == "postgres" else 1,
        "database_name": "PostgreSQL (jayraldines_catering)" if _engine_type == "postgres" else "SQLite WAL Embedded",
        "ping_ms": 0.0
    }

    t0 = time.perf_counter()
    try:
        if _engine_type == "postgres":
            pg_res = fetchone("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            if pg_res:
                stats["pg_active_connections"] = pg_res[0] if isinstance(pg_res, (list, tuple)) else pg_res.get("count", 1)

            db_name_res = fetchone("SELECT current_database() AS dbname")
            if db_name_res:
                if isinstance(db_name_res, (list, tuple)):
                    stats["database_name"] = str(db_name_res[0])
                elif isinstance(db_name_res, dict):
                    stats["database_name"] = str(db_name_res.get("dbname") or db_name_res.get("current_database") or "PostgreSQL")
                else:
                    stats["database_name"] = str(db_name_res)

        devices, devices_ok, devices_err = get_connected_devices_with_status()
        stats["active_devices_count"] = sum(1 for d in devices if d.get("live_status") == "online")
        stats["total_registered_devices"] = len(devices)
        stats["devices_reachable"] = devices_ok
        stats["devices_error"] = devices_err
    except Exception as e:
        log.warning(f"[DB] get_server_connection_stats failed: {e}")
    finally:
        stats["ping_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    return stats
