from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QFormLayout
)
from PySide6.QtCore import Qt, QSize

from utils.icon_manager import btn_icon_primary


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(20)

        sec_title = QLabel("Business Information")
        sec_title.setObjectName("h3")
        card_layout.addWidget(sec_title)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        for label, placeholder in [
            ("Business Name",  "e.g. Jayraldine's Catering"),
            ("Contact Number", "+63 XXX XXX XXXX"),
            ("Email",          "admin@jayraldines.com"),
            ("Address",        "Street, City, Province"),
        ]:
            field = QLineEdit()
            field.setPlaceholderText(placeholder)
            form.addRow(QLabel(label), field)

        card_layout.addLayout(form)

        save_btn = QPushButton("  Save Changes")
        save_btn.setObjectName("primaryButton")
        save_btn.setIcon(btn_icon_primary("check"))
        save_btn.setIconSize(QSize(15, 15))
        save_btn.setFixedWidth(160)
        card_layout.addWidget(save_btn, alignment=Qt.AlignRight)

        root.addWidget(card)
        root.addStretch()
