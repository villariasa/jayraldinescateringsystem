"""
Database connection module.
All DB access goes through get_conn() / execute() / fetchall() / fetchone() / callproc_out().
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
    if not _ensure_connected():
        raise RuntimeError("No database connection")
    try:
        yield
        _conn.commit()
    except Exception:
        _conn.rollback()
        raise


def execute(sql: str, params: tuple = ()) -> None:
    if not _ensure_connected():
        raise RuntimeError("No database connection")
    with _conn.cursor() as cur:
        cur.execute(sql, params)
    _conn.commit()


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    if not _ensure_connected():
        return []
    with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def fetchone(sql: str, params: tuple = ()) -> Optional[dict]:
    if not _ensure_connected():
        return None
    with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def callproc_out(proc: str, in_params: tuple = (), out_names: list = None) -> Optional[dict]:
    """
    Call a stored PROCEDURE that has OUT parameters using CALL.
    PostgreSQL returns OUT param values as a single result row.
    out_names: list of OUT parameter names in declaration order.
    Returns a dict keyed by out_names, or None on failure.
    """
    if not _ensure_connected():
        return None
    placeholders = ", ".join(["%s"] * len(in_params))
    if out_names:
        out_placeholders = ", ".join(["NULL"] * len(out_names))
        if in_params:
            sql = f"CALL {proc}({placeholders}, {out_placeholders})"
        else:
            sql = f"CALL {proc}({out_placeholders})"
    else:
        sql = f"CALL {proc}({placeholders})" if in_params else f"CALL {proc}()"
    try:
        with _conn.cursor() as cur:
            cur.execute(sql, in_params if in_params else ())
            row = cur.fetchone()
            _conn.commit()
            if row is None:
                return {}
            if out_names:
                return dict(zip(out_names, row))
            return {}
    except Exception as exc:
        _conn.rollback()
        print(f"[DB] callproc_out({proc}) failed: {exc}")
        return None


def callproc_void(proc: str, in_params: tuple = ()) -> bool:
    """
    Call a stored PROCEDURE that has no OUT parameters (VOID equivalent).
    Returns True on success, False on failure.
    """
    if not _ensure_connected():
        return False
    placeholders = ", ".join(["%s"] * len(in_params))
    sql = f"CALL {proc}({placeholders})" if in_params else f"CALL {proc}()"
    try:
        with _conn.cursor() as cur:
            cur.execute(sql, in_params if in_params else ())
        _conn.commit()
        return True
    except Exception as exc:
        _conn.rollback()
        print(f"[DB] callproc_void({proc}) failed: {exc}")
        return False


def callproc_cursor(proc: str, cursor_name: str = "ref_cursor") -> list[dict]:
    """
    Call a stored PROCEDURE that opens a REFCURSOR OUT parameter.
    Requires autocommit=False (default). Fetches all rows from the cursor.
    """
    if not _ensure_connected():
        return []
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"CALL {proc}(%s)", (cursor_name,))
            cur.execute(f'FETCH ALL FROM "{cursor_name}"')
            rows = [dict(r) for r in cur.fetchall()]
        _conn.commit()
        return rows
    except Exception as exc:
        try:
            _conn.rollback()
        except Exception:
            pass
        print(f"[DB] callproc_cursor({proc}) failed: {exc}")
        return []


def close() -> None:
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None
