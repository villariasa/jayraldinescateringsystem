"""
utils/client_sync.py
--------------------
Desktop Client Workstation Data Sync & Proxy for Jayraldine's Catering.

Architecture:
  - SERVER PC (192.168.1.32): Runs the Sync Hub on port 8000. Holds the master SQLite DB.
  - CLIENT WORKSTATION: All reads and writes are proxied through the server.

On startup:
  - Pulls full DB snapshot from server via GET /api/db/snapshot.
  - Upserts all rows into local SQLite as a working cache.

During operation:
  - All db.execute() calls (INSERT/UPDATE/DELETE) on client are proxied to the server
    via POST /api/db/write, then also applied locally so the UI stays responsive.
  - All db.fetchall()/fetchone() calls are first read from server via POST /api/db/query,
    falling back to local cache if server is unreachable.
  - A background thread re-pulls the snapshot every 5 minutes to stay in sync.
"""

import json
import re
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import utils.db as db
from utils.db_config import get_db_config
from utils.logger import get_logger

log = get_logger()

# ─────────────────────────────────────────────────────────────
# Tables in upsert order (parents before children)
# ─────────────────────────────────────────────────────────────
_SNAPSHOT_TABLES = [
    # System / Settings / Addresses
    "business_info",
    "app_settings",
    "address_provinces",
    "address_cities",
    "address_barangays",
    "addresses",
    "occasions",
    "users",
    "user_permissions",
    # Menu & Packages
    "menu_categories",
    "menu_items",
    "packages",
    "package_items",
    # Customers & Follow-ups
    "customer_loyalty_tiers",
    "customers",
    "customer_addresses",
    "customer_follow_ups",
    # Bookings, Items & Charges
    "bookings",
    "booking_menu_items",
    "booking_items",
    "booking_additional_charges",
    "terms_acknowledgements",
    # Invoices & Billing
    "invoices",
    "payment_records",
    # Kitchen Operations
    "kitchen_orders",
    "kitchen_tasks",
    # Inventory & Calendar
    "inventory",
    "calendar_events",
    # Expenses & Cash Flow
    "expenses",
    "cash_flow_transactions",
    # Notifications & Audits
    "notifications",
    "audit_logs",
]

_TABLE_PKS = {
    "business_info":               "bi_id",
    "app_settings":                "setting_key",
    "address_provinces":           "ap_id",
    "address_cities":              "ac_id",
    "address_barangays":           "ab_id",
    "addresses":                   "ad_id",
    "occasions":                   "occ_id",
    "users":                       "id",
    "user_permissions":            "id",
    "menu_categories":             "mc_id",
    "menu_items":                  "mi_id",
    "packages":                    "pkg_id",
    "package_items":               "pi_id",
    "customer_loyalty_tiers":      "cl_id",
    "customers":                   "cus_id",
    "customer_addresses":          "ca_id",
    "customer_follow_ups":         "cfu_id",
    "bookings":                    "bk_id",
    "booking_menu_items":          "bmi_id",
    "booking_items":               "bi_id",
    "booking_additional_charges":  "ac_id",
    "terms_acknowledgements":      "ta_id",
    "invoices":                    "inv_id",
    "payment_records":             "pr_id",
    "kitchen_orders":              "ko_id",
    "kitchen_tasks":               "kt_id",
    "inventory":                   "inv_id",
    "calendar_events":             "ce_id",
    "expenses":                    "exp_id",
    "cash_flow_transactions":      "cft_id",
    "notifications":               "notif_id",
    "audit_logs":                  "al_id",
}

# ─────────────────────────────────────────────────────────────
# Server URL helpers
# ─────────────────────────────────────────────────────────────

def _clean_host(raw: str) -> str:
    raw = str(raw).strip()
    raw = re.sub(r'^https?://', '', raw)
    raw = re.sub(r':\d+$', '', raw)
    return raw.rstrip('/')


def get_server_url() -> Optional[str]:
    """Return the configured sync server base URL, or None if not in client mode."""
    cfg = get_db_config()
    if cfg.get("sync_role") != "client":
        return None
    url = cfg.get("sync_server_url", "").strip()
    if url:
        return url.rstrip("/")
    host = _clean_host(str(cfg.get("host", "192.168.1.32")))
    port = int(cfg.get("port", 8000))
    return f"http://{host}:{port}"


def is_client_mode() -> bool:
    """Return True if this workstation is configured as a client using SQLite LAN sync (not direct PostgreSQL)."""
    cfg = get_db_config()
    if str(cfg.get("engine", "sqlite")).lower() == "postgres":
        return False
    return cfg.get("sync_role") == "client"


