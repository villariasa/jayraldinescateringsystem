"""
Tablet local SQLite connection layer.

Deliberately simpler than the PC app's utils/db.py — no Postgres fallback,
no stored-procedure emulation layer. Direct parameterized SQL only, since
this is a smaller, single-purpose, offline-first app.
"""
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from utils.logger import get_logger
from utils.sqlite_schema import init_sqlite_db, get_sqlite_db_path

log = get_logger()

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None
_db_path: Optional[Path] = None


def set_db_path(custom_path: Path) -> None:
    """Override the DB file location (used for testing)."""
    global _db_path, _conn
    close()
    _db_path = custom_path


def connect() -> bool:
    global _conn, _db_path
    with _lock:
        if _conn is not None:
            return True
        try:
            if _db_path is None:
                _db_path = get_sqlite_db_path()
            log.info(f"Connecting to Tablet SQLite database at: {_db_path}")
            _conn = sqlite3.connect(str(_db_path), check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA foreign_keys = ON")
            _conn.execute("PRAGMA journal_mode = WAL")
            init_sqlite_db(_conn)
            return True
        except Exception as exc:
            log.error(f"Tablet DB connection failed: {exc}")
            return False


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None


def _ensure() -> bool:
    if _conn is None:
        return connect()
    return True


def execute(sql: str, params: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE. Returns cursor.lastrowid."""
    with _lock:
        if not _ensure():
            raise RuntimeError("No tablet database connection")
        cur = _conn.cursor()
        cur.execute(sql, params)
        _conn.commit()
        rowid = cur.lastrowid
        cur.close()
        return rowid


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    with _lock:
        if not _ensure():
            return []
        cur = _conn.cursor()
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows


def fetchone(sql: str, params: tuple = ()) -> Optional[dict]:
    with _lock:
        if not _ensure():
            return None
        cur = _conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None


def compute_invoice_status(total_amount: float, amount_paid: float) -> str:
    """Single source of truth for Paid/Partial/Unpaid — kept identical to the
    PC app's utils/db.py:compute_invoice_status() so both sides can never
    disagree about a status derived from the same numbers."""
    total_amount = total_amount or 0.0
    amount_paid = amount_paid or 0.0
    remaining = total_amount - amount_paid
    if total_amount > 0 and remaining <= 0.0:
        return "Paid"
    if amount_paid > 0:
        return "Partial"
    return "Unpaid"
