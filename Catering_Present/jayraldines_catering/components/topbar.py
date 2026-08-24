from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QLineEdit, QWidget, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
import sys
import os
import subprocess
from datetime import datetime
from utils.icons import get_icon
import utils.icons as icons
from utils.theme import ThemeManager
from utils.accent import AccentManager


_PAGE_TITLES = {
    0: "Dashboard",
    1: "Orders",
    2: "Customers",
    3: "Menu",
    4: "Calendar",
    5: "Cash Flow",
    6: "Billing",
    7: "Reports",
    8: "Expenses",
    9: "AI Assistant",
    10: "Settings",
}

_TOP_NAV_ITEMS = [
    ("Dashboard",    "dashboard", 0),
    ("Orders",       "orders",    1),
    ("Calendar",     "calendar",  4),
    ("Billing",      "billing",   6),
    ("AI Assistant", "search",    9),
]


class AnimatedTopNav(QWidget):
    """Modern pill capsule navigation bar with a smooth sliding indicator."""
    tab_selected = Signal(int)

    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self._theme = theme_mgr
        self.setFixedHeight(38)
        self.setObjectName("topNavCapsule")

        self._active_index = 0
        self._buttons = {}

        # Floating sliding indicator pill
        self._indicator = QFrame(self)
        self._indicator.setObjectName("navPillIndicator")
        self._indicator.setStyleSheet("""
            QFrame#navPillIndicator {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #FB7185);
                border-radius: 8px;
            }
        """)
        self._indicator.hide()

        self._anim = QPropertyAnimation(self._indicator, b"geometry")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 3, 4, 3)
        self._layout.setSpacing(4)

        for text, icon_name, index in _TOP_NAV_ITEMS:
            btn = QPushButton(f" {text}", self)
            btn.setObjectName("topNavTabClean")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setIconSize(QSize(15, 15))
            btn.setProperty("icon_name", icon_name)
            btn.setProperty("tab_index", index)
            btn.clicked.connect(lambda _, idx=index: self.tab_selected.emit(idx))
            self._layout.addWidget(btn)
            self._buttons[index] = btn

        self._apply_theme()
        QTimer.singleShot(60, lambda: self.set_active_page(0, animate=False))

    def _apply_theme(self):
        dark = self._theme.is_dark()
        if dark:
            self.setStyleSheet("""
                QWidget#topNavCapsule {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#topNavCapsule {
                    background-color: rgba(0, 0, 0, 0.04);
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 10px;
                }
            """)

    def set_active_page(self, index: int, animate: bool = True):
        self._active_index = index
        dark = self._theme.is_dark()
        target_btn = self._buttons.get(index)

        if target_btn:
            self._indicator.show()
            self._indicator.raise_()
            for btn in self._buttons.values():
                btn.raise_()

            target_geo = target_btn.geometry()
            if target_geo.isValid() and target_geo.width() > 0:
                if animate and self._indicator.isVisible() and self._indicator.geometry().width() > 0:
                    self._anim.stop()
                    self._anim.setStartValue(self._indicator.geometry())
                    self._anim.setEndValue(target_geo)
                    self._anim.start()
                else:
                    self._indicator.setGeometry(target_geo)

            for idx, btn in self._buttons.items():
                icon_name = btn.property("icon_name")
                if idx == index:
                    btn.setStyleSheet("QPushButton { background: transparent; color: #FFFFFF; font-weight: 700; border: none; padding: 0 12px; font-size: 13px; }")
                    btn.setIcon(get_icon(icon_name, color="#FFFFFF", size=QSize(15, 15)))
                else:
                    color_muted = "#94A3B8" if dark else "#64748B"
                    hover_color = "#F9FAFB" if dark else "#0F172A"
                    btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {color_muted}; font-weight: 600; border: none; padding: 0 12px; font-size: 13px; }} QPushButton:hover {{ color: {hover_color}; }}")
                    btn.setIcon(get_icon(icon_name, color=color_muted, size=QSize(15, 15)))
        else:
            self._indicator.hide()
            for idx, btn in self._buttons.items():
                icon_name = btn.property("icon_name")
                color_muted = "#94A3B8" if dark else "#64748B"
                btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {color_muted}; font-weight: 600; border: none; padding: 0 12px; font-size: 13px; }}")
                btn.setIcon(get_icon(icon_name, color=color_muted, size=QSize(15, 15)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        target_btn = self._buttons.get(self._active_index)
        if target_btn and target_btn.geometry().isValid() and target_btn.geometry().width() > 0:
            self._indicator.setGeometry(target_btn.geometry())


class TopBar(QFrame):
    search_changed = Signal(str)
    tab_selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.setObjectName("topBar")
        self.setFixedHeight(56)
        self._theme = ThemeManager()

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(16, 0, 16, 0)
        self.main_layout.setSpacing(12)

        self.page_title = QLabel("Dashboard", self)
        self.page_title.setObjectName("h2")
        self.main_layout.addWidget(self.page_title)

        self.main_layout.addStretch()

        # Animated sliding top navigation
        self.top_nav = AnimatedTopNav(self._theme, self)
        self.top_nav.tab_selected.connect(self.tab_selected.emit)
        self.main_layout.addWidget(self.top_nav)

        self.main_layout.addStretch()

        # ✅ Responsive search bar
        self.search_wrap = QWidget(self)
        self.search_wrap.setMinimumWidth(100)
        self.search_wrap.setMaximumWidth(200)
        self.search_inner = QHBoxLayout(self.search_wrap)
        self.search_inner.setContentsMargins(0, 0, 0, 0)
        self.search_inner.setSpacing(0)
        self.search_box = QLineEdit(self.search_wrap)
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setFixedHeight(32)
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.timeout.connect(lambda: self.search_changed.emit(self.search_box.text()))
        self.search_box.textChanged.connect(lambda: self._search_debounce.start(180))
        self.search_inner.addWidget(self.search_box)
        self.main_layout.addWidget(self.search_wrap)

        self.clock_lbl = QLabel(self)
        self.clock_lbl.setObjectName("subtitle")
        self.clock_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.main_layout.addWidget(self.clock_lbl)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("notifBtn")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setToolTip("Toggle Light / Dark theme")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_icon()
        self.main_layout.addWidget(self.theme_btn)

        # ✅ Notification button
        self.notif_wrap = QWidget(self)
        self.notif_layout = QHBoxLayout(self.notif_wrap)
        self.notif_layout.setContentsMargins(0, 0, 0, 0)
        self.notif_layout.setSpacing(0)
        self.notif_btn = QPushButton(self.notif_wrap)
        self.notif_btn.setObjectName("notifBtn")
        self.notif_btn.setIcon(get_icon("bell", color="#9CA3AF", size=QSize(16, 16)))
        self.notif_btn.setIconSize(QSize(16, 16))
        self.notif_btn.setFixedSize(32, 32)
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
        self.divider.setFixedHeight(20)
        self.main_layout.addWidget(self.divider)

        self.avatar = QLabel("O", self)
        self.avatar.setObjectName("userAvatar")
        self.avatar.setFixedSize(30, 30)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.avatar)

        self.owner_lbl = QLabel("Owner", self)
        self.owner_lbl.setObjectName("h3")
        self.main_layout.addWidget(self.owner_lbl)

        self.main_layout.addSpacing(6)

        self.min_btn = QPushButton(self)
        self.min_btn.setFixedSize(30, 30)
        self.min_btn.setToolTip("Minimize Window")
        self.min_btn.setCursor(Qt.PointingHandCursor)
        self.min_btn.setIcon(get_icon("minimize", color="#9CA3AF", size=QSize(14, 14)))
        self.min_btn.setIconSize(QSize(14, 14))
        self.min_btn.clicked.connect(self._minimize_window)
        self.main_layout.addWidget(self.min_btn)

        self.fs_btn = QPushButton(self)
        self.fs_btn.setFixedSize(30, 30)
        self.fs_btn.setToolTip("Toggle Fullscreen (F11)")
        self.fs_btn.setCursor(Qt.PointingHandCursor)
        self.fs_btn.setIcon(get_icon("maximize", color="#9CA3AF", size=QSize(14, 14)))
        self.fs_btn.setIconSize(QSize(14, 14))
        self.fs_btn.clicked.connect(self._toggle_window_fullscreen)
        self.main_layout.addWidget(self.fs_btn)

        self.close_btn = QPushButton(self)
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setIcon(get_icon("close", color="#EF4444", size=QSize(14, 14)))
        self.close_btn.setIconSize(QSize(14, 14))
        self.close_btn.setToolTip("Close Application")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self._confirm_close)
        self.main_layout.addWidget(self.close_btn)

        self._current_page_index = 0
        self._apply_theme_styles()
        self._theme.theme_changed.connect(self._on_theme_changed)
        AccentManager().accent_changed.connect(self._on_accent_changed)

    def _minimize_window(self):
        w = self.window()
        if w:
            w.showMinimized()

    def _toggle_window_fullscreen(self):
        w = self.window()
        if w and hasattr(w, "_toggle_fullscreen"):
            w._toggle_fullscreen()
        elif w:
            if w.isFullScreen():
                w.showNormal()
            else:
                w.showFullScreen()
        self._update_fs_icon()

    def _update_fs_icon(self):
        w = self.window()
        is_fs = w.isFullScreen() if w else False
        dark = self._theme.is_dark()
        btn_color = "#9CA3AF" if dark else "#5B6B84"
        icon_name = "restore" if is_fs else "maximize"
        self.fs_btn.setIcon(get_icon(icon_name, color=btn_color, size=QSize(14, 14)))
        self.fs_btn.setToolTip("Exit Fullscreen (Esc)" if is_fs else "Toggle Fullscreen (F11)")

    def _on_theme_changed(self, *_args):
        try:
            from shiboken6 import isValid
            if isValid(self):
                self._apply_theme_styles()
        except Exception:
            pass

    def _on_accent_changed(self, *_args):
        try:
            from shiboken6 import isValid
            if isValid(self):
                self.set_page(self._current_page_index, self.search_box.text())
        except Exception:
            pass

    def _apply_theme_styles(self):
        dark = self._theme.is_dark()
        btn_color = "#9CA3AF" if dark else "#5B6B84"
        hover_bg = "rgba(156,163,175,0.25)" if dark else "rgba(100,116,139,0.18)"

        self.clock_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: %s;"
            % btn_color
        )
        self.divider.setStyleSheet("color: %s;" % ("#243244" if dark else "#E4E9F1"))
        self.notif_btn.setIcon(get_icon(
            "bell", color=btn_color, size=QSize(16, 16)
        ))

        self.min_btn.setIcon(get_icon("minimize", color=btn_color, size=QSize(14, 14)))
        self.min_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {hover_bg}; }}"
        )

        self._update_fs_icon()
        self.fs_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {hover_bg}; }}"
        )

        self.close_btn.setIcon(get_icon("close", color="#EF4444", size=QSize(14, 14)))
        self.close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: rgba(239,68,68,0.25); }"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        is_compact = w < 1080
        self.owner_lbl.setVisible(not is_compact)
        self.divider.setVisible(not is_compact)
        if w < 880:
            self.clock_lbl.setVisible(False)
        else:
            self.clock_lbl.setVisible(True)

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
        self.top_nav._apply_theme()
        self.top_nav.set_active_page(getattr(self, "_current_page_index", 0), animate=False)

    def _update_theme_icon(self):
        if self._theme.is_dark():
            self.theme_btn.setText("")
            self.theme_btn.setIcon(get_icon("sun", color="#F59E0B", size=QSize(16, 16)))
            self.theme_btn.setToolTip("Switch to Light theme")
            self.theme_btn.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; }"
                "QPushButton:hover { background: rgba(255, 255, 255, 0.12); border-color: rgba(255, 255, 255, 0.2); }"
            )
        else:
            self.theme_btn.setText("")
            self.theme_btn.setIcon(get_icon("moon", color="#6366F1", size=QSize(16, 16)))
            self.theme_btn.setToolTip("Switch to Dark theme")
            self.theme_btn.setStyleSheet(
                "QPushButton { background: rgba(0, 0, 0, 0.04); border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 8px; }"
                "QPushButton:hover { background: rgba(0, 0, 0, 0.08); border-color: rgba(0, 0, 0, 0.15); }"
            )

    def _tick_clock(self):
        now = datetime.now()
        self.clock_lbl.setText(now.strftime("%a, %b %d  %I:%M %p"))

    def set_page(self, index: int, search_text: str = ""):
        self._current_page_index = index
        self.page_title.setText(_PAGE_TITLES.get(index, ""))
        self.search_box.blockSignals(True)
        self.search_box.setText(search_text)
        self.search_box.blockSignals(False)
        self.top_nav.set_active_page(index, animate=True)
