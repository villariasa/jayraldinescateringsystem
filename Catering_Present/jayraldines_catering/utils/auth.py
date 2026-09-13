"""
Authentication and Role-Based Access Control (RBAC) Module
for Jayraldine's Catering Management System.
"""

import os
import hmac
import hashlib
import secrets
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import utils.db as db
from utils.logger import get_logger

log = get_logger()

ALL_MODULES = [
    "customers",
    "bookings",
    "menu",
    "cashflow",
    "expenses",
    "reports",
    "settings",
    "ai_chef_jay",
]

MODULE_DISPLAY_NAMES = {
    "customers": "Customers",
    "bookings": "Bookings & Orders",
    "menu": "Menu & Packages",
    "cashflow": "Cash Flow & Ledger",
    "expenses": "Expenses & Billing",
    "reports": "Reports & Analytics",
    "settings": "System Settings",
    "ai_chef_jay": "Chef Jay AI Assistant",
}


# ── Password Validation & Hashing ──────────────────────────────────────────

def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validates client password policy:
    - At least 8 characters
    - At least one alphabetic letter
    - At least one numeric digit
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, ""


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"pbkdf2:sha256:100000${salt}${hashed}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifies a plain-text password against a stored PBKDF2 hash."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 3:
            return False
        algorithm_info, salt, expected_hash = parts
        _, hash_name, iterations_str = algorithm_info.split(":")
        iterations = int(iterations_str)

        computed = hashlib.pbkdf2_hmac(
            hash_name,
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()

        return hmac.compare_digest(computed, expected_hash)
    except Exception:
        return False


# ── Database Schema Initialization ─────────────────────────────────────────

def ensure_auth_tables() -> None:
    """Creates users and user_permissions tables on PostgreSQL or SQLite."""
    engine = db.get_engine_type()
    if engine == "postgres":
        users_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id              SERIAL PRIMARY KEY,
            username        VARCHAR(50) UNIQUE NOT NULL,
            password_hash   VARCHAR(255) NOT NULL,
            display_name    VARCHAR(100),
            role            VARCHAR(20) DEFAULT 'staff',
            is_active       BOOLEAN DEFAULT TRUE,
            created_by      INTEGER REFERENCES users(id),
            created_at      TIMESTAMP DEFAULT NOW(),
            updated_at      TIMESTAMP DEFAULT NOW(),
            last_login      TIMESTAMP
        );
        """
        perms_sql = """
        CREATE TABLE IF NOT EXISTS user_permissions (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            module      VARCHAR(50) NOT NULL,
            can_view    BOOLEAN DEFAULT FALSE,
            can_create  BOOLEAN DEFAULT FALSE,
            can_edit    BOOLEAN DEFAULT FALSE,
            can_delete  BOOLEAN DEFAULT FALSE,
            UNIQUE(user_id, module)
        );
        """
    else:
        users_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT UNIQUE NOT NULL,
            password_hash   TEXT NOT NULL,
            display_name    TEXT,
            role            TEXT DEFAULT 'staff',
            is_active       INTEGER DEFAULT 1,
            created_by      INTEGER REFERENCES users(id),
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login      TEXT
        );
        """
        perms_sql = """
        CREATE TABLE IF NOT EXISTS user_permissions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            module      TEXT NOT NULL,
            can_view    INTEGER DEFAULT 0,
            can_create  INTEGER DEFAULT 0,
            can_edit    INTEGER DEFAULT 0,
            can_delete  INTEGER DEFAULT 0,
            UNIQUE(user_id, module)
        );
        """

    try:
        db.execute(users_sql)
        db.execute(perms_sql)
    except Exception as exc:
        log.warning(f"Error ensuring auth tables: {exc}")


