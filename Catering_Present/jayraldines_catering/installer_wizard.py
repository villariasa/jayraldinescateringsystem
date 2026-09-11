"""
Jayraldine's Catering - Modern Windows Application Installer.
Designed with a sleek, frameless glassmorphic interface, interactive 5-step stepper,
and automated Centralized PostgreSQL Server vs Client Node configuration.
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Ensure base directory is in sys.path for bundled or dev execution
base_dir = Path(__file__).resolve().parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))
if getattr(sys, "frozen", False):
    meipass = Path(sys._MEIPASS)
    if str(meipass) not in sys.path:
        sys.path.insert(0, str(meipass))

from PySide6.QtWidgets import (
    QApplication, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QLineEdit, QFileDialog, QCheckBox, QRadioButton,
    QButtonGroup, QProgressBar, QFrame, QGraphicsDropShadowEffect, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QPoint
from PySide6.QtGui import QPixmap, QIcon, QFont, QColor, QPainter, QBrush, QPen

try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "1.3.1"
    APP_NAME = "Jayraldine's Catering"

from utils.db_config import (
    generate_random_password,
    get_local_lan_ip,
    save_db_config,
    load_db_config,
    get_db_config,
    test_postgres_connection,
    add_windows_firewall_rule,
    open_all_kiosk_firewall_ports,
    configure_network_profile_private,
)


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def get_default_install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "JayraldinesCatering"
    return Path.home() / "AppData" / "Local" / "JayraldinesCatering"


def get_desktop_directories() -> list[Path]:
    dirs = []
    if os.name == "nt":
        try:
            import ctypes.wintypes
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
            if buf.value:
                p = Path(buf.value)
                if p.exists() and p not in dirs:
                    dirs.append(p)
        except Exception:
            pass

    user_prof = Path(os.environ.get("USERPROFILE", str(Path.home())))
    for cand in [user_prof / "Desktop", user_prof / "OneDrive" / "Desktop", Path.home() / "Desktop"]:
        if cand.exists() and cand not in dirs:
            dirs.append(cand)

    if not dirs:
        dirs.append(user_prof / "Desktop")
    return dirs


def create_shortcut(target_exe: Path, shortcut_path: Path, icon_path: Path, work_dir: Path, description: str = "Jayraldine's Catering"):
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    ps_cmd = (
        f'$WshShell = New-Object -ComObject WScript.Shell; '
        f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); '
        f'$Shortcut.TargetPath = "{target_exe}"; '
        f'$Shortcut.WorkingDirectory = "{work_dir}"; '
        f'$Shortcut.IconLocation = "{icon_path},0"; '
        f'$Shortcut.Description = "{description}"; '
        f'$Shortcut.Save()'
    )
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


# ── Background Installation Worker ─────────────────────────────────────────

class ExtractWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str, dict)

    def __init__(
        self,
        dest_dir: Path,
        create_desktop: bool,
        create_start: bool,
        server_mode: str = "server",
        client_config: Optional[dict] = None,
        clean_db: bool = True,
        sqlite_source_path: Optional[Path] = None
    ):
        super().__init__()
        self.dest_dir = dest_dir
        self.create_desktop = create_desktop
        self.create_start = create_start
        self.server_mode = server_mode  # "server" or "client"
        self.client_config = client_config or {}
        self.clean_db = clean_db
        self.sqlite_source_path = sqlite_source_path
        self.credentials = {}

    @staticmethod
    def _find_psql_static() -> Optional[str]:
        if shutil.which("psql"):
            return "psql"
        for ver in ["17", "16", "15", "14", "13"]:
            for pf in [r"C:\Program Files\PostgreSQL", r"C:\Program Files (x86)\PostgreSQL"]:
                cand = os.path.join(pf, ver, "bin", "psql.exe")
                if os.path.exists(cand):
                    return cand
        return None

    def _auto_install_postgresql(self) -> Tuple[bool, str]:
        """Attempts to install PostgreSQL silently if not found."""
        self.progress.emit(15, "PostgreSQL not detected. Installing PostgreSQL database engine silently...")
        try:
            cmd = [
                "winget", "install", "--id", "PostgreSQL.PostgreSQL",
                "-e", "--silent", "--accept-package-agreements", "--accept-source-agreements"
            ]
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if res.returncode == 0:
                return True, "Installed via winget."
        except Exception:
            pass

        setup_ps1 = self.dest_dir / "setup.ps1"
        if setup_ps1.exists():
            try:
                ps_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -File "{setup_ps1}"'
                subprocess.run(
                    ps_cmd, shell=True, timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                return True, "Installed via setup.ps1."
            except Exception as exc:
                return False, f"Failed setup.ps1: {exc}"

        return False, "PostgreSQL silent installation was unable to complete automatically."

    def _find_asset_file(self, filename: str) -> Optional[Path]:
        """Locates bundled or repository SQL/asset files across multiple candidate directories."""
        search_dirs = [
            self.dest_dir,
            self.dest_dir / "_internal",
            Path(__file__).resolve().parent,
            Path(sys.executable).resolve().parent,
            Path(sys.executable).resolve().parent / "_internal",
            get_base_dir(),
        ]
        if hasattr(sys, "_MEIPASS"):
            search_dirs.insert(0, Path(sys._MEIPASS))
        for d in search_dirs:
            if d and d.exists():
                p = d / filename
                if p.exists():
                    return p
        return None

    def _init_server_database(self, psql_exe: str, db_pass: str, admin_pass: str) -> bool:
        """Initializes Central PostgreSQL Database, scoped user, places dropdown, and admin account."""
        env = os.environ.copy()
        env["PGPASSWORD"] = "12345678"  # Default superuser password

        try:
            # 1. Terminate existing connections and recreate database if requested or missing
            kill_sql = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'jayraldines_catering' AND pid <> pg_backend_pid();"
            subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "postgres", "-c", kill_sql],
                env=env, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=10
            )

            main_sql = self._find_asset_file("jayraldines_catering_clean.sql")
            if self.clean_db and main_sql and main_sql.exists():
                # Clean install: run clean schema directly which recreates database, tables, and places dropdown
                self.progress.emit(74, "Applying full database schema & seeding places dropdown...")
                subprocess.run(
                    [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-f", str(main_sql)],
                    env=env, capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=45
                )
            else:
                # Ensure database exists
                subprocess.run(
                    [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "postgres", "-c", "CREATE DATABASE jayraldines_catering;"],
                    env=env, capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=15
                )
                if main_sql and main_sql.exists():
                    subprocess.run(
                        [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-f", str(main_sql)],
                        env=env, capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=45
                    )

            # 2. Create scoped application DB user: jayraldines_app and grant permissions
            user_sql = f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jayraldines_app') THEN
                    CREATE ROLE jayraldines_app WITH LOGIN PASSWORD '{db_pass}';
                ELSE
                    ALTER ROLE jayraldines_app WITH PASSWORD '{db_pass}';
                END IF;
            END
            $$;
            GRANT ALL PRIVILEGES ON DATABASE jayraldines_catering TO jayraldines_app;
            GRANT ALL ON SCHEMA public TO jayraldines_app;
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON ALL TABLES IN SCHEMA public TO jayraldines_app;
            GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO jayraldines_app;
            GRANT ALL ON ALL ROUTINES IN SCHEMA public TO jayraldines_app;
            ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO jayraldines_app;
            ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO jayraldines_app;
            ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON ROUTINES TO jayraldines_app;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO jayraldines_app;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO jayraldines_app;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON ROUTINES TO jayraldines_app;
            """
            subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "jayraldines_catering", "-c", user_sql],
                env=env, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=15
            )

            # 3. Run supplemental migrations if present
            for mig in [
                "occasions_migration.sql",
                "confirmed_only_views_migration.sql",
                "analytics_functions_migration.sql",
                "fix_customer_ledger_view.sql",
                "device_monitoring_migration.sql"
            ]:
                mig_path = self._find_asset_file(mig)
                if mig_path and mig_path.exists():
                    subprocess.run(
                        [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "jayraldines_catering", "-f", str(mig_path)],
                        env=env, capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=15
                    )

            # 4. Initialize Auth and Audit tables + default admin account
            from utils.auth import hash_password
            admin_hash = hash_password(admin_pass)
            auth_sql = f"""
            CREATE TABLE IF NOT EXISTS users (
                id              SERIAL PRIMARY KEY,
                username        VARCHAR(50) UNIQUE NOT NULL,
                password_hash   VARCHAR(255) NOT NULL,
                display_name    VARCHAR(100),
                role            VARCHAR(20) DEFAULT 'admin',
                is_active       BOOLEAN DEFAULT TRUE,
                created_by      INTEGER,
                created_at      TIMESTAMP DEFAULT NOW(),
                updated_at      TIMESTAMP DEFAULT NOW(),
                last_login      TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS user_permissions (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                module      VARCHAR(50) NOT NULL,
                can_view    BOOLEAN DEFAULT TRUE,
                can_create  BOOLEAN DEFAULT TRUE,
                can_edit    BOOLEAN DEFAULT TRUE,
                can_delete  BOOLEAN DEFAULT TRUE,
                UNIQUE(user_id, module)
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id              SERIAL PRIMARY KEY,
                user_id         INT REFERENCES users(id) ON DELETE SET NULL,
                username        VARCHAR(100),
                action          VARCHAR(100) NOT NULL,
                target_type     VARCHAR(50),
                target_id       VARCHAR(50),
                details         TEXT,
                ip_address      VARCHAR(50),
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO users (username, password_hash, display_name, role, is_active)
            VALUES ('admin', '{admin_hash}', 'System Administrator', 'admin', TRUE)
            ON CONFLICT (username) DO UPDATE
            SET password_hash = '{admin_hash}', is_active = TRUE;
            """
            subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "jayraldines_catering", "-c", auth_sql],
                env=env, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=15
            )

            # Populate permissions for all modules for admin
            modules = ["customers", "bookings", "menu", "cashflow", "expenses", "reports", "settings", "ai_chef_jay", "users", "audit_logs"]
            perm_inserts = " ".join([
                f"INSERT INTO user_permissions (user_id, module, can_view, can_create, can_edit, can_delete) "
                f"SELECT id, '{m}', TRUE, TRUE, TRUE, TRUE FROM users WHERE username='admin' "
                f"ON CONFLICT (user_id, module) DO UPDATE SET can_view=TRUE, can_create=TRUE, can_edit=TRUE, can_delete=TRUE;"
                for m in modules
            ])
            subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "jayraldines_catering", "-c", perm_inserts],
                env=env, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=15
            )

            # Re-grant all privileges for newly created tables to jayraldines_app
            regrant_sql = """
            GRANT ALL PRIVILEGES ON DATABASE jayraldines_catering TO jayraldines_app;
            GRANT ALL ON SCHEMA public TO jayraldines_app;
            GRANT ALL ON ALL TABLES IN SCHEMA public TO jayraldines_app;
            GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO jayraldines_app;
            GRANT ALL ON ALL ROUTINES IN SCHEMA public TO jayraldines_app;
            """
            subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "jayraldines_catering", "-c", regrant_sql],
                env=env, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=15
            )

            # 5. Guaranteed Places / Cebu Address Dropdown verification
            check_proc = subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "jayraldines_catering", "-t", "-c", "SELECT count(*) FROM address_cities;"],
                env=env, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=10
            )
            count = 0
            try:
                count = int((check_proc.stdout or "0").strip())
            except Exception:
                count = 0

            if count == 0:
                self.progress.emit(78, "Auto-inserting full Cebu places dropdown hierarchy...")
                addr_sql_path = self._find_asset_file("cebu_address_migration.sql")
                if addr_sql_path and addr_sql_path.exists():
                    subprocess.run(
                        [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "jayraldines_catering", "-f", str(addr_sql_path)],
                        env=env, capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=20
                    )

            return True
        except Exception as exc:
            print(f"[installer] Database initialization error: {exc}")
            return False

    def run(self):
        try:
            base_dir = get_base_dir()
            zip_path = base_dir / "app_package.zip"

            # ── 1. Extraction ──────────────────────────────────────────
            if not zip_path.exists():
                dist_dir = base_dir / "dist" / "JayraldinesCatering"
                if not dist_dir.exists():
                    dist_dir = Path("dist/JayraldinesCatering").resolve()

                if not dist_dir.exists():
                    self.finished.emit(False, "Package archive 'app_package.zip' not found.", {})
                    return

                self.progress.emit(10, "Preparing target installation directory...")
                self.dest_dir.mkdir(parents=True, exist_ok=True)

                total_files = sum(len(files) for _, _, files in os.walk(dist_dir))
                copied = 0
                for root, _, files in os.walk(dist_dir):
                    rel = Path(root).relative_to(dist_dir)
                    target_subdir = self.dest_dir / rel
                    target_subdir.mkdir(parents=True, exist_ok=True)
                    for f in files:
                        shutil.copy2(Path(root) / f, target_subdir / f)
                        copied += 1
                        pct = 10 + int((copied / max(1, total_files)) * 50)
                        self.progress.emit(pct, f"Installing: {f}")
            else:
                self.dest_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    members = zf.infolist()
                    total = len(members)
                    for i, member in enumerate(members):
                        zf.extract(member, self.dest_dir)
                        pct = int((i / max(1, total)) * 60)
                        self.progress.emit(pct, f"Extracting: {member.filename}")

            # ── 2. Database Setup ───────────────────────────────────────
            if self.server_mode == "server":
                self.progress.emit(65, "Checking PostgreSQL Database Engine...")
                psql = self._find_psql_static()
                if not psql:
                    self._auto_install_postgresql()
                    psql = self._find_psql_static()

                self.progress.emit(72, "Configuring Central PostgreSQL Server & Credentials...")
                db_password = getattr(self, "db_password", None) or "12345678"
                admin_password = getattr(self, "admin_password", None) or "Admin1234!"
                lan_ip = get_local_lan_ip()

                if psql:
                    self._init_server_database(psql, db_password, admin_password)

                # Migrate existing SQLite data into PostgreSQL if source database provided
                migrated_stats = {}
                if self.sqlite_source_path and Path(self.sqlite_source_path).exists():
                    self.progress.emit(76, f"Migrating existing SQLite data ({Path(self.sqlite_source_path).name}) into PostgreSQL...")
                    try:
                        from utils.sqlite_to_postgres import migrate_sqlite_to_postgres
                        ok_mig, mig_stats, mig_err = migrate_sqlite_to_postgres(
                            Path(self.sqlite_source_path),
                            {
                                "host": "localhost",
                                "port": 5432,
                                "dbname": "jayraldines_catering",
                                "user": "postgres",
                                "password": "12345678"
                            },
                            progress_callback=lambda p, msg: self.progress.emit(76 + int(p * 0.05), msg)
                        )
                        if ok_mig:
                            migrated_stats = mig_stats
                    except Exception as m_exc:
                        print(f"[installer] SQLite data migration error: {m_exc}")

                # Configure Private Network Profile & Open Windows Firewall for LAN & Tablets
                self.progress.emit(82, "Configuring Wi-Fi & Hotspot network profile to Private...")
                configure_network_profile_private()

                self.progress.emit(86, "Configuring Windows Firewall (Ports 5432, 8000, 8085)...")
                open_all_kiosk_firewall_ports()

                # Write db_config.json for localhost
                save_db_config(
                    engine="postgres",
                    host="localhost",
                    port=5432,
                    dbname="jayraldines_catering",
                    user="jayraldines_app",
                    password=db_password
                )

                self.credentials = {
                    "role": "server",
                    "host": lan_ip,
                    "port": 5432,
                    "dbname": "jayraldines_catering",
                    "db_user": "jayraldines_app",
                    "db_password": db_password,
                    "admin_user": "admin",
                    "admin_password": admin_password,
                    "migrated_stats": migrated_stats,
                    "migrated_source": str(self.sqlite_source_path) if self.sqlite_source_path else ""
                }
            else:
                # Client Mode: save config pointing to remote server
                self.progress.emit(75, "Configuring Client connection to Central Server...")
                host = self.client_config.get("host", "localhost")
                port = int(self.client_config.get("port", 5432))
                dbname = self.client_config.get("dbname", "jayraldines_catering")
                user = self.client_config.get("user", "jayraldines_app")
                password = self.client_config.get("password", "")

                save_db_config(
                    engine="postgres",
                    host=host,
                    port=port,
                    dbname=dbname,
                    user=user,
                    password=password
                )

                self.credentials = {
                    "role": "client",
                    "host": host,
                    "port": port,
                    "dbname": dbname,
                    "db_user": user,
                }

            # ── 3. Shortcuts ───────────────────────────────────────────
            self.progress.emit(88, "Registering Windows shortcuts & icons...")

            exe_path = self.dest_dir / "JayraldinesCatering.exe"
            ico_path = self.dest_dir / "assets" / "logo.ico"
            if not ico_path.exists():
                ico_path = exe_path

            if self.create_desktop:
                for d_dir in get_desktop_directories():
                    try:
                        d_dir.mkdir(parents=True, exist_ok=True)
                        lnk_desktop = d_dir / "Jayraldine's Catering.lnk"
                        create_shortcut(exe_path, lnk_desktop, ico_path, self.dest_dir)
                    except Exception:
                        pass

            if self.create_start:
                app_data = Path(os.environ.get("APPDATA", str(Path.home())))
                start_menu = app_data / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Jayraldine's Catering"
                lnk_start = start_menu / "Jayraldine's Catering.lnk"
                create_shortcut(exe_path, lnk_start, ico_path, self.dest_dir)

            if os.name == "nt":
                try:
                    import ctypes
                    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
                except Exception:
                    pass

            uninstaller = self.dest_dir / "uninstall.bat"
            desktop_lnks_cmd = "\n".join([f'del /F /Q "{d / "Jayraldine\'s Catering.lnk"}" 2>nul' for d in get_desktop_directories()])
            start_menu_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Jayraldine's Catering"

            uninstall_content = f"""@echo off
title Jayraldine's Catering - Uninstaller
echo ======================================================
echo   Uninstalling Jayraldine's Catering...
echo ======================================================
echo.
taskkill /F /IM JayraldinesCatering.exe 2>nul
{desktop_lnks_cmd}
rd /S /Q "{start_menu_dir}" 2>nul
echo Cleaning up application files...
cd /d "%TEMP%"
rd /S /Q "{self.dest_dir}" 2>nul
echo.
echo Jayraldine's Catering has been completely uninstalled.
echo.
pause
"""
            try:
                uninstaller.write_text(uninstall_content, encoding="utf-8")
            except Exception:
                pass

            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, "", self.credentials)
        except Exception as exc:
            self.finished.emit(False, str(exc), {})


