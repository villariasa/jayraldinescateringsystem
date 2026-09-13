"""
Service controller and live status monitor for Centralized PostgreSQL Database Server.
Handles:
- Central server machine detection (host vs client workstation)
- Live PostgreSQL service discovery & status (port 5432, service state)
- LAN Sync Hub status (port 8000)
- Safe restart / start of PostgreSQL service
- Owner authorization verification for restricted server controls
"""

import os
import sys
import json
import time
import socket
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from utils.db_config import get_db_config, get_local_lan_ip, load_db_config
import utils.db as db
from utils.logger import get_logger

log = get_logger()

# Known standard PostgreSQL service name patterns on Windows
KNOWN_PG_SERVICES = [
    "postgresql-x64-18",
    "postgresql-x64-17",
    "postgresql-x64-16",
    "postgresql-x64-15",
    "postgresql-x64-14",
    "postgresql-x64-13",
    "postgresql-x64-12",
    "postgresql",
]


def is_central_db_server_machine() -> bool:
    """
    Determines whether the current machine is the Centralized DB Server host:
    1. Configured DB host is 'localhost', '127.0.0.1', '0.0.0.0', empty, or matches the PC's local LAN IP.
    2. OR a local PostgreSQL Windows service is installed on this machine.
    """
    cfg = get_db_config()
    sync_role = cfg.get("sync_role")
    if sync_role == "client":
        return False

    host = str(cfg.get("host", "localhost")).strip().lower()
    local_ip = get_local_lan_ip()

    if host in ("localhost", "127.0.0.1", "0.0.0.0", "", "::1") or host == local_ip.lower():
        return True

    # Check if local postgres service is installed regardless of host config
    if cfg.get("engine", "sqlite") == "postgres" and find_local_postgres_service() is not None:
        return True

    return False


def find_local_postgres_service() -> Optional[str]:
    """
    Finds the exact Windows service name for PostgreSQL on this machine.
    Returns service name string or None if not found / non-Windows.
    """
    if os.name != "nt":
        return None

    # Check known names first via sc.exe (very fast, no PowerShell overhead)
    for svc in KNOWN_PG_SERVICES:
        try:
            res = subprocess.run(
                ["sc.exe", "query", svc],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=2,
            )
            if res.returncode == 0 and ("RUNNING" in res.stdout or "STOPPED" in res.stdout or "PAUSED" in res.stdout):
                return svc
        except Exception:
            pass

    # Dynamic PowerShell lookup if not found in list
    try:
        ps_cmd = "(Get-Service -Name *postgres* -ErrorAction SilentlyContinue | Select-Object -First 1).Name"
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=3,
        )
        name = res.stdout.strip()
        if name:
            return name
    except Exception:
        pass

    return None


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Checks if a TCP port is accepting socket connections."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def get_local_db_server_status() -> Dict[str, Any]:
    """
    Queries live status of the database server and supporting sync daemons.
    Returns a comprehensive dictionary of status indicators.
    """
    cfg = get_db_config()
    engine = cfg.get("engine", "sqlite")
    host = str(cfg.get("host", "localhost")).strip()
    port = int(cfg.get("port", 8000 if engine == "sqlite" else 5432))
    dbname = cfg.get("dbname", "catering.db" if engine == "sqlite" else "jayraldines_catering")
    local_ip = get_local_lan_ip()
    is_central = is_central_db_server_machine()

    if engine == "sqlite":
        import utils.db as db
        db_alive = False
        try:
            db_alive = db.is_available()
            if db_alive:
                row = db.fetchone("SELECT 1 as alive")
                db_alive = bool(row and row.get("alive") == 1)
        except Exception:
            db_alive = False

        if is_central:
            sync_running = is_port_open("127.0.0.1", 8000, timeout=1.0)
            is_running = db_alive
            status_badge = "🟢 RUNNING" if db_alive else "🔴 ERROR"

            return {
                "is_central_server": True,
                "engine": "sqlite",
                "host": local_ip,
                "local_ip": local_ip,
                "port": 8000,
                "dbname": "catering.db",
                "service_name": "SQLite WAL Embedded Engine (Central Server)",
                "service_state": "ACTIVE" if db_alive else "INACTIVE",
                "port_listening": sync_running,
                "sync_running": sync_running,
                "is_running": is_running,
                "status_badge": status_badge,
                "timestamp": time.strftime("%H:%M:%S"),
            }
        else:
            # Client Workstation connected to remote server (e.g. 192.168.1.32)
            remote_sync_alive = is_port_open(host, port, timeout=1.5)
            status_badge = "🟢 CONNECTED" if remote_sync_alive else "🔴 SERVER UNREACHABLE"

            return {
                "is_central_server": False,
                "engine": "sqlite",
                "host": host,
                "local_ip": local_ip,
                "port": port,
                "dbname": "catering.db",
                "service_name": f"Client Workstation (Connected to {host}:{port})",
                "service_state": "CONNECTED" if remote_sync_alive else "OFFLINE",
                "port_listening": remote_sync_alive,
                "sync_running": remote_sync_alive,
                "is_running": remote_sync_alive,
                "status_badge": status_badge,
                "timestamp": time.strftime("%H:%M:%S"),
            }

    service_name = find_local_postgres_service() if is_central else None
    service_state = "UNKNOWN"

    if service_name and os.name == "nt":
        try:
            res = subprocess.run(
                ["sc.exe", "query", service_name],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=2,
            )
            if "RUNNING" in res.stdout:
                service_state = "RUNNING"
            elif "STOPPED" in res.stdout:
                service_state = "STOPPED"
            elif "START_PENDING" in res.stdout:
                service_state = "STARTING"
            elif "STOP_PENDING" in res.stdout:
                service_state = "STOPPING"
        except Exception as exc:
            log.warning(f"Error querying service {service_name}: {exc}")

    # Check TCP socket responsiveness
    port_listening = is_port_open("127.0.0.1" if is_central else host, port, timeout=1.2)

    # Check LAN Sync Hub (port 8000)
    sync_running = is_port_open("127.0.0.1" if is_central else host, 8000, timeout=1.0)

    # Overall DB server running state
    is_running = port_listening or (service_state == "RUNNING")

    status_badge = "🟢 RUNNING" if is_running else ("🔴 STOPPED" if service_state == "STOPPED" else "⚠️ UNKNOWN")

    return {
        "is_central_server": is_central,
        "engine": engine,
        "host": host,
        "local_ip": local_ip,
        "port": port,
        "dbname": dbname,
        "service_name": service_name or "postgresql-x64-18",
        "service_state": service_state,
        "port_listening": port_listening,
        "sync_running": sync_running,
        "is_running": is_running,
        "status_badge": status_badge,
        "timestamp": time.strftime("%H:%M:%S"),
    }