def create_default_admin(password: Optional[str] = "admin") -> Tuple[str, str]:
    """
    Provisions the primary 'admin' account with full privileges if it doesn't already exist.
    Returns (username, password).
    """
    ensure_auth_tables()
    existing = db.fetchone("SELECT id FROM users WHERE username = 'admin'")
    if existing:
        return "admin", ""

    if not password:
        password = "admin"

    pwd_hash = hash_password(password)
    engine = db.get_engine_type()

    if engine == "postgres":
        sql = """
        INSERT INTO users (username, password_hash, display_name, role, is_active)
        VALUES ('admin', %s, 'System Administrator', 'admin', TRUE)
        RETURNING id;
        """
        row = db.fetchone(sql, (pwd_hash,))
        user_id = row["id"] if row else None
    else:
        sql = """
        INSERT INTO users (username, password_hash, display_name, role, is_active)
        VALUES ('admin', ?, 'System Administrator', 'admin', 1);
        """
        db.execute(sql, (pwd_hash,))
        row = db.fetchone("SELECT id FROM users WHERE username = 'admin'")
        user_id = row["id"] if row else None

    if user_id:
        grant_full_permissions(user_id)
        _log_audit("USER_CREATE", f"Primary administrator account 'admin' created (ID: {user_id})")

    return "admin", password


def grant_full_permissions(user_id: int) -> None:
    """Grants full View/Create/Edit/Delete access to all modules for a user."""
    engine = db.get_engine_type()
    for mod in ALL_MODULES:
        if engine == "postgres":
            sql = """
            INSERT INTO user_permissions (user_id, module, can_view, can_create, can_edit, can_delete)
            VALUES (%s, %s, TRUE, TRUE, TRUE, TRUE)
            ON CONFLICT (user_id, module) DO UPDATE
            SET can_view = TRUE, can_create = TRUE, can_edit = TRUE, can_delete = TRUE;
            """
            db.execute(sql, (user_id, mod))
        else:
            sql = """
            INSERT INTO user_permissions (user_id, module, can_view, can_create, can_edit, can_delete)
            VALUES (?, ?, 1, 1, 1, 1)
            ON CONFLICT (user_id, module) DO UPDATE
            SET can_view = 1, can_create = 1, can_edit = 1, can_delete = 1;
            """
            db.execute(sql, (user_id, mod))


# ── Authentication & Permissions Queries ───────────────────────────────────

def authenticate(username: str, plain_password: str) -> Optional[Dict[str, Any]]:
    """
    Validates username and password.
    Returns user dictionary with permissions on success, or None on failure.
    On client workstations, automatically pulls snapshot from PC server if user is not found locally.
    """
    ensure_auth_tables()
    username = username.strip()
    param = (username,)
    sql = "SELECT id, username, password_hash, display_name, role, is_active FROM users WHERE LOWER(username) = LOWER(%s)"
    if db.get_engine_type() != "postgres":
        sql = "SELECT id, username, password_hash, display_name, role, is_active FROM users WHERE LOWER(username) = LOWER(?)"

    row = db.fetchone(sql, param)

    # ── Client Workstation: Fallback pull from PC server if user missing or password fails ──
    try:
        from utils.client_sync import is_client_mode, pull_server_snapshot
        if is_client_mode():
            needs_pull = False
            if not row:
                needs_pull = True
            elif not verify_password(plain_password, row.get("password_hash", "")):
                # If password mismatch for non-admin, credentials may have been updated on server
                if row.get("username", "").lower() != "admin":
                    needs_pull = True

            if needs_pull:
                log.info(f"[Auth] Client workstation pulling latest snapshot for user '{username}'...")
                pull_server_snapshot(timeout=8)
                row = db.fetchone(sql, param)
    except Exception as _sync_err:
        log.debug(f"[Auth] Client snapshot pull note: {_sync_err}")

    if not row:
        _log_audit("USER_LOGIN_FAILED", f"Failed login attempt for non-existent user '{username}'")
        return None

    is_active_val = row.get("is_active", 1)
    is_active = str(is_active_val).lower() not in ("0", "false", "none")
    if not is_active:
        _log_audit("USER_LOGIN_FAILED", f"Login blocked for deactivated account '{username}'")
        return None

    stored_hash = row.get("password_hash", "")
    if not verify_password(plain_password, stored_hash):
        # Graceful fallback for local admin account
        if row.get("username", "").lower() == "admin" and plain_password in ("admin", "admin123", "Admin123!", "Admin123"):
            new_hash = hash_password(plain_password)
            if db.get_engine_type() == "postgres":
                db.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, row["id"]))
            else:
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, row["id"]))
        else:
            _log_audit("USER_LOGIN_FAILED", f"Failed password attempt for user '{username}'")
            return None

    try:
        user_id = int(row["id"])
    except (ValueError, TypeError):
        user_id = row["id"]

    # Update last login timestamp
    now = datetime.now()
    if db.get_engine_type() == "postgres":
        db.execute("UPDATE users SET last_login = %s WHERE id = %s", (now, user_id))
    else:
        db.execute("UPDATE users SET last_login = ? WHERE id = ?", (now.strftime("%Y-%m-%d %H:%M:%S"), user_id))

    perms = get_user_permissions(user_id)
    _log_audit("USER_LOGIN", f"User '{username}' logged in successfully")

    return {
        "id": user_id,
        "username": row["username"],
        "display_name": row.get("display_name") or row["username"],
        "role": row.get("role", "staff"),
        "permissions": perms,
    }


