import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PySide6.QtCore import Signal, Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPixmap

from utils.icons import nav_icon, nav_icon_active, get_icon

from utils.paths import resource_path

_NAV_ITEMS = [
    ("Dashboard", "dashboard", 0),
    ("Orders",    "orders",    1),
    ("Customers", "customers", 2),
    ("Menu",      "menu",      3),
    ("Calendar",  "calendar",  4),
    ("Kitchen",   "kitchen",   5),
    ("Billing",   "billing",   6),
    ("Reports",   "reports",   7),
    ("Settings",  "settings",  8),
]

EXPANDED_WIDTH  = 240
COLLAPSED_WIDTH = 64


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

        # ✅ FIX: Attached logo_frame to self
        self.logo_frame = QFrame(self)
        self.logo_frame.setObjectName("logoArea")
        self.logo_layout = QHBoxLayout(self.logo_frame)
        self.logo_layout.setContentsMargins(20, 24, 12, 20)
        self.logo_layout.setSpacing(10)

        self.logo_icon = QLabel(self.logo_frame)
        logo_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_path):
            px = QPixmap(logo_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_icon.setPixmap(px)
        else:
            self.logo_icon.setText("🍽")
            self.logo_icon.setStyleSheet("font-size: 22px;")
        self.logo_icon.setFixedSize(32, 32)
        self.logo_layout.addWidget(self.logo_icon)

        self.logo_text = QLabel("Jayraldine's\nCATERING", self.logo_frame)
        self.logo_text.setObjectName("logoText")
        self.logo_layout.addWidget(self.logo_text)
        self.logo_layout.addStretch()

        self.collapse_btn = QPushButton(self.logo_frame)
        self.collapse_btn.setObjectName("collapseBtn")
        self.collapse_btn.setIcon(get_icon("menu-collapse", color="#6B7280", size=QSize(18, 18)))
        self.collapse_btn.setIconSize(QSize(18, 18))
        self.collapse_btn.setFixedSize(32, 32)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        self.logo_layout.addWidget(self.collapse_btn)

        self.root_layout.addWidget(self.logo_frame)

        # --- Nav buttons ---
        self.buttons = []
        self.root_layout.addSpacing(8)

        for text, icon_name, index in _NAV_ITEMS:
            btn = QPushButton(f"   {text}", self)
            btn.setCheckable(True)
            btn.setIconSize(QSize(18, 18))
            btn.setIcon(nav_icon(icon_name))
            btn.setProperty("icon_name", icon_name)

            if index == 0:
                btn.setChecked(True)
                btn.setIcon(nav_icon_active(icon_name))

            btn.clicked.connect(lambda _, idx=index: self._on_nav_clicked(idx))

            self.root_layout.addWidget(btn)
            self.buttons.append(btn)

        self.root_layout.addStretch()

        # ✅ FIX: Attached user_frame to self
        self.user_frame = QFrame(self)
        self.user_frame.setObjectName("userProfileArea")
        self.user_layout = QHBoxLayout(self.user_frame)
        self.user_layout.setContentsMargins(16, 12, 16, 12)
        self.user_layout.setSpacing(10)

        self.avatar = QLabel("O", self.user_frame)
        self.avatar.setObjectName("userAvatar")
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.user_layout.addWidget(self.avatar)

        self.user_info = QVBoxLayout()
        self.user_info.setSpacing(0)
        self.name_lbl  = QLabel("Owner", self.user_frame)
        self.name_lbl.setStyleSheet("color: #F9FAFB; font-weight: 700; font-size: 13px;")
        self.email_lbl = QLabel("admin@jayraldines.com", self.user_frame)
        self.email_lbl.setStyleSheet("color: #6B7280; font-size: 11px;")
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

        # animation
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._anim2 = QPropertyAnimation(self, b"maximumWidth")
        self._anim2.setDuration(200)
        self._anim2.setEasingCurve(QEasingCurve.OutCubic)

        QTimer.singleShot(0, self._mark_ready)

    def _mark_ready(self):
        self._ready = True

    def handle_click(self, index):
        for i, btn in enumerate(self.buttons):
            icon_name = btn.property("icon_name")
            active = (i == index)
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

        self.logo_text.setVisible(not self._collapsed)
        self.logout_lbl.setVisible(not self._collapsed)

        for w in (self.user_info.itemAt(i).widget() for i in range(self.user_info.count())):
            if w:
                w.setVisible(not self._collapsed)

        for btn in self.buttons:
            btn.setText("   " + btn.property("icon_name").capitalize() if not self._collapsed else "")