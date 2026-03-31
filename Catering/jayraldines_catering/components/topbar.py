from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

class Topbar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("topbar")
        self.setFixedHeight(60)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        
        title = QLabel("Jayraldine's Catering | Owner Dashboard")
        title.setObjectName("appTitle")
        
        bell_btn = QPushButton("🔔")
        bell_btn.setFixedSize(35, 35)
        bell_btn.setStyleSheet("border: none; font-size: 18px;")
        
        profile = QLabel("👤 Admin")
        profile.setStyleSheet("font-weight: bold; color: #555;")
        
        layout.addWidget(title)
        layout.addStretch() # Pushes the next items to the right
        layout.addWidget(bell_btn)
        layout.addWidget(profile)