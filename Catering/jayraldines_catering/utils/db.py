"""
Database connection module.
All DB access goes through get_conn() / execute() / fetchall() / fetchone().
Never import psycopg2 directly outside this file.

Config is read from environment variables with safe fallbacks:
    DB_HOST     default: localhost
    DB_PORT     default: 5432
    DB_NAME     default: jayraldines_catering
    DB_USER     default: postgres
    DB_PASSWORD default: (empty)
"""
import os
import contextlib
from typing import Any, Optional

try:
    import psycopg2
    import psycopg2.extras
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False

_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "port":     int(os.environ.get("DB_PORT", "5432")),
    "dbname":   os.environ.get("DB_NAME",     "jayraldines_catering"),
    "user":     os.environ.get("DB_USER",     "postgres"),
    "password": os.environ.get("DB_PASSWORD", "12345678"),
}

_conn: Optional[Any] = None


def is_available() -> bool:
    return _PSYCOPG2_AVAILABLE


def connect() -> bool:
    """
    Open (or re-open) the database connection.
    Returns True on success, False on failure.
    Call once at application startup.
    """
    global _conn
    if not _PSYCOPG2_AVAILABLE:
        return False
    try:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
        _conn = psycopg2.connect(**_CONFIG)
        _conn.autocommit = False
        return True
    except Exception as exc:
        print(f"[DB] Connection failed: {exc}")
        _conn = None
        return False


def _ensure_connected() -> bool:
    global _conn
    if _conn is None:
        return connect()
    try:
        _conn.cursor().execute("SELECT 1")
        return True
    except Exception:
        return connect()


@contextlib.contextmanager
def transaction():
    """
    Context manager for an explicit transaction block.
    Commits on clean exit, rolls back on exception.
    Usage:
        with db.transaction():
            db.execute(...)
    """
    if not _ensure_connected():
        raise RuntimeError("No database connection")
    try:
        yield
        _conn.commit()
    except Exception:
        _conn.rollback()
        raise


def execute(sql: str, params: tuple = ()) -> None:
    """Run a non-returning statement inside an auto-transaction."""
    if not _ensure_connected():
        raise RuntimeError("No database connection")
    with _conn.cursor() as cur:
        cur.execute(sql, params)
    _conn.commit()


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT and return list of dicts (column-name keyed)."""
    if not _ensure_connected():
        return []
    with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def fetchone(sql: str, params: tuple = ()) -> Optional[dict]:
    """Run a SELECT and return the first row as a dict, or None."""
    if not _ensure_connected():
        return None
    with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def callproc(func: str, params: tuple = ()) -> list[dict]:
    """
    Call a PostgreSQL function that returns a TABLE / SETOF and return rows.
    Uses SELECT func(...) syntax which works for both scalar and set-returning.
    """
    if not _ensure_connected():
        return []
    placeholders = ", ".join(["%s"] * len(params))
    sql = f"SELECT * FROM {func}({placeholders})"
    return fetchall(sql, params)


def close() -> None:
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None
