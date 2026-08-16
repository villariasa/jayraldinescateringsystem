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

from utils.icons import btn_icon_primary, btn_icon_secondary, get_icon
from utils.theme import ThemeManager
from utils.accent import AccentManager, PRESET_THEMES
from utils.palette import THEME_CATEGORIES, THEME_PALETTES, get_palettes_by_category
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
        lay.addWidget(self._build_import_card())
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

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        test_btn = QPushButton("  Test Connection")
        test_btn.setObjectName("secondaryButton")
        test_btn.setIcon(get_icon("bell", color="#64748B", size=QSize(15, 15)))
        test_btn.setIconSize(QSize(15, 15))
        test_btn.setFixedWidth(160)
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.clicked.connect(self._test_smtp)
        btn_row.addWidget(test_btn)

        save_btn = QPushButton("  Save SMTP Config")
        save_btn.setObjectName("primaryButton")
        save_btn.setIcon(btn_icon_primary("check"))
        save_btn.setIconSize(QSize(15, 15))
        save_btn.setFixedWidth(180)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_smtp)
        btn_row.addWidget(save_btn)

        lay.addLayout(btn_row)

        return card

    def _build_theme_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        header_row = QHBoxLayout()
        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)

        sec_title = QLabel("Appearance & Themes")
        sec_title.setObjectName("h3")
        sec_sub = QLabel("Select from curated theme palettes across nature, mood, colors, vibes, and seasons.")
        sec_sub.setObjectName("subtitle")
        v_titles.addWidget(sec_title)
        v_titles.addWidget(sec_sub)
        header_row.addLayout(v_titles, 1)

        self._theme_lbl = QLabel(self._theme.palette.get("name", "Dark Mode"))
        self._theme_lbl.setStyleSheet(f"color: {AccentManager().current}; font-size: 13px; font-weight: 700;")
        header_row.addWidget(self._theme_lbl)

        toggle_btn = QPushButton("  Toggle Dark/Light")
        toggle_btn.setObjectName("secondaryButton")
        toggle_btn.setFixedWidth(160)
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.clicked.connect(self._toggle_theme)
        header_row.addWidget(toggle_btn)
        lay.addLayout(header_row)

        # ── Category Filter Pills ──────────────────────────────────────────
        self._active_category = "All"
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(46)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        cat_w = QWidget()
        self._cat_row = QHBoxLayout(cat_w)
        self._cat_row.setContentsMargins(0, 4, 0, 4)
        self._cat_row.setSpacing(8)

        self._cat_buttons = []
        for cat in ["All"] + THEME_CATEGORIES:
            btn = QPushButton(cat)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda _, c=cat: self._on_select_category(c))
            self._cat_row.addWidget(btn)
            self._cat_buttons.append((cat, btn))

        self._cat_row.addStretch()
        cat_scroll.setWidget(cat_w)
        lay.addWidget(cat_scroll)
        self._update_cat_buttons_style()

        # ── Palette Cards Container ─────────────────────────────────────────
        self._palettes_container = QVBoxLayout()
        self._palettes_container.setSpacing(12)
        lay.addLayout(self._palettes_container)
        self._rebuild_palette_cards()

        # ── Accent Color Customizer ─────────────────────────────────────────
        accent_divider = QFrame()
        accent_divider.setFrameShape(QFrame.HLine)
        accent_divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        lay.addWidget(accent_divider)

        color_lbl = QLabel("Primary Accent Color")
        color_lbl.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 4px;")
        lay.addWidget(color_lbl)

        self._swatch_container = QVBoxLayout()
        self._swatch_container.setSpacing(8)
        lay.addLayout(self._swatch_container)
        self._rebuild_color_swatches()

        return card

    # ── Category & Palette Selection ────────────────────────────────────────

    def _on_select_category(self, cat: str):
        self._active_category = cat
        self._update_cat_buttons_style()
        self._rebuild_palette_cards()

    def _update_cat_buttons_style(self):
        for cat, btn in self._cat_buttons:
            if cat == self._active_category:
                btn.setStyleSheet(
                    f"background: {AccentManager().current}; color: #FFFFFF; font-weight: 700; "
                    f"border-radius: 16px; padding: 0 16px; border: none; font-size: 12px;"
                )
            else:
                dark = self._theme.is_dark()
                bg = "rgba(255, 255, 255, 0.05)" if dark else "rgba(0, 0, 0, 0.05)"
                fg = "#94A3B8" if dark else "#64748B"
                border = "#334155" if dark else "#CBD5E1"
                btn.setStyleSheet(
                    f"background: {bg}; color: {fg}; font-weight: 600; "
                    f"border-radius: 16px; padding: 0 16px; border: 1px solid {border}; font-size: 12px;"
                )

    def _rebuild_palette_cards(self):
        self._clear_layout(self._palettes_container)

        by_cat = get_palettes_by_category()
        categories_to_show = [self._active_category] if self._active_category != "All" else THEME_CATEGORIES

        for cat in categories_to_show:
            palettes = by_cat.get(cat, [])
            if not palettes:
                continue

            if self._active_category == "All":
                cat_head = QLabel(cat)
                cat_head.setStyleSheet("font-weight: 700; font-size: 13px; color: #94A3B8; margin-top: 6px;")
                self._palettes_container.addWidget(cat_head)

            # Grid in rows of 3
            current_row = QHBoxLayout()
            current_row.setSpacing(12)
            cards_in_row = 0

            for pal in palettes:
                card = self._create_palette_card(pal)
                current_row.addWidget(card)
                cards_in_row += 1
                if cards_in_row == 3:
                    self._palettes_container.addLayout(current_row)
                    current_row = QHBoxLayout()
                    current_row.setSpacing(12)
                    cards_in_row = 0

            if cards_in_row > 0:
                current_row.addStretch()
                self._palettes_container.addLayout(current_row)

    def _create_palette_card(self, pal: dict) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(84)
        card.setMinimumWidth(220)

        is_active = self._theme.palette_id == pal["id"]
        dark = self._theme.is_dark()
        active_border = f"2px solid {pal['primary']}" if is_active else ("1px solid #334155" if dark else "1px solid #E2E8F0")
        card_bg = pal["surface"]

        card.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: {active_border};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 2px solid {pal['primary']};
            }}
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        top_row = QHBoxLayout()
        name_lbl = QLabel(pal["name"])
        name_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-weight: 700; font-size: 13px;")
        top_row.addWidget(name_lbl, 1)

        mode_badge = QLabel(f" {pal['mode'].upper()} ")
        mode_color = "#38BDF8" if pal["mode"] == "dark" else "#F59E0B"
        mode_badge.setStyleSheet(f"background: rgba(255,255,255,0.08); color: {mode_color}; font-size: 10px; font-weight: 800; border-radius: 6px; padding: 2px 6px;")
        top_row.addWidget(mode_badge)

        if is_active:
            check_lbl = QLabel("✓")
            check_lbl.setStyleSheet(f"color: {pal['primary']}; font-weight: 900; font-size: 14px;")
            top_row.addWidget(check_lbl)

        lay.addLayout(top_row)

        # 4-bar swatch preview: [Background, Surface, Accent, Text]
        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(4)
        colors = [pal["background"], pal["surface"], pal["primary"], pal["text_primary"]]
        labels = ["BG", "Card", "Accent", "Text"]
        for c, _ in zip(colors, labels):
            sw = QFrame()
            sw.setFixedHeight(14)
            sw.setStyleSheet(f"background-color: {c}; border-radius: 4px; border: 1px solid rgba(0,0,0,0.15);")
            swatch_row.addWidget(sw, 1)
        lay.addLayout(swatch_row)

        card.mousePressEvent = lambda _, pid=pal["id"]: self._on_select_palette(pid)
        return card

    def _on_select_palette(self, palette_id: str):
        self._theme.apply_palette(palette_id)
        self._theme_lbl.setText(self._theme.palette.get("name", "Dark Mode"))
        self._theme_lbl.setStyleSheet(f"color: {AccentManager().current}; font-size: 13px; font-weight: 700;")
        self._update_cat_buttons_style()
        self._rebuild_palette_cards()
        self._rebuild_color_swatches()
        success(self, message=f"Theme set to '{self._theme.palette.get('name')}'")

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
        self._rebuild_palette_cards()

    def _pick_custom_color(self):
        color = QColorDialog.getColor(QColor(self._accent.current), self, "Choose a Custom Color")
        if not color.isValid():
            return
        hex_color = color.name().upper()
        self._accent.add_custom_color(hex_color)
        self._accent.set_accent(hex_color)
        self._rebuild_color_swatches()
        self._rebuild_palette_cards()

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

    def _build_import_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        sec_title = QLabel("Data Import & Export Migration")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        sub = QLabel("Import or export Bookings, Customers, Expenses, Menu Items, or Billings using pre-formatted Excel or CSV templates.")
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        import_btn = QPushButton("  Open Data Import Wizard")
        import_btn.setObjectName("primaryButton")
        import_btn.setIcon(btn_icon_primary("export"))
        import_btn.setIconSize(QSize(15, 15))
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._open_import_wizard)

        export_btn = QPushButton("  Open Data Export Wizard")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._open_export_wizard)

        btn_row.addWidget(import_btn)
        btn_row.addWidget(export_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        return card

    def _open_import_wizard(self):
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="customers", parent=self)
        dlg.exec()

    def _open_export_wizard(self):
        from components.export_dialog import ExportWizardDialog
        dlg = ExportWizardDialog(parent=self)
        dlg.exec()

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

    def _test_smtp(self):
        host = self._smtp_host_f.text().strip()
        port = self._smtp_port_f.value()
        user = self._smtp_user_f.text().strip()
        pwd  = self._smtp_pass_f.text()

        if not host or not user or not pwd:
            QMessageBox.warning(self, "Incomplete Configuration", "Please enter SMTP Host, Username/Email, and Password before testing.")
            return

        import smtplib
        import ssl
        try:
            context = ssl.create_default_context()
            if port == 465:
                with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
                    server.login(user, pwd)
            else:
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.login(user, pwd)
            success(self, message=f"SMTP Connection Successful!\nConnected and authenticated with {host}:{port} as {user}.")
        except Exception as exc:
            err_msg = str(exc)
            if "Application-specific password required" in err_msg or "BadCredentials" in err_msg or "Username and Password not accepted" in err_msg:
                err_msg += "\n\nTip for Gmail: Google requires a 16-character 'App Password'.\nGo to Google Account -> Security -> 2-Step Verification -> App Passwords."
            QMessageBox.critical(self, "SMTP Connection Failed", f"Could not connect to SMTP server:\n\n{err_msg}")

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
