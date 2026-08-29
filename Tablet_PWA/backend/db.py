"""
SQLite connection layer for the PWA backend — one shared connection guarded
by a lock, same pattern the original Tablet app used (utils/db.py), so
concurrent requests from multiple kiosk tablets hitting this one backend
don't corrupt each other's writes.
"""
import sqlite3
import threading
from typing import Any, Optional

from schema import DATA_DIR, DB_PATH, init_db

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None


def connect() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is not None:
            return _conn
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
        # NOT WAL: this app runs as a single process serializing all access
        # through _lock, so WAL's concurrent-reader benefit doesn't apply —
        # and WAL needs shared-memory mmap that's unreliable on network
        # filesystems (CIFS/SMB/NFS), which this project directory may be
        # deployed on. Default rollback journal works everywhere.
        init_db(_conn)
        return _conn


def execute(sql: str, params: tuple = ()) -> int:
    with _lock:
        conn = connect()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        rowid = cur.lastrowid
        cur.close()
        return rowid


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    with _lock:
        conn = connect()
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows


def fetchone(sql: str, params: tuple = ()) -> Optional[dict]:
    with _lock:
        conn = connect()
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None


def compute_invoice_status(total_amount: float, amount_paid: float) -> str:
    """Kept identical to the PC app / original Tablet app's status derivation
    so a status computed here never disagrees with either of those."""
    total_amount = total_amount or 0.0
    amount_paid = amount_paid or 0.0
    remaining = total_amount - amount_paid
    if total_amount > 0 and remaining <= 0.0:
        return "Paid"
    if amount_paid > 0:
        return "Partial"
    return "Unpaid"