# ─────────────────────────────────────────────────────────────
# Proxy health tracking - db.execute()/fetchall()/fetchone() silently fall
# back to the local SQLite cache whenever a proxy call fails (by design, so
# the UI never hard-blocks on a flaky network), but that meant callers had
# no way to tell "0 results" apart from "couldn't reach the server, showing
# stale/incomplete local data". This tracks the outcome of the MOST RECENT
# proxy call so screens that need to know (e.g. Connected Devices) can warn
# the user instead of silently showing a misleadingly small local view.
# ─────────────────────────────────────────────────────────────

_last_proxy_ok: bool = True
_last_proxy_error: Optional[str] = None


def _mark_proxy_result(ok: bool, error: Optional[str] = None) -> None:
    global _last_proxy_ok, _last_proxy_error
    _last_proxy_ok = ok
    _last_proxy_error = error


def get_last_proxy_status() -> Tuple[bool, Optional[str]]:
    """(ok, error_message) for the most recent client-mode proxy write/read.
    Meaningless when not in client mode (always reports ok=True)."""
    if not is_client_mode():
        return True, None
    return _last_proxy_ok, _last_proxy_error


# ─────────────────────────────────────────────────────────────
# Internal HTTP helpers
# ─────────────────────────────────────────────────────────────

def _post_json(url: str, payload: dict, timeout: float = 3.0) -> Optional[dict]:
    """POST JSON to url, return parsed response dict or None on error."""
    try:
        body = json.dumps(payload, default=str).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "JayraldinesClientProxy/1.0",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        log.debug(f"[ClientSync] POST {url} failed: {exc}")
        return None