# ── Stepper UI Component ───────────────────────────────────────────────────

class StepIndicator(QFrame):
    """Left sidebar with live progress stepper and brand graphics."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E1B4B, stop:0.45 #0F172A, stop:1 #020617);
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Brand Logo with circular glow border
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        logo_lbl = QLabel()
        logo_path = get_base_dir() / "assets" / "logo.png"
        if logo_path.exists():
            pm = QPixmap(str(logo_path)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pm)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        brand_row.addWidget(logo_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        app_name_lbl = QLabel("Jayraldine's")
        app_name_lbl.setStyleSheet("color: #FB7185; font-size: 16px; font-weight: 800; background: transparent; border: none;")
        sub_lbl = QLabel("CATERING SYSTEM")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
        title_col.addWidget(app_name_lbl)
        title_col.addWidget(sub_lbl)
        brand_row.addLayout(title_col)
        brand_row.addStretch()
        lay.addLayout(brand_row)

        lay.addSpacing(10)

        # 5 Stepper Items
        self.steps = [
            ("Welcome", "Overview & Setup"),
            ("Server Role", "Server or Client"),
            ("Preferences", "Path & Shortcuts"),
            ("Installing", "Unpacking & DB Setup"),
            ("Completed", "Credentials & Launch")
        ]
        self.step_widgets = []

        for i, (title, desc) in enumerate(self.steps):
            step_box = QWidget()
            step_box.setStyleSheet("background: transparent; border: none;")
            s_lay = QHBoxLayout(step_box)
            s_lay.setContentsMargins(0, 3, 0, 3)
            s_lay.setSpacing(10)

            num_lbl = QLabel(str(i + 1))
            num_lbl.setFixedSize(24, 24)
            num_lbl.setAlignment(Qt.AlignCenter)
            num_lbl.setStyleSheet("""
                QLabel {
                    background-color: #1E293B;
                    color: #94A3B8;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 12px;
                    border: 1px solid rgba(255,255,255,0.1);
                }
            """)

            txt_col = QVBoxLayout()
            txt_col.setSpacing(1)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600; background: transparent;")
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("color: #64748B; font-size: 10px; background: transparent;")
            txt_col.addWidget(t_lbl)
            txt_col.addWidget(d_lbl)

            s_lay.addWidget(num_lbl)
            s_lay.addLayout(txt_col, 1)

            lay.addWidget(step_box)
            self.step_widgets.append((num_lbl, t_lbl, d_lbl))

        lay.addStretch()

        # Bottom Version Tag
        ver_badge = QLabel(f"v{__version__} • Commercial Edition")
        ver_badge.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 10px;
                font-weight: 600;
                background-color: rgba(255, 255, 255, 0.04);
                padding: 6px 10px;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        ver_badge.setAlignment(Qt.AlignCenter)
        lay.addWidget(ver_badge)

    def set_active_step(self, current_step: int):
        for i, (num_lbl, t_lbl, d_lbl) in enumerate(self.step_widgets):
            if i < current_step:
                num_lbl.setText("✓")
                num_lbl.setStyleSheet("""
                    background-color: #10B981;
                    color: #FFFFFF;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 12px;
                    border: none;
                """)
                t_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: 600; background: transparent;")
            elif i == current_step:
                num_lbl.setText(str(i + 1))
                num_lbl.setStyleSheet("""
                    background-color: #E11D48;
                    color: #FFFFFF;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 12px;
                    border: 2px solid #FDA4AF;
                """)
                t_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700; background: transparent;")
            else:
                num_lbl.setText(str(i + 1))
                num_lbl.setStyleSheet("""
                    background-color: #1E293B;
                    color: #64748B;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 12px;
                    border: 1px solid rgba(255,255,255,0.06);
                """)
                t_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500; background: transparent;")


# ── Main Wizard Window ─────────────────────────────────────────────────────

class ModernInstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(880, 590)

        self._drag_pos = None
        self._server_mode = "server"  # "server" or "client"
        self._connection_tested = False
        self._credentials = {}

        # Root layout with padding for window shadow
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(10, 10, 10, 10)

        # Main glass frame
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("mainFrame")
        self.main_frame.setStyleSheet("""
            QFrame#mainFrame {
                background-color: #0F172A;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.main_frame.setGraphicsEffect(shadow)

        frame_layout = QHBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # 1. Left Stepper Column
        self.stepper = StepIndicator(self.main_frame)
        frame_layout.addWidget(self.stepper)

        # 2. Right Content Column
        right_container = QWidget(self.main_frame)
        right_container.setStyleSheet("background: transparent;")
        right_lay = QVBoxLayout(right_container)
        right_lay.setContentsMargins(32, 22, 32, 22)
        right_lay.setSpacing(14)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        self.title_bar_lbl = QLabel("Jayraldine's Catering Setup")
        self.title_bar_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
        top_bar.addWidget(self.title_bar_lbl)
        top_bar.addStretch()

        min_btn = QPushButton("—")
        min_btn.setFixedSize(28, 28)
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #94A3B8; font-size: 13px; font-weight: bold; border-radius: 6px; }
            QPushButton:hover { background: rgba(255,255,255,0.08); color: #FFFFFF; }
        """)
        min_btn.clicked.connect(self.showMinimized)
        top_bar.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #94A3B8; font-size: 12px; font-weight: bold; border-radius: 6px; }
            QPushButton:hover { background: rgba(239, 68, 68, 0.2); color: #EF4444; }
        """)
        close_btn.clicked.connect(self.close)
        top_bar.addWidget(close_btn)

        right_lay.addLayout(top_bar)

        # Stacked Pages (0: Welcome, 1: Server Role, 2: Preferences, 3: Progress, 4: Complete)
        self.stack = QStackedWidget()
        right_lay.addWidget(self.stack, 1)

        # Build Pages
        self._init_welcome_page()
        self._init_server_role_page()
        self._init_preferences_page()
        self._init_progress_page()
        self._init_completed_page()

        frame_layout.addWidget(right_container, 1)
        root_lay.addWidget(self.main_frame)

        self.set_step(0)

    # ── Window Dragging ─────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 60:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def set_step(self, step: int):
        self.stepper.set_active_step(step)
        self.stack.setCurrentIndex(step)

    # ── Page 0: Welcome Page ────────────────────────────────────────
    def _init_welcome_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)

        header = QLabel("Ready to Install")
        header.setStyleSheet("color: #F8FAFC; font-size: 22px; font-weight: 800;")
        lay.addWidget(header)

        sub = QLabel("Jayraldine's Catering & Event Management System provides centralized multi-PC booking, financial ledger, AI assistant, and tablet kiosk sync.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 140%;")
        lay.addWidget(sub)

        # Features highlight cards
        cards_grid = QVBoxLayout()
        cards_grid.setSpacing(6)

        highlights = [
            ("🖥️ Centralized PostgreSQL Server", "One main PC acts as central database server for all client laptops and tablets"),
            ("🔒 User Accounts & Module RBAC", "Role-based access control protecting financials, customers, and reports"),
            ("📱 Offline Tablet Kiosk & Auto-Sync", "Take orders standalone on tablets off-site and sync back without duplicates"),
            ("🤖 Chef Jay AI Assistant Gating", "AI actions strictly enforced by user permission tiers")
        ]

        for i, (title, desc) in enumerate(highlights):
            card = QFrame()
            card.setObjectName(f"welcome_card_{i}")
            card.setStyleSheet(f"""
                QFrame#welcome_card_{i} {{
                    background-color: rgba(30, 41, 59, 0.55);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }}
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(14, 8, 14, 8)
            c_lay.setSpacing(12)

            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 700; border: none; background: transparent;")
            d_lbl = QLabel(desc)
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; border: none; background: transparent;")

            c_lay.addWidget(t_lbl)
            c_lay.addWidget(d_lbl, 1)
            cards_grid.addWidget(card)

        lay.addLayout(cards_grid)
        lay.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        continue_btn = QPushButton("Continue Setup  →")
        continue_btn.setCursor(Qt.PointingHandCursor)
        continue_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #F43F5E);
                border: none;
                color: #FFFFFF;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 700;
                border-radius: 8px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BE123C, stop:1 #E11D48); }
        """)
        continue_btn.clicked.connect(lambda: self.set_step(1))
        btn_row.addWidget(continue_btn)

        lay.addLayout(btn_row)
        self.stack.addWidget(page)

    # ── Page 1: Server Role Selection ──────────────────────────────
    def _init_server_role_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(16)

        header = QLabel("Choose Installation Role")
        header.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 800;")
        lay.addWidget(header)

        sub = QLabel("Select whether this machine will host the primary PostgreSQL database or connect over your local network as a client station.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 130%;")
        lay.addWidget(sub)

        # Role Options Cards
        self.role_btn_group = QButtonGroup(self)

        # Card 1: Server
        self.card_server = QFrame()
        self.card_server.setObjectName("card_server")
        self.card_server.setCursor(Qt.PointingHandCursor)
        self.card_server.setStyleSheet("""
            QFrame#card_server {
                background-color: rgba(30, 41, 59, 0.7);
                border: 2px solid #E11D48;
                border-radius: 12px;
            }
        """)
        c1_lay = QHBoxLayout(self.card_server)
        c1_lay.setContentsMargins(18, 16, 18, 16)
        c1_lay.setSpacing(16)

        self.rb_server = QRadioButton()
        self.rb_server.setChecked(True)
        self.role_btn_group.addButton(self.rb_server)
        c1_lay.addWidget(self.rb_server)

        t_col1 = QVBoxLayout()
        t_col1.setSpacing(4)
        t1 = QLabel("🖥️  Set up as Central Database Server (Main PC)")
        t1.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: 700; border: none; background: transparent;")
        d1 = QLabel("This PC hosts the primary PostgreSQL database for all client laptops and tablets.<br>Auto-installs PostgreSQL if missing, opens firewall port 5432, and displays connection credentials upon completion.")
        d1.setWordWrap(True)
        d1.setStyleSheet("color: #94A3B8; font-size: 11.5px; border: none; background: transparent;")
        t_col1.addWidget(t1)
        t_col1.addWidget(d1)
        c1_lay.addLayout(t_col1, 1)

        lay.addWidget(self.card_server)

        # Card 2: Client
        self.card_client = QFrame()
        self.card_client.setObjectName("card_client")
        self.card_client.setCursor(Qt.PointingHandCursor)
        self.card_client.setStyleSheet("""
            QFrame#card_client {
                background-color: rgba(30, 41, 59, 0.35);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
        """)
        c2_lay = QHBoxLayout(self.card_client)
        c2_lay.setContentsMargins(18, 16, 18, 16)
        c2_lay.setSpacing(16)

        self.rb_client = QRadioButton()
        self.role_btn_group.addButton(self.rb_client)
        c2_lay.addWidget(self.rb_client)

        t_col2 = QVBoxLayout()
        t_col2.setSpacing(4)
        t2 = QLabel("🔗  Connect to Server (Client Laptop / Station)")
        t2.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: 700; border: none; background: transparent;")
        d2 = QLabel("This machine connects to an existing Central Database Server over the LAN.<br>Skips local database setup. Prompts for the server's IP address and credentials.")
        d2.setWordWrap(True)
        d2.setStyleSheet("color: #94A3B8; font-size: 11.5px; border: none; background: transparent;")
        t_col2.addWidget(t2)
        t_col2.addWidget(d2)
        c2_lay.addLayout(t_col2, 1)

        lay.addWidget(self.card_client)

        # Card click handlers (click anywhere on card to select)
        self.card_server.mousePressEvent = lambda ev: self.rb_server.setChecked(True)
        self.card_client.mousePressEvent = lambda ev: self.rb_client.setChecked(True)
        self.rb_server.toggled.connect(self._on_role_toggled)
        self.rb_client.toggled.connect(self._on_role_toggled)

        lay.addStretch()

        # Nav row
        btn_row = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #94A3B8;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
            }
            QPushButton:hover { color: #FFFFFF; background: rgba(255, 255, 255, 0.05); }
        """)
        back_btn.clicked.connect(lambda: self.set_step(0))
        btn_row.addWidget(back_btn)

        btn_row.addStretch()

        next_btn = QPushButton("Next: Preferences →")
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #F43F5E);
                border: none;
                color: #FFFFFF;
                padding: 10px 26px;
                font-size: 13px;
                font-weight: 700;
                border-radius: 8px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BE123C, stop:1 #E11D48); }
        """)
        next_btn.clicked.connect(self._to_preferences_page)
        btn_row.addWidget(next_btn)

        lay.addLayout(btn_row)
        self.stack.addWidget(page)

    def _on_role_toggled(self):
        if self.rb_server.isChecked():
            self._server_mode = "server"
            self.card_server.setStyleSheet("QFrame#card_server { background-color: rgba(30, 41, 59, 0.7); border: 2px solid #E11D48; border-radius: 12px; }")
            self.card_client.setStyleSheet("QFrame#card_client { background-color: rgba(30, 41, 59, 0.35); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; }")
        else:
            self._server_mode = "client"
            self.card_client.setStyleSheet("QFrame#card_client { background-color: rgba(30, 41, 59, 0.7); border: 2px solid #E11D48; border-radius: 12px; }")
            self.card_server.setStyleSheet("QFrame#card_server { background-color: rgba(30, 41, 59, 0.35); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; }")

    def _to_preferences_page(self):
        self._update_preferences_view()
        self.set_step(2)

    # ── Page 2: Preferences / Configuration ─────────────────────────
    def _init_preferences_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)

        self.pref_header = QLabel("Installation Preferences")
        self.pref_header.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 800;")
        lay.addWidget(self.pref_header)

        # Directory Selector
        dir_lbl = QLabel("Installation Location:")
        dir_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        lay.addWidget(dir_lbl)

        dir_box = QHBoxLayout()
        self.path_edit = QLineEdit(str(get_default_install_dir()))
        self.path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                padding: 7px 10px;
                font-size: 12px;
                border-radius: 7px;
            }
        """)
        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 600;
                border-radius: 7px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        browse_btn.clicked.connect(self._browse_folder)
        dir_box.addWidget(self.path_edit, 1)
        dir_box.addWidget(browse_btn)
        lay.addLayout(dir_box)

        # Shortcuts Checkboxes
        opts_box = QHBoxLayout()
        cb_style = """
            QCheckBox { color: #E2E8F0; font-size: 12px; font-weight: 600; spacing: 6px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #475569; background-color: #1E293B; }
            QCheckBox::indicator:checked { background-color: #E11D48; border-color: #E11D48; }
        """
        self.cb_desktop = QCheckBox("Desktop Shortcut")
        self.cb_desktop.setChecked(True)
        self.cb_desktop.setStyleSheet(cb_style)
        opts_box.addWidget(self.cb_desktop)

        self.cb_start = QCheckBox("Start Menu Shortcut")
        self.cb_start.setChecked(True)
        self.cb_start.setStyleSheet(cb_style)
        opts_box.addWidget(self.cb_start)
        opts_box.addStretch()
        lay.addLayout(opts_box)

        # Dynamic Section: Server Mode vs Client Mode
        self.dynamic_stack = QStackedWidget()

        # Dynamic Page 0: Server Mode Info & SQLite Data Migration
        server_info_widget = QFrame()
        server_info_widget.setObjectName("server_info_widget")
        server_info_widget.setStyleSheet("QFrame#server_info_widget { background-color: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; }")
        s_inf_lay = QVBoxLayout(server_info_widget)
        s_inf_lay.setContentsMargins(16, 12, 16, 12)
        s_inf_lay.setSpacing(10)

        si_t = QLabel("🛠️  Server Provisioning & Existing Data Migration:")
        si_t.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 700; border: none; background: transparent;")
        si_d = QLabel("• PostgreSQL will be configured on port 5432 with auto-firewall rules for LAN stations & tablets.<br>• Default scoped user 'jayraldines_app' and primary administrator account 'admin' will be created.")
        si_d.setWordWrap(True)
        si_d.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 135%; border: none; background: transparent;")
        s_inf_lay.addWidget(si_t)
        s_inf_lay.addWidget(si_d)

        # SQLite Data Migration Sub-Card
        from utils.sqlite_to_postgres import find_candidate_sqlite_databases, inspect_sqlite_database
        detected_sqlite_dbs = find_candidate_sqlite_databases()
        default_sqlite = detected_sqlite_dbs[0] if detected_sqlite_dbs else None

        self.cb_migrate_sqlite = QCheckBox("Import existing local SQLite client data into PostgreSQL server")
        self.cb_migrate_sqlite.setChecked(bool(default_sqlite))
        self.cb_migrate_sqlite.setStyleSheet(cb_style)
        s_inf_lay.addWidget(self.cb_migrate_sqlite)

        sqlite_box = QHBoxLayout()
        sqlite_box.setSpacing(8)
        self.sqlite_file_edit = QLineEdit(str(default_sqlite) if default_sqlite else "")
        self.sqlite_file_edit.setPlaceholderText("Path to existing SQLite file (catering.db / database.db)...")
        self.sqlite_file_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                padding: 6px 10px;
                font-size: 11.5px;
                border-radius: 6px;
            }
        """)
        browse_sqlite_btn = QPushButton("Browse DB...")
        browse_sqlite_btn.setCursor(Qt.PointingHandCursor)
        browse_sqlite_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                padding: 6px 12px;
                font-size: 11.5px;
                font-weight: 600;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        browse_sqlite_btn.clicked.connect(self._browse_sqlite_file)
        sqlite_box.addWidget(self.sqlite_file_edit, 1)
        sqlite_box.addWidget(browse_sqlite_btn)
        s_inf_lay.addLayout(sqlite_box)

        self.sqlite_stat_lbl = QLabel()
        self.sqlite_stat_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        s_inf_lay.addWidget(self.sqlite_stat_lbl)

        self._update_sqlite_stat_label(default_sqlite)
        self.sqlite_file_edit.textChanged.connect(lambda txt: self._update_sqlite_stat_label(Path(txt.strip()) if txt.strip() else None))

        self.dynamic_stack.addWidget(server_info_widget)

        # Dynamic Page 1: Client Mode Connection Form
        client_form_widget = QFrame()
        client_form_widget.setObjectName("client_form_widget")
        client_form_widget.setStyleSheet("QFrame#client_form_widget { background-color: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; }")
        c_form_lay = QVBoxLayout(client_form_widget)
        c_form_lay.setContentsMargins(16, 12, 16, 12)
        c_form_lay.setSpacing(8)

        cf_t = QLabel("🔗  Connect to Server Details (from Server Credentials):")
        cf_t.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 700; border: none; background: transparent;")
        c_form_lay.addWidget(cf_t)

        input_style = """
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                padding: 6px 10px;
                font-size: 12px;
                border-radius: 6px;
            }
        """

        # Row 1: Host IP & Port
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.client_host_edit = QLineEdit("192.168.1.")
        self.client_host_edit.setPlaceholderText("Server LAN IP (e.g. 192.168.1.100)")
        self.client_host_edit.setStyleSheet(input_style)

        self.client_port_edit = QLineEdit("5432")
        self.client_port_edit.setFixedWidth(70)
        self.client_port_edit.setPlaceholderText("Port")
        self.client_port_edit.setStyleSheet(input_style)
        row1.addWidget(QLabel("Host IP:"))
        row1.addWidget(self.client_host_edit, 1)
        row1.addWidget(QLabel("Port:"))
        row1.addWidget(self.client_port_edit)
        c_form_lay.addLayout(row1)

        # Row 2: User & Password
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.client_user_edit = QLineEdit("jayraldines_app")
        self.client_user_edit.setStyleSheet(input_style)

        self.client_pwd_edit = QLineEdit()
        self.client_pwd_edit.setEchoMode(QLineEdit.Password)
        self.client_pwd_edit.setPlaceholderText("Database Password")
        self.client_pwd_edit.setStyleSheet(input_style)

        row2.addWidget(QLabel("User:"))
        row2.addWidget(self.client_user_edit)
        row2.addWidget(QLabel("Password:"))
        row2.addWidget(self.client_pwd_edit, 1)
        c_form_lay.addLayout(row2)

        # Row 3: Test Connection Button & Status
        row3 = QHBoxLayout()
        self.test_conn_btn = QPushButton("Test Connection")
        self.test_conn_btn.setCursor(Qt.PointingHandCursor)
        self.test_conn_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: none;
                color: #FFFFFF;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.test_conn_btn.clicked.connect(self._test_client_connection)
        row3.addWidget(self.test_conn_btn)

        self.test_status_lbl = QLabel("Please test connection before installing.")
        self.test_status_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        row3.addWidget(self.test_status_lbl, 1)
        c_form_lay.addLayout(row3)

        self.dynamic_stack.addWidget(client_form_widget)
        lay.addWidget(self.dynamic_stack)

        lay.addStretch()

        # Nav row
        btn_row = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #94A3B8;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
            }
            QPushButton:hover { color: #FFFFFF; background: rgba(255, 255, 255, 0.05); }
        """)
        back_btn.clicked.connect(lambda: self.set_step(1))
        btn_row.addWidget(back_btn)

        btn_row.addStretch()

        self.start_install_btn = QPushButton("Start Installation →")
        self.start_install_btn.setCursor(Qt.PointingHandCursor)
        self.start_install_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #F43F5E);
                border: none;
                color: #FFFFFF;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 700;
                border-radius: 8px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BE123C, stop:1 #E11D48); }
        """)
        self.start_install_btn.clicked.connect(self._start_installation)
        btn_row.addWidget(self.start_install_btn)

        lay.addLayout(btn_row)
        self.stack.addWidget(page)

    def _update_preferences_view(self):
        if self._server_mode == "server":
            self.dynamic_stack.setCurrentIndex(0)
            self.start_install_btn.setEnabled(True)
        else:
            self.dynamic_stack.setCurrentIndex(1)
            # Require connection test if client
            self.start_install_btn.setEnabled(self._connection_tested)

    def _test_client_connection(self):
        host = self.client_host_edit.text().strip()
        port_str = self.client_port_edit.text().strip()
        user = self.client_user_edit.text().strip()
        pwd = self.client_pwd_edit.text()

        try:
            port = int(port_str)
        except ValueError:
            self.test_status_lbl.setText("❌ Invalid port number.")
            self.test_status_lbl.setStyleSheet("color: #EF4444; font-size: 11px;")
            return

        self.test_status_lbl.setText("Testing connection...")
        self.test_status_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
        QApplication.processEvents()

        ok, msg = test_postgres_connection(
            host=host,
            port=port,
            dbname="jayraldines_catering",
            user=user,
            password=pwd,
            timeout=5
        )

        if ok:
            self._connection_tested = True
            self.test_status_lbl.setText("✅ Connection successful!")
            self.test_status_lbl.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
            self.start_install_btn.setEnabled(True)
        else:
            self._connection_tested = False
            self.test_status_lbl.setText(f"❌ Failed: {msg}")
            self.test_status_lbl.setStyleSheet("color: #EF4444; font-size: 11px;")
            self.start_install_btn.setEnabled(False)

    def _browse_sqlite_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Existing SQLite Database", "", "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*.*)")
        if f:
            self.sqlite_file_edit.setText(f)
            self.cb_migrate_sqlite.setChecked(True)

    def _update_sqlite_stat_label(self, sqlite_path: Optional[Path]):
        if not sqlite_path or not sqlite_path.exists():
            self.sqlite_stat_lbl.setText("No local SQLite database selected.")
            self.sqlite_stat_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
            return

        from utils.sqlite_to_postgres import inspect_sqlite_database
        counts = inspect_sqlite_database(sqlite_path)
        if counts:
            parts = []
            if counts.get("customers"):
                parts.append(f"{counts['customers']} customers")
            if counts.get("bookings"):
                parts.append(f"{counts['bookings']} bookings")
            if counts.get("invoices"):
                parts.append(f"{counts['invoices']} invoices")
            if counts.get("menu_items"):
                parts.append(f"{counts['menu_items']} menu items")
            if counts.get("packages"):
                parts.append(f"{counts['packages']} packages")
            summary_str = ", ".join(parts) if parts else "Database verified"
            self.sqlite_stat_lbl.setText(f"📦 Ready to migrate: {summary_str} ({sqlite_path.name})")
            self.sqlite_stat_lbl.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
        else:
            self.sqlite_stat_lbl.setText(f"Selected: {sqlite_path.name}")
            self.sqlite_stat_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Directory", self.path_edit.text())
        if folder:
            self.path_edit.setText(str(Path(folder) / "JayraldinesCatering"))

    # ── Page 3: Installation Progress ───────────────────────────────
    def _init_progress_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 20, 0, 0)
        lay.setSpacing(14)

        header = QLabel("Installing Jayraldine's Catering")
        header.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 800;")
        lay.addWidget(header)

        sub = QLabel("Please wait while application files are extracted and database configurations are provisioned.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        lay.addWidget(sub)

        lay.addSpacing(14)

        self.status_lbl = QLabel("Preparing installation files...")
        self.status_lbl.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        lay.addWidget(self.status_lbl)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E293B;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #FB7185);
                border-radius: 5px;
            }
        """)
        lay.addWidget(self.progress_bar)

        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setAlignment(Qt.AlignRight)
        self.pct_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        lay.addWidget(self.pct_lbl)

        lay.addStretch()
        self.stack.addWidget(page)

    def _start_installation(self):
        dest_dir = Path(self.path_edit.text())
        create_desktop = self.cb_desktop.isChecked()
        create_start = self.cb_start.isChecked()
        client_cfg = {}
        if self._server_mode == "client":
            client_cfg = {
                "host": self.client_host_edit.text().strip(),
                "port": int(self.client_port_edit.text().strip() or 5432),
                "dbname": "jayraldines_catering",
                "user": self.client_user_edit.text().strip(),
                "password": self.client_pwd_edit.text(),
            }

        sqlite_source = None
        if self._server_mode == "server" and hasattr(self, "cb_migrate_sqlite") and self.cb_migrate_sqlite.isChecked():
            path_str = self.sqlite_file_edit.text().strip()
            if path_str and Path(path_str).exists():
                sqlite_source = Path(path_str)

        self.set_step(3)
        self.worker = ExtractWorker(
            dest_dir=dest_dir,
            create_desktop=create_desktop,
            create_start=create_start,
            server_mode=self._server_mode,
            client_config=client_cfg,
            clean_db=True,
            sqlite_source_path=sqlite_source
        )
        self.worker.progress.connect(self._on_install_progress)
        self.worker.finished.connect(self._on_install_finished)
        self.worker.start()

    def _on_install_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.pct_lbl.setText(f"{val}%")
        self.status_lbl.setText(msg)

    def _on_install_finished(self, ok: bool, err: str, creds: dict):
        if hasattr(self, "worker") and self.worker:
            try:
                self.worker.quit()
                self.worker.wait(500)
            except Exception:
                pass
        if ok:
            self._credentials = creds
            self._populate_completed_page(creds)
            self.set_step(4)
        else:
            self.status_lbl.setText(f"Installation failed: {err}")
            self.status_lbl.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;")

    # ── Page 4: Installation Complete ───────────────────────────────
    def _init_completed_page(self):
        self.completed_page = QWidget()
        self.completed_lay = QVBoxLayout(self.completed_page)
        self.completed_lay.setContentsMargins(0, 8, 0, 0)
        self.completed_lay.setSpacing(10)

        # Header Badge
        badge_row = QHBoxLayout()
        check_icon = QLabel("✓")
        check_icon.setFixedSize(38, 38)
        check_icon.setAlignment(Qt.AlignCenter)
        check_icon.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10B981, stop:1 #059669);
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
                border-radius: 19px;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
        """)
        badge_row.addWidget(check_icon)

        self.complete_header = QLabel("Installation & Configuration Complete!")
        self.complete_header.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: 800;")
        badge_row.addWidget(self.complete_header)
        badge_row.addStretch()
        self.completed_lay.addLayout(badge_row)

        # Dynamic Content Container (Credentials Card or Client Summary)
        self.creds_container = QWidget()
        self.creds_lay = QVBoxLayout(self.creds_container)
        self.creds_lay.setContentsMargins(0, 0, 0, 0)
        self.creds_lay.setSpacing(8)
        self.completed_lay.addWidget(self.creds_container)

        self.cb_launch_now = QCheckBox("Launch Jayraldine's Catering immediately")
        self.cb_launch_now.setChecked(True)
        self.cb_launch_now.setStyleSheet("""
            QCheckBox { color: #F43F5E; font-size: 12px; font-weight: 700; spacing: 6px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #E11D48; background-color: #1E293B; }
            QCheckBox::indicator:checked { background-color: #E11D48; border-color: #E11D48; }
        """)
        self.completed_lay.addWidget(self.cb_launch_now)

        self.completed_lay.addStretch()

        # Bottom Buttons
        btn_row = QHBoxLayout()
        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.setCursor(Qt.PointingHandCursor)
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #94A3B8;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
            }
            QPushButton:hover { color: #FFFFFF; background: rgba(255, 255, 255, 0.05); }
        """)
        open_folder_btn.clicked.connect(self._open_app_folder)
        btn_row.addWidget(open_folder_btn)

        btn_row.addStretch()

        finish_btn = QPushButton("Finish")
        finish_btn.setCursor(Qt.PointingHandCursor)
        finish_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
                border: none;
                color: #FFFFFF;
                padding: 9px 24px;
                font-size: 13px;
                font-weight: 700;
                border-radius: 6px;
            }
            QPushButton:hover { background: #047857; }
        """)
        finish_btn.clicked.connect(self._on_finish_clicked)
        btn_row.addWidget(finish_btn)

        self.completed_lay.addLayout(btn_row)
        self.stack.addWidget(self.completed_page)

    def _populate_completed_page(self, creds: dict):
        # Clear existing dynamic widgets in creds_container
        while self.creds_lay.count():
            item = self.creds_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if creds.get("role") == "server":
            card = QFrame()
            card.setObjectName("server_cred_card")
            card.setStyleSheet("""
                QFrame#server_cred_card {
                    background-color: #020617;
                    border: 1px solid #10B981;
                    border-radius: 10px;
                }
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(16, 14, 16, 14)
            c_lay.setSpacing(8)

            title = QLabel("🔑  Central Server Credentials (Save or Print Now)")
            title.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 800; border: none; background: transparent;")
            c_lay.addWidget(title)

            # Details Grid
            details_text = (
                f"• Central DB Host IP     : {creds.get('host', '127.0.0.1')}\n"
                f"• PostgreSQL DB Port     : {creds.get('port', 5432)}\n"
                f"• Database Name          : {creds.get('dbname', 'jayraldines_catering')}\n"
                f"• Scoped DB User         : {creds.get('db_user', 'jayraldines_app')}\n"
                f"• Scoped DB Password     : {creds.get('db_password', '')}\n"
                f"---------------------------------------------------\n"
                f"• Tablet Kiosk Sync URL  : http://{creds.get('host', '127.0.0.1')}:8000\n"
                f"• Tablet Web Kiosk URL   : http://{creds.get('host', '127.0.0.1')}:8085\n"
                f"---------------------------------------------------\n"
                f"• App Login Username     : {creds.get('admin_user', 'admin')}\n"
                f"• App Admin Password     : {creds.get('admin_password', '')}"
            )
            txt_lbl = QLabel(details_text)
            txt_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            txt_lbl.setStyleSheet("color: #F8FAFC; font-family: monospace; font-size: 11px; background: #0F172A; padding: 8px; border-radius: 6px; border: none;")
            c_lay.addWidget(txt_lbl)

            # Buttons: Save to file & Copy
            btn_box = QHBoxLayout()
            save_file_btn = QPushButton("📄 Save to credentials.txt")
            save_file_btn.setCursor(Qt.PointingHandCursor)
            save_file_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    color: #F8FAFC;
                    padding: 7px 14px;
                    font-size: 11.5px;
                    font-weight: 600;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #334155; }
            """)
            save_file_btn.clicked.connect(self._save_credentials_file)
            btn_box.addWidget(save_file_btn)

            copy_btn = QPushButton("📋 Copy All to Clipboard")
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    color: #F8FAFC;
                    padding: 7px 14px;
                    font-size: 11.5px;
                    font-weight: 600;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #334155; }
            """)
            copy_btn.clicked.connect(self._copy_credentials_to_clipboard)
            btn_box.addWidget(copy_btn)
            btn_box.addStretch()

            c_lay.addLayout(btn_box)

            # SQLite Migration summary badge if data was migrated
            mig_stats = creds.get("migrated_stats") or {}
            total_migrated = sum(mig_stats.values()) if isinstance(mig_stats, dict) else 0
            if total_migrated > 0:
                mig_box = QFrame()
                mig_box.setObjectName("mig_summary_box")
                mig_box.setStyleSheet("""
                    QFrame#mig_summary_box {
                        background-color: rgba(16, 185, 129, 0.12);
                        border: 1px solid #10B981;
                        border-radius: 6px;
                    }
                """)
                m_lay = QHBoxLayout(mig_box)
                m_lay.setContentsMargins(10, 6, 10, 6)
                m_txt = QLabel(
                    f"📦 <b>SQLite Data Migrated:</b> {mig_stats.get('customers', 0)} customers, "
                    f"{mig_stats.get('bookings', 0)} bookings, {mig_stats.get('invoices', 0)} invoices, "
                    f"{mig_stats.get('packages', 0)} packages imported into PostgreSQL."
                )
                m_txt.setWordWrap(True)
                m_txt.setStyleSheet("color: #6EE7B7; font-size: 11px; line-height: 135%; border: none; background: transparent;")
                m_lay.addWidget(m_txt)
                c_lay.addWidget(mig_box)

            self.creds_lay.addWidget(card)
        else:
            # Client info card
            card = QFrame()
            card.setObjectName("client_cred_card")
            card.setStyleSheet("""
                QFrame#client_cred_card {
                    background-color: rgba(30, 41, 59, 0.5);
                    border: 1px solid #0284C7;
                    border-radius: 8px;
                }
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(16, 14, 16, 14)
            c_lay.setSpacing(6)
            c_t = QLabel("🔗  Connected to Central Database Server:")
            c_t.setStyleSheet("color: #38BDF8; font-size: 13px; font-weight: 700; border: none; background: transparent;")
            c_d = QLabel(
                f"Server Host: {creds.get('host')}:{creds.get('port')}\n"
                f"Database: {creds.get('dbname')}\n"
                f"User: {creds.get('db_user')}\n\n"
                "Launch the application and sign in with your staff or administrator account."
            )
            c_d.setStyleSheet("color: #F8FAFC; font-size: 11.5px; line-height: 140%; border: none; background: transparent;")
            c_lay.addWidget(c_t)
            c_lay.addWidget(c_d)
            self.creds_lay.addWidget(card)

    def _get_formatted_credentials_text(self) -> str:
        creds = self._credentials
        host = creds.get('host', '127.0.0.1')
        return (
            "=====================================================\n"
            "   JAYRALDINE'S CATERING - SERVER CREDENTIALS\n"
            "=====================================================\n\n"
            "[CENTRAL DATABASE CONNECTION - FOR CLIENT PCs & LAPTOPS]\n"
            f"Server Host IP           : {host}\n"
            f"Database Port            : {creds.get('port', 5432)}\n"
            f"Database Name            : {creds.get('dbname', 'jayraldines_catering')}\n"
            f"Scoped DB User           : {creds.get('db_user', 'jayraldines_app')}\n"
            f"Scoped DB Password       : {creds.get('db_password', '')}\n\n"
            "[TABLET KIOSK & ANDROID APP CONNECTION]\n"
            f"Tablet Server Host IP    : {host}\n"
            f"Tablet Sync Port         : 8000\n"
            f"Tablet Sync URL          : http://{host}:8000\n"
            f"Tablet Web Kiosk URL     : http://{host}:8085\n\n"
            "Instructions for Tablet Kiosk:\n"
            f"1. Connect the tablet to the same Wi-Fi as this PC.\n"
            f"2. Open the Tablet app -> tap Settings -> enter Server Host: {host}\n"
            f"3. Tap 'Test Connection' -> Sync is instantly active!\n\n"
            "[APPLICATION LOGIN - PRIMARY ADMINISTRATOR]\n"
            f"Username                 : {creds.get('admin_user', 'admin')}\n"
            f"Admin Password           : {creds.get('admin_password', '')}\n\n"
            "Save this file in a secure location.\n"
        )

    def _save_credentials_file(self):
        content = self._get_formatted_credentials_text()
        default_path = str(Path.home() / "Desktop" / "jayraldines_server_credentials.txt")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Server Credentials",
            default_path,
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "Saved", f"Credentials saved successfully to:\n{file_path}")
            except Exception as exc:
                QMessageBox.warning(self, "Error", f"Could not save file: {exc}")

    def _copy_credentials_to_clipboard(self):
        content = self._get_formatted_credentials_text()
        cb = QApplication.clipboard()
        if cb:
            cb.setText(content)
            QMessageBox.information(self, "Copied", "Credentials copied to clipboard!")

    def _open_app_folder(self):
        dest_dir = Path(self.path_edit.text())
        if dest_dir.exists():
            os.startfile(str(dest_dir))

    def _on_finish_clicked(self):
        if self.cb_launch_now.isChecked():
            dest_dir = Path(self.path_edit.text())
            exe = dest_dir / "JayraldinesCatering.exe"
            if exe.exists():
                try:
                    os.startfile(str(exe))
                except Exception:
                    DETACHED_PROCESS = 0x00000008
                    subprocess.Popen([str(exe)], cwd=str(dest_dir), close_fds=True, creationflags=DETACHED_PROCESS)
        self._terminate_installer()

    def closeEvent(self, event):
        self._terminate_installer()
        event.accept()

    def _terminate_installer(self):
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            try:
                self.worker.quit()
                self.worker.wait(500)
            except Exception:
                pass
        self.close()
        QApplication.quit()
        sys.exit(0)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ModernInstallerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
