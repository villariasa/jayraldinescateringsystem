from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDateEdit, QTimeEdit, QSpinBox,
    QFrame, QWidget, QStackedWidget, QTextEdit, QCheckBox,
    QScrollArea, QSizePolicy, QCompleter
)
from PySide6.QtCore import Qt, QDate, QTime, QSize, Signal

from utils.icons import btn_icon_primary, btn_icon_secondary, get_icon
from utils.theme import ThemeManager
import utils.menu_store as menu_store
import utils.repository as repo


def _is_light():
    return not ThemeManager().is_dark()


def _readonly_input_style():
    if _is_light():
        return "background:#F1F5F9;color:#64748B;border:1px solid #E2E8F0;border-radius:8px;padding:8px 14px;"
    return "background:#111827;color:#9CA3AF;border:1px solid #243244;border-radius:8px;padding:8px 14px;"


def _package_card_style(selected=False):
    if selected:
        return "QFrame { background: rgba(225,29,72,0.10); border-radius: 10px; border: 2px solid #E11D48; }"
    if _is_light():
        return ("QFrame { background: #F8FAFC; border-radius: 10px; border: 2px solid #E2E8F0; }"
                "QFrame:hover { border: 2px solid #E11D48; }")
    return ("QFrame { background: #1F2937; border-radius: 10px; border: 2px solid #243244; }"
            "QFrame:hover { border: 2px solid #E11D48; }")


def _package_name_style():
    return "font-weight: 700; color: %s; font-size: 13px;" % ("#0F172A" if _is_light() else "#F9FAFB")


def _package_desc_style():
    return "color: %s; font-size: 12px;" % ("#64748B" if _is_light() else "#9CA3AF")


def _notes_style():
    if _is_light():
        return ("background: #F8FAFC; color: #0F172A; border: 1px solid #E2E8F0; "
                "border-radius: 8px; padding: 8px; font-size: 13px;")
    return ("background: #1F2937; color: #F9FAFB; border: 1px solid #243244; "
            "border-radius: 8px; padding: 8px; font-size: 13px;")


def _cost_breakdown_style():
    return "color: %s; font-size: 11px; font-weight: 700; letter-spacing: 1px;" % (
        "#64748B" if _is_light() else "#6B7280"
    )


def _cost_base_style():
    return "color: %s; font-size: 13px;" % ("#475569" if _is_light() else "#9CA3AF")


def _cost_total_style():
    return "color: %s; font-size: 15px; font-weight: 800;" % ("#0F172A" if _is_light() else "#F9FAFB")


def _checkbox_item_style():
    return "color: %s; font-size: 13px;" % ("#0F172A" if _is_light() else "#F9FAFB")


def _step_line_inactive():
    return "background: %s; margin-top: 13px;" % ("#E2E8F0" if _is_light() else "#243244")


_STEPS = ["Customer", "Event", "Menu", "Payment"]

_PACKAGES = [
    ("Standard Package",  "₱1,500/pax", "Buffet setup, 5 dishes, dessert",  1500),
    ("Premium Package",   "₱2,500/pax", "Plated service, 8 dishes, dessert + drinks", 2500),
    ("VIP Package",       "₱3,500/pax", "Full service, 12 dishes, open bar, décor",  3500),
]


def _section_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("sectionLabel")
    return lbl


def _field_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("fieldLabel")
    return lbl


def _input(placeholder="", fixed_height=38):
    f = QLineEdit()
    f.setPlaceholderText(placeholder)
    f.setFixedHeight(fixed_height)
    return f


