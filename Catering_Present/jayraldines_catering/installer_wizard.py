"""
Jayraldine's Catering - Modern Windows Application Installer.
Designed with a sleek, frameless glassmorphic interface, interactive stepper,
and automated dependency/database initialization.
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QLineEdit, QFileDialog, QCheckBox,
    QProgressBar, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QPoint
from PySide6.QtGui import QPixmap, QIcon, QFont, QColor, QPainter, QBrush, QPen

try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "1.2.1"
    APP_NAME = "Jayraldine's Catering"


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


class ExtractWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, dest_dir: Path, create_desktop: bool, create_start: bool, setup_db: bool = True):
        super().__init__()
        self.dest_dir = dest_dir
        self.create_desktop = create_desktop
        self.create_start = create_start
        self.setup_db = setup_db

    def _find_psql(self) -> Optional[str]:
        if shutil.which("psql"):
            return "psql"
        for ver in ["17", "16", "15", "14", "13"]:
            for pf in [r"C:\Program Files\PostgreSQL", r"C:\Program Files (x86)\PostgreSQL"]:
                cand = os.path.join(pf, ver, "bin", "psql.exe")
                if os.path.exists(cand):
                    return cand
        return None

    def _init_local_database(self, psql_exe: str):
        env = os.environ.copy()
        env["PGPASSWORD"] = "12345678"
        main_sql = self.dest_dir / "jayraldines_catering_clean.sql"
        if not main_sql.exists():
            return

        try:
            subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "postgres", "-f", str(main_sql)],
                env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=30
            )

            for mig in ["cebu_address_migration.sql", "occasions_migration.sql", "confirmed_only_views_migration.sql", "analytics_functions_migration.sql", "fix_customer_ledger_view.sql"]:
                mig_path = self.dest_dir / mig
                if mig_path.exists():
                    subprocess.run(
                        [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "jayraldines_catering", "-f", str(mig_path)],
                        env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=15
                    )
        except Exception:
            pass

    def run(self):
        try:
            base_dir = get_base_dir()
            zip_path = base_dir / "app_package.zip"

            if not zip_path.exists():
                dist_dir = base_dir / "dist" / "JayraldinesCatering"
                if not dist_dir.exists():
                    dist_dir = Path("dist/JayraldinesCatering").resolve()

                if not dist_dir.exists():
                    self.finished.emit(False, "Package archive 'app_package.zip' not found.")
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
                        pct = 10 + int((copied / max(1, total_files)) * 60)
                        self.progress.emit(pct, f"Installing: {f}")
            else:
                self.dest_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    members = zf.infolist()
                    total = len(members)
                    for i, member in enumerate(members):
                        zf.extract(member, self.dest_dir)
                        pct = int((i / max(1, total)) * 70)
                        self.progress.emit(pct, f"Extracting: {member.filename}")

            if self.setup_db:
                self.progress.emit(75, "Checking PostgreSQL Database environment...")
                psql = self._find_psql()
                if psql:
                    self.progress.emit(80, "Applying database tables & migrations...")
                    self._init_local_database(psql)

            self.progress.emit(88, "Registering Windows shortcuts & icons...")

            exe_path = self.dest_dir / "JayraldinesCatering.exe"
            ico_path = self.dest_dir / "assets" / "logo.ico"
            if not ico_path.exists():
                ico_path = exe_path

            setup_ps1 = self.dest_dir / "setup.ps1"

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

                if setup_ps1.exists():
                    lnk_db = start_menu / "Configure Database.lnk"
                    ps_cmd = (
                        f'$WshShell = New-Object -ComObject WScript.Shell; '
                        f'$Shortcut = $WshShell.CreateShortcut("{lnk_db}"); '
                        f'$Shortcut.TargetPath = "powershell.exe"; '
                        f'$Shortcut.Arguments = "-ExecutionPolicy Bypass -File ""{setup_ps1}"""; '
                        f'$Shortcut.WorkingDirectory = "{self.dest_dir}"; '
                        f'$Shortcut.Description = "Configure PostgreSQL Database"; '
                        f'$Shortcut.Save()'
                    )
                    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

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
            self.finished.emit(True, "")
        except Exception as exc:
            self.finished.emit(False, str(exc))


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
        lay.setContentsMargins(24, 28, 24, 24)
        lay.setSpacing(20)

        # Brand Logo with circular glow border
        brand_row = QHBoxLayout()
        logo_lbl = QLabel()
        logo_path = get_base_dir() / "assets" / "logo.png"
        if not logo_path.exists():
            logo_path = Path("assets/logo.png").resolve()
        if logo_path.exists():
            pm = QPixmap(str(logo_path)).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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

        lay.addSpacing(16)

        # Stepper Items
        self.steps = [
            ("Welcome", "System Overview & Setup"),
            ("Preferences", "Install Path & Options"),
            ("Installing", "Unpacking & Configuring"),
            ("Completed", "Ready to Launch")
        ]
        self.step_widgets = []

        for i, (title, desc) in enumerate(self.steps):
            step_box = QWidget()
            step_box.setStyleSheet("background: transparent; border: none;")
            s_lay = QHBoxLayout(step_box)
            s_lay.setContentsMargins(0, 4, 0, 4)
            s_lay.setSpacing(12)

            num_lbl = QLabel(str(i + 1))
            num_lbl.setFixedSize(26, 26)
            num_lbl.setAlignment(Qt.AlignCenter)
            num_lbl.setStyleSheet("""
                QLabel {
                    background-color: #1E293B;
                    color: #94A3B8;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 13px;
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
                # Completed
                num_lbl.setText("✓")
                num_lbl.setStyleSheet("""
                    background-color: #10B981;
                    color: #FFFFFF;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 13px;
                    border: none;
                """)
                t_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: 600; background: transparent;")
            elif i == current_step:
                # Active
                num_lbl.setText(str(i + 1))
                num_lbl.setStyleSheet("""
                    background-color: #E11D48;
                    color: #FFFFFF;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 13px;
                    border: 2px solid #FDA4AF;
                """)
                t_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700; background: transparent;")
            else:
                # Upcoming
                num_lbl.setText(str(i + 1))
                num_lbl.setStyleSheet("""
                    background-color: #1E293B;
                    color: #64748B;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 13px;
                    border: 1px solid rgba(255,255,255,0.06);
                """)
                t_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500; background: transparent;")


class ModernInstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(760, 500)

        self._drag_pos = None

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
        right_lay.setContentsMargins(28, 20, 28, 24)
        right_lay.setSpacing(16)

        # Top Bar with Draggable Area & Controls
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

        # Stacked Pages
        self.stack = QStackedWidget()
        right_lay.addWidget(self.stack, 1)

        # Build Pages
        self._init_welcome_page()
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
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(14)

        header = QLabel("Ready to Install")
        header.setStyleSheet("color: #F8FAFC; font-size: 22px; font-weight: 800;")
        lay.addWidget(header)

        sub = QLabel("Jayraldine's Catering & Event Management System provides high-speed offline booking, billing, AI kitchen assistant, and live tracking.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 140%;")
        lay.addWidget(sub)

        # Features highlight cards
        cards_grid = QVBoxLayout()
        cards_grid.setSpacing(8)

        highlights = [
            ("⚡ Fast Offline Bookings", "Instant order entry, PDF invoices, and receipts"),
            ("🤖 Chef Jay AI Assistant", "Natural-language kitchen alarms, timer alerts & queries"),
            ("🗄️ Automated Database Sync", "Zero-friction PostgreSQL configuration on install"),
            ("🖥️ High-DPI Desktop Engine", "Smooth fullscreen responsive scaling on all laptops")
        ]

        for title, desc in highlights:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(30, 41, 59, 0.5);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                    padding: 4px;
                }
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(12, 6, 12, 6)
            c_lay.setSpacing(10)

            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 700;")
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("color: #64748B; font-size: 11px;")

            c_lay.addWidget(t_lbl)
            c_lay.addWidget(d_lbl, 1)
            cards_grid.addWidget(card)

        lay.addLayout(cards_grid)
        lay.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        custom_btn = QPushButton("Customize Options")
        custom_btn.setCursor(Qt.PointingHandCursor)
        custom_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #CBD5E1;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.1); color: #FFFFFF; }
        """)
        custom_btn.clicked.connect(lambda: self.set_step(1))
        btn_row.addWidget(custom_btn)

        install_now_btn = QPushButton("Install Now  →")
        install_now_btn.setCursor(Qt.PointingHandCursor)
        install_now_btn.setStyleSheet("""
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
        install_now_btn.clicked.connect(self._start_installation)
        btn_row.addWidget(install_now_btn)

        lay.addLayout(btn_row)
        self.stack.addWidget(page)

    # ── Page 1: Preferences / Customization ────────────────────────
    def _init_preferences_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(16)

        header = QLabel("Installation Preferences")
        header.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 800;")
        lay.addWidget(header)

        # Directory Selector
        dir_lbl = QLabel("Installation Location:")
        dir_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        lay.addWidget(dir_lbl)

        dir_box = QHBoxLayout()
        self.path_edit = QLineEdit(str(get_default_install_dir()))
        self.path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                padding: 8px 12px;
                font-size: 12px;
                border-radius: 8px;
            }
        """)
        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        browse_btn.clicked.connect(self._browse_folder)
        dir_box.addWidget(self.path_edit, 1)
        dir_box.addWidget(browse_btn)
        lay.addLayout(dir_box)

        # Options Checkboxes
        opts_box = QVBoxLayout()
        opts_box.setSpacing(10)

        cb_style = """
            QCheckBox {
                color: #E2E8F0;
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1E293B;
            }
            QCheckBox::indicator:checked {
                background-color: #E11D48;
                border-color: #E11D48;
            }
        """

        self.cb_desktop = QCheckBox("Create a Desktop Shortcut (with official icon)")
        self.cb_desktop.setChecked(True)
        self.cb_desktop.setStyleSheet(cb_style)
        opts_box.addWidget(self.cb_desktop)

        self.cb_start = QCheckBox("Create a Start Menu Program Shortcut")
        self.cb_start.setChecked(True)
        self.cb_start.setStyleSheet(cb_style)
        opts_box.addWidget(self.cb_start)

        self.cb_db = QCheckBox("Initialize & Configure PostgreSQL Database tables automatically")
        self.cb_db.setChecked(True)
        self.cb_db.setStyleSheet(cb_style)
        opts_box.addWidget(self.cb_db)

        lay.addLayout(opts_box)
        lay.addStretch()

        # Navigation row
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
        back_btn.clicked.connect(lambda: self.set_step(0))
        btn_row.addWidget(back_btn)

        btn_row.addStretch()

        next_btn = QPushButton("Start Installation →")
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.setStyleSheet("""
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
        next_btn.clicked.connect(self._start_installation)
        btn_row.addWidget(next_btn)

        lay.addLayout(btn_row)
        self.stack.addWidget(page)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Directory", self.path_edit.text())
        if folder:
            self.path_edit.setText(str(Path(folder) / "JayraldinesCatering"))

    # ── Page 2: Installation Progress ──────────────────────────────
    def _init_progress_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 24, 0, 0)
        lay.setSpacing(16)

        header = QLabel("Installing Jayraldine's Catering")
        header.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 800;")
        lay.addWidget(header)

        sub = QLabel("Please wait while the system files, assets, and database configurations are extracted.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        lay.addWidget(sub)

        lay.addSpacing(16)

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
        self.set_step(2)
        dest_dir = Path(self.path_edit.text())
        create_desktop = self.cb_desktop.isChecked()
        create_start = self.cb_start.isChecked()
        setup_db = self.cb_db.isChecked()

        self.worker = ExtractWorker(dest_dir, create_desktop, create_start, setup_db)
        self.worker.progress.connect(self._on_install_progress)
        self.worker.finished.connect(self._on_install_finished)
        self.worker.start()

    def _on_install_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.pct_lbl.setText(f"{val}%")
        self.status_lbl.setText(msg)

    def _on_install_finished(self, ok: bool, err: str):
        if ok:
            self.set_step(3)
        else:
            self.status_lbl.setText(f"Installation failed: {err}")
            self.status_lbl.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;")

    # ── Page 3: Installation Complete ──────────────────────────────
    def _init_completed_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(14)

        # Success badge
        badge_row = QHBoxLayout()
        check_icon = QLabel("✓")
        check_icon.setFixedSize(48, 48)
        check_icon.setAlignment(Qt.AlignCenter)
        check_icon.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10B981, stop:1 #059669);
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
                border-radius: 24px;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
        """)
        badge_row.addWidget(check_icon)
        badge_row.addStretch()
        lay.addLayout(badge_row)

        header = QLabel("All Set & Ready to Go!")
        header.setStyleSheet("color: #F8FAFC; font-size: 22px; font-weight: 800;")
        lay.addWidget(header)

        msg = QLabel("Jayraldine's Catering System has been successfully installed on your computer. All files, shortcuts, and AI assistant components are ready.")
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 140%;")
        lay.addWidget(msg)

        lay.addSpacing(10)

        self.cb_launch_now = QCheckBox("Launch Jayraldine's Catering immediately")
        self.cb_launch_now.setChecked(True)
        self.cb_launch_now.setStyleSheet("""
            QCheckBox {
                color: #F43F5E;
                font-size: 13px;
                font-weight: 700;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #E11D48;
                background-color: #1E293B;
            }
            QCheckBox::indicator:checked {
                background-color: #E11D48;
                border-color: #E11D48;
            }
        """)
        lay.addWidget(self.cb_launch_now)

        lay.addStretch()

        # Finish buttons
        btn_row = QHBoxLayout()
        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.setCursor(Qt.PointingHandCursor)
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #94A3B8;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
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
                padding: 10px 28px;
                font-size: 13px;
                font-weight: 700;
                border-radius: 8px;
            }
            QPushButton:hover { background: #047857; }
        """)
        finish_btn.clicked.connect(self._on_finish_clicked)
        btn_row.addWidget(finish_btn)

        lay.addLayout(btn_row)
        self.stack.addWidget(page)

    def _open_app_folder(self):
        dest_dir = Path(self.path_edit.text())
        if dest_dir.exists():
            os.startfile(str(dest_dir))

    def _on_finish_clicked(self):
        if self.cb_launch_now.isChecked():
            dest_dir = Path(self.path_edit.text())
            exe = dest_dir / "JayraldinesCatering.exe"
            if exe.exists():
                subprocess.Popen([str(exe)], cwd=str(dest_dir))
        self.close()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ModernInstallerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
