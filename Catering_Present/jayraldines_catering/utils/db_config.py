"""
Configuration and connection utilities for Centralized PostgreSQL Server
and client setups in Jayraldine's Catering Management System.
"""

import os
import json
import socket
import secrets
import string
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

try:
    import psycopg2
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False


def get_config_dir() -> Path:
    """Returns directory path where configuration is stored."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        cfg_dir = Path(local_app_data) / "JayraldinesCatering"
    else:
        cfg_dir = Path.home() / ".jayraldines_catering"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


def get_config_path() -> Path:
    """Returns full path to db_config.json."""
    return get_config_dir() / "db_config.json"


def load_db_config() -> Dict[str, Any]:
    """
    Loads database configuration from db_config.json and applies it
    to environment variables (DB_ENGINE, DB_HOST, etc.) if not already set.
    """
    path = get_config_path()
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        if isinstance(cfg, dict):
            engine = cfg.get("engine", "postgres")
            if not isinstance(engine, str):
                engine = "postgres"
            os.environ["DB_ENGINE"] = engine
            if "host" in cfg:
                os.environ["DB_HOST"] = str(cfg["host"])
            if "port" in cfg:
                os.environ["DB_PORT"] = str(cfg["port"])
            if "dbname" in cfg:
                os.environ["DB_NAME"] = str(cfg["dbname"])
            if "user" in cfg:
                os.environ["DB_USER"] = str(cfg["user"])
            if "password" in cfg:
                os.environ["DB_PASSWORD"] = str(cfg["password"])
            return cfg
    except Exception as exc:
        print(f"[db_config] Warning: Failed to load db_config.json: {exc}")

    return {}


def save_db_config(
    engine: Any = "postgres",
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "jayraldines_catering",
    user: str = "jayraldines_app",
    password: str = "12345678",
    **extra
) -> Path:
    """Saves database connection configuration to db_config.json."""
    if isinstance(engine, dict):
        cfg = dict(engine)
        cfg.update(extra)
    else:
        cfg = {
            "engine": str(engine),
            "host": str(host),
            "port": int(port),
            "dbname": str(dbname),
            "user": str(user),
            "password": str(password),
        }
        cfg.update(extra)

    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    # Immediately reflect in current process environment
    if "engine" in cfg:
        os.environ["DB_ENGINE"] = str(cfg["engine"])
    if "host" in cfg:
        os.environ["DB_HOST"] = str(cfg["host"])
    if "port" in cfg:
        os.environ["DB_PORT"] = str(cfg["port"])
    if "dbname" in cfg:
        os.environ["DB_NAME"] = str(cfg["dbname"])
    if "user" in cfg:
        os.environ["DB_USER"] = str(cfg["user"])
    if "password" in cfg:
        os.environ["DB_PASSWORD"] = str(cfg["password"])

    return path


def get_db_config() -> Dict[str, Any]:
    """Returns current saved config or environment defaults without modifying env."""
    path = get_config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "engine": os.environ.get("DB_ENGINE", "sqlite"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", 5432)),
        "dbname": os.environ.get("DB_NAME", "jayraldines_catering"),
        "user": os.environ.get("DB_USER", "jayraldines_app"),
        "password": os.environ.get("DB_PASSWORD", ""),
    }


def generate_random_password(length: int = 16) -> str:
    """
    Generates a cryptographically strong random password satisfying:
    - At least 1 lowercase letter
    - At least 1 uppercase letter
    - At least 1 digit
    - At least 1 special character
    - Total length >= 8
    """
    if length < 8:
        length = 8

    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()_+-="

    # Ensure at least one from each category
    pwd = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]

    all_chars = lower + upper + digits + symbols
    for _ in range(length - 4):
        pwd.append(secrets.choice(all_chars))

    # Shuffle characters
    pwd_list = list(pwd)
    # Use Fisher-Yates with secrets
    for i in range(len(pwd_list) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        pwd_list[i], pwd_list[j] = pwd_list[j], pwd_list[i]

    return "".join(pwd_list)


def get_local_lan_ip() -> str:
    """
    Attempts to detect the primary non-loopback IPv4 address for this PC on the local network.
    Falls back to '127.0.0.1' if disconnected or undetected.
    """
    try:
        # Create a dummy UDP socket to a private LAN gateway IP to determine local routing interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Does not actually transmit packets since UDP is connectionless
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for addr in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = addr[4][0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def test_postgres_connection(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    timeout: int = 4
) -> Tuple[bool, str]:
    """
    Tests live connection to a PostgreSQL database.
    Returns (True, "Connected successfully") or (False, error_message).
    """
    if not _PSYCOPG2_AVAILABLE:
        return False, "psycopg2 library is not installed or available."

    try:
        conn = psycopg2.connect(
            host=host,
            port=int(port),
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=timeout,
        )
        conn.close()
        return True, "Connected successfully to PostgreSQL database."
    except Exception as exc:
        err_msg = str(exc).strip().replace("\n", " ")
        return False, err_msg


def add_windows_firewall_rule(
    rule_name: str = "JayraldinesCatering-Postgres",
    port: int = 5432,
    profile: str = "any"
) -> Tuple[bool, str]:
    """
    Adds Windows Firewall inbound allow rule.
    Only executes on Windows NT. Deletes stale rule first to avoid duplicates.
    """
    if os.name != "nt":
        return True, "Not on Windows, firewall rule skipped."

    try:
        # Delete old rule first if exists
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=5,
        )

        cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={port}",
            f"profile={profile}",
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10,
        )
        if res.returncode == 0:
            return True, f"Firewall rule '{rule_name}' (port {port}) created successfully."
        else:
            return False, f"Firewall command returned code {res.returncode}: {res.stderr or res.stdout}"
    except Exception as exc:
        return False, f"Failed to execute firewall command: {exc}"


def open_all_kiosk_firewall_ports() -> List[Tuple[str, bool, str]]:
    """
    Opens all ports needed for Tablet Kiosk, LAN Sync Hub, and PostgreSQL:
    - Port 5432 (PostgreSQL Central DB)
    - Port 8000 (Desktop LAN Sync Hub)
    - Port 8085 (Tablet Kiosk Web Server)
    - ICMPv4 (Ping discovery)
    """
    results = []
    if os.name != "nt":
        return [("non-windows", True, "Skipped non-windows")]

    # 1. PostgreSQL (5432)
    ok, msg = add_windows_firewall_rule("Jayraldines Central DB (5432)", 5432, profile="any")
    results.append(("PostgreSQL-5432", ok, msg))

    # 2. LAN Sync Hub (8000)
    ok, msg = add_windows_firewall_rule("Jayraldines LAN Sync Server (8000)", 8000, profile="any")
    results.append(("SyncServer-8000", ok, msg))

    # 3. Tablet Web Server (8085)
    ok, msg = add_windows_firewall_rule("Jayraldines Tablet Web Server (8085)", 8085, profile="any")
    results.append(("WebServer-8085", ok, msg))

    # 4. ICMP Ping Rule
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=Allow ICMPv4-In (Ping)"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=5
        )
        cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            "name=Allow ICMPv4-In (Ping)",
            "protocol=icmpv4:8,any",
            "dir=in",
            "action=allow",
            "profile=any"
        ]
        res = subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
        results.append(("ICMP-Ping", res.returncode == 0, "Ping rule added"))
    except Exception as e:
        results.append(("ICMP-Ping", False, str(e)))

    return results


def configure_network_profile_private() -> Tuple[bool, str]:
    """
    Sets the active Wi-Fi / Ethernet / Hotspot network connection profile to Private
    so Windows allows inbound LAN connections without blocking.
    Requires administrative permissions.
    """
    if os.name != "nt":
        return True, "Non-Windows, skipped."

    ps_cmd = (
        "Get-NetConnectionProfile | "
        "Where-Object { $_.IPv4Connectivity -eq 'Internet' -or $_.Name -like '*iPhone*' "
        "-or $_.Name -like '*Android*' -or $_.InterfaceAlias -like '*Wi-Fi*' -or $_.InterfaceAlias -like '*Ethernet*' } | "
        "Set-NetConnectionProfile -NetworkCategory Private"
    )

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=12
        )
        if res.returncode == 0:
            return True, "Network connection profile successfully set to Private."
        else:
            return False, f"PowerShell returned code {res.returncode}: {res.stderr}"
    except Exception as exc:
        return False, f"Failed to set network profile: {exc}"

