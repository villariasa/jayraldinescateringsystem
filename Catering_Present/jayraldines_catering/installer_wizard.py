"""
Jayraldine's Catering - Standalone Windows GUI Installer.

Compiles into a single-file 'Jayraldines_Catering_Setup.exe' that:
1. Extracts all bundled application files and resources to the destination directory (e.g. %LOCALAPPDATA%\\JayraldinesCatering).
2. Creates a Desktop Shortcut with the official logo icon.
3. Creates a Start Menu Program Shortcut.
4. Creates an Uninstaller shortcut.
5. Offers to launch Jayraldine's Catering immediately upon completion.
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from PySide6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QCheckBox,
    QProgressBar, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QFont


try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "1.2.0"
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
            # CSIDL_DESKTOPDIRECTORY = 0x0010
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
            # 1. Run main schema
            subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "postgres", "-f", str(main_sql)],
                env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, timeout=30
            )

            # 2. Run migrations
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

                self.progress.emit(10, "Preparing destination directory...")
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

            # Database check & automated initialization
            if self.setup_db:
                self.progress.emit(75, "Checking PostgreSQL Database configuration...")
                psql = self._find_psql()
                if psql:
                    self.progress.emit(80, "Initializing database tables & migrations...")
                    self._init_local_database(psql)

            self.progress.emit(85, "Creating Shortcuts & Icons...")

            exe_path = self.dest_dir / "JayraldinesCatering.exe"
            ico_path = self.dest_dir / "assets" / "logo.ico"
            if not ico_path.exists():
                ico_path = exe_path

            setup_ps1 = self.dest_dir / "setup.ps1"

            # 1. Desktop Shortcuts on all discovered Desktop locations
            if self.create_desktop:
                for d_dir in get_desktop_directories():
                    try:
                        d_dir.mkdir(parents=True, exist_ok=True)
                        lnk_desktop = d_dir / "Jayraldine's Catering.lnk"
                        create_shortcut(exe_path, lnk_desktop, ico_path, self.dest_dir)
                    except Exception:
                        pass

            # 2. Start Menu Shortcut
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

            # 3. Notify Windows shell to immediately refresh icons on desktop
            if os.name == "nt":
                try:
                    import ctypes
                    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
                except Exception:
                    pass

            # 4. Create Uninstaller Script
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


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle(f"Welcome to {APP_NAME} Setup (v{__version__})")
        self.setSubTitle(f"This wizard will install {APP_NAME} on your computer.")

        lay = QVBoxLayout(self)
        lay.setSpacing(16)

        banner = QLabel()
        logo_path = get_base_dir() / "assets" / "logo.png"
        if not logo_path.exists():
            logo_path = Path("assets/logo.png").resolve()
        if logo_path.exists():
            pm = QPixmap(str(logo_path)).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            banner.setPixmap(pm)
        banner.setAlignment(Qt.AlignCenter)
        lay.addWidget(banner)

        info = QLabel(
            f"<b>{APP_NAME}</b><br>"
            f"Version <b>{__version__}</b> (Commercial Edition)<br><br>"
            "Features included:<br>"
            "• Offline Booking & Event Management<br>"
            "• Built-in Chef Jay AI Assistant with Session Alarms<br>"
            "• Real-time Billing, Payments & Expense Tracking<br>"
            "• Responsive High-DPI Fullscreen Interface<br><br>"
            "Click <b>Next</b> to continue."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 13px; color: #374151; line-height: 140%;")
        lay.addWidget(info)


class DirectoryPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Choose Installation Location")
        self.setSubTitle("Select the destination folder where the catering system will be installed.")

        lay = QVBoxLayout(self)
        lay.setSpacing(14)

        lbl = QLabel("Install folder:")
        lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        lay.addWidget(lbl)

        h = QHBoxLayout()
        self.path_edit = QLineEdit(str(get_default_install_dir()))
        self.path_edit.setStyleSheet("padding: 8px; font-size: 13px; border-radius: 6px; border: 1px solid #CBD5E1;")
        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet("padding: 8px 16px; font-weight: 600;")
        browse_btn.clicked.connect(self._browse)
        h.addWidget(self.path_edit, 1)
        h.addWidget(browse_btn)
        lay.addLayout(h)

        lay.addSpacing(10)

        self.cb_desktop = QCheckBox("Create a Desktop Shortcut")
        self.cb_desktop.setChecked(True)
        self.cb_desktop.setStyleSheet("font-size: 13px; font-weight: 600;")
        lay.addWidget(self.cb_desktop)

        self.cb_start = QCheckBox("Create a Start Menu Shortcut")
        self.cb_start.setChecked(True)
        self.cb_start.setStyleSheet("font-size: 13px; font-weight: 600;")
        lay.addWidget(self.cb_start)

        self.cb_db = QCheckBox("Configure & initialize PostgreSQL Database automatically")
        self.cb_db.setChecked(True)
        self.cb_db.setStyleSheet("font-size: 13px; font-weight: 600; color: #0284C7;")
        lay.addWidget(self.cb_db)

        lay.addStretch()

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Directory", self.path_edit.text())
        if folder:
            self.path_edit.setText(str(Path(folder) / "JayraldinesCatering"))


class InstallProgressPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installing Jayraldine's Catering")
        self.setSubTitle("Please wait while the system files and resources are being installed.")
        self.is_complete = False

        lay = QVBoxLayout(self)
        lay.setSpacing(14)

        self.status_lbl = QLabel("Preparing installation...")
        self.status_lbl.setStyleSheet("font-size: 13px; color: #4B5563;")
        lay.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                text-align: center;
                background-color: #F1F5F9;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #E11D48;
                border-radius: 7px;
            }
        """)
        lay.addWidget(self.progress_bar)
        lay.addStretch()

        self.worker = None

    def initializePage(self):
        dir_page = self.wizard().page(1)
        dest_dir = Path(dir_page.path_edit.text())
        create_desktop = dir_page.cb_desktop.isChecked()
        create_start = dir_page.cb_start.isChecked()
        setup_db = dir_page.cb_db.isChecked()

        self.wizard().button(QWizard.BackButton).setEnabled(False)
        self.wizard().button(QWizard.NextButton).setEnabled(False)

        self.worker = ExtractWorker(dest_dir, create_desktop, create_start, setup_db)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, value: int, msg: str):
        self.progress_bar.setValue(value)
        self.status_lbl.setText(msg)

    def _on_finished(self, success: bool, err_msg: str):
        if success:
            self.is_complete = True
            self.status_lbl.setText("Installation completed successfully!")
            self.wizard().button(QWizard.NextButton).setEnabled(True)
            self.wizard().next()
        else:
            QMessageBox.critical(self, "Installation Failed", f"An error occurred during installation:\n{err_msg}")
            self.wizard().button(QWizard.BackButton).setEnabled(True)

    def isComplete(self):
        return self.is_complete


class FinishedPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installation Finished")
        self.setSubTitle("Jayraldine's Catering System has been successfully installed on your computer.")

        lay = QVBoxLayout(self)
        lay.setSpacing(16)

        msg = QLabel(
            "<b>Ready to use!</b><br><br>"
            "All application files, Chef Jay AI components, and desktop shortcuts have been created.<br>"
            "You can start managing your catering bookings, billing, and menus immediately."
        )
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 13px; color: #1E293B; line-height: 140%;")
        lay.addWidget(msg)

        self.cb_launch = QCheckBox("Launch Jayraldine's Catering now")
        self.cb_launch.setChecked(True)
        self.cb_launch.setStyleSheet("font-size: 13px; font-weight: 700; color: #E11D48;")
        lay.addWidget(self.cb_launch)

        lay.addStretch()


class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jayraldine's Catering Setup")
        self.setFixedSize(560, 420)
        self.setWizardStyle(QWizard.ModernStyle)

        logo_ico = get_base_dir() / "assets" / "logo.ico"
        if not logo_ico.exists():
            logo_ico = Path("assets/logo.ico").resolve()
        if logo_ico.exists():
            self.setWindowIcon(QIcon(str(logo_ico)))

        self.addPage(WelcomePage())
        self.addPage(DirectoryPage())
        self.addPage(InstallProgressPage())
        self.addPage(FinishedPage())

    def accept(self):
        finished_page = self.page(3)
        dir_page = self.page(1)
        if finished_page.cb_launch.isChecked():
            exe = Path(dir_page.path_edit.text()) / "JayraldinesCatering.exe"
            if exe.exists():
                subprocess.Popen([str(exe)], cwd=str(exe.parent))
        super().accept()


def main():
    app = QApplication(sys.argv)
    wizard = InstallerWizard()
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