class StepIndicator(QWidget):
    def __init__(self, steps):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._labels = []
        self._dots = []
        self._lines = []

        for i, step in enumerate(steps):
            col = QVBoxLayout()
            col.setSpacing(4)
            col.setAlignment(Qt.AlignHCenter)

            dot = QLabel()
            dot.setFixedSize(28, 28)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet("border-radius: 14px; background: transparent; color: #6B7280; font-weight: 700; font-size: 12px; border: 2px solid #6B7280;")
            dot.setText(str(i + 1))

            lbl = QLabel(step)
            lbl.setAlignment(Qt.AlignHCenter)
            lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 600;")
            lbl.setObjectName("stepLblInactive")

            col.addWidget(dot, alignment=Qt.AlignHCenter)
            col.addWidget(lbl, alignment=Qt.AlignHCenter)

            self._dots.append(dot)
            self._labels.append(lbl)

            w = QWidget()
            w.setLayout(col)
            layout.addWidget(w)

            if i < len(steps) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFixedHeight(2)
                line.setStyleSheet(_step_line_inactive())
                line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                layout.addWidget(line)
                self._lines.append(line)

    def set_step(self, index):
        for i, (dot, lbl) in enumerate(zip(self._dots, self._labels)):
            if i < index:
                dot.setStyleSheet("border-radius: 14px; background: #22C55E; color: #F9FAFB; font-weight: 700; font-size: 12px; border: 2px solid #22C55E;")
                dot.setText("✓")
                lbl.setStyleSheet("color: #22C55E; font-size: 11px; font-weight: 600;")
            elif i == index:
                dot.setStyleSheet("border-radius: 14px; background: #E11D48; color: #F9FAFB; font-weight: 700; font-size: 12px; border: 2px solid #E11D48;")
                dot.setText(str(i + 1))
                lbl.setStyleSheet("color: #E11D48; font-size: 11px; font-weight: 700;")
            else:
                dot.setStyleSheet("border-radius: 14px; background: transparent; color: #6B7280; font-weight: 700; font-size: 12px; border: 2px solid #6B7280;")
                dot.setText(str(i + 1))
                lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 600;")

        for i, line in enumerate(self._lines):
            color = "#22C55E" if i < index else "#6B7280"
            line.setStyleSheet(f"background: {color}; margin-top: 13px;")