def restart_local_db_server() -> Tuple[bool, str]:
    """
    Restarts the local database server / sync hub.
    """
    cfg = get_db_config()
    if cfg.get("engine") == "sqlite":
        from utils.db_sync_server import stop_sync_server, start_sync_server_background
        stop_sync_server()
        started = start_sync_server_background(host="0.0.0.0", port=8000)
        return started, "SQLite LAN Sync Server restarted successfully on Port 8000."

    if not is_central_db_server_machine():
        return False, "This machine is a client workstation. Server restart must be performed on the Central Server Host."

    svc = find_local_postgres_service() or "postgresql-x64-18"

    # 1. Attempt service restart
    restarted = False
    err_output = ""

    # Direct PowerShell restart attempt first
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"Restart-Service -Name '{svc}' -Force"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=15,
        )
        if res.returncode == 0:
            restarted = True
        else:
            err_output = res.stderr or res.stdout
    except Exception as exc:
        err_output = str(exc)

    # If direct failed (likely elevation required), invoke elevated restart
    if not restarted:
        try:
            elev_cmd = (
                f"Start-Process powershell -Verb RunAs -Wait -ArgumentList "
                f"'-NoProfile -WindowStyle Hidden -Command Restart-Service -Name \"{svc}\" -Force'"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", elev_cmd],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=25,
            )
            if res.returncode == 0:
                restarted = True
            else:
                err_output = res.stderr or res.stdout
        except Exception as exc:
            err_output = str(exc)

    # Wait for service port to come back up (up to 8 seconds)
    time.sleep(2.0)
    for _ in range(6):
        if is_port_open("127.0.0.1", 5432, timeout=1.0):
            restarted = True
            break
        time.sleep(1.0)

    if not restarted:
        return False, f"Failed to restart PostgreSQL service '{svc}':\n{err_output}"

    # 2. Restart LAN Sync Hub if active
    try:
        from utils.db_sync_server import start_sync_server_background
        start_sync_server_background()
    except Exception as exc:
        log.warning(f"Note on sync server restart: {exc}")

    # 3. Reconnect desktop application database connection pool
    try:
        db.connect_postgres(force=True)
    except Exception as exc:
        log.warning(f"Note on reconnecting database pool: {exc}")

    return True, f"PostgreSQL server service '{svc}' restarted successfully. Active connections refreshed."


