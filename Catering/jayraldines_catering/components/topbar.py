from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QLineEdit, QWidget
from PySide6.QtCore import Qt, QSize

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
    def __init__(self):
        super().__init__()
        self.setObjectName("topBar")
        self.setFixedHeight(56)
        self._theme = ThemeManager()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("h2")
        layout.addWidget(self.page_title)

        layout.addStretch()

        search_wrap = QWidget()
        search_wrap.setFixedWidth(280)
        search_inner = QHBoxLayout(search_wrap)
        search_inner.setContentsMargins(0, 0, 0, 0)
        search_inner.setSpacing(0)
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setFixedHeight(36)
        search_inner.addWidget(self.search_box)
        layout.addWidget(search_wrap)

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("notifBtn")
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setToolTip("Toggle Light / Dark theme")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_icon()
        layout.addWidget(self.theme_btn)

        notif_wrap = QWidget()
        notif_layout = QHBoxLayout(notif_wrap)
        notif_layout.setContentsMargins(0, 0, 0, 0)
        notif_layout.setSpacing(0)
        self.notif_btn = QPushButton()
        self.notif_btn.setObjectName("notifBtn")
        self.notif_btn.setIcon(get_icon("bell", color="#9CA3AF", size=QSize(18, 18)))
        self.notif_btn.setIconSize(QSize(18, 18))
        self.notif_btn.setFixedSize(36, 36)
        notif_layout.addWidget(self.notif_btn)
        self.notif_badge = QLabel("3")
        self.notif_badge.setObjectName("notifBadge")
        self.notif_badge.setFixedSize(16, 16)
        self.notif_badge.setAlignment(Qt.AlignCenter)
        notif_layout.addWidget(self.notif_badge)
        notif_layout.setAlignment(self.notif_badge, Qt.AlignTop)
        layout.addWidget(notif_wrap)

        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("color: #E2E8F0;")
        divider.setFixedHeight(24)
        layout.addWidget(divider)

        avatar = QLabel("O")
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        layout.addWidget(avatar)

        owner_lbl = QLabel("Owner")
        owner_lbl.setObjectName("h3")
        layout.addWidget(owner_lbl)

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

    def set_page(self, index: int):
        self.page_title.setText(_PAGE_TITLES.get(index, ""))
