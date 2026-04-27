import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QFormLayout, QMessageBox, QScrollArea,
    QTableWidget, QHeaderView, QDoubleSpinBox, QSpinBox, QCheckBox,
    QFileDialog
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
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        lay.addWidget(title)

        lay.addWidget(self._build_business_card())
        lay.addWidget(self._build_policy_card())
        lay.addWidget(self._build_smtp_card())
        lay.addWidget(self._build_theme_card())
        lay.addWidget(self._build_backup_card())
        lay.addWidget(self._build_audit_card())
        lay.addStretch()

        scroll.setWidget(content)
        root_lay.addWidget(scroll)

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

    def _build_policy_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        sec_title = QLabel("Booking & Capacity Policy")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        try:
            policy = repo.get_business_policy()
        except Exception:
            policy = {"min_downpayment_pct": 30.0, "allow_zero_downpayment": False, "max_daily_pax": 600}

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        self._min_dp_spin = QDoubleSpinBox()
        self._min_dp_spin.setRange(0, 100)
        self._min_dp_spin.setSuffix(" %")
        self._min_dp_spin.setValue(policy["min_downpayment_pct"])
        form.addRow(QLabel("Minimum Downpayment"), self._min_dp_spin)

        self._allow_zero_cb = QCheckBox("Allow confirming without downpayment")
        self._allow_zero_cb.setChecked(policy["allow_zero_downpayment"])
        form.addRow(QLabel("Override"), self._allow_zero_cb)

        self._max_pax_spin = QSpinBox()
        self._max_pax_spin.setRange(1, 10000)
        self._max_pax_spin.setSuffix(" pax")
        self._max_pax_spin.setValue(policy["max_daily_pax"])
        form.addRow(QLabel("Max Daily Capacity"), self._max_pax_spin)

        lay.addLayout(form)

        save_btn = QPushButton("  Save Policy")
        save_btn.setObjectName("primaryButton")
        save_btn.setIcon(btn_icon_primary("check"))
        save_btn.setIconSize(QSize(15, 15))
        save_btn.setFixedWidth(140)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_policy)
        lay.addWidget(save_btn, alignment=Qt.AlignRight)

        return card

    def _build_smtp_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        sec_title = QLabel("Email (SMTP) Configuration")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        sub = QLabel("Used for sending receipts and booking confirmations. Gmail: use App Password with port 587.")
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        try:
            smtp = repo.get_smtp_config()
        except Exception:
            smtp = {"smtp_host": "", "smtp_port": 587, "smtp_user": "", "smtp_pass": ""}

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        self._smtp_host_f = QLineEdit(smtp["smtp_host"])
        self._smtp_host_f.setPlaceholderText("smtp.gmail.com")
        self._smtp_port_f = QSpinBox()
        self._smtp_port_f.setRange(1, 65535)
        self._smtp_port_f.setValue(smtp["smtp_port"])
        self._smtp_user_f = QLineEdit(smtp["smtp_user"])
        self._smtp_user_f.setPlaceholderText("your@email.com")
        self._smtp_pass_f = QLineEdit(smtp["smtp_pass"])
        self._smtp_pass_f.setEchoMode(QLineEdit.Password)
        self._smtp_pass_f.setPlaceholderText("App password or SMTP password")

        for label, field in [
            ("SMTP Host",     self._smtp_host_f),
            ("Port",          self._smtp_port_f),
            ("Username",      self._smtp_user_f),
            ("Password",      self._smtp_pass_f),
        ]:
            form.addRow(QLabel(label), field)

        lay.addLayout(form)

        save_btn = QPushButton("  Save SMTP Config")
        save_btn.setObjectName("primaryButton")
        save_btn.setIcon(btn_icon_primary("check"))
        save_btn.setIconSize(QSize(15, 15))
        save_btn.setFixedWidth(180)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_smtp)
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

    def _build_backup_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        sec_title = QLabel("Database Backup & Restore")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        sub = QLabel("Backup exports the full database to a .sql file. Restore will overwrite current data.")
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        backup_btn = QPushButton("  Backup Database")
        backup_btn.setObjectName("primaryButton")
        backup_btn.setIcon(btn_icon_primary("export"))
        backup_btn.setIconSize(QSize(15, 15))
        backup_btn.setCursor(Qt.PointingHandCursor)
        backup_btn.clicked.connect(self._backup_db)

        restore_btn = QPushButton("  Restore Database")
        restore_btn.setObjectName("secondaryButton")
        restore_btn.setCursor(Qt.PointingHandCursor)
        restore_btn.clicked.connect(self._restore_db)

        btn_row.addWidget(backup_btn)
        btn_row.addWidget(restore_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        return card

    def _build_audit_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        head = QHBoxLayout()
        sec_title = QLabel("Audit Log")
        sec_title.setObjectName("h3")
        head.addWidget(sec_title)
        head.addStretch()
        refresh_btn = QPushButton("  Refresh")
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.setFixedHeight(30)
        refresh_btn.clicked.connect(self._load_audit_log)
        head.addWidget(refresh_btn)
        lay.addLayout(head)

        self._audit_table = QTableWidget(0, 4)
        self._audit_table.setHorizontalHeaderLabels(["TIME", "ACTOR", "ACTION", "DESCRIPTION"])
        self._audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._audit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._audit_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._audit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._audit_table.setColumnWidth(0, 150)
        self._audit_table.setColumnWidth(1, 100)
        self._audit_table.setColumnWidth(2, 100)
        self._audit_table.verticalHeader().setVisible(False)
        self._audit_table.setShowGrid(False)
        self._audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._audit_table.setFocusPolicy(Qt.NoFocus)
        self._audit_table.setSelectionMode(QTableWidget.NoSelection)
        self._audit_table.setMinimumHeight(260)
        lay.addWidget(self._audit_table)

        self._load_audit_log()
        return card

    def _load_audit_log(self):
        from PySide6.QtWidgets import QTableWidgetItem
        logs = repo.get_audit_log(50)
        self._audit_table.setRowCount(0)
        if not logs:
            self._audit_table.insertRow(0)
            self._audit_table.setItem(0, 3, QTableWidgetItem("No audit entries yet."))
            return
        for log in logs:
            row = self._audit_table.rowCount()
            self._audit_table.insertRow(row)
            self._audit_table.setRowHeight(row, 40)
            self._audit_table.setItem(row, 0, QTableWidgetItem(log["created_at"]))
            self._audit_table.setItem(row, 1, QTableWidgetItem(log["actor"]))
            self._audit_table.setItem(row, 2, QTableWidgetItem(log["action"]))
            self._audit_table.setItem(row, 3, QTableWidgetItem(log["description"]))

    def _save_business(self):
        _BUSINESS_INFO["name"]    = self._name_f.text().strip()
        _BUSINESS_INFO["contact"] = self._contact_f.text().strip()
        _BUSINESS_INFO["email"]   = self._email_f.text().strip()
        _BUSINESS_INFO["address"] = self._address_f.text().strip()
        repo.save_business_info(_BUSINESS_INFO)
        self._save_notice.setText("Changes saved successfully.")
        self._save_notice.show()
        success(self, message="Business information saved successfully.")

    def _save_policy(self):
        try:
            repo.save_booking_policy(self._min_dp_spin.value(), self._allow_zero_cb.isChecked())
            repo.save_capacity_policy(self._max_pax_spin.value())
            success(self, message="Policy saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _save_smtp(self):
        try:
            repo.save_smtp_config(
                self._smtp_host_f.text().strip(),
                self._smtp_port_f.value(),
                self._smtp_user_f.text().strip(),
                self._smtp_pass_f.text(),
            )
            success(self, message="SMTP configuration saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _toggle_theme(self):
        new_theme = self._theme.toggle()
        self._theme_lbl.setText("Dark Mode" if new_theme == "dark" else "Light Mode")

    def _backup_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", "jayraldines_backup.sql", "SQL Files (*.sql)"
        )
        if not path:
            return
        try:
            result = subprocess.run(
                ["pg_dump", "-U", "postgres", "-d", "jayraldines_catering", "-f", path],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                success(self, message=f"Database backed up successfully to:\n{path}")
            else:
                QMessageBox.warning(self, "Backup Failed", result.stderr or "pg_dump returned an error.")
        except FileNotFoundError:
            QMessageBox.warning(self, "Not Found",
                "pg_dump not found. Make sure PostgreSQL is installed and in your PATH.")
        except Exception as exc:
            QMessageBox.warning(self, "Backup Error", str(exc))

    def _restore_db(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore Database", "", "SQL Files (*.sql)"
        )
        if not path:
            return
        confirm = QMessageBox.warning(
            self, "Confirm Restore",
            "This will OVERWRITE all current data with the selected backup.\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            result = subprocess.run(
                ["psql", "-U", "postgres", "-d", "jayraldines_catering", "-f", path],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                success(self, message="Database restored successfully. Please restart the application.")
            else:
                QMessageBox.warning(self, "Restore Failed", result.stderr or "psql returned an error.")
        except FileNotFoundError:
            QMessageBox.warning(self, "Not Found",
                "psql not found. Make sure PostgreSQL is installed and in your PATH.")
        except Exception as exc:
            QMessageBox.warning(self, "Restore Error", str(exc))
