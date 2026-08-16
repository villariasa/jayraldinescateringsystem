import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PySide6.QtCore import Signal, Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPixmap, QCursor

from utils.icons import nav_icon, nav_icon_active, get_icon
from utils.theme import ThemeManager
from utils.accent import AccentManager
from utils.paths import resource_path

_NAV_ITEMS = [
    ("Customers", "customers", 2),
    ("Menu",      "menu",      3),
    ("Expenses",  "billing",   8),
    ("Kitchen",   "kitchen",   5),
    ("Reports",   "reports",   7),
    ("Settings",  "settings",  10),
]

EXPANDED_WIDTH  = 250
COLLAPSED_WIDTH = 68


class Sidebar(QFrame):
    page_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(EXPANDED_WIDTH)
        self._collapsed = False
        self._ready = False

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Header Area
        self.logo_frame = QFrame(self)
        self.logo_frame.setObjectName("logoArea")
        self.logo_layout = QHBoxLayout(self.logo_frame)
        self.logo_layout.setContentsMargins(12, 14, 12, 14)
        self.logo_layout.setSpacing(8)

        self.logo_icon = QLabel(self.logo_frame)
        self.logo_icon.setCursor(Qt.PointingHandCursor)
        self.logo_icon.mousePressEvent = lambda e: self.toggle_collapse() if self._collapsed else None
        logo_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_path):
            px = QPixmap(logo_path).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_icon.setPixmap(px)
        else:
            self.logo_icon.setPixmap(get_icon("orders", color="#E11D48", size=QSize(26, 26)).pixmap(QSize(26, 26)))
        self.logo_icon.setFixedSize(30, 30)
        self.logo_icon.setAlignment(Qt.AlignCenter)
        self.logo_layout.addWidget(self.logo_icon)

        from version import __version__
        self.logo_text = QLabel(
            f"<div style='line-height:1.15;'>"
            f"<span style='font-size:13px; font-weight:800;'>Jayraldine's</span><br>"
            f"<span style='font-size:9.5px; color:#9CA3AF; font-weight:700; letter-spacing:0.8px;'>CATERING v{__version__}</span>"
            f"</div>",
            self.logo_frame
        )
        self.logo_text.setTextFormat(Qt.RichText)
        self.logo_text.setObjectName("logoText")
        self.logo_layout.addWidget(self.logo_text, 1)

        self.collapse_btn = QPushButton(self.logo_frame)
        self.collapse_btn.setObjectName("collapseBtn")
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.setToolTip("Collapse Sidebar")
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        self.logo_layout.addWidget(self.collapse_btn)

        self.root_layout.addWidget(self.logo_frame)

        # Nav buttons
        self.buttons = []
        self.root_layout.addSpacing(8)

        for text, icon_name, index in _NAV_ITEMS:
            btn = QPushButton(f"   {text}", self)
            btn.setCheckable(True)
            btn.setIconSize(QSize(18, 18))
            btn.setIcon(nav_icon(icon_name))
            btn.setProperty("icon_name", icon_name)
            btn.setProperty("nav_label", text)
            btn.setProperty("page_index", index)

            if index == 0:
                btn.setChecked(True)
                btn.setIcon(nav_icon_active(icon_name))

            btn.clicked.connect(lambda _, idx=index: self._on_nav_clicked(idx))
            self.root_layout.addWidget(btn)
            self.buttons.append(btn)

        self.root_layout.addStretch()

        # User Profile Footer
        self.user_frame = QFrame(self)
        self.user_frame.setObjectName("userProfileArea")
        self.user_layout = QHBoxLayout(self.user_frame)
        self.user_layout.setContentsMargins(14, 12, 14, 12)
        self.user_layout.setSpacing(10)

        self.avatar = QLabel("O", self.user_frame)
        self.avatar.setObjectName("userAvatar")
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.user_layout.addWidget(self.avatar)

        self.user_info = QVBoxLayout()
        self.user_info.setSpacing(0)
        self.name_lbl  = QLabel("Owner", self.user_frame)
        self.email_lbl = QLabel("admin@jayraldines.com", self.user_frame)
        self.user_info.addWidget(self.name_lbl)
        self.user_info.addWidget(self.email_lbl)
        self.user_layout.addLayout(self.user_info)
        self.user_layout.addStretch()

        self.logout_lbl = QLabel(self.user_frame)
        self.logout_lbl.setPixmap(
            get_icon("log-out", color="#6B7280", size=QSize(15, 15)).pixmap(QSize(15, 15))
        )
        self.user_layout.addWidget(self.logout_lbl)

        self.root_layout.addWidget(self.user_frame)

        # Animations
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._anim2 = QPropertyAnimation(self, b"maximumWidth")
        self._anim2.setDuration(200)
        self._anim2.setEasingCurve(QEasingCurve.OutCubic)

        self._apply_theme_styles()
        ThemeManager().theme_changed.connect(self._on_theme_changed)
        QTimer.singleShot(0, self._mark_ready)

    def _on_theme_changed(self, *_args):
        try:
            from shiboken6 import isValid
            if isValid(self):
                self._apply_theme_styles()
        except Exception:
            pass

    def _apply_theme_styles(self):
        dark = ThemeManager().is_dark()
        self.name_lbl.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: %s;"
            % ("#F9FAFB" if dark else "#101828")
        )
        self.email_lbl.setStyleSheet(
            "font-size: 11px; color: %s;" % ("#6B7280" if dark else "#7A879E")
        )
        if dark:
            self.collapse_btn.setStyleSheet("""
                QPushButton#collapseBtn {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.16);
                    border-radius: 6px;
                }
                QPushButton#collapseBtn:hover {
                    background-color: rgba(225, 29, 72, 0.35);
                    border-color: #E11D48;
                }
            """)
            btn_icon_col = "#38BDF8" if self._collapsed else "#F9FAFB"
        else:
            self.collapse_btn.setStyleSheet("""
                QPushButton#collapseBtn {
                    background-color: rgba(0, 0, 0, 0.05);
                    border: 1px solid rgba(0, 0, 0, 0.12);
                    border-radius: 6px;
                }
                QPushButton#collapseBtn:hover {
                    background-color: rgba(225, 29, 72, 0.18);
                    border-color: #E11D48;
                }
            """)
            btn_icon_col = "#0284C7" if self._collapsed else "#334155"

        icon_name = "sidebar-expand" if self._collapsed else "sidebar-collapse"
        self.collapse_btn.setIcon(get_icon(icon_name, color=btn_icon_col, size=QSize(15, 15)))

        muted = "#6B7280" if dark else "#7A879E"
        self.logout_lbl.setPixmap(
            get_icon("log-out", color=muted, size=QSize(15, 15)).pixmap(QSize(15, 15))
        )

    def _mark_ready(self):
        self._ready = True

    def handle_click(self, page_index: int):
        for btn in self.buttons:
            btn_idx = btn.property("page_index")
            icon_name = btn.property("icon_name")
            active = (btn_idx == page_index)
            btn.setChecked(active)
            btn.setIcon(nav_icon_active(icon_name) if active else nav_icon(icon_name))

    def _on_nav_clicked(self, index):
        if not self._ready:
            return
        self.handle_click(index)
        self.page_changed.emit(index)

    def toggle_collapse(self):
        self._collapsed = not self._collapsed
        target = COLLAPSED_WIDTH if self._collapsed else EXPANDED_WIDTH

        for anim in (self._anim, self._anim2):
            anim.setStartValue(self.width())
            anim.setEndValue(target)
            anim.start()

        dark = ThemeManager().is_dark()
        if self._collapsed:
            self.logo_layout.setContentsMargins(0, 14, 0, 10)
            self.logo_layout.setAlignment(self.logo_icon, Qt.AlignCenter)
            self.logo_text.hide()
            self.logout_lbl.hide()
            self.collapse_btn.setToolTip("Expand Sidebar")
            btn_icon_col = "#38BDF8" if dark else "#0284C7"
            self.collapse_btn.setIcon(get_icon("sidebar-expand", color=btn_icon_col, size=QSize(15, 15)))
            self.user_layout.setContentsMargins(0, 12, 0, 12)
            self.user_layout.setAlignment(self.avatar, Qt.AlignCenter)
            for w in (self.user_info.itemAt(i).widget() for i in range(self.user_info.count())):
                if w:
                    w.hide()
            for btn in self.buttons:
                btn.setText("")
                btn.setToolTip(btn.property("nav_label"))
        else:
            self.logo_layout.setContentsMargins(12, 14, 12, 14)
            self.logo_layout.setAlignment(self.logo_icon, Qt.AlignLeft | Qt.AlignVCenter)
            self.logo_text.show()
            self.logout_lbl.show()
            self.collapse_btn.setToolTip("Collapse Sidebar")
            btn_icon_col = "#F9FAFB" if dark else "#334155"
            self.collapse_btn.setIcon(get_icon("sidebar-collapse", color=btn_icon_col, size=QSize(15, 15)))
            self.user_layout.setContentsMargins(14, 12, 14, 12)
            self.user_layout.setAlignment(self.avatar, Qt.AlignLeft | Qt.AlignVCenter)
            for w in (self.user_info.itemAt(i).widget() for i in range(self.user_info.count())):
                if w:
                    w.show()
            for btn in self.buttons:
                btn.setText("   " + btn.property("nav_label"))
                btn.setToolTip("")