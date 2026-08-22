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
from pathlib import Path
from datetime import date, datetime, time as time_type
from typing import Any, Optional, Dict, List, Tuple

from utils.logger import get_logger
from utils.sqlite_schema import init_sqlite_db

log = get_logger()

try:
    import psycopg2
    import psycopg2.extras
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False

_db_lock = threading.RLock()
_engine_type: str = "sqlite"  # 'sqlite' or 'postgres'
_sqlite_conn: Optional[sqlite3.Connection] = None
_pg_conn: Optional[Any] = None
_sqlite_path: Optional[Path] = None


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
    return _engine_type


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
            _engine_type = "sqlite"
            log.info("SQLite Database initialized and ready.")
            return True
        except Exception as exc:
            log.error(f"Failed to connect to SQLite database: {exc}", exc_info=True)
            _sqlite_conn = None
            return False


def connect_postgres() -> bool:
    """Connect to PostgreSQL if explicitly requested."""
    global _pg_conn, _engine_type
    if not _PSYCOPG2_AVAILABLE:
        return False

    import getpass
    env_user = os.environ.get("DB_USER")
    user = env_user if env_user else getpass.getuser()
    cfg = {
        "host":     os.environ.get("DB_HOST", "localhost"),
        "port":     int(os.environ.get("DB_PORT", "5432")),
        "dbname":   os.environ.get("DB_NAME", "jayraldines_catering"),
        "user":     user,
        "password": os.environ.get("DB_PASSWORD", "12345678"),
    }

    with _db_lock:
        try:
            if _pg_conn is not None:
                try:
                    _pg_conn.close()
                except Exception:
                    pass
            _pg_conn = psycopg2.connect(**cfg, connect_timeout=4)
            _pg_conn.autocommit = False
            _engine_type = "postgres"
            log.info("Connected to PostgreSQL database.")
            return True
        except Exception as exc:
            log.warning(f"PostgreSQL connection failed: {exc}. Using SQLite embedded database.")
            _pg_conn = None
            return False


def connect() -> bool:
    """Connect to preferred database (SQLite default)."""
    pref = os.environ.get("DB_ENGINE", "sqlite").lower().strip()
    if pref == "postgres" and _PSYCOPG2_AVAILABLE:
        if connect_postgres():
            return True
    return connect_sqlite()


def _ensure_connected() -> bool:
    global _engine_type, _sqlite_conn, _pg_conn
    if _engine_type == "sqlite":
        if _sqlite_conn is None:
            return connect_sqlite()
        return True
    elif _engine_type == "postgres":
        if _pg_conn is None or getattr(_pg_conn, "closed", 1) != 0:
            return connect()
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


def execute(sql: str, params: tuple = ()) -> None:
    with _db_lock:
        if not _ensure_connected():
            raise RuntimeError("No database connection")
        if _engine_type == "sqlite":
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
            try:
                with _pg_conn.cursor() as cur:
                    cur.execute(sql, params)
                _pg_conn.commit()
            except Exception as exc:
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass
                log.error(f"[Postgres] execute failed: {exc}")
                raise