def _get_json(url: str, timeout: float = 3.0) -> Optional[dict]:
    """GET url, return parsed response dict or None on error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JayraldinesClientProxy/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        log.debug(f"[ClientSync] GET {url} failed: {exc}")
        return None


# ─────────────────────────────────────────────────────────────
# Write proxy — sends writes to server AND applies locally
# ─────────────────────────────────────────────────────────────

def proxy_write(sql: str, params: tuple = (), server_url: Optional[str] = None) -> bool:
    """
    Send a write SQL statement to the server.
    Returns True if server accepted it, False if unreachable.
    The local write is done separately by db.execute() itself.
    """
    if server_url is None:
        server_url = get_server_url()
    if not server_url:
        return False

    params_list = [str(p) if p is not None else None for p in (params or [])]
    result = _post_json(
        f"{server_url}/api/db/write",
        {"sql": sql, "params": params_list},
        timeout=3.0
    )
    if result and result.get("ok"):
        _mark_proxy_result(True)
        return True
    log.warning(f"[ClientSync] Write proxy failed for: {sql[:80]} | result={result}")
    _mark_proxy_result(False, f"Write failed: {sql[:60]}")
    return False


def proxy_callproc(proc: str, in_params: tuple = (), out_names: Optional[list] = None,
                    void: bool = True, server_url: Optional[str] = None) -> Optional[Dict]:
    """
    Run a stored-procedure emulation (sp_create_booking, sp_delete_booking,
    sp_pay_invoice, etc.) on the SERVER's own DB via /api/db/callproc.

    db.execute()'s write-through proxy only ever covered raw SQL statements -
    callproc_void()/callproc_out() (used by nearly every booking/payment
    mutation) had no proxy path at all, so on a client workstation those
    calls only ever wrote to that machine's own local SQLite cache and never
    reached the server. This is the missing counterpart to proxy_write().

    Returns {"ok": True} (void) or {"ok": True, "result": {...}} (out) on
    success, None if the server is unreachable or rejected the call (caller
    should treat that as non-fatal, same as proxy_write - the local
    emulation still runs so the UI stays responsive either way).
    """
    if server_url is None:
        server_url = get_server_url()
    if not server_url:
        return None

    params_list = [str(p) if p is not None else None for p in (in_params or [])]
    result = _post_json(
        f"{server_url}/api/db/callproc",
        {"proc": proc, "in_params": params_list, "out_names": out_names, "void": void},
        timeout=5.0
    )
    if result and result.get("ok"):
        _mark_proxy_result(True)
        return result
    log.warning(f"[ClientSync] callproc proxy failed for: {proc} | result={result}")
    _mark_proxy_result(False, f"callproc failed: {proc}")
    return None


# ─────────────────────────────────────────────────────────────
# Read proxy — fetches rows from server, falls back to local
# ─────────────────────────────────────────────────────────────

def proxy_fetchall(sql: str, params: tuple = (), server_url: Optional[str] = None) -> Optional[List[Dict]]:
    """
    Execute a SELECT on the server and return rows.
    Returns None if server is unreachable (caller should fall back to local).
    """
    if server_url is None:
        server_url = get_server_url()
    if not server_url:
        return None

    params_list = [str(p) if p is not None else None for p in (params or [])]
    result = _post_json(
        f"{server_url}/api/db/query",
        {"sql": sql, "params": params_list, "one": False},
        timeout=3.0
    )
    if result is None:
        _mark_proxy_result(False, "Server unreachable")
        return None
    if "error" in result:
        log.warning(f"[ClientSync] Query error from server: {result['error']} | SQL: {sql[:80]}")
        _mark_proxy_result(False, f"Query error: {result['error']}")
        return None
    _mark_proxy_result(True)
    return result.get("rows", [])


def proxy_fetchone(sql: str, params: tuple = (), server_url: Optional[str] = None) -> Optional[Dict]:
    """
    Execute a SELECT returning one row on the server.
    Returns None if server is unreachable (caller should fall back to local).
    """
    if server_url is None:
        server_url = get_server_url()
    if not server_url:
        return None

    params_list = [str(p) if p is not None else None for p in (params or [])]
    result = _post_json(
        f"{server_url}/api/db/query",
        {"sql": sql, "params": params_list, "one": True},
        timeout=3.0
    )
    if result is None:
        _mark_proxy_result(False, "Server unreachable")
        return None
    if "error" in result:
        log.warning(f"[ClientSync] Query error from server: {result['error']} | SQL: {sql[:80]}")
        _mark_proxy_result(False, f"Query error: {result['error']}")
        return None
    _mark_proxy_result(True)
    return result.get("row")


# ─────────────────────────────────────────────────────────────
# Full snapshot pull (startup sync)
# ─────────────────────────────────────────────────────────────

def _upsert_rows(table: str, rows: List[Dict]) -> int:
    """INSERT OR REPLACE all rows into a local table and reconcile deletions from the server."""
    if not db._sqlite_conn:
        return 0
    cur = db._sqlite_conn.cursor()
    pk = _TABLE_PKS.get(table)

    if not rows:
        # Server has 0 rows for this table - remove all local rows
        try:
            cur.execute(f"DELETE FROM {table}")
            db._sqlite_conn.commit()
        except Exception as e:
            log.debug(f"[ClientSync] Clear local table {table} failed: {e}")
        return 0

    server_ids = set()
    upserted = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if pk and pk in row and row[pk] is not None:
            try:
                row[pk] = int(row[pk])
            except (ValueError, TypeError):
                pass
            server_ids.add(row[pk])

        cols = list(row.keys())
        col_names = ", ".join(cols)
        placeholders = ", ".join(["?" for _ in cols])
        values = []
        for k, v in row.items():
            if isinstance(v, str):
                if k == "password_hash":
                    pass  # Preserve password hashes intact
                elif v.lower() in ("none", "null"):
                    v = None
                else:
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
            values.append(v)

        try:
            cur.execute(
                f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})",
                tuple(values)
            )
            upserted += 1
        except Exception as e:
            log.debug(f"[ClientSync] Upsert row in {table} failed: {e}")

    # Reconcile deletions: remove any local rows that no longer exist on server
    if pk and server_ids:
        try:
            cur.execute(f"SELECT {pk} FROM {table}")
            local_ids = {r[0] for r in cur.fetchall()}
            stale_ids = local_ids - server_ids
            if stale_ids:
                stale_list = list(stale_ids)
                for i in range(0, len(stale_list), 500):
                    chunk = stale_list[i:i + 500]
                    q_marks = ", ".join(["?" for _ in chunk])
                    cur.execute(f"DELETE FROM {table} WHERE {pk} IN ({q_marks})", tuple(chunk))
                log.info(f"[ClientSync] Purged {len(stale_ids)} deleted row(s) from {table}")
        except Exception as de:
            log.debug(f"[ClientSync] Stale row deletion in {table} failed: {de}")

    try:
        db._sqlite_conn.commit()
    except Exception:
        pass

    return upserted


def pull_server_snapshot(
    server_url: Optional[str] = None,
    timeout: int = 20,
    on_progress: Optional[Callable[[str], None]] = None
) -> dict:
    """
    Pull a full DB snapshot from the server and upsert into local SQLite.
    Covers ALL data: users, menu, packages, customers, bookings, invoices,
    expenses, cashflow, occasions, address data, and business info.
    """
    if server_url is None:
        server_url = get_server_url()
    if not server_url:
        return {"success": False, "message": "Not in client mode or no server URL.", "synced": {}}

    def _prog(msg: str):
        log.info(msg)
        if on_progress:
            try:
                on_progress(msg)
            except Exception:
                pass

    _prog(f"[ClientSync] Pulling snapshot from {server_url} ...")

    snapshot = _get_json(f"{server_url}/api/db/snapshot", timeout=timeout)
    if snapshot is None:
        # Fallback: Pull full SQLite database file directly from server HTTP static route
        try:
            _prog(f"[ClientSync] Pulling master database directly from {server_url}/catering.db ...")
            db_url = f"{server_url}/catering.db"
            req = urllib.request.Request(db_url, headers={"User-Agent": "JayraldinesClientProxy/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            if data and len(data) > 10000:
                local_path = db.get_sqlite_db_path()
                _prog(f"[ClientSync] Applying server database file to {local_path} ...")
                db.close()
                with open(local_path, "wb") as f:
                    f.write(data)
                db.connect_sqlite()

                synced_counts = {}
                for t in ["bookings", "customers", "menu_items", "packages", "expenses", "invoices"]:
                    try:
                        row = db.fetchone(f"SELECT count(*) as c FROM {t}")
                        synced_counts[t] = int(row["c"]) if row else 0
                    except Exception:
                        pass
                total = sum(synced_counts.values())
                msg = f"[ClientSync] Master database replicated ({total} total records) from {server_url}"
                log.info(msg)
                try:
                    from utils.data_cache import DataCache
                    DataCache.clear()
                except Exception:
                    pass
                return {"success": True, "message": msg, "synced": synced_counts}
        except Exception as fe:
            log.warning(f"[ClientSync] Direct DB download fallback failed: {fe}")

        msg = f"[ClientSync] Could not reach server at {server_url}"
        log.warning(msg)
        return {"success": False, "message": msg, "synced": {}}

    meta = snapshot.get("_meta", {})
    _prog(f"[ClientSync] Connected to server {meta.get('server_ip', server_url)} @ {meta.get('timestamp','')}")

    synced_counts = {}
    errors = []

    conn = db.get_connection()
    if conn is None:
        return {"success": False, "message": "No local DB connection.", "synced": {}}

    if db._sqlite_conn:
        try:
            db._sqlite_conn.execute("PRAGMA foreign_keys = OFF;")
        except Exception:
            pass

    for table in _SNAPSHOT_TABLES:
        if table not in snapshot:
            continue
        rows = snapshot.get(table)
        if rows is None:
            continue
        try:
            count = _upsert_rows(table, rows)
            synced_counts[table] = count
            if count:
                _prog(f"[ClientSync]   {table}: {count} rows")
        except Exception as te:
            log.warning(f"[ClientSync] Table {table} sync error: {te}")
            errors.append(f"{table}: {te}")
            synced_counts[table] = 0

    if db._sqlite_conn:
        try:
            db._sqlite_conn.execute("PRAGMA foreign_keys = ON;")
        except Exception:
            pass

    # Clear memory cache so all UI views (dashboard, bookings, etc.) update immediately
    try:
        from utils.data_cache import DataCache
        DataCache.clear()
    except Exception:
        pass

    total = sum(synced_counts.values())
    msg = (
        f"[ClientSync] Snapshot sync complete — {total} rows from {server_url}"
        if not errors else
        f"[ClientSync] Sync done with {len(errors)} error(s). {total} rows synced."
    )
    log.info(msg)
    return {"success": True, "message": msg, "synced": synced_counts}


# ─────────────────────────────────────────────────────────────
# Background threads
# ─────────────────────────────────────────────────────────────

def pull_server_snapshot_background(
    server_url: Optional[str] = None,
    on_done: Optional[Callable[[dict], None]] = None,
    on_progress: Optional[Callable[[str], None]] = None
) -> threading.Thread:
    """Run pull_server_snapshot in a background daemon thread."""
    def _run():
        result = pull_server_snapshot(server_url=server_url, on_progress=on_progress)
        if on_done:
            try:
                on_done(result)
            except Exception as e:
                log.warning(f"[ClientSync] on_done callback error: {e}")

    t = threading.Thread(target=_run, daemon=True, name="ClientSnapshotSync")
    t.start()
    return t


def start_periodic_sync(
    interval_seconds: int = 300,
    server_url: Optional[str] = None
) -> threading.Thread:
    """
    Start a background thread that periodically pulls from the server.
    Default interval: 5 minutes.
    """
    def _loop():
        while True:
            time.sleep(interval_seconds)
            try:
                if is_client_mode():
                    pull_server_snapshot(server_url=server_url)
            except Exception as exc:
                log.warning(f"[ClientSync] Periodic sync error: {exc}")

    t = threading.Thread(target=_loop, daemon=True, name="ClientPeriodicSync")
    t.start()
    log.info(f"[ClientSync] Periodic sync started — every {interval_seconds}s")
    return t


# ─────────────────────────────────────────────────────────────
# Real-Time Version Watcher (Option 1: Micro-Heartbeat & UI Refresh)
# ─────────────────────────────────────────────────────────────

_known_server_version: int = 0
_watcher_thread: Optional[threading.Thread] = None
_watcher_stop_event = threading.Event()


def start_realtime_version_watcher(
    poll_interval: float = 1.5,
    server_url: Optional[str] = None
) -> Optional[threading.Thread]:
    """
    Start an ultra-lightweight real-time version watcher (Option 1).
    Polls GET /api/sync/version every `poll_interval` seconds.
    When server version increments (meaning any PC/laptop/tablet made a change),
    it pulls the latest database snapshot and notifies the UI via Qt signals.
    """
    global _watcher_thread, _known_server_version
    if _watcher_thread is not None and _watcher_thread.is_alive():
        return _watcher_thread

    def _watcher_loop():
        global _known_server_version
        target_url = server_url or get_server_url()
        log.info(f"[ClientSync] Real-time version watcher started (poll={poll_interval}s, target={target_url})")

        # Initial baseline query
        try:
            init_res = _get_json(f"{target_url}/api/sync/version", timeout=4)
            if init_res and "version" in init_res:
                _known_server_version = int(init_res["version"])
        except Exception:
            pass

        while not _watcher_stop_event.is_set():
            time.sleep(poll_interval)
            if not is_client_mode():
                continue

            current_srv = server_url or get_server_url()
            if not current_srv:
                continue

            try:
                res = _get_json(f"{current_srv}/api/sync/version", timeout=3)
                if not res or "version" not in res:
                    continue

                server_ver = int(res["version"])
                if _known_server_version == 0:
                    _known_server_version = server_ver
                    continue

                if server_ver > _known_server_version:
                    log.info(f"[ClientSync] Server data version changed ({_known_server_version} -> {server_ver}). Syncing & updating UI...")
                    _known_server_version = server_ver

                    # Pull fresh snapshot from server
                    pull_server_snapshot(server_url=current_srv, timeout=8)

                    # Invalidate DataCache so UI renders fresh data immediately
                    try:
                        from utils.data_cache import DataCache
                        DataCache.clear()
                    except Exception:
                        pass

                    # Trigger real-time UI refresh on main Qt thread
                    try:
                        from PySide6.QtCore import QTimer
                        from utils.signals import app_events

                        def _emit_ui_events():
                            try:
                                # Must mirror db_sync_server.py's bump_db_version()
                                # emit set exactly - this only had 5 of the 12 real
                                # signals, so e.g. a booking/expense/cash-flow
                                # transaction created on ANOTHER machine never
                                # actively refreshed Orders/Expenses/Cash Flow here
                                # (booking_saved/expense_saved/cash_flow_saved were
                                # simply never emitted), even though the DB write
                                # itself synced correctly - it just silently waited
                                # for the next manual page visit instead.
                                ev = app_events()
                                ev.data_changed.emit()
                                ev.booking_saved.emit()
                                ev.booking_created.emit()
                                ev.booking_updated.emit()
                                ev.invoice_saved.emit()
                                ev.invoice_created.emit()
                                ev.payment_recorded.emit()
                                ev.kitchen_updated.emit()
                                ev.customer_saved.emit()
                                ev.menu_saved.emit()
                                ev.expense_saved.emit()
                                ev.cash_flow_saved.emit()
                            except Exception as ue:
                                log.debug(f"[ClientSync] UI signal emit note: {ue}")

                        QTimer.singleShot(0, _emit_ui_events)
                    except Exception as sig_err:
                        log.debug(f"[ClientSync] Signal dispatch note: {sig_err}")

            except Exception as loop_err:
                log.debug(f"[ClientSync] Version poll error: {loop_err}")

    _watcher_thread = threading.Thread(target=_watcher_loop, daemon=True, name="RealtimeVersionWatcher")
    _watcher_thread.start()
    return _watcher_thread
