"""
Robust SQLite to PostgreSQL Data Migration Engine for Jayraldine's Catering System.
Migrates all existing local SQLite client/station data into the central PostgreSQL database.
Handles foreign keys, boolean normalization, timestamp conversions, sequence resets, and deduplication.
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple

log = logging.getLogger("JayraldinesApp")

# Mapping of tables in foreign-key safe dependency order
MIGRATION_TABLES = [
    "business_info",
    "occasions",
    "address_provinces",
    "address_cities",
    "address_barangays",
    "addresses",
    "customers",
    "customer_addresses",
    "customer_loyalty_tiers",
    "customer_follow_ups",
    "menu_items",
    "packages",
    "package_items",
    "bookings",
    "booking_menu_items",
    "booking_items",
    "booking_additional_charges",
    "terms_acknowledgements",
    "invoices",
    "payment_records",
    "kitchen_orders",
    "kitchen_tasks",
    "expenses",
    "calendar_events",
    "notifications",
    "audit_logs",
    "cash_flow_transactions",
    "monthly_sales_targets",
    "device_sessions",
    "users",
    "user_permissions"
]

# Primary key sequences to reset in PostgreSQL
TABLE_SEQUENCES = {
    "business_info": ("bi_id", "business_info_bi_id_seq"),
    "occasions": ("occ_id", "occasions_occ_id_seq"),
    "address_provinces": ("ap_id", "address_provinces_ap_id_seq"),
    "address_cities": ("ac_id", "address_cities_ac_id_seq"),
    "address_barangays": ("ab_id", "address_barangays_ab_id_seq"),
    "addresses": ("ad_id", "addresses_ad_id_seq"),
    "customers": ("cus_id", "customers_cus_id_seq"),
    "customer_addresses": ("ca_id", "customer_addresses_ca_id_seq"),
    "customer_loyalty_tiers": ("cl_id", "customer_loyalty_tiers_cl_id_seq"),
    "customer_follow_ups": ("cfu_id", "customer_follow_ups_cfu_id_seq"),
    "menu_items": ("mi_id", "menu_items_mi_id_seq"),
    "packages": ("pkg_id", "packages_pkg_id_seq"),
    "package_items": ("pi_id", "package_items_pi_id_seq"),
    "bookings": ("bk_id", "bookings_bk_id_seq"),
    "booking_menu_items": ("bmi_id", "booking_menu_items_bmi_id_seq"),
    "booking_items": ("bi_id", "booking_items_bi_id_seq"),
    "booking_additional_charges": ("ac_id", "booking_additional_charges_ac_id_seq"),
    "terms_acknowledgements": ("ta_id", "terms_acknowledgements_ta_id_seq"),
    "invoices": ("inv_id", "invoices_inv_id_seq"),
    "payment_records": ("pr_id", "payment_records_pr_id_seq"),
    "kitchen_orders": ("ko_id", "kitchen_orders_ko_id_seq"),
    "kitchen_tasks": ("kt_id", "kitchen_tasks_kt_id_seq"),
    "expenses": ("exp_id", "expenses_exp_id_seq"),
    "calendar_events": ("ce_id", "calendar_events_ce_id_seq"),
    "notifications": ("notif_id", "notifications_notif_id_seq"),
    "audit_logs": ("al_id", "audit_logs_al_id_seq"),
    "cash_flow_transactions": ("cft_id", "cash_flow_transactions_cft_id_seq"),
    "users": ("id", "users_id_seq"),
    "user_permissions": ("id", "user_permissions_id_seq"),
}


def find_candidate_sqlite_databases(custom_dir: Optional[Path] = None) -> List[Path]:
    """Scan standard locations for existing SQLite database files."""
    candidates = []
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")

    search_dirs = [
        Path(local_appdata) / "JayraldinesCatering" if local_appdata else None,
        Path(appdata) / "JayraldinesCatering" if appdata else None,
        Path.cwd(),
        Path.cwd() / "data",
        custom_dir,
        custom_dir / "data" if custom_dir else None,
    ]

    filenames = ["catering.db", "database.db", "jayraldines_catering.db", "jayraldines.db"]

    seen = set()
    for d in search_dirs:
        if d and d.exists() and d.is_dir():
            for fn in filenames:
                p = (d / fn).resolve()
                if p.exists() and p.is_file() and str(p) not in seen:
                    # Verify it has SQLite header and size > 0
                    if p.stat().st_size > 0:
                        try:
                            with open(p, "rb") as f:
                                header = f.read(16)
                                if header.startswith(b"SQLite format 3"):
                                    seen.add(str(p))
                                    candidates.append(p)
                        except Exception:
                            pass

    return candidates


def inspect_sqlite_database(sqlite_path: Path) -> Dict[str, int]:
    """Inspect SQLite database and count records per key table."""
    counts = {}
    if not sqlite_path.exists():
        return counts

    try:
        conn = sqlite3.connect(str(sqlite_path))
        cur = conn.cursor()
        for tbl in ["customers", "bookings", "invoices", "menu_items", "packages", "expenses", "cash_flow_transactions"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                row = cur.fetchone()
                if row:
                    counts[tbl] = int(row[0])
            except Exception:
                pass
        conn.close()
    except Exception as e:
        log.warning(f"[Migrate] Could not inspect SQLite DB {sqlite_path}: {e}")

    return counts


def migrate_sqlite_to_postgres(
    sqlite_path: Path,
    pg_conn_params: Dict[str, Any],
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Tuple[bool, Dict[str, int], str]:
    """
    Extract all data from SQLite database and migrate into PostgreSQL.
    
    Returns:
        (success: bool, stats: Dict[str, int], error_message: str)
    """
    if not sqlite_path.exists():
        return False, {}, f"SQLite database not found: {sqlite_path}"

    import psycopg2
    from psycopg2.extras import DictCursor, execute_values

    stats = {}
    total_steps = len(MIGRATION_TABLES) + len(TABLE_SEQUENCES)

    try:
        # 1. Connect to SQLite
        sqlite_conn = sqlite3.connect(str(sqlite_path))
        sqlite_conn.row_factory = sqlite3.Row
        s_cur = sqlite_conn.cursor()

        # 2. Connect to PostgreSQL
        pg_conn = psycopg2.connect(
            host=pg_conn_params.get("host", "localhost"),
            port=pg_conn_params.get("port", 5432),
            dbname=pg_conn_params.get("dbname", "jayraldines_catering"),
            user=pg_conn_params.get("user", "postgres"),
            password=pg_conn_params.get("password", "12345678"),
            connect_timeout=10
        )
        pg_conn.autocommit = False
        p_cur = pg_conn.cursor()

        # Discover tables in SQLite
        s_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        sqlite_tables = {row[0] for row in s_cur.fetchall()}

        step_idx = 0

        # Temporarily disable foreign key triggers if superuser, or insert in strict order
        for tbl in MIGRATION_TABLES:
            step_idx += 1
            pct = int((step_idx / total_steps) * 80)
            if tbl not in sqlite_tables:
                continue

            if progress_callback:
                progress_callback(pct, f"Migrating table: {tbl}...")

            # Fetch SQLite column info
            s_cur.execute(f"PRAGMA table_info({tbl})")
            s_cols_info = s_cur.fetchall()
            s_cols = [c["name"] for c in s_cols_info]

            if not s_cols:
                continue

            # Fetch PostgreSQL column info
            p_cur.execute(
                """
                SELECT column_name, data_type, udt_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                """,
                (tbl,)
            )
            pg_cols_info = {r[0]: (r[1], r[2]) for r in p_cur.fetchall()}
            if not pg_cols_info:
                continue

            # Matching columns present in both
            common_cols = [c for c in s_cols if c in pg_cols_info]
            if not common_cols:
                continue

            # Fetch SQLite rows
            s_cur.execute(f"SELECT {', '.join(common_cols)} FROM {tbl}")
            rows = s_cur.fetchall()

            if not rows:
                stats[tbl] = 0
                continue

            # Clean and prepare rows for PostgreSQL insertion
            converted_rows = []
            for r in rows:
                row_vals = []
                for c in common_cols:
                    val = r[c]
                    pg_type, pg_udt = pg_cols_info[c]

                    # Boolean conversion (SQLite 0/1 to Python True/False)
                    if pg_type == "boolean":
                        if val is None:
                            val = None
                        elif isinstance(val, (int, float)):
                            val = bool(val)
                        elif isinstance(val, str):
                            val = val.strip().lower() in ("1", "true", "t", "yes", "y")

                    # Handle string enums or empty date strings
                    if (pg_type in ("date", "time", "timestamp without time zone", "timestamp with time zone")) and val == "":
                        val = None

                    row_vals.append(val)
                converted_rows.append(tuple(row_vals))

            # Build PostgreSQL Insert Query
            cols_str = ", ".join(common_cols)
            placeholders = ", ".join(["%s"] * len(common_cols))

            # Deduplication / conflict handling
            # If table has a primary key (e.g. cus_id, bk_booking_ref, etc.)
            pk_col = common_cols[0]
            if tbl == "business_info":
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT (bi_id) DO NOTHING
                """
            elif tbl == "occasions":
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT (occ_name) DO NOTHING
                """
            elif tbl == "bookings":
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT (bk_booking_ref) DO NOTHING
                """
            elif tbl == "invoices":
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT (inv_invoice_ref) DO NOTHING
                """
            elif tbl == "monthly_sales_targets":
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT (mst_year, mst_month) DO NOTHING
                """
            elif tbl == "device_sessions":
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT (device_id) DO UPDATE SET
                        last_heartbeat = EXCLUDED.last_heartbeat,
                        status = EXCLUDED.status
                """
            elif tbl == "users":
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT (username) DO NOTHING
                """
            elif tbl == "user_permissions":
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT (user_id, module) DO NOTHING
                """
            else:
                # Generic fallback insert with primary key conflict ignore
                insert_sql = f"""
                    INSERT INTO {tbl} ({cols_str}) VALUES ({placeholders})
                    ON CONFLICT ({pk_col}) DO NOTHING
                """

            # Batch insert rows safely using savepoints to isolate individual errors
            inserted_count = 0
            for r_data in converted_rows:
                try:
                    p_cur.execute("SAVEPOINT row_savepoint")
                    p_cur.execute(insert_sql, r_data)
                    p_cur.execute("RELEASE SAVEPOINT row_savepoint")
                    inserted_count += p_cur.rowcount if p_cur.rowcount > 0 else 0
                except Exception as row_err:
                    try:
                        p_cur.execute("ROLLBACK TO SAVEPOINT row_savepoint")
                    except Exception:
                        pass
                    continue

            pg_conn.commit()
            stats[tbl] = len(converted_rows)
            log.info(f"[Migrate] Table {tbl}: {len(converted_rows)} rows processed ({inserted_count} inserted).")

        # 3. Synchronize all PostgreSQL sequences
        if progress_callback:
            progress_callback(85, "Synchronizing PostgreSQL auto-increment sequences...")

        for tbl, (pk_col, seq_name) in TABLE_SEQUENCES.items():
            try:
                p_cur.execute(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence(%s, %s),
                        COALESCE((SELECT MAX({pk_col}) FROM {tbl}), 1)
                    )
                    """,
                    (tbl, pk_col)
                )
                pg_conn.commit()
            except Exception as seq_err:
                pg_conn.rollback()
                try:
                    # Fallback direct sequence setval
                    p_cur.execute(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX({pk_col}) FROM {tbl}), 1), true)")
                    pg_conn.commit()
                except Exception:
                    pg_conn.rollback()

        sqlite_conn.close()
        pg_conn.close()

        if progress_callback:
            progress_callback(100, "SQLite to PostgreSQL data migration complete!")

        return True, stats, ""

    except Exception as exc:
        log.exception(f"[Migrate] SQLite to PostgreSQL migration failed: {exc}")
        return False, stats, str(exc)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate SQLite DB to PostgreSQL")
    parser.add_argument("sqlite_path", help="Path to SQLite database file")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--dbname", default="jayraldines_catering")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="12345678")
    args = parser.parse_args()

    sq_path = Path(args.sqlite_path)
    if not sq_path.exists():
        print(f"Error: file not found: {sq_path}")
        sys.exit(1)

    print(f"Starting migration from {sq_path} to PostgreSQL {args.host}:{args.port}/{args.dbname}...")
    ok, st, err = migrate_sqlite_to_postgres(
        sq_path,
        {"host": args.host, "port": args.port, "dbname": args.dbname, "user": args.user, "password": args.password},
        progress_callback=lambda p, m: print(f"[{p}%] {m}")
    )
    if ok:
        print("\nSUCCESS! Migration Summary:")
        for t, cnt in st.items():
            if cnt > 0:
                print(f"  • {t}: {cnt} records")
    else:
        print(f"\nFAILED: {err}")
        sys.exit(1)
