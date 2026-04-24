from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QSize

from utils.icons import btn_icon_primary, get_icon
from utils.theme import ThemeManager
from components.dialogs import success
import utils.repository as repo


_BUSINESS_INFO = {
    "name":    "Jayraldine's Catering",
    "contact": "+63 912 345 6789",
    "email":   "admin@jayraldines.com",
    "address": "123 Rizal St., Manila, Metro Manila",
}


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._theme = ThemeManager()
        db_info = repo.get_business_info()
        if db_info:
            _BUSINESS_INFO.update(db_info)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        root.addWidget(self._build_business_card())
        root.addWidget(self._build_theme_card())
        root.addStretch()

    def _build_business_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        sec_title = QLabel("Business Information")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        self._name_f    = QLineEdit(_BUSINESS_INFO["name"])
        self._contact_f = QLineEdit(_BUSINESS_INFO["contact"])
        self._email_f   = QLineEdit(_BUSINESS_INFO["email"])
        self._address_f = QLineEdit(_BUSINESS_INFO["address"])

        for label, field in [
            ("Business Name",  self._name_f),
            ("Contact Number", self._contact_f),
            ("Email",          self._email_f),
            ("Address",        self._address_f),
        ]:
            form.addRow(QLabel(label), field)

        lay.addLayout(form)

        self._save_notice = QLabel("")
        self._save_notice.setStyleSheet("color: #22C55E; font-size: 12px;")
        self._save_notice.hide()
        lay.addWidget(self._save_notice)

        save_btn = QPushButton("  Save Changes")
        save_btn.setObjectName("primaryButton")
        save_btn.setIcon(btn_icon_primary("check"))
        save_btn.setIconSize(QSize(15, 15))
        save_btn.setFixedWidth(160)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_business)
        lay.addWidget(save_btn, alignment=Qt.AlignRight)

        return card

    def _build_theme_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        sec_title = QLabel("Appearance")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        row = QHBoxLayout()
        lbl = QLabel("Theme")
        lbl.setStyleSheet("font-size: 13px;")
        row.addWidget(lbl)
        row.addStretch()

        self._theme_lbl = QLabel("Dark Mode" if self._theme.is_dark() else "Light Mode")
        self._theme_lbl.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        row.addWidget(self._theme_lbl)

        toggle_btn = QPushButton("  Toggle Theme")
        toggle_btn.setObjectName("secondaryButton")
        toggle_btn.setFixedWidth(140)
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.clicked.connect(self._toggle_theme)
        row.addWidget(toggle_btn)

        lay.addLayout(row)
        return card

    def _save_business(self):
        _BUSINESS_INFO["name"]    = self._name_f.text().strip()
        _BUSINESS_INFO["contact"] = self._contact_f.text().strip()
        _BUSINESS_INFO["email"]   = self._email_f.text().strip()
        _BUSINESS_INFO["address"] = self._address_f.text().strip()
        repo.save_business_info(_BUSINESS_INFO)
        self._save_notice.setText("Changes saved successfully.")
        self._save_notice.show()
        success(self, message="Business information saved successfully.")

    def _toggle_theme(self):
        new_theme = self._theme.toggle()
        self._theme_lbl.setText("Dark Mode" if new_theme == "dark" else "Light Mode")
