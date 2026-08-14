import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QFormLayout, QMessageBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QSpinBox, QCheckBox, QFileDialog, QListWidget, QListWidgetItem,
    QInputDialog, QColorDialog,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, get_icon
from utils.theme import ThemeManager
from utils.accent import AccentManager, PRESET_THEMES
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
        self._accent = AccentManager()
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
        lay.addWidget(self._build_occasions_card())
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

        color_lbl = QLabel("Color Theme")
        color_lbl.setStyleSheet("font-size: 13px; margin-top: 4px;")
        lay.addWidget(color_lbl)

        self._swatch_container = QVBoxLayout()
        self._swatch_container.setSpacing(8)
        lay.addLayout(self._swatch_container)
        self._rebuild_color_swatches()

        return card

    # ── Color theme picker ──────────────────────────────────────────────

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _make_swatch(self, hex_color: str, removable: bool = False) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        selected = hex_color.upper() == self._accent.current.upper()
        ring = "#F9FAFB" if self._theme.is_dark() else "#0F172A"
        border = f"3px solid {ring}" if selected else "3px solid transparent"
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {hex_color}; border-radius: 14px; border: {border}; }}"
        )
        btn.setToolTip(hex_color.upper() + (" (right-click to remove)" if removable else ""))
        btn.clicked.connect(lambda _checked=False, h=hex_color: self._select_accent(h))
        if removable:
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda _pos, h=hex_color: self._remove_custom_color(h))
        return btn

    def _rebuild_color_swatches(self):
        self._clear_layout(self._swatch_container)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for _name, hex_color in PRESET_THEMES:
            preset_row.addWidget(self._make_swatch(hex_color))
        preset_row.addStretch()
        self._swatch_container.addLayout(preset_row)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        for hex_color in self._accent.custom_colors:
            custom_row.addWidget(self._make_swatch(hex_color, removable=True))

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setCursor(Qt.PointingHandCursor)
        dark = self._theme.is_dark()
        muted_border = "#4B5563" if dark else "#CBD5E1"
        muted_text = "#9CA3AF" if dark else "#64748B"
        add_btn.setStyleSheet(
            f"QPushButton {{ border-radius: 14px; border: 2px dashed {muted_border}; "
            f"color: {muted_text}; font-weight: 700; background: transparent; }}"
            f"QPushButton:hover {{ border-color: {self._accent.current}; color: {self._accent.current}; }}"
        )
        add_btn.setToolTip("Add a custom color")
        add_btn.clicked.connect(self._pick_custom_color)
        custom_row.addWidget(add_btn)
        custom_row.addStretch()
        self._swatch_container.addLayout(custom_row)

    def _select_accent(self, hex_color: str):
        self._accent.set_accent(hex_color)
        self._rebuild_color_swatches()

    def _pick_custom_color(self):
        color = QColorDialog.getColor(QColor(self._accent.current), self, "Choose a Custom Color")
        if not color.isValid():
            return
        hex_color = color.name().upper()
        self._accent.add_custom_color(hex_color)
        self._accent.set_accent(hex_color)
        self._rebuild_color_swatches()

    def _remove_custom_color(self, hex_color: str):
        self._accent.remove_custom_color(hex_color)
        self._rebuild_color_swatches()

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

    def _build_occasions_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        head = QHBoxLayout()
        sec_title = QLabel("Occasion Types")
        sec_title.setObjectName("h3")
        head.addWidget(sec_title)
        head.addStretch()
        add_btn = QPushButton("  Add")
        add_btn.setObjectName("primaryButton")
        add_btn.setFixedHeight(30)
        add_btn.setIcon(btn_icon_primary("plus"))
        add_btn.clicked.connect(self._add_occasion)
        head.addWidget(add_btn)
        lay.addLayout(head)

        self._occ_list = QListWidget()
        self._occ_list.setFixedHeight(200)
        self._occ_list.setFocusPolicy(Qt.NoFocus)
        lay.addWidget(self._occ_list)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        edit_btn = QPushButton("  Rename")
        edit_btn.setObjectName("secondaryButton")
        edit_btn.setFixedHeight(30)
        edit_btn.clicked.connect(self._edit_occasion)
        del_btn = QPushButton("  Delete")
        del_btn.setObjectName("secondaryButton")
        del_btn.setFixedHeight(30)
        del_btn.clicked.connect(self._delete_occasion)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        lay.addLayout(btn_row)

        self._load_occasions()
        return card

    def _load_occasions(self):
        self._occ_list.clear()
        for name in repo.get_all_occasions():
            self._occ_list.addItem(QListWidgetItem(name))

    def _add_occasion(self):
        text, ok = QInputDialog.getText(self, "Add Occasion", "Occasion name:")
        if ok and text.strip():
            try:
                repo.add_occasion(text.strip())
                self._load_occasions()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _edit_occasion(self):
        item = self._occ_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select an occasion to rename.")
            return
        old_name = item.text()
        text, ok = QInputDialog.getText(self, "Rename Occasion", "New name:", text=old_name)
        if ok and text.strip() and text.strip() != old_name:
            try:
                repo.update_occasion(old_name, text.strip())
                self._load_occasions()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_occasion(self):
        item = self._occ_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select an occasion to delete.")
            return
        name = item.text()
        reply = QMessageBox.question(
            self, "Delete Occasion",
            f"Delete '{name}'? Existing bookings using this occasion will not be affected.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                repo.delete_occasion(name)
                self._load_occasions()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

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

        self.audit_scroll = QScrollArea()
        self.audit_scroll.setWidgetResizable(True)
        self.audit_scroll.setFrameShape(QFrame.NoFrame)
        self.audit_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.audit_scroll.setStyleSheet("background: transparent;")
        self.audit_scroll.setMinimumHeight(260)

        self.audit_cards_container = QWidget()
        self.audit_cards_container.setStyleSheet("background: transparent;")
        self.audit_cards_layout = QVBoxLayout(self.audit_cards_container)
        self.audit_cards_layout.setContentsMargins(0, 0, 10, 0)
        self.audit_cards_layout.setSpacing(8)

        self.audit_scroll.setWidget(self.audit_cards_container)
        lay.addWidget(self.audit_scroll)

        self._load_audit_log()
        return card

    def _load_audit_log(self):
        while self.audit_cards_layout.count():
            item = self.audit_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        logs = repo.get_audit_log(50)
        if not logs:
            empty_card = QFrame()
            empty_card.setObjectName("entryCard")
            el = QVBoxLayout(empty_card)
            item = QLabel("No audit entries yet.")
            item.setObjectName("subtitle")
            item.setAlignment(Qt.AlignCenter)
            el.addWidget(item)
            self.audit_cards_layout.addWidget(empty_card)
        else:
            action_colors = {
                "APPROVE": "#22C55E", "CREATE": "#3B82F6", "CANCEL": "#EF4444",
                "PAYMENT": "#F59E0B", "DELETE": "#EF4444", "UPDATE": "#8B5CF6",
            }
            for log in logs:
                card = QFrame()
                card.setObjectName("entryCard")
                cl = QHBoxLayout(card)
                cl.setContentsMargins(12, 10, 12, 10)
                cl.setSpacing(14)

                c1 = QVBoxLayout()
                c1.setSpacing(2)
                act_str = log.get("action", "LOG")
                act_color = action_colors.get(act_str, "#9CA3AF")
                act_lbl = QLabel(act_str)
                act_lbl.setStyleSheet(f"font-weight: 800; font-size: 11px; color: {act_color}; padding: 2px 6px; background: rgba(255,255,255,0.05); border-radius: 4px;")
                actor_lbl = QLabel(f"By: {log.get('actor', 'User')}")
                actor_lbl.setObjectName("subtitle")
                c1.addWidget(act_lbl, alignment=Qt.AlignLeft)
                c1.addWidget(actor_lbl)
                cl.addLayout(c1, 1)

                desc_lbl = QLabel(log.get("description", ""))
                desc_lbl.setStyleSheet("font-size: 12px;")
                desc_lbl.setWordWrap(True)
                cl.addWidget(desc_lbl, 4)

                time_lbl = QLabel(log.get("created_at", ""))
                time_lbl.setStyleSheet("font-size: 11px; color: #6B7280;")
                cl.addWidget(time_lbl, 2)

                self.audit_cards_layout.addWidget(card)

        self.audit_cards_layout.addStretch()

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