class BookingModal(QDialog):
    booking_saved = Signal(dict)

    def __init__(self, parent=None, booking_data=None):
        super().__init__(parent)
        self._booking_data = booking_data or {}
        self._edit_mode = bool(booking_data)
        self.setWindowTitle("Edit Booking" if self._edit_mode else "New Booking")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(680, 620)
        self.setModal(True)

        self._step = 0
        self._data = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        self._container = QFrame()
        self._container.setObjectName("card")
        self._container.setStyleSheet("")

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(32, 28, 32, 28)
        container_layout.setSpacing(24)

        title_row = QHBoxLayout()
        self._title_lbl = QLabel("Edit Booking" if self._edit_mode else "New Booking")
        self._title_lbl.setObjectName("h2")
        title_row.addWidget(self._title_lbl)
        title_row.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(16, 16)))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(close_btn)
        container_layout.addLayout(title_row)

        self._step_indicator = StepIndicator(_STEPS)
        container_layout.addWidget(self._step_indicator)

        div = QFrame()
        div.setObjectName("divider")
        container_layout.addWidget(div)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step0())
        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        self._stack.addWidget(self._build_step3())
        container_layout.addWidget(self._stack, 1)

        nav_row = QHBoxLayout()
        nav_row.setSpacing(12)
        self._btn_back = QPushButton("  Back")
        self._btn_back.setObjectName("secondaryButton")
        self._btn_back.setIcon(btn_icon_secondary("chevron-left"))
        self._btn_back.setIconSize(QSize(14, 14))
        self._btn_back.setVisible(False)
        self._btn_back.clicked.connect(self._go_back)

        self._btn_next = QPushButton("Next  ")
        self._btn_next.setObjectName("primaryButton")
        self._btn_next.setIcon(get_icon("chevron-right", color="#F9FAFB", size=QSize(14, 14)))
        self._btn_next.setIconSize(QSize(14, 14))
        self._btn_next.clicked.connect(self._go_next)

        nav_row.addWidget(self._btn_back)
        nav_row.addStretch()
        nav_row.addWidget(self._btn_next)
        container_layout.addLayout(nav_row)

        outer.addWidget(self._container)
        self._refresh_step()

    def _scrollable(self, inner_widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(inner_widget)
        return scroll

    def _build_step0(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(_section_label("Customer Information"))

        note = QLabel("Select an existing customer. To add a new customer, go to the Customers module first.")
        note.setStyleSheet("color:#F59E0B;font-size:11px;")
        note.setWordWrap(True)
        lay.addWidget(note)

        lay.addWidget(_field_label("Select Customer *"))
        self._customers = repo.get_all_customers() or []
        self.f_customer_combo = QComboBox()
        self.f_customer_combo.setFixedHeight(38)
        self.f_customer_combo.setEditable(True)
        self.f_customer_combo.setPlaceholderText("Search customer...")
        self.f_customer_combo.addItem("", None)
        for c in self._customers:
            self.f_customer_combo.addItem(c["name"], c)
        self.f_customer_combo.setCurrentIndex(0)
        self.f_customer_combo.setEditText("")
        self.f_customer_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.f_customer_combo.completer().setFilterMode(Qt.MatchContains)
        self.f_customer_combo.currentIndexChanged.connect(self._on_customer_selected)
        lay.addWidget(self.f_customer_combo)

        row = QHBoxLayout()
        row.setSpacing(16)
        left = QVBoxLayout()
        left.addWidget(_field_label("Contact Number"))
        self.f_contact = _input("+63 9XX XXX XXXX")
        self.f_contact.setReadOnly(True)
        self.f_contact.setStyleSheet(_readonly_input_style())
        left.addWidget(self.f_contact)

        right = QVBoxLayout()
        right.addWidget(_field_label("Email"))
        self.f_email = _input("email@example.com")
        self.f_email.setReadOnly(True)
        self.f_email.setStyleSheet(_readonly_input_style())
        right.addWidget(self.f_email)

        row.addLayout(left)
        row.addLayout(right)
        lay.addLayout(row)

        lay.addWidget(_field_label("Address"))
        self.f_address = _input("Street, Barangay, City")
        self.f_address.setReadOnly(True)
        self.f_address.setStyleSheet(_readonly_input_style())
        lay.addWidget(self.f_address)
        lay.addStretch()

        if self._edit_mode:
            name = self._booking_data.get("name", "")
            idx = self.f_customer_combo.findText(name)
            if idx >= 0:
                self.f_customer_combo.setCurrentIndex(idx)
            else:
                self.f_customer_combo.setEditText(name)

        return w

    def _on_customer_selected(self, index):
        data = self.f_customer_combo.itemData(index)
        if data and isinstance(data, dict):
            self.f_contact.setText(data.get("contact", ""))
            self.f_email.setText(data.get("email", ""))
            self.f_address.setText(data.get("address", ""))
        else:
            self.f_contact.clear()
            self.f_email.clear()
            self.f_address.clear()

    def _build_step1(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(_section_label("Event Details"))

        row1 = QHBoxLayout()
        row1.setSpacing(16)
        v1 = QVBoxLayout()
        v1.addWidget(_field_label("Occasion *"))
        self.f_occasion = _input("e.g. Wedding, Birthday")
        v1.addWidget(self.f_occasion)
        v2 = QVBoxLayout()
        v2.addWidget(_field_label("Venue *"))
        self.f_venue = _input("Event Location")
        v2.addWidget(self.f_venue)
        row1.addLayout(v1)
        row1.addLayout(v2)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        v3 = QVBoxLayout()
        v3.addWidget(_field_label("Event Date *"))
        self.f_date = QDateEdit(QDate.currentDate())
        self.f_date.setCalendarPopup(True)
        self.f_date.setFixedHeight(38)
        v3.addWidget(self.f_date)
        v4 = QVBoxLayout()
        v4.addWidget(_field_label("Time"))
        self.f_time = QTimeEdit(QTime(18, 0))
        self.f_time.setFixedHeight(38)
        v4.addWidget(self.f_time)
        v5 = QVBoxLayout()
        v5.addWidget(_field_label("No. of Pax *"))
        self.f_pax = QSpinBox()
        self.f_pax.setRange(10, 2000)
        self.f_pax.setValue(100)
        self.f_pax.setFixedHeight(38)
        v5.addWidget(self.f_pax)
        row2.addLayout(v3)
        row2.addLayout(v4)
        row2.addLayout(v5)
        lay.addLayout(row2)

        lay.addWidget(_field_label("Special Notes"))
        self.f_notes = QTextEdit()
        self.f_notes.setPlaceholderText("Dietary requirements, setup instructions, etc.")
        self.f_notes.setFixedHeight(80)
        self.f_notes.setStyleSheet(_notes_style())
        lay.addWidget(self.f_notes)
        lay.addStretch()

        if self._edit_mode:
            raw_date = self._booking_data.get("date", "")
            for fmt in ("MMM dd, yyyy", "yyyy-MM-dd"):
                d = QDate.fromString(raw_date, fmt)
                if d.isValid():
                    self.f_date.setDate(d)
                    break
            raw_time = self._booking_data.get("time", "")
            for fmt in ("hh:mm AP", "HH:mm"):
                t = QTime.fromString(raw_time, fmt)
                if t.isValid():
                    self.f_time.setTime(t)
                    break
            try:
                self.f_pax.setValue(int(self._booking_data.get("pax", 100)))
            except (ValueError, TypeError):
                pass
            self.f_notes.setPlainText(self._booking_data.get("notes", ""))
            self.f_occasion.setText(self._booking_data.get("occasion", ""))
            self.f_venue.setText(self._booking_data.get("venue", ""))

        return w

    def _build_step2(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(_section_label("Menu Selection"))

        type_row = QHBoxLayout()
        type_row.setSpacing(0)
        self.btn_pkg = QPushButton("Packages")
        self.btn_pkg.setObjectName("segmentLeft")
        self.btn_pkg.setCheckable(True)
        self.btn_pkg.setChecked(True)
        self.btn_custom = QPushButton("Custom Menu")
        self.btn_custom.setObjectName("segmentRight")
        self.btn_custom.setCheckable(True)
        type_row.addWidget(self.btn_pkg)
        type_row.addWidget(self.btn_custom)
        lay.addLayout(type_row)

        self.menu_stack = QStackedWidget()
        self.menu_stack.setStyleSheet("background: transparent;")

        pkg_w = QWidget()
        pkg_w.setStyleSheet("background: transparent;")
        pkg_lay = QVBoxLayout(pkg_w)
        pkg_lay.setSpacing(10)
        pkg_lay.setContentsMargins(0, 0, 0, 0)
        self._pkg_btns = []
        for i, (name, price, desc, _rate) in enumerate(_PACKAGES):
            card = QFrame()
            card.setStyleSheet(_package_card_style(selected=False))
            card.setCursor(Qt.PointingHandCursor)
            card_lay = QHBoxLayout(card)
            card_lay.setContentsMargins(16, 14, 16, 14)
            info = QVBoxLayout()
            info.setSpacing(2)
            n_lbl = QLabel(name)
            n_lbl.setStyleSheet(_package_name_style())
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet(_package_desc_style())
            info.addWidget(n_lbl)
            info.addWidget(d_lbl)
            card_lay.addLayout(info)
            card_lay.addStretch()
            p_lbl = QLabel(price)
            p_lbl.setStyleSheet("font-weight: 700; color: #F59E0B; font-size: 13px;")
            card_lay.addWidget(p_lbl)
            sel_btn = QPushButton("Select")
            sel_btn.setObjectName("secondaryButton")
            sel_btn.setFixedWidth(80)
            sel_btn.clicked.connect(lambda _, idx=i, c=card: self._select_package(idx, c))
            card_lay.addWidget(sel_btn)
            self._pkg_btns.append((card, sel_btn))
            pkg_lay.addWidget(card)
        pkg_lay.addStretch()
        self.menu_stack.addWidget(pkg_w)

        custom_w = QWidget()
        custom_w.setStyleSheet("background: transparent;")
        cus_lay = QVBoxLayout(custom_w)
        cus_lay.setSpacing(8)
        cus_lay.setContentsMargins(0, 0, 0, 0)
        self._custom_checks = []
        for item in menu_store.get_available_items():
            row = QHBoxLayout()
            chk = QCheckBox(item["item"])
            chk.setStyleSheet(_checkbox_item_style())
            cat = QLabel(item["category"])
            cat.setStyleSheet("color: #6B7280; font-size: 11px;")
            p = QLabel(f"₱{item['price']:,.0f}")
            p.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: 700;")
            row.addWidget(chk)
            row.addWidget(cat)
            row.addStretch()
            row.addWidget(p)
            self._custom_checks.append(chk)
            cus_lay.addLayout(row)
        cus_lay.addStretch()
        scroll_c = QScrollArea()
        scroll_c.setWidgetResizable(True)
        scroll_c.setFrameShape(QFrame.NoFrame)
        scroll_c.setStyleSheet("background: transparent;")
        scroll_c.setWidget(custom_w)
        self.menu_stack.addWidget(scroll_c)

        self.btn_pkg.clicked.connect(lambda: self.menu_stack.setCurrentIndex(0))
        self.btn_custom.clicked.connect(lambda: self.menu_stack.setCurrentIndex(1))

        lay.addWidget(self.menu_stack, 1)
        self._selected_pkg = 0
        return w

    def _select_package(self, idx, clicked_card):
        self._selected_pkg = idx
        for i, (card, btn) in enumerate(self._pkg_btns):
            if i == idx:
                card.setStyleSheet(_package_card_style(selected=True))
                btn.setObjectName("primaryButton")
                btn.setText("Selected")
            else:
                card.setStyleSheet(_package_card_style(selected=False))
                btn.setObjectName("secondaryButton")
                btn.setText("Select")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _build_step3(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(_section_label("Payment Details"))

        row = QHBoxLayout()
        row.setSpacing(16)
        v1 = QVBoxLayout()
        v1.addWidget(_field_label("Mode of Payment"))
        self.f_payment_mode = QComboBox()
        self.f_payment_mode.addItems(["Cash", "Bank Transfer", "GCash", "PayMaya"])
        self.f_payment_mode.setFixedHeight(38)
        v1.addWidget(self.f_payment_mode)
        v2 = QVBoxLayout()
        v2.addWidget(_field_label("Amount Paid"))
        self.f_amount_paid = _input("₱ 0.00")
        v2.addWidget(self.f_amount_paid)
        row.addLayout(v1)
        row.addLayout(v2)
        lay.addLayout(row)

        self._cost_box = QFrame()
        self._cost_box.setObjectName("costBox")
        cb_lay = QVBoxLayout(self._cost_box)
        cb_lay.setSpacing(8)

        cb_title = QLabel("COST BREAKDOWN")
        cb_title.setStyleSheet(_cost_breakdown_style())
        cb_lay.addWidget(cb_title)

        self._lbl_base    = QLabel()
        self._lbl_base.setStyleSheet(_cost_base_style())
        self._lbl_total   = QLabel()
        self._lbl_total.setStyleSheet(_cost_total_style())
        self._lbl_deposit = QLabel()
        self._lbl_deposit.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: 700;")

        cb_lay.addWidget(self._lbl_base)
        cb_lay.addWidget(self._lbl_total)
        cb_lay.addWidget(self._lbl_deposit)
        lay.addWidget(self._cost_box)

        self.f_pax.valueChanged.connect(self._update_cost)
        self._update_cost()

        lay.addStretch()
        return w

    def _update_cost(self):
        pax = self.f_pax.value() if hasattr(self, "f_pax") else 100
        pkg_idx = getattr(self, "_selected_pkg", 0)
        rate = _PACKAGES[pkg_idx][3]
        total = pax * rate
        deposit = total // 2
        self._lbl_base.setText(f"Base Rate: ₱{rate:,} × {pax} pax")
        self._lbl_total.setText(f"Grand Total: ₱{total:,}")
        self._lbl_deposit.setText(f"Required 50% Deposit: ₱{deposit:,}")

    def _refresh_step(self):
        self._stack.setCurrentIndex(self._step)
        self._step_indicator.set_step(self._step)
        self._btn_back.setVisible(self._step > 0)
        is_last = self._step == len(_STEPS) - 1
        if is_last:
            self._btn_next.setText("Save Booking")
            self._btn_next.setIcon(get_icon("check", color="#F9FAFB", size=QSize(14, 14)))
        else:
            self._btn_next.setText("Next  ")
            self._btn_next.setIcon(get_icon("chevron-right", color="#F9FAFB", size=QSize(14, 14)))

    def _validate_current(self):
        if self._step == 0:
            if self.f_customer_combo.currentIndex() <= 0 or self.f_customer_combo.itemData(self.f_customer_combo.currentIndex()) is None:
                self.f_customer_combo.setStyleSheet("border: 1px solid #EF4444;")
                return False
            self.f_customer_combo.setStyleSheet("")
        if self._step == 1:
            if not self.f_occasion.text().strip():
                self.f_occasion.setFocus()
                self.f_occasion.setStyleSheet("border: 1px solid #EF4444; border-radius: 8px; padding: 8px 14px;")
                return False
            self.f_occasion.setStyleSheet("")
            if not self.f_venue.text().strip():
                self.f_venue.setFocus()
                self.f_venue.setStyleSheet("border: 1px solid #EF4444; border-radius: 8px; padding: 8px 14px;")
                return False
            self.f_venue.setStyleSheet("")
        return True

    def _go_next(self):
        if not self._validate_current():
            return
        if self._step < len(_STEPS) - 1:
            self._step += 1
            if self._step == 3:
                self._update_cost()
            self._refresh_step()
        else:
            self._save()

    def _go_back(self):
        if self._step > 0:
            self._step -= 1
            self._refresh_step()

    def _save(self):
        pkg_names = [p[0] for p in _PACKAGES]
        custom_items = [chk.text() for chk in self._custom_checks if chk.isChecked()]
        menu_type = "package"
        menu_value = pkg_names[self._selected_pkg]
        if self.btn_custom.isChecked() and custom_items:
            menu_type = "custom"
            menu_value = ", ".join(custom_items)

        pax = self.f_pax.value()
        rate = _PACKAGES[self._selected_pkg][3]
        total = pax * rate

        selected_customer = self.f_customer_combo.itemData(self.f_customer_combo.currentIndex()) or {}
        data = {
            "name":         selected_customer.get("name", ""),
            "contact":      self.f_contact.text().strip(),
            "email":        self.f_email.text().strip(),
            "address":      self.f_address.text().strip(),
            "occasion":     self.f_occasion.text().strip(),
            "venue":        self.f_venue.text().strip(),
            "date":         self.f_date.date().toString("MMM dd, yyyy"),
            "time":         self.f_time.time().toString("hh:mm AP"),
            "pax":          pax,
            "notes":        self.f_notes.toPlainText().strip(),
            "menu_type":    menu_type,
            "menu_value":   menu_value,
            "payment_mode": self.f_payment_mode.currentText(),
            "amount_paid":  self.f_amount_paid.text().strip(),
            "total":        total,
            "status":       "PENDING",
        }
        self.booking_saved.emit(data)
        self.accept()