def fetchall(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with _db_lock:
        if not _ensure_connected():
            return []
        if _engine_type == "sqlite":
            try:
                clean_sql = _translate_pg_to_sqlite(sql)
                actual_placeholders = clean_sql.count("?")
                sanitized_params = _sanitize_params(params[:actual_placeholders]) if params else ()
                cur = _sqlite_conn.cursor()
                cur.execute(clean_sql, sanitized_params)
                rows = cur.fetchall()
                result = [dict(r) for r in rows]
                cur.close()
                return result
            except Exception as exc:
                log.error(f"[SQLite] fetchall failed on SQL: {sql[:100]} | Error: {exc}")
                return []
        else:
            try:
                with _pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    return [dict(row) for row in cur.fetchall()]
            except Exception as exc:
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass
                log.error(f"[Postgres] fetchall failed: {exc}")
                return []


def fetchone(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    with _db_lock:
        if not _ensure_connected():
            return None
        if _engine_type == "sqlite":
            try:
                clean_sql = _translate_pg_to_sqlite(sql)
                actual_placeholders = clean_sql.count("?")
                sanitized_params = _sanitize_params(params[:actual_placeholders]) if params else ()
                cur = _sqlite_conn.cursor()
                cur.execute(clean_sql, sanitized_params)
                row = cur.fetchone()
                result = dict(row) if row else None
                cur.close()
                return result
            except Exception as exc:
                log.error(f"[SQLite] fetchone failed on SQL: {sql[:100]} | Error: {exc}")
                return None
        else:
            try:
                with _pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    row = cur.fetchone()
                    return dict(row) if row else None
            except Exception as exc:
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass
                log.error(f"[Postgres] fetchone failed: {exc}")
                return None


def callproc_out(proc: str, in_params: tuple = (), out_names: list = None) -> Optional[Dict[str, Any]]:
    """Emulate stored procedure execution with OUT parameters for SQLite, or run PostgreSQL procedure."""
    with _db_lock:
        if not _ensure_connected():
            return None

        if _engine_type == "sqlite":
            try:
                return _emulate_sqlite_procedure_out(proc, in_params, out_names)
            except Exception as exc:
                log.error(f"[SQLite] Procedure emulation failed for {proc}: {exc}")
                return None

        # PostgreSQL Execution
        placeholders = ", ".join(["%s"] * len(in_params))
        if out_names:
            out_placeholders = ", ".join(["NULL"] * len(out_names))
            sql = f"CALL {proc}({placeholders}, {out_placeholders})" if in_params else f"CALL {proc}({out_placeholders})"
        else:
            sql = f"CALL {proc}({placeholders})" if in_params else f"CALL {proc}()"
        try:
            with _pg_conn.cursor() as cur:
                cur.execute(sql, in_params if in_params else ())
                row = cur.fetchone()
                _pg_conn.commit()
                if row is None:
                    return {}
                if out_names:
                    return dict(zip(out_names, row))
                return {}
        except Exception as exc:
            try:
                _pg_conn.rollback()
            except Exception:
                pass
            log.error(f"[Postgres] callproc_out({proc}) failed: {exc}")
            return None


def callproc_void(proc: str, in_params: tuple = ()) -> bool:
    """Emulate void stored procedure execution for SQLite, or run PostgreSQL procedure."""
    with _db_lock:
        if not _ensure_connected():
            return False

        if _engine_type == "sqlite":
            try:
                return _emulate_sqlite_procedure_void(proc, in_params)
            except Exception as exc:
                log.error(f"[SQLite] Void procedure emulation failed for {proc}: {exc}")
                return False

        placeholders = ", ".join(["%s"] * len(in_params))
        sql = f"CALL {proc}({placeholders})" if in_params else f"CALL {proc}()"
        try:
            with _pg_conn.cursor() as cur:
                cur.execute(sql, in_params if in_params else ())
            _pg_conn.commit()
            return True
        except Exception as exc:
            try:
                _pg_conn.rollback()
            except Exception:
                pass
            log.error(f"[Postgres] callproc_void({proc}) failed: {exc}")
            return False


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
        # in_params: (name, price_per_pax, min_pax, description)
        cur.execute("""
            INSERT INTO packages (pkg_name, pkg_price_per_pax, pkg_min_pax, pkg_description)
            VALUES (?, ?, ?, ?)
        """, p)
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
        cur.execute("""
            INSERT INTO calendar_events (ce_event_date, ce_name, ce_pax, ce_event_time, ce_location)
            VALUES (?, ?, ?, ?, ?)
        """, p)
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
        cur.execute("SELECT COUNT(*) FROM kitchen_orders")
        cnt = cur.fetchone()[0] + 1
        order_ref = f"ORD-{cnt:04d}"
        cur.execute("""
            INSERT INTO kitchen_orders (ko_booking_id, ko_order_ref, ko_customer_name, ko_event_date, ko_event_time, ko_pax, ko_status, ko_notes)
            VALUES (?, ?, ?, DATE('now'), '18:00', ?, 'PREPARING', ?)
        """, (p[0], order_ref, p[1], p[3], p[4]))
        _sqlite_conn.commit()
        out_dict["p_order_id"] = cur.lastrowid
        out_dict["p_order_ref"] = order_ref

    elif proc == "sp_create_booking":
        # in_params: (name, contact, email, address, occasion, venue, event_date, event_time, pax, notes, menu_type, package_id, menu_value, total, payment_mode, amount_paid)
        cust_name = str(p[0]).strip()
        total_amt = float(p[13] or 0.0)
        amt_paid = float(p[15] or 0.0)
        if amt_paid <= 0.0:
            amt_paid = total_amt  # Default to full payment on auto-approval

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
            new_events = int(c_row[1] or 0) + 1
            new_spent = float(c_row[2] or 0.0) + total_amt
            tier = "Gold" if (new_events >= 5 or new_spent >= 100000) else ("Silver" if (new_events >= 3 or new_spent >= 50000) else "Bronze")
            cur.execute("""
                UPDATE customers
                SET cus_total_events = ?, cus_total_spent = ?, cus_loyalty_tier = ?
                WHERE cus_id = ?
            """, (new_events, new_spent, tier, cust_id))
        else:
            tier = "Gold" if total_amt >= 100000 else ("Silver" if total_amt >= 50000 else "Bronze")
            cur.execute("""
                INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status, cus_total_events, cus_total_spent, cus_loyalty_tier)
                VALUES (?, ?, ?, ?, 'Active', 1, ?, ?)
            """, (cust_name, p[1], p[2], p[3], total_amt, tier))
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

        cur.execute("SELECT COUNT(*) FROM bookings")
        cnt = cur.fetchone()[0] + 1
        booking_ref = f"BK-{cnt:04d}"

        cur.execute("""
            INSERT INTO bookings (
                bk_booking_ref, bk_customer_id, bk_customer_name, bk_address, bk_event_date, bk_event_time,
                bk_venue, bk_occasion, bk_pax, bk_notes, bk_menu_type, bk_package_id, bk_total_amount,
                bk_payment_mode, bk_amount_paid, bk_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')
        """, (
            booking_ref, cust_id, cust_name, p[3], event_d, p[7],
            p[5], p[4], p[8], p[9], p[10], p[11], total_amt,
            pay_mode, amt_paid
        ))
        booking_id = cur.lastrowid

        # Auto create invoice (Paid)
        bal = max(0.0, total_amt - amt_paid)
        inv_status = "Paid" if bal <= 0.0 else ("Partial" if amt_paid > 0 else "Unpaid")
        inv_num = f"INV-{booking_id:04d}"
        cur.execute("""
            INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name, inv_event_date, inv_total_amount, inv_amount_paid, inv_balance, inv_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (booking_id, inv_num, inv_num, cust_name, event_d, total_amt, amt_paid, bal, inv_status))
        inv_id = cur.lastrowid

        # Auto record payment in payment_records
        if amt_paid > 0:
            cur.execute("""
                INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_method, pr_notes, pr_note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (inv_id, amt_paid, event_d, pay_mode, pay_mode, "Auto-approved payment on booking creation", "Auto-approved payment on booking creation"))

        # Auto create kitchen order
        cur.execute("""
            INSERT INTO kitchen_orders (ko_booking_id, ko_order_ref, ko_customer_name, ko_event_date, ko_event_time, ko_pax, ko_status, ko_notes)
            VALUES (?, ?, ?, ?, ?, ?, 'PREPARING', ?)
        """, (booking_id, booking_ref, cust_name, event_d, p[7], p[8], p[9]))

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
            inv_ref = f"INV-{b_id:04d}"
            cur.execute("""
                INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_customer_name, inv_event_date, inv_total_amount, inv_amount_paid, inv_status)
                VALUES (?, ?, ?, ?, ?, 0.0, 'Unpaid')
            """, (b_id, inv_ref, bk_row[0], bk_row[1], float(bk_row[2])))
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
        new_inv_status = "Paid" if remaining <= 0 else ("Partial" if new_paid > 0 else "Unpaid")

        # Get downpayment policy
        cur.execute("SELECT bi_min_downpayment_pct, bi_allow_zero_downpayment FROM business_info WHERE bi_id = 1")
        b_info = cur.fetchone()
        min_pct = float(b_info[0] if b_info else 30.0)
        allow_zero = bool(b_info[1] if b_info else False)
        req_down = round(v_total * min_pct / 100, 2)
        new_bk_status = "CONFIRMED" if (new_paid >= req_down or allow_zero or new_paid >= v_total) else "PENDING"

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
            inv_ref = f"INV-{b_id:04d}"
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
            status = "Paid" if rem <= 0 else ("Partial" if paid > 0 else "Unpaid")
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
        # (db_id, name, price_per_pax, min_pax, description)
        cur.execute("""
            UPDATE packages
            SET pkg_name = ?, pkg_price_per_pax = ?, pkg_min_pax = ?, pkg_description = ?
            WHERE pkg_id = ?
        """, (p[1], p[2], p[3], p[4], p[0]))

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

    elif proc == "sp_update_booking_status":
        # (booking_id, new_status)
        cur.execute("UPDATE bookings SET bk_status = ? WHERE bk_id = ?", (p[1], p[0]))

    elif proc == "sp_delete_booking":
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
    """Close active database connections."""
    global _sqlite_conn, _pg_conn
    with _db_lock:
        if _sqlite_conn is not None:
            try:
                _sqlite_conn.close()
            except Exception:
                pass
            _sqlite_conn = None
        if _pg_conn is not None:
            try:
                _pg_conn.close()
            except Exception:
                pass
            _pg_conn = None