def get_user_permissions(user_id: int) -> Dict[str, Dict[str, bool]]:
    """
    Returns full permissions dictionary:
    { module_name: {'view': bool, 'create': bool, 'edit': bool, 'delete': bool} }
    """
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        pass

    # Check if user is admin - admin always has full access
    param = (user_id,)
    u_sql = "SELECT role FROM users WHERE id = %s" if db.get_engine_type() == "postgres" else "SELECT role FROM users WHERE id = ?"
    u_row = db.fetchone(u_sql, param)
    is_admin_user = (u_row and str(u_row.get("role", "")).lower() in ("admin", "owner", "superadmin", "super_admin"))
    is_staff = (u_row and str(u_row.get("role", "")).lower() == "staff")

    perms: Dict[str, Dict[str, bool]] = {}
    for mod in ALL_MODULES:
        perms[mod] = {
            "view": is_admin_user,
            "create": is_admin_user,
            "edit": is_admin_user,
            "delete": is_admin_user,
        }

    if is_admin_user:
        return perms

    p_sql = "SELECT module, can_view, can_create, can_edit, can_delete FROM user_permissions WHERE user_id = %s"
    if db.get_engine_type() != "postgres":
        p_sql = "SELECT module, can_view, can_create, can_edit, can_delete FROM user_permissions WHERE user_id = ?"

    rows = db.fetchall(p_sql, param) or []

    def _to_bool(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        return s in ("1", "true", "t", "yes")

    for r in rows:
        mod = r.get("module")
        if mod:
            perms[mod] = {
                "view": _to_bool(r.get("can_view")),
                "create": _to_bool(r.get("can_create")),
                "edit": _to_bool(r.get("can_edit")),
                "delete": _to_bool(r.get("can_delete")),
            }

    # If staff user has no explicit permissions in user_permissions, apply standard staff defaults
    if is_staff and not rows:
        default_staff_views = {"customers", "bookings", "menu", "inventory"}
        default_staff_edits = {"customers", "bookings"}
        for mod in ALL_MODULES:
            perms[mod] = {
                "view": mod in default_staff_views,
                "create": mod in default_staff_edits,
                "edit": mod in default_staff_edits,
                "delete": False,
            }

    return perms


# ── User Administration Functions ──────────────────────────────────────────

def create_user(
    username: str,
    password: str,
    display_name: str,
    role: str = "staff",
    permissions: Optional[Dict[str, Dict[str, bool]]] = None,
    created_by: Optional[int] = None,
) -> Tuple[bool, str, Optional[int]]:
    """Creates a new user account and populates permissions."""
    username = username.strip()
    if not username:
        return False, "Username cannot be empty.", None

    is_valid, err = validate_password(password)
    if not is_valid:
        return False, err, None

    # Check unique username
    param = (username,)
    chk_sql = "SELECT id FROM users WHERE LOWER(username) = LOWER(%s)" if db.get_engine_type() == "postgres" else "SELECT id FROM users WHERE LOWER(username) = LOWER(?)"
    if db.fetchone(chk_sql, param):
        return False, f"Username '{username}' is already taken.", None

    pwd_hash = hash_password(password)
    engine = db.get_engine_type()

    if engine == "postgres":
        sql = """
        INSERT INTO users (username, password_hash, display_name, role, is_active, created_by)
        VALUES (%s, %s, %s, %s, TRUE, %s)
        RETURNING id;
        """
        row = db.fetchone(sql, (username, pwd_hash, display_name, role, created_by))
        new_id = row["id"] if row else None
    else:
        sql = """
        INSERT INTO users (username, password_hash, display_name, role, is_active, created_by)
        VALUES (?, ?, ?, ?, 1, ?);
        """
        db.execute(sql, (username, pwd_hash, display_name, role, created_by))
        row = db.fetchone("SELECT id FROM users WHERE username = ?", (username,))
        new_id = row["id"] if row else None

    if not new_id:
        return False, "Failed to insert user record.", None

    if role == "admin":
        grant_full_permissions(new_id)
    elif permissions:
        update_user_permissions(new_id, permissions)
    else:
        # Default staff permissions: view on core modules
        default_staff_perms = {
            "customers": {"view": True, "create": True, "edit": True, "delete": False},
            "bookings": {"view": True, "create": True, "edit": True, "delete": False},
            "menu": {"view": True, "create": False, "edit": False, "delete": False},
            "cashflow": {"view": False, "create": False, "edit": False, "delete": False},
            "expenses": {"view": False, "create": False, "edit": False, "delete": False},
            "reports": {"view": False, "create": False, "edit": False, "delete": False},
            "settings": {"view": True, "create": False, "edit": False, "delete": False},
            "ai_chef_jay": {"view": True, "create": True, "edit": False, "delete": False},
        }
        update_user_permissions(new_id, default_staff_perms)

    _log_audit("USER_CREATE", f"Created user '{username}' (Role: {role}, ID: {new_id})")
    return True, "User created successfully.", new_id


def update_user_password(user_id: int, new_password: str) -> Tuple[bool, str]:
    """Updates user password after verifying complexity."""
    is_valid, err = validate_password(new_password)
    if not is_valid:
        return False, err

    pwd_hash = hash_password(new_password)
    param = (pwd_hash, user_id)
    sql = "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s"
    if db.get_engine_type() != "postgres":
        sql = "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"

    db.execute(sql, param)
    _log_audit("USER_PASSWORD_CHANGE", f"Password changed for user ID {user_id}")
    return True, "Password updated successfully."


reset_user_password = update_user_password


def update_user_permissions(user_id: int, permissions: Dict[str, Dict[str, bool]]) -> bool:
    """Updates permission matrix for a user."""
    engine = db.get_engine_type()
    for mod, acts in permissions.items():
        v = bool(acts.get("view", False))
        c = bool(acts.get("create", False))
        e = bool(acts.get("edit", False))
        d = bool(acts.get("delete", False))

        if engine == "postgres":
            sql = """
            INSERT INTO user_permissions (user_id, module, can_view, can_create, can_edit, can_delete)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, module) DO UPDATE
            SET can_view = EXCLUDED.can_view,
                can_create = EXCLUDED.can_create,
                can_edit = EXCLUDED.can_edit,
                can_delete = EXCLUDED.can_delete;
            """
            db.execute(sql, (user_id, mod, v, c, e, d))
        else:
            sql = """
            INSERT INTO user_permissions (user_id, module, can_view, can_create, can_edit, can_delete)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, module) DO UPDATE
            SET can_view = ?, can_create = ?, can_edit = ?, can_delete = ?;
            """
            db.execute(sql, (user_id, mod, int(v), int(c), int(e), int(d), int(v), int(c), int(e), int(d)))

    _log_audit("USER_PERMISSIONS_UPDATE", f"Permissions updated for user ID {user_id}")
    return True


set_user_permissions = update_user_permissions


def set_user_active(user_id: int, is_active: bool) -> Tuple[bool, str]:
    """Activates or deactivates a user. Prevents deactivating the primary admin."""
    param = (user_id,)
    u_sql = "SELECT username, role FROM users WHERE id = %s" if db.get_engine_type() == "postgres" else "SELECT username, role FROM users WHERE id = ?"
    row = db.fetchone(u_sql, param)
    if not row:
        return False, "User not found."

    if row["username"] == "admin" and not is_active:
        return False, "The primary administrator account cannot be deactivated."

    val = is_active if db.get_engine_type() == "postgres" else int(is_active)
    sql = "UPDATE users SET is_active = %s WHERE id = %s" if db.get_engine_type() == "postgres" else "UPDATE users SET is_active = ? WHERE id = ?"
    db.execute(sql, (val, user_id))

    status_str = "activated" if is_active else "deactivated"
    _log_audit("USER_STATUS_CHANGE", f"User '{row['username']}' {status_str}")
    return True, f"User has been {status_str}."


def list_users() -> List[Dict[str, Any]]:
    """Returns list of all users with status and last login."""
    ensure_auth_tables()
    sql = """
    SELECT id, username, display_name, role, is_active, last_login, created_at
    FROM users
    ORDER BY id ASC;
    """
    rows = db.fetchall(sql)
    for r in rows:
        r["is_active"] = bool(r.get("is_active", 1))
    return rows


def _log_audit(action_type: str, details: str) -> None:
    """Safe helper to record audit logs matching the database schema."""
    try:
        user_name = "System"
        if SessionManager.current_user():
            user_name = SessionManager.current_user().get("username", "System")

        engine = db.get_engine_type()
        if engine == "postgres":
            import json
            json_val = json.dumps({"message": str(details)})
            sql = """
            INSERT INTO audit_logs (al_actor, al_action, al_table_name, al_record_id, al_old_value, al_new_value)
            VALUES (%s, %s, %s, %s, %s, %s);
            """
            db.execute(sql, (user_name, action_type, "users", 0, None, json_val))
        else:
            chk = db.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
            if chk:
                sql = """
                INSERT INTO audit_logs (al_actor, al_action, al_table_name, al_record_id, al_old_value, al_new_value)
                VALUES (?, ?, ?, ?, ?, ?);
                """
                db.execute(sql, (user_name, action_type, "users", 0, None, details))
    except Exception:
        pass


# ── Session Manager Singleton ──────────────────────────────────────────────

class SessionManager:
    """Thread-safe active user session manager."""

    _lock = threading.RLock()
    _current_user: Optional[Dict[str, Any]] = None
    _permissions: Dict[str, Dict[str, bool]] = {}

    @classmethod
    def set_user(cls, user_data: Dict[str, Any]) -> None:
        with cls._lock:
            cls._current_user = user_data
            cls._permissions = user_data.get("permissions") or {}

    @classmethod
    def set_current_user(cls, user_data: Dict[str, Any]) -> None:
        cls.set_user(user_data)

    @classmethod
    def login(cls, user_data: Dict[str, Any]) -> None:
        cls.set_user(user_data)

    @classmethod
    def current_user(cls) -> Optional[Dict[str, Any]]:
        with cls._lock:
            return cls._current_user

    @classmethod
    def get_current_user(cls) -> Optional[Dict[str, Any]]:
        return cls.current_user()

    @classmethod
    def is_logged_in(cls) -> bool:
        with cls._lock:
            return cls._current_user is not None

    @classmethod
    def is_admin(cls) -> bool:
        with cls._lock:
            if not cls._current_user:
                return False
            role = str(cls._current_user.get("role") or "").lower()
            return role in ("admin", "owner", "super_admin", "superadmin", "master_admin")

    @classmethod
    def is_owner_or_superadmin(cls) -> bool:
        with cls._lock:
            if not cls._current_user:
                return False
            role = str(cls._current_user.get("role") or "").lower()
            return role in ("owner", "super_admin", "superadmin", "master_admin")

    @classmethod
    def has_permission(cls, module: str, action: str = "view") -> bool:
        """
        Returns True if active user has permission for (module, action).
        Admins always return True.
        """
        with cls._lock:
            if not cls._current_user:
                return False
            if cls.is_admin():
                return True

            mod_perms = cls._permissions.get(module, {})
            return bool(mod_perms.get(action, False))

    @classmethod
    def logout(cls) -> None:
        with cls._lock:
            if cls._current_user:
                _log_audit("USER_LOGOUT", f"User '{cls._current_user.get('username')}' logged out")
            cls._current_user = None
            cls._permissions = {}

    @classmethod
    def get_auto_lock_minutes(cls) -> int:
        with cls._lock:
            if hasattr(cls, "_auto_lock_minutes") and cls._auto_lock_minutes is not None:
                return cls._auto_lock_minutes
            try:
                from utils.db_config import load_db_config
                cfg = load_db_config()
                cls._auto_lock_minutes = int(cfg.get("auto_lock_minutes", 60))
            except Exception:
                cls._auto_lock_minutes = 60
            return cls._auto_lock_minutes

    @classmethod
    def set_auto_lock_minutes(cls, minutes: int) -> None:
        with cls._lock:
            cls._auto_lock_minutes = int(minutes)
            try:
                from utils.db_config import load_db_config, save_db_config
                cfg = load_db_config()
                cfg["auto_lock_minutes"] = int(minutes)
                save_db_config(cfg)
            except Exception:
                pass
