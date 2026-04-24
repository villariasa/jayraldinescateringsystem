import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QPixmap

from utils.icon_manager import nav_icon, nav_icon_active, get_icon
from PySide6.QtCore import QSize

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

_NAV_ICON_MAP = {
    0: "dashboard",
    1: "bookings",
    2: "calendar",
    3: "reports",
}

class Sidebar(QFrame):
    page_changed = Signal(int) 

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        logo_frame = QFrame()
        logo_frame.setObjectName("logoArea")
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(10)

        self.logo_icon = QLabel()
        logo_path = os.path.join(ASSETS_DIR, "logo.png")
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_icon.setPixmap(pixmap)
        else:
            self.logo_icon.setText("🧑‍🍳")
            
        logo_layout.addWidget(self.logo_icon)

        logo_text = QLabel("Jayraldine's\nCATERING")
        logo_text.setObjectName("logoText")
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()

        layout.addWidget(logo_frame)

        self.buttons = []
        
        pages = [
            ("Dashboard", 0),
            ("Bookings",  1),
            ("Calendar",  2),
            ("Reports",   3),
        ]
        
        layout.addSpacing(20)

        for text, index in pages:
            btn = QPushButton(f"  {text}")
            btn.setCheckable(True)
            btn.setIconSize(QSize(18, 18))
            btn.setIcon(nav_icon(_NAV_ICON_MAP[index]))

            if index == 0:
                btn.setChecked(True)
                btn.setIcon(nav_icon_active(_NAV_ICON_MAP[index]))

            btn.clicked.connect(lambda checked=False, idx=index: self.handle_click(idx))
            layout.addWidget(btn)
            self.buttons.append(btn)
            
        layout.addStretch()

        user_frame = QFrame()
        user_frame.setObjectName("userProfileArea")
        user_layout = QHBoxLayout(user_frame)
        user_layout.setContentsMargins(0, 0, 0, 0)
        
        avatar = QLabel("A")
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(35, 35)
        avatar.setAlignment(Qt.AlignCenter)
        user_layout.addWidget(avatar)

        vbox_details = QVBoxLayout()
        name = QLabel("Admin User")
        name.setStyleSheet("color: #eaeaea; font-weight: bold; font-size: 13px;")
        email = QLabel("admin@jayraldines.com")
        email.setStyleSheet("color: #9aa0a6; font-size: 11px;")
        vbox_details.addWidget(name)
        vbox_details.addWidget(email)
        vbox_details.setSpacing(0)
        user_layout.addLayout(vbox_details)
        user_layout.addStretch()

        logout_btn = QLabel()
        logout_btn.setPixmap(get_icon("log-out", color="#9aa0a6", size=QSize(16, 16)).pixmap(QSize(16, 16)))
        user_layout.addWidget(logout_btn)

        layout.addWidget(user_frame)

    def handle_click(self, index):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)
            icon_name = _NAV_ICON_MAP[i]
            btn.setIcon(nav_icon_active(icon_name) if i == index else nav_icon(icon_name))
        self.page_changed.emit(index)
