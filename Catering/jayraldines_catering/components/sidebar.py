import os  # <-- Add this missing line right at the top
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QPixmap

# Get the absolute path to the assets folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# ... the rest of your Sidebar code continues below ...
class Sidebar(QFrame):
    page_changed = Signal(int) 

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Top Section: Custom Logo Area ---
        logo_frame = QFrame()
        logo_frame.setObjectName("logoArea")
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(10)

        # Load your custom SVG logo
        self.logo_icon = QLabel()
        logo_path = os.path.join(ASSETS_DIR, "logo.png")
        
        if os.path.exists(logo_path):
            # Load and scale the SVG smoothly
            pixmap = QPixmap(logo_path).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_icon.setPixmap(pixmap)
        else:
            self.logo_icon.setText("🧑‍🍳") # Fallback if file isn't there yet
            
        logo_layout.addWidget(self.logo_icon)

        # Logo Text (You can remove this if your SVG logo already includes the text!)
        logo_text = QLabel("Jayraldine's\nCATERING")
        logo_text.setObjectName("logoText")
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()

        layout.addWidget(logo_frame)

        # --- Middle Section: Menu Buttons with Custom Icons ---
        self.buttons = []
        
        # Format: (Text, Icon Filename, Index)
        pages = [
            ("Dashboard", "dashboard.png", 0),
            ("Bookings", "booking.png", 1),
            ("Calendar", "calendar.png", 2),
            ("Reports", "reports.png", 3)
        ]
        
        layout.addSpacing(20) 

        for text, icon_file, index in pages:
            btn = QPushButton(f"  {text}") # Added a little spacing before text
            btn.setCheckable(True)
            
            # Load the custom icon
            icon_path = os.path.join(ASSETS_DIR, "icons", icon_file)
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
            
            if index == 0: 
                btn.setChecked(True)
            
            btn.clicked.connect(lambda checked=False, idx=index: self.handle_click(idx))
            layout.addWidget(btn)
            self.buttons.append(btn)
            
        layout.addStretch()

        # --- Bottom Section: User Profile ---
        user_frame = QFrame()
        user_frame.setObjectName("userProfileArea")
        user_layout = QHBoxLayout(user_frame)
        user_layout.setContentsMargins(0, 0, 0, 0)
        
        # Avatar circle
        avatar = QLabel("A")
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(35, 35)
        avatar.setAlignment(Qt.AlignCenter)
        user_layout.addWidget(avatar)

        # User details
        vbox_details = QVBoxLayout()
        name = QLabel("Admin User")
        name.setStyleSheet("color: #212529; font-weight: bold; font-size: 13px;")
        email = QLabel("admin@jayraldines.com")
        email.setStyleSheet("color: #6C757D; font-size: 11px;")
        vbox_details.addWidget(name)
        vbox_details.addWidget(email)
        vbox_details.setSpacing(0)
        user_layout.addLayout(vbox_details)
        user_layout.addStretch()

        # Logout placeholder icon
        logout_btn = QLabel("↪️") 
        logout_btn.setStyleSheet("color: #6C757D; font-size: 16px; font-weight: bold;")
        user_layout.addWidget(logout_btn)

        layout.addWidget(user_frame)

    def handle_click(self, index):
        for i, btn in enumerate(self.buttons):
            # Assumes list of buttons matches pages 0, 1, 2, 3
            btn.setChecked(i == index)
        self.page_changed.emit(index)