def start_local_db_server() -> Tuple[bool, str]:
    """
    Starts the local database server / sync hub if stopped.
    """
    cfg = get_db_config()
    if cfg.get("engine") == "sqlite":
        from utils.db_sync_server import start_sync_server_background
        started = start_sync_server_background(host="0.0.0.0", port=8000)
        return started, "SQLite LAN Sync Server started successfully on Port 8000."

    if not is_central_db_server_machine():
        return False, "This machine is a client workstation. Server start must be performed on the Central Server Host."

    svc = find_local_postgres_service() or "postgresql-x64-18"

    started = False
    err_output = ""

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"Start-Service -Name '{svc}'"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=12,
        )
        if res.returncode == 0:
            started = True
        else:
            err_output = res.stderr or res.stdout
    except Exception as exc:
        err_output = str(exc)

    if not started:
        try:
            elev_cmd = (
                f"Start-Process powershell -Verb RunAs -Wait -ArgumentList "
                f"'-NoProfile -WindowStyle Hidden -Command Start-Service -Name \"{svc}\"'"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", elev_cmd],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=20,
            )
            if res.returncode == 0:
                started = True
            else:
                err_output = res.stderr or res.stdout
        except Exception as exc:
            err_output = str(exc)

    time.sleep(2.0)
    for _ in range(6):
        if is_port_open("127.0.0.1", 5432, timeout=1.0):
            started = True
            break
        time.sleep(1.0)

    if not started:
        return False, f"Failed to start PostgreSQL service '{svc}':\n{err_output}"

    try:
        from utils.db_sync_server import start_sync_server_background
        start_sync_server_background()
    except Exception:
        pass

    try:
        db.connect_postgres(force=True)
    except Exception:
        pass

    return True, f"PostgreSQL server service '{svc}' started successfully."


def configure_server_remote_access() -> Tuple[bool, str]:
    """
    Configures PostgreSQL server pg_hba.conf and postgresql.conf to allow
    all remote LAN client workstations and tablets, and opens Windows Firewall.
    """
    ps1_script = Path(__file__).resolve().parent.parent / "enable_server_remote_access.ps1"
    if not ps1_script.exists():
        ps1_script = Path(__file__).resolve().parents[2] / "enable_server_remote_access.ps1"

    if not ps1_script.exists():
        return False, f"Setup script not found at {ps1_script}"

    try:
        elev_cmd = (
            f"Start-Process powershell -Verb RunAs -Wait -ArgumentList "
            f"'-NoProfile -ExecutionPolicy Bypass -File \"{ps1_script}\"'"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", elev_cmd],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=35,
        )
        if res.returncode == 0:
            return True, "PostgreSQL remote client access (pg_hba.conf & Firewall) configured successfully."
        else:
            return False, f"Failed to execute configuration script:\n{res.stderr or res.stdout}"
    except Exception as exc:
        return False, str(exc)



def verify_owner_authorization(entered_key: str) -> bool:
    """
    Verifies Master Owner passkey for restricted server maintenance actions.
    Checks against:
    1. 'owner_passkey' or 'admin_passkey' in db_config.json
    2. Primary admin account password in users table
    3. System fallback master key '12345678'
    """
    entered = (entered_key or "").strip()
    if not entered:
        return False

    # 1. Check db_config.json
    cfg = load_db_config()
    for k in ("owner_passkey", "admin_passkey", "master_key", "password"):
        val = str(cfg.get(k, "")).strip()
        if val and entered == val:
            return True

    # 2. Check primary admin password in database
    try:
        from utils.auth import verify_password
        engine = db.get_engine_type()
        u_sql = "SELECT password_hash FROM users WHERE username = 'admin' LIMIT 1;"
        row = db.fetchone(u_sql)
        if row and row.get("password_hash"):
            if verify_password(entered, row["password_hash"]):
                return True
    except Exception:
        pass

    # 3. Default fallback master passkey
    if entered == "12345678":
        return True

    return False
