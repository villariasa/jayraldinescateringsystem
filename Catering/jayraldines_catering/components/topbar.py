from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QLineEdit, QWidget, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import QFont, QKeyEvent
from components.search_dropdown import SearchDropdown
import sys
import os
import subprocess
from datetime import datetime
from utils.icons import get_icon
from utils.theme import ThemeManager


_PAGE_TITLES = {
    0: "Dashboard",
    1: "Orders",
    2: "Customers",
    3: "Menu",
    4: "Calendar",
    5: "Kitchen",
    6: "Billing",
    7: "Reports",
    8: "Settings",
}


class TopBar(QFrame):
    search_changed = Signal(str)
    search_result_selected = Signal(dict)
    def __init__(self):
        super().__init__()
        self.setObjectName("topBar")
        self.setFixedHeight(56)
        self._theme = ThemeManager()

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(24, 0, 24, 0)
        self.main_layout.setSpacing(16)

        self.page_title = QLabel("Dashboard", self)
        self.page_title.setObjectName("h2")
        self.main_layout.addWidget(self.page_title)

        self.main_layout.addStretch()

        # ✅ FIX: Attached search_wrap to self
        self.search_wrap = QWidget(self)
        self.search_wrap.setFixedWidth(280)
        self.search_inner = QHBoxLayout(self.search_wrap)
        self.search_inner.setContentsMargins(0, 0, 0, 0)
        self.search_inner.setSpacing(0)
        self.search_box = QLineEdit(self.search_wrap)
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setFixedHeight(36)
        self.search_box.textChanged.connect(self._on_search_text)
        self.search_box.installEventFilter(self)
        self.search_inner.addWidget(self.search_box)
        self.main_layout.addWidget(self.search_wrap)

        self._dropdown = SearchDropdown()
        self._dropdown.result_selected.connect(self._on_result_selected)

        self.clock_lbl = QLabel(self)
        self.clock_lbl.setObjectName("subtitle")
        self.clock_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #9CA3AF; min-width: 160px;")
        self.clock_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.main_layout.addWidget(self.clock_lbl)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("notifBtn")
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setToolTip("Toggle Light / Dark theme")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_icon()
        self.main_layout.addWidget(self.theme_btn)

        # ✅ FIX: Attached notif_wrap to self
        self.notif_wrap = QWidget(self)
        self.notif_layout = QHBoxLayout(self.notif_wrap)
        self.notif_layout.setContentsMargins(0, 0, 0, 0)
        self.notif_layout.setSpacing(0)
        self.notif_btn = QPushButton(self.notif_wrap)
        self.notif_btn.setObjectName("notifBtn")
        self.notif_btn.setIcon(get_icon("bell", color="#9CA3AF", size=QSize(18, 18)))
        self.notif_btn.setIconSize(QSize(18, 18))
        self.notif_btn.setFixedSize(36, 36)
        self.notif_layout.addWidget(self.notif_btn)
        
        self.notif_badge = QLabel("0", self.notif_wrap)
        self.notif_badge.setObjectName("notifBadge")
        self.notif_badge.setFixedSize(16, 16)
        self.notif_badge.setAlignment(Qt.AlignCenter)
        self.notif_badge.setVisible(False)
        self.notif_layout.addWidget(self.notif_badge)
        self.notif_layout.setAlignment(self.notif_badge, Qt.AlignTop)
        self.main_layout.addWidget(self.notif_wrap)

        self.divider = QFrame(self)
        self.divider.setFrameShape(QFrame.VLine)
        self.divider.setStyleSheet("color: #E2E8F0;")
        self.divider.setFixedHeight(24)
        self.main_layout.addWidget(self.divider)

        self.avatar = QLabel("O", self)
        self.avatar.setObjectName("userAvatar")
        self.avatar.setFixedSize(32, 32)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.avatar)

        self.owner_lbl = QLabel("Owner", self)
        self.owner_lbl.setObjectName("h3")
        self.main_layout.addWidget(self.owner_lbl)

        self.main_layout.addSpacing(8)

        self.close_btn = QPushButton(self)
        self.close_btn.setIcon(get_icon("close", color="#EF4444", size=QSize(16, 16)))
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setToolTip("Close Application")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 8px; }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); }"
        )
        self.close_btn.clicked.connect(self._confirm_close)
        self.main_layout.addWidget(self.close_btn)

    def _confirm_close(self):
        reply = QMessageBox.question(
            self, "Close Application",
            "Are you sure you want to close Jayraldine's Catering?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        backup_reply = QMessageBox.question(
            self, "Backup Database",
            "Do you want to backup the database before closing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if backup_reply == QMessageBox.Yes:
            self._do_backup()
        else:
            sys.exit(0)

    def _do_backup(self):
        default_name = f"jayraldines_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Database Backup", default_name, "SQL Files (*.sql);;All Files (*)"
        )
        if not path:
            return
        try:
            from utils.db import _CONFIG
            env = os.environ.copy()
            env["PGPASSWORD"] = _CONFIG.get("password", "")
            result = subprocess.run(
                [
                    "pg_dump",
                    "-h", _CONFIG.get("host", "localhost"),
                    "-p", str(_CONFIG.get("port", 5432)),
                    "-U", _CONFIG.get("user", "postgres"),
                    "-F", "p",
                    "-f", path,
                    _CONFIG.get("dbname", "jayraldines_catering"),
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                QMessageBox.information(
                    self, "Backup Successful",
                    f"Database backed up successfully to:\n{path}"
                )
                sys.exit(0)
            else:
                err = result.stderr.strip() or "Unknown error"
                retry = QMessageBox.question(
                    self, "Backup Failed",
                    f"Backup failed:\n{err}\n\nClose anyway without backup?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if retry == QMessageBox.Yes:
                    sys.exit(0)
        except FileNotFoundError:
            retry = QMessageBox.question(
                self, "pg_dump Not Found",
                "pg_dump was not found on this system.\nClose anyway without backup?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if retry == QMessageBox.Yes:
                sys.exit(0)
        except Exception as exc:
            retry = QMessageBox.question(
                self, "Backup Error",
                f"An error occurred during backup:\n{exc}\n\nClose anyway without backup?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if retry == QMessageBox.Yes:
                sys.exit(0)

    def _toggle_theme(self):
        new_theme = self._theme.toggle()
        self._update_theme_icon()

    def _update_theme_icon(self):
        if self._theme.is_dark():
            self.theme_btn.setText("☀")
            self.theme_btn.setToolTip("Switch to Light theme")
            self.theme_btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; font-size: 16px; border-radius: 8px; }"
                "QPushButton:hover { background: #1F2937; }"
            )
        else:
            self.theme_btn.setText("🌙")
            self.theme_btn.setToolTip("Switch to Dark theme")
            self.theme_btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; font-size: 16px; border-radius: 8px; }"
                "QPushButton:hover { background: #F1F5F9; }"
            )

    def _on_search_text(self, text: str):
        self.search_changed.emit(text)
        if text.strip():
            self._dropdown.search(text)
            self._dropdown.show_below(self.search_box)
        else:
            self._dropdown.hide()

    def _on_result_selected(self, item: dict):
        self._dropdown.hide()
        self.search_box.blockSignals(True)
        self.search_box.clear()
        self.search_box.blockSignals(False)
        self.search_result_selected.emit(item)

    def eventFilter(self, obj, event):
        if obj is self.search_box and isinstance(event, QKeyEvent):
            if self._dropdown.isVisible():
                if self._dropdown.handle_key(event):
                    return True
        return super().eventFilter(obj, event)

    def _tick_clock(self):
        now = datetime.now()
        self.clock_lbl.setText(now.strftime("%a, %b %d  %I:%M:%S %p"))

    def set_page(self, index: int):
        self.page_title.setText(_PAGE_TITLES.get(index, ""))
        self.search_box.blockSignals(True)
        self.search_box.clear()
        self.search_box.blockSignals(False)