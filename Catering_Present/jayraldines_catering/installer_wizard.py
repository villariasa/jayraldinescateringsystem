"""
Jayraldine's Catering - Modern Windows Application Installer.
Designed with a sleek, frameless glassmorphic interface, interactive 5-step stepper,
and automated Embedded SQLite Database & LAN Sync Server configuration.
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
    get_config_dir,
    get_local_lan_ip,
    save_db_config,
    load_db_config,
    get_db_config,
    test_sqlite_sync_connection,
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
        clean_db: bool = False,
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

    def _find_asset_file(self, filename: str) -> Optional[Path]:
        """Locates bundled or repository database/asset files across candidate paths."""
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

            # ── 2. Database Setup (100% SQLite) ──────────────────────────
            appdata_data_dir = get_config_dir() / "data"
            appdata_data_dir.mkdir(parents=True, exist_ok=True)
            target_db = appdata_data_dir / "catering.db"

            dest_data_dir = self.dest_dir / "data"
            dest_data_dir.mkdir(parents=True, exist_ok=True)
            dest_db = dest_data_dir / "catering.db"

            if self.server_mode == "server":
                self.progress.emit(65, "Provisioning Embedded SQLite Database Engine...")
                
                # Check if custom SQLite backup was provided
                if self.sqlite_source_path and Path(self.sqlite_source_path).exists():
                    self.progress.emit(70, f"Restoring selected SQLite database ({Path(self.sqlite_source_path).name})...")
                    shutil.copy2(Path(self.sqlite_source_path), target_db)
                elif target_db.exists() and not self.clean_db:
                    self.progress.emit(70, "Preserving existing SQLite database records...")
                else:
                    self.progress.emit(70, "Installing pre-populated SQLite database...")
                    bundled_db = self._find_asset_file("catering.db")
                    if bundled_db and bundled_db.exists():
                        shutil.copy2(bundled_db, target_db)
                    else:
                        from utils.sqlite_schema import init_sqlite_db
                        init_sqlite_db(target_db)

                # Mirror database to dest_dir
                try:
                    shutil.copy2(target_db, dest_db)
                except Exception:
                    pass

                # Inspect SQLite records
                rec_counts = {}
                try:
                    import sqlite3
                    conn = sqlite3.connect(str(target_db))
                    cur = conn.cursor()
                    for t in ["bookings", "customers", "invoices", "menu_items", "packages"]:
                        try:
                            cur.execute(f"SELECT COUNT(*) FROM {t}")
                            row = cur.fetchone()
                            if row:
                                rec_counts[t] = int(row[0])
                        except Exception:
                            pass
                    conn.close()
                except Exception:
                    pass

                # Configure Network Profile & Windows Firewall for LAN Sync & Tablets
                self.progress.emit(82, "Configuring Wi-Fi & Hotspot network profile to Private...")
                configure_network_profile_private()

                self.progress.emit(86, "Configuring Windows Firewall (Ports 8000, 8085)...")
                open_all_kiosk_firewall_ports()

                lan_ip = get_local_lan_ip()

                # Write db_config.json for SQLite Host
                save_db_config(
                    engine="sqlite",
                    host="localhost",
                    port=8000,
                    dbname="catering.db",
                    user="admin",
                    password="",
                    sqlite_path=str(target_db),
                    sync_role="host",
                    sync_port=8000
                )

                self.credentials = {
                    "role": "server",
                    "engine": "sqlite",
                    "host": lan_ip,
                    "port": 8000,
                    "web_port": 8085,
                    "db_path": str(target_db),
                    "admin_user": "admin",
                    "rec_counts": rec_counts,
                }
            else:
                # Client Mode: save config pointing to host server
                self.progress.emit(75, "Configuring Client connection to Main Station...")
                host = self.client_config.get("host", "localhost")
                port = int(self.client_config.get("port", 8000))
                engine = self.client_config.get("engine", "postgres" if port == 5432 else "sqlite")

                # Ensure client local SQLite database cache exists
                bundled_db = self._find_asset_file("catering.db")
                if not target_db.exists() and bundled_db and bundled_db.exists():
                    shutil.copy2(bundled_db, target_db)
                try:
                    shutil.copy2(target_db, dest_db)
                except Exception:
                    pass

                if engine == "postgres" or port == 5432:
                    save_db_config(
                        engine="postgres",
                        host=host,
                        port=port if port else 5432,
                        dbname="jayraldines_catering",
                        user="jayraldines_app",
                        password="password" if "password" in self.client_config else "12345678",
                        sqlite_path=str(target_db),
                        sync_role="client"
                    )
                    self.credentials = {
                        "role": "client",
                        "engine": "postgres",
                        "host": host,
                        "port": port,
                        "dbname": "jayraldines_catering",
                        "user": "jayraldines_app",
                        "db_path": f"{host}:{port}/jayraldines_catering",
                    }
                else:
                    save_db_config(
                        engine="sqlite",
                        host=host,
                        port=port,
                        dbname="catering.db",
                        user="client",
                        password="",
                        sqlite_path=str(target_db),
                        sync_role="client",
                        sync_server_url=f"http://{host}:{port}"
                    )
                    self.credentials = {
                        "role": "client",
                        "engine": "sqlite",
                        "host": host,
                        "port": port,
                        "sync_url": f"http://{host}:{port}",
                        "db_path": str(target_db),
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
            lnk_name = "Jayraldine's Catering.lnk"
            desktop_lnks_cmd = "\n".join([f'del /F /Q "{d / lnk_name}" 2>nul' for d in get_desktop_directories()])
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
            ("Station Role", "Main Station or Client"),
            ("Preferences", "Path & Options"),
            ("Installing", "Unpacking & DB Setup"),
            ("Completed", "Details & Launch")
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

        sub = QLabel("Jayraldine's Catering & Event Management System provides high-performance SQLite booking, financial ledger, AI assistant, and tablet kiosk sync.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 140%;")
        lay.addWidget(sub)

        # Features highlight cards
        cards_grid = QVBoxLayout()
        cards_grid.setSpacing(6)

        highlights = [
            ("⚡ High-Performance Embedded SQLite", "Zero-configuration, ultra-fast 0ms latency database with automated LAN sync hub"),
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

        sub = QLabel("Select whether this machine will run as the primary Main Station (Host) or connect over LAN as a Client Station.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 130%;")
        lay.addWidget(sub)

        # Role Options Cards
        self.role_btn_group = QButtonGroup(self)

        # Card 1: Server / Standalone
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
        t1 = QLabel("🖥️  Standalone / Main Station (Central Host)")
        t1.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: 700; border: none; background: transparent;")
        d1 = QLabel("This PC runs the primary SQLite database (catering.db) with 0ms latency.<br>Automatically activates built-in LAN Sync Hub on port 8000 so laptops and tablet kiosks can synchronize orders.")
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
        t2 = QLabel("🔗  Client Station (LAN Sync Node)")
        t2.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: 700; border: none; background: transparent;")
        d2 = QLabel("This machine connects to the Main Station PC over your local network.<br>Synchronizes orders, customers, and menu catalog directly with the host on port 8000.")
        d2.setWordWrap(True)
        d2.setStyleSheet("color: #94A3B8; font-size: 11.5px; border: none; background: transparent;")
        t_col2.addWidget(t2)
        t_col2.addWidget(d2)
        c2_lay.addLayout(t_col2, 1)

        lay.addWidget(self.card_client)

        # Card click handlers
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

        # Dynamic Page 0: Server Mode Info & SQLite Data Provisioning
        server_info_widget = QFrame()
        server_info_widget.setObjectName("server_info_widget")
        server_info_widget.setStyleSheet("QFrame#server_info_widget { background-color: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; }")
        s_inf_lay = QVBoxLayout(server_info_widget)
        s_inf_lay.setContentsMargins(16, 12, 16, 12)
        s_inf_lay.setSpacing(10)

        si_t = QLabel("🛠️  Embedded SQLite Provisioning & Data Protection:")
        si_t.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 700; border: none; background: transparent;")
        si_d = QLabel("• High-performance SQLite engine (catering.db) with 0ms query latency and WAL journaling mode.<br>• Built-in LAN Sync Hub on port 8000 and Tablet Web Kiosk on port 8085 with auto-configured Windows Firewall rules.")
        si_d.setWordWrap(True)
        si_d.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 135%; border: none; background: transparent;")
        s_inf_lay.addWidget(si_t)
        s_inf_lay.addWidget(si_d)

        # SQLite Data Preservation / Restore
        self.cb_preserve_db = QCheckBox("Preserve existing database records (Keep all bookings, customers & packages)")
        self.cb_preserve_db.setChecked(True)
        self.cb_preserve_db.setStyleSheet(cb_style)
        s_inf_lay.addWidget(self.cb_preserve_db)

        self.cb_migrate_sqlite = QCheckBox("Restore / Import from existing SQLite database or backup file")
        self.cb_migrate_sqlite.setChecked(False)
        self.cb_migrate_sqlite.setStyleSheet(cb_style)
        s_inf_lay.addWidget(self.cb_migrate_sqlite)

        sqlite_box = QHBoxLayout()
        sqlite_box.setSpacing(8)
        self.sqlite_file_edit = QLineEdit()
        self.sqlite_file_edit.setPlaceholderText("Path to existing SQLite file (catering.db / backup.db)...")
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

        self.sqlite_stat_lbl = QLabel("Bundled pre-populated database with complete catering records will be provisioned.")
        self.sqlite_stat_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        s_inf_lay.addWidget(self.sqlite_stat_lbl)

        self.sqlite_file_edit.textChanged.connect(lambda txt: self._update_sqlite_stat_label(Path(txt.strip()) if txt.strip() else None))

        self.dynamic_stack.addWidget(server_info_widget)

        # Dynamic Page 1: Client Mode Connection Form
        client_form_widget = QFrame()
        client_form_widget.setObjectName("client_form_widget")
        client_form_widget.setStyleSheet("QFrame#client_form_widget { background-color: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; }")
        c_form_lay = QVBoxLayout(client_form_widget)
        c_form_lay.setContentsMargins(16, 12, 16, 12)
        c_form_lay.setSpacing(8)

        cf_t = QLabel("🔗  Main Station Connection Details:")
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
        existing_cfg = load_db_config()
        default_ip = str(existing_cfg.get("host", "")).strip()
        if not default_ip or default_ip in ("localhost", "127.0.0.1"):
            default_ip = "192.168.1.32"
        self.client_host_edit = QLineEdit(default_ip)
        self.client_host_edit.setPlaceholderText("Main Station LAN IP (e.g. 192.168.1.32)")
        self.client_host_edit.setStyleSheet(input_style)

        # Default to the LAN Sync Hub port (8000) — the server setup step
        # above always provisions the Main Station as a SQLite LAN sync hub,
        # never a standalone PostgreSQL server, so a fresh client install
        # defaulting to 5432 would point at a server that doesn't exist and
        # silently fall back to an empty local cache (reads work via nothing,
        # writes crash with "No database connection" on first login).
        self.client_port_edit = QLineEdit("8000")
        self.client_port_edit.setFixedWidth(70)
        self.client_port_edit.setPlaceholderText("Port")
        self.client_port_edit.setStyleSheet(input_style)
        row1.addWidget(QLabel("Host IP:"))
        row1.addWidget(self.client_host_edit, 1)
        row1.addWidget(QLabel("Port:"))
        row1.addWidget(self.client_port_edit)
        c_form_lay.addLayout(row1)

        # Quick Preset Buttons
        pills_row = QHBoxLayout()
        pills_row.setSpacing(6)
        btn_p32_pg = QPushButton("192.168.1.32 : 5432 (PostgreSQL Server)")
        btn_p32_pg.setCursor(Qt.PointingHandCursor)
        btn_p32_pg.setStyleSheet("background: #1E293B; color: #38BDF8; font-size: 11px; padding: 2px 8px; border-radius: 4px; border: 1px solid #0284C7; font-weight: bold;")
        def _set_p32():
            self.client_host_edit.setText("192.168.1.32")
            self.client_port_edit.setText("5432")
        btn_p32_pg.clicked.connect(_set_p32)
        pills_row.addWidget(btn_p32_pg)

        btn_p32_sync = QPushButton("192.168.1.32 : 8000 (LAN Hub)")
        btn_p32_sync.setCursor(Qt.PointingHandCursor)
        btn_p32_sync.setStyleSheet("background: #1E293B; color: #94A3B8; font-size: 11px; padding: 2px 8px; border-radius: 4px; border: 1px solid #334155;")
        def _set_p32_sync():
            self.client_host_edit.setText("192.168.1.32")
            self.client_port_edit.setText("8000")
        btn_p32_sync.clicked.connect(_set_p32_sync)
        pills_row.addWidget(btn_p32_sync)

        pills_row.addStretch()
        c_form_lay.addLayout(pills_row)

        # Row 2: Test Connection Button & Status
        row2 = QHBoxLayout()
        self.test_conn_btn = QPushButton("Test LAN Sync Connection")
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
        row2.addWidget(self.test_conn_btn)

        self.test_status_lbl = QLabel("Test connection or proceed (server can be running or configured later).")
        self.test_status_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        row2.addWidget(self.test_status_lbl, 1)
        c_form_lay.addLayout(row2)

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
        else:
            self.dynamic_stack.setCurrentIndex(1)
        self.start_install_btn.setEnabled(True)

    def _test_client_connection(self):
        host = self.client_host_edit.text().strip()
        port_str = self.client_port_edit.text().strip()

        try:
            port = int(port_str)
        except ValueError:
            self.test_status_lbl.setText("❌ Invalid port number.")
            self.test_status_lbl.setStyleSheet("color: #EF4444; font-size: 11px;")
            return

        if port == 5432:
            self.test_status_lbl.setText("Testing connection to Central PostgreSQL Server...")
            self.test_status_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
            QApplication.processEvents()
            from utils.db_config import test_postgres_connection
            ok, msg = test_postgres_connection(
                host=host, port=5432, dbname="jayraldines_catering",
                user="jayraldines_app", password="password", timeout=4
            )
            if not ok:
                ok2, msg2 = test_postgres_connection(
                    host=host, port=5432, dbname="jayraldines_catering",
                    user="jayraldines_app", password="12345678", timeout=4
                )
                if ok2:
                    ok, msg = ok2, msg2
        else:
            self.test_status_lbl.setText("Testing LAN Sync Hub connection...")
            self.test_status_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
            QApplication.processEvents()
            ok, msg = test_sqlite_sync_connection(host=host, port=port, timeout=4)

        if ok:
            self._connection_tested = True
            succ_label = "✅ Connection successful! PostgreSQL Server verified." if port == 5432 else "✅ Connection successful! Sync Hub verified."
            self.test_status_lbl.setText(succ_label)
            self.test_status_lbl.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
            self.start_install_btn.setEnabled(True)
        else:
            self._connection_tested = False
            self.test_status_lbl.setText(f"⚠️ {msg} (You can still proceed; ensure Server is running when opening app)")
            self.test_status_lbl.setStyleSheet("color: #F59E0B; font-size: 11px;")
            self.start_install_btn.setEnabled(True)

    def _browse_sqlite_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Existing SQLite Database", "", "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*.*)")
        if f:
            self.sqlite_file_edit.setText(f)
            self.cb_migrate_sqlite.setChecked(True)

    def _update_sqlite_stat_label(self, sqlite_path: Optional[Path]):
        if not sqlite_path or not sqlite_path.exists():
            self.sqlite_stat_lbl.setText("Bundled pre-populated database with complete catering records will be provisioned.")
            self.sqlite_stat_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
            return

        counts = {}
        try:
            import sqlite3
            conn = sqlite3.connect(str(sqlite_path))
            cur = conn.cursor()
            for tbl in ["customers", "bookings", "invoices", "menu_items", "packages"]:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                    row = cur.fetchone()
                    if row:
                        counts[tbl] = int(row[0])
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass

        if counts:
            parts = []
            if counts.get("customers"):
                parts.append(f"{counts['customers']} customers")
            if counts.get("bookings"):
                parts.append(f"{counts['bookings']} bookings")
            if counts.get("invoices"):
                parts.append(f"{counts['invoices']} invoices")
            if counts.get("packages"):
                parts.append(f"{counts['packages']} packages")
            summary_str = ", ".join(parts) if parts else "Database verified"
            self.sqlite_stat_lbl.setText(f"📦 Ready to restore: {summary_str} ({sqlite_path.name})")
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

        sub = QLabel("Please wait while application files are extracted and SQLite database components are configured.")
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
                "port": int(self.client_port_edit.text().strip() or 8000),
            }

        sqlite_source = None
        if self._server_mode == "server" and hasattr(self, "cb_migrate_sqlite") and self.cb_migrate_sqlite.isChecked():
            path_str = self.sqlite_file_edit.text().strip()
            if path_str and Path(path_str).exists():
                sqlite_source = Path(path_str)

        self.set_step(3)
        preserve_db = hasattr(self, "cb_preserve_db") and self.cb_preserve_db.isChecked()
        self.worker = ExtractWorker(
            dest_dir=dest_dir,
            create_desktop=create_desktop,
            create_start=create_start,
            server_mode=self._server_mode,
            client_config=client_cfg,
            clean_db=not preserve_db,
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

        # Dynamic Content Container
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

            title = QLabel("⚡  Main Station Details (Embedded SQLite & LAN Sync)")
            title.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 800; border: none; background: transparent;")
            c_lay.addWidget(title)

            rec_counts = creds.get("rec_counts", {})
            records_summary = (
                f"{rec_counts.get('bookings', 0)} bookings, "
                f"{rec_counts.get('customers', 0)} customers, "
                f"{rec_counts.get('packages', 0)} packages"
            )

            # Details Grid
            details_text = (
                f"• Database Engine        : High-Performance Embedded SQLite (WAL Mode)\n"
                f"• Query Latency          : 0ms (Local in-memory index cache)\n"
                f"• Database File          : {creds.get('db_path', '')}\n"
                f"• Verified Records       : {records_summary}\n"
                f"---------------------------------------------------\n"
                f"• Host LAN IP            : {creds.get('host', '127.0.0.1')}\n"
                f"• LAN Sync Hub Port      : {creds.get('port', 8000)}\n"
                f"• Tablet Kiosk Sync URL  : http://{creds.get('host', '127.0.0.1')}:8000\n"
                f"• Tablet Web Kiosk URL   : http://{creds.get('host', '127.0.0.1')}:8085\n"
                f"---------------------------------------------------\n"
                f"• Primary Admin Login    : admin (staff accounts configured)\n"
            )
            txt_lbl = QLabel(details_text)
            txt_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            txt_lbl.setStyleSheet("color: #F8FAFC; font-family: monospace; font-size: 11px; background: #0F172A; padding: 8px; border-radius: 6px; border: none;")
            c_lay.addWidget(txt_lbl)

            btn_box = QHBoxLayout()
            save_file_btn = QPushButton("📄 Save to server_info.txt")
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
            self.creds_lay.addWidget(card)
        else:
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
            c_t = QLabel("🔗  Connected to Main Station via LAN Hub:")
            c_t.setStyleSheet("color: #38BDF8; font-size: 13px; font-weight: 700; border: none; background: transparent;")
            c_d = QLabel(
                f"Main Station Server : http://{creds.get('host')}:{creds.get('port')}\n"
                f"Local Database Cache: {creds.get('db_path')}\n"
                f"Database Engine     : Embedded SQLite with LAN Sync Hub\n\n"
                "Launch the application and sign in with your staff or administrator credentials."
            )
            c_d.setStyleSheet("color: #F8FAFC; font-size: 11.5px; line-height: 140%; border: none; background: transparent;")
            c_lay.addWidget(c_t)
            c_lay.addWidget(c_d)
            self.creds_lay.addWidget(card)

    def _get_formatted_credentials_text(self) -> str:
        creds = self._credentials
        host = creds.get('host', '127.0.0.1')
        rec_counts = creds.get("rec_counts", {})
        records_summary = (
            f"{rec_counts.get('bookings', 0)} bookings, "
            f"{rec_counts.get('customers', 0)} customers, "
            f"{rec_counts.get('packages', 0)} packages"
        )
        return (
            "=====================================================\n"
            "   JAYRALDINE'S CATERING - STATION SETUP DETAILS\n"
            "=====================================================\n\n"
            "[DATABASE & PERFORMANCE]\n"
            "Engine                   : High-Performance Embedded SQLite (WAL Mode)\n"
            "Query Latency            : 0ms\n"
            f"Database Path            : {creds.get('db_path', '')}\n"
            f"Active Records           : {records_summary}\n\n"
            "[LAN SYNC HUB & TABLET KIOSK]\n"
            f"Host LAN IP              : {host}\n"
            f"LAN Sync Port            : {creds.get('port', 8000)}\n"
            f"LAN Sync URL             : http://{host}:8000\n"
            f"Tablet Web Kiosk URL     : http://{host}:8085\n\n"
            "Instructions for Tablet Kiosk:\n"
            f"1. Connect tablet to the same Wi-Fi as this PC.\n"
            f"2. Open Tablet app -> Settings -> enter Server Host: {host}\n"
            f"3. Tap 'Test Connection' -> Sync is instantly active!\n\n"
            "[APPLICATION LOGIN]\n"
            "Primary Admin Account    : admin\n"
            "Password                 : (configured staff accounts)\n\n"
            "Save this file in a secure location.\n"
        )

    def _save_credentials_file(self):
        content = self._get_formatted_credentials_text()
        default_path = str(Path.home() / "Desktop" / "jayraldines_station_info.txt")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Station Details",
            default_path,
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "Saved", f"Details saved successfully to:\n{file_path}")
            except Exception as exc:
                QMessageBox.warning(self, "Error", f"Could not save file: {exc}")

    def _copy_credentials_to_clipboard(self):
        content = self._get_formatted_credentials_text()
        cb = QApplication.clipboard()
        if cb:
            cb.setText(content)
            QMessageBox.information(self, "Copied", "Details copied to clipboard!")

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
