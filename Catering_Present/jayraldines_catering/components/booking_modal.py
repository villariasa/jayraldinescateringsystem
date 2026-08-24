from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox,
    QFrame, QWidget, QStackedWidget, QTextEdit, QCheckBox,
    QScrollArea, QSizePolicy,
)
from components.customer_search import CustomerSearchWidget
from PySide6.QtCore import Qt, QDate, QTime, QSize, Signal

from utils.icons import btn_icon_primary, btn_icon_secondary, get_icon
from utils.theme import ThemeManager
from utils.animations import animate_dialog_open, animate_slide_fade_in
import utils.menu_store as menu_store
import utils.repository as repo


def _is_light():
    return not ThemeManager().is_dark()


def _readonly_input_style():
    if _is_light():
        return "background:#F3F5F9;color:#5B6B84;border:1px solid #E4E9F1;border-radius:9px;padding:8px 14px;"
    return "background:#111827;color:#9CA3AF;border:1px solid #243244;border-radius:9px;padding:8px 14px;"


def _muted_style(size=12):
    return "color: %s; font-size: %dpx;" % ("#7A879E" if _is_light() else "#9CA3AF", size)


def _price_style(size=13):
    return "font-weight: 700; color: %s; font-size: %dpx;" % (
        "#B45309" if _is_light() else "#F59E0B", size
    )


def _package_card_style(selected=False):
    if selected:
        if _is_light():
            return ("QFrame#packageCard { background: rgba(225,29,72,0.06); border-radius: 12px; border: 2px solid #E11D48; }"
                    "QFrame#packageCard QLabel { color: #101828; }")
        return ("QFrame#packageCard { background: rgba(225,29,72,0.12); border-radius: 12px; border: 2px solid #E11D48; }"
                "QFrame#packageCard QLabel { color: #F9FAFB; }")
    if _is_light():
        return ("QFrame#packageCard { background: #FFFFFF; border-radius: 12px; border: 2px solid #E4E9F1; }"
                "QFrame#packageCard:hover { border: 2px solid #F4A6B8; background: #FFF8F9; }"
                "QFrame#packageCard QLabel { color: #101828; }")
    return ("QFrame#packageCard { background: #1F2937; border-radius: 12px; border: 2px solid #243244; }"
            "QFrame#packageCard:hover { border: 2px solid #E11D48; }"
            "QFrame#packageCard QLabel { color: #F9FAFB; }")


def _package_name_style():
    return "font-weight: 700; color: %s; font-size: 13px;" % ("#101828" if _is_light() else "#F9FAFB")


def _package_desc_style():
    return "color: %s; font-size: 12px;" % ("#5B6B84" if _is_light() else "#9CA3AF")


def _notes_style():
    if _is_light():
        return ("background: #FFFFFF; color: #101828; border: 1px solid #D8DFEA; "
                "border-radius: 9px; padding: 8px; font-size: 13px;")
    return ("background: #1F2937; color: #F9FAFB; border: 1px solid #243244; "
            "border-radius: 9px; padding: 8px; font-size: 13px;")


def _cost_breakdown_style():
    return "color: %s; font-size: 11px; font-weight: 700; letter-spacing: 1px;" % (
        "#5B6B84" if _is_light() else "#6B7280"
    )


def _cost_base_style():
    return "color: %s; font-size: 13px;" % ("#46536B" if _is_light() else "#9CA3AF")


def _cost_total_style():
    return "color: %s; font-size: 15px; font-weight: 800;" % ("#101828" if _is_light() else "#F9FAFB")


def _checkbox_item_style():
    return "color: %s; font-size: 13px;" % ("#101828" if _is_light() else "#F9FAFB")


def _combo_style():
    if _is_light():
        return (
            "QComboBox { padding: 10px 14px; border: 1px solid #D8DFEA; border-radius: 9px;"
            " background-color: #FFFFFF; color: #101828; font-size: 13px; }"
            "QComboBox:hover { border: 1px solid #B9C4D4; }"
            "QComboBox:focus { border: 1px solid #E11D48; }"
            "QComboBox::drop-down { width: 28px; border-left: none; background: transparent; }"
            "QComboBox QAbstractItemView { background-color: #FFFFFF; color: #101828;"
            " border: 1px solid #E4E9F1; border-radius: 9px; outline: none; padding: 4px;"
            " selection-background-color: rgba(225,29,72,0.08); selection-color: #D31647; }"
            "QComboBox QAbstractItemView::item { padding: 8px 12px; border-radius: 6px;"
            " color: #101828; background-color: #FFFFFF; }"
            "QComboBox QAbstractItemView::item:hover { background-color: #F3F5F9; color: #101828; }"
            "QComboBox QAbstractItemView::item:selected { background-color: rgba(225,29,72,0.08); color: #D31647; }"
        )
    return (
        "QComboBox { padding: 10px 14px; border: 1px solid #243244; border-radius: 8px;"
        " background-color: #1F2937; color: #F9FAFB; font-size: 13px; }"
        "QComboBox:focus { border: 1px solid #E11D48; }"
        "QComboBox::drop-down { width: 28px; border-left: none; background: transparent; }"
        "QComboBox QAbstractItemView { background-color: #1F2937; color: #F9FAFB;"
        " border: 1px solid #243244; border-radius: 8px; outline: none; padding: 4px;"
        " selection-background-color: rgba(225,29,72,0.15); selection-color: #E11D48; }"
        "QComboBox QAbstractItemView::item { padding: 8px 12px; border-radius: 6px;"
        " color: #F9FAFB; background-color: #1F2937; }"
        "QComboBox QAbstractItemView::item:hover { background-color: #243244; color: #F9FAFB; }"
        "QComboBox QAbstractItemView::item:selected { background-color: rgba(225,29,72,0.15); color: #E11D48; }"
    )


def _step_inactive_fg():
    return "#98A2B3" if _is_light() else "#6B7280"


def _step_line_inactive():
    return "background: %s; margin-top: 13px;" % ("#E4E9F1" if _is_light() else "#243244")


_STEPS = ["Customer", "Event", "Menu", "Payment"]



def _section_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("sectionLabel")
    return lbl


def _segment_button_style(selected=False, left=True):
    """Return stylesheet for segment buttons (Packages / Custom Menu).
    left=True for the left segment, False for the right.
    """
    radius = ("border-top-left-radius: 9px; border-bottom-left-radius: 9px;"
              " border-top-right-radius: 0px; border-bottom-right-radius: 0px;") if left else \
             ("border-top-right-radius: 9px; border-bottom-right-radius: 9px;"
              " border-top-left-radius: 0px; border-bottom-left-radius: 0px;")
    if selected:
        return ("background: #E11D48; color: #FFFFFF; border: 1px solid #E11D48;"
                " font-weight: 700; padding: 10px 16px; " + radius)
    if _is_light():
        return ("background: #FFFFFF; color: #46536B; border: 1px solid #D8DFEA;"
                " padding: 10px 16px; " + radius)
    return ("background: #111827; color: #F9FAFB; border: 1px solid #243244;"
            " padding: 10px 16px; " + radius)


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

            fg = _step_inactive_fg()
            dot = QLabel()
            dot.setFixedSize(28, 28)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet(f"border-radius: 14px; background: transparent; color: {fg}; font-weight: 700; font-size: 12px; border: 2px solid {fg};")
            dot.setText(str(i + 1))

            lbl = QLabel(step)
            lbl.setAlignment(Qt.AlignHCenter)
            lbl.setStyleSheet(f"color: {fg}; font-size: 11px; font-weight: 600;")
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
        fg = _step_inactive_fg()
        done_fg = "#16A34A" if _is_light() else "#22C55E"
        for i, (dot, lbl) in enumerate(zip(self._dots, self._labels)):
            if i < index:
                dot.setStyleSheet(f"border-radius: 14px; background: {done_fg}; color: #FFFFFF; font-weight: 700; font-size: 12px; border: 2px solid {done_fg};")
                dot.setText("✓")
                lbl.setStyleSheet(f"color: {done_fg}; font-size: 11px; font-weight: 600;")
            elif i == index:
                dot.setStyleSheet("border-radius: 14px; background: #E11D48; color: #FFFFFF; font-weight: 700; font-size: 12px; border: 2px solid #E11D48;")
                dot.setText(str(i + 1))
                lbl.setStyleSheet("color: #E11D48; font-size: 11px; font-weight: 700;")
            else:
                dot.setStyleSheet(f"border-radius: 14px; background: transparent; color: {fg}; font-weight: 700; font-size: 12px; border: 2px solid {fg};")
                dot.setText(str(i + 1))
                lbl.setStyleSheet(f"color: {fg}; font-size: 11px; font-weight: 600;")

        for i, line in enumerate(self._lines):
            line.setStyleSheet(
                f"background: {done_fg}; margin-top: 13px;" if i < index else _step_line_inactive()
            )


class BookingModal(QDialog):
    booking_saved = Signal(dict)

    def __init__(self, parent=None, booking_data=None):
        super().__init__(parent)
        self._booking_data = booking_data or {}
        self._edit_mode = bool(booking_data)
        self.setWindowTitle("Edit Booking" if self._edit_mode else "New Booking")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(700, 660)
        self.setModal(True)

        self._step = 0
        self._data = {}
        self._addon_items = []

        from PySide6.QtWidgets import QApplication
        self.setStyleSheet(QApplication.instance().styleSheet())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._container = QFrame()
        self._container.setObjectName("modalCard")

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(32, 28, 32, 24)
        container_layout.setSpacing(22)

        from components.loading_overlay import LoadingOverlay
        self._overlay = LoadingOverlay(parent=self._container, text="Saving reservation & updating schedule...")

        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self._title_lbl = QLabel("Edit Booking" if self._edit_mode else "New Booking")
        self._title_lbl.setObjectName("h2")
        title_col.addWidget(self._title_lbl)
        self._subtitle_lbl = QLabel()
        self._subtitle_lbl.setObjectName("subtitle")
        title_col.addWidget(self._subtitle_lbl)
        title_row.addLayout(title_col)
        title_row.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#98A2B3", size=QSize(16, 16)))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setFixedSize(32, 32)
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(close_btn, alignment=Qt.AlignTop)
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

        footer_div = QFrame()
        footer_div.setObjectName("divider")
        container_layout.addWidget(footer_div)

        nav_row = QHBoxLayout()
        nav_row.setSpacing(12)
        self._btn_back = QPushButton("  Back")
        self._btn_back.setObjectName("secondaryButton")
        self._btn_back.setIcon(btn_icon_secondary("chevron-left"))
        self._btn_back.setIconSize(QSize(14, 14))
        self._btn_back.setMinimumWidth(96)
        self._btn_back.setCursor(Qt.PointingHandCursor)
        self._btn_back.setVisible(False)
        self._btn_back.clicked.connect(self._go_back)

        self._step_hint = QLabel()
        self._step_hint.setObjectName("muted")

        self._btn_next = QPushButton("Next  ")
        self._btn_next.setObjectName("primaryButton")
        self._btn_next.setIcon(get_icon("chevron-right", color="#F9FAFB", size=QSize(14, 14)))
        self._btn_next.setIconSize(QSize(14, 14))
        self._btn_next.setMinimumWidth(130)
        self._btn_next.setCursor(Qt.PointingHandCursor)
        self._btn_next.clicked.connect(self._go_next)

        nav_row.addWidget(self._btn_back)
        nav_row.addStretch()
        nav_row.addWidget(self._step_hint)
        nav_row.addStretch()
        nav_row.addWidget(self._btn_next)
        container_layout.addLayout(nav_row)

        outer.addWidget(self._container)
        self._refresh_step()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=260)

    def _build_step0(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(_section_label("Customer Information"))

        note = QLabel("Select an existing customer. To add a new customer, go to the Customers module first.")
        note.setStyleSheet(
            "color:%s;font-size:11px;" % ("#B45309" if _is_light() else "#F59E0B")
        )
        note.setWordWrap(True)
        lay.addWidget(note)

        lay.addWidget(_field_label("Select Customer *"))
        self._customers = repo.get_all_customers() or []
        self.f_customer_search = CustomerSearchWidget()
        self.f_customer_search.load_customers(self._customers)
        self.f_customer_search.customer_selected.connect(self._on_customer_selected)
        self.f_customer_search.customer_cleared.connect(self._on_customer_cleared)
        lay.addWidget(self.f_customer_search)

        row = QHBoxLayout()
        row.setSpacing(16)
        left = QVBoxLayout()
        left.addWidget(_field_label("Contact Number"))
        self.f_contact = _input("+63 9XX XXX XXXX")
        left.addWidget(self.f_contact)

        right = QVBoxLayout()
        right.addWidget(_field_label("Email"))
        self.f_email = _input("email@example.com")
        right.addWidget(self.f_email)

        row.addLayout(left)
        row.addLayout(right)
        lay.addLayout(row)

        lay.addWidget(_field_label("Address"))
        self.f_address = _input("Street, Barangay, City")
        lay.addWidget(self.f_address)
        lay.addStretch()

        if self._edit_mode:
            name = self._booking_data.get("name", "")
            match = next((c for c in self._customers if c.get("name") == name), None)
            if match:
                self.f_customer_search.set_customer(match)
                self._on_customer_selected(match)

        return w

    def _on_customer_selected(self, data: dict):
        if data.get("contact"):
            self.f_contact.setText(str(data.get("contact", "")))
        if data.get("email"):
            self.f_email.setText(str(data.get("email", "")))
        if data.get("address"):
            self.f_address.setText(str(data.get("address", "")))
            if hasattr(self, "f_venue") and not self.f_venue.text().strip():
                self.f_venue.setText(str(data.get("address", "")))
        self.f_customer_search.clear_error()

    def _on_customer_cleared(self):
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
        self.f_occasion = QComboBox()
        self.f_occasion.setFixedHeight(38)
        self.f_occasion.setEditable(False)
        self.f_occasion.setStyleSheet(_combo_style())
        self._occasions = repo.get_all_occasions()
        self.f_occasion.addItems(self._occasions)
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
            occasion_val = self._booking_data.get("occasion", "")
            idx = self.f_occasion.findText(occasion_val)
            if idx >= 0:
                self.f_occasion.setCurrentIndex(idx)
            elif occasion_val:
                self.f_occasion.insertItem(0, occasion_val)
                self.f_occasion.setCurrentIndex(0)
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
        # apply initial styles for segment buttons
        self.btn_pkg.setStyleSheet(_segment_button_style(selected=True, left=True))
        self.btn_custom = QPushButton("Custom Menu")
        self.btn_custom.setObjectName("segmentRight")
        self.btn_custom.setCheckable(True)
        self.btn_custom.setStyleSheet(_segment_button_style(selected=False, left=False))
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
        self._db_packages = repo.get_all_packages()
        if not self._db_packages:
            empty_lbl = QLabel("No packages defined yet.\nAsk the owner to add packages in the Menu section.")
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setWordWrap(True)
            pkg_lay.addWidget(empty_lbl)
        else:
            for i, pkg in enumerate(self._db_packages):
                name = pkg["name"]
                desc = pkg["description"] or ""
                card = QFrame()
                card.setObjectName("packageCard")
                card.setStyleSheet(_package_card_style(selected=(i == 0)))
                card.setCursor(Qt.PointingHandCursor)
                card_lay = QHBoxLayout(card)
                card_lay.setContentsMargins(16, 14, 16, 14)
                card_lay.setSpacing(12)
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
                sel_btn = QPushButton("Selected" if i == 0 else "Select")
                sel_btn.setObjectName("primaryButton" if i == 0 else "secondaryButton")
                sel_btn.setMinimumWidth(96)
                sel_btn.clicked.connect(lambda _, idx=i, c=card: self._select_package(idx, c))
                card_lay.addWidget(sel_btn)
                self._pkg_btns.append((card, sel_btn))
                pkg_lay.addWidget(card)
        pkg_lay.addStretch()
        self.menu_stack.addWidget(pkg_w)

        custom_w = QWidget()
        custom_w.setStyleSheet("background: transparent;")
        cus_lay = QVBoxLayout(custom_w)
        cus_lay.setSpacing(10)
        cus_lay.setContentsMargins(0, 0, 0, 0)
        self._custom_checks = []

        try:
            custom_items = repo.get_available_menu_items()
            if not custom_items:
                custom_items = menu_store.get_available_items()
        except Exception as exc:
            print(f"[BookingModal] Error fetching custom menu items: {exc}")
            custom_items = menu_store.get_available_items()

        if not custom_items:
            empty_lbl = QLabel("No custom menu items found.\nAdd items in the Menu section.")
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setContentsMargins(0, 20, 0, 20)
            cus_lay.addWidget(empty_lbl)
        else:
            for item in custom_items:
                row = QHBoxLayout()
                row.setSpacing(12)
                item_name = item.get("item") or item.get("name", "")
                chk = QCheckBox(item_name)
                chk.setStyleSheet(_checkbox_item_style())
                chk.toggled.connect(lambda: self._update_cost())
                cat = QLabel(item.get("category", ""))
                cat.setStyleSheet(_muted_style(11))
                price_val = float(item.get("price", 0))
                p = QLabel(f"₱{price_val:,.0f}")
                p.setStyleSheet(_price_style(12))
                row.addWidget(chk)
                row.addWidget(cat)
                row.addStretch()
                row.addWidget(p)
                self._custom_checks.append((chk, item))
                cus_lay.addLayout(row)
        cus_lay.addStretch()
        scroll_c = QScrollArea()
        scroll_c.setWidgetResizable(True)
        scroll_c.setFrameShape(QFrame.NoFrame)
        scroll_c.setStyleSheet("background: transparent;")
        scroll_c.setWidget(custom_w)
        self.menu_stack.addWidget(scroll_c)

        self.btn_pkg.clicked.connect(lambda: self._set_menu_mode(0))
        self.btn_custom.clicked.connect(lambda: self._set_menu_mode(1))

        lay.addWidget(self.menu_stack, 1)
        self._selected_pkg = 0 if self._db_packages else None
        return w

    def _set_menu_mode(self, index):
        if self.menu_stack.currentIndex() == index:
            return
        # Update segment button checked state and styles
        if index == 0:
            self.btn_pkg.setChecked(True)
            self.btn_custom.setChecked(False)
            self.btn_pkg.setStyleSheet(_segment_button_style(selected=True, left=True))
            self.btn_custom.setStyleSheet(_segment_button_style(selected=False, left=False))
            # ensure a package is selected when switching back to packages
            if getattr(self, "_selected_pkg", None) is None and getattr(self, "_db_packages", None):
                self._selected_pkg = 0
                # update visual selection
                if getattr(self, "_pkg_btns", None):
                    for i, (card, btn) in enumerate(self._pkg_btns):
                        if i == 0:
                            card.setStyleSheet(_package_card_style(selected=True))
                            btn.setObjectName("primaryButton")
                            btn.setText("Selected")
                        else:
                            card.setStyleSheet(_package_card_style(selected=False))
                            btn.setObjectName("secondaryButton")
                            btn.setText("Select")
        else:
            self.btn_pkg.setChecked(False)
            self.btn_custom.setChecked(True)
            self.btn_pkg.setStyleSheet(_segment_button_style(selected=False, left=True))
            self.btn_custom.setStyleSheet(_segment_button_style(selected=True, left=False))
            # when switching to custom menu, clear any selected package so cost uses custom items
            self._selected_pkg = None

        direction = 1 if index > self.menu_stack.currentIndex() else -1
        self.menu_stack.setCurrentIndex(index)
        self._update_cost()
        animate_slide_fade_in(
            self.menu_stack.currentWidget(),
            offset_x=8 * direction,
            duration=180,
        )

    def _select_package(self, idx, clicked_card):
        # select a package and switch menu mode to Packages
        self._selected_pkg = idx
        # ensure we're in Packages mode
        try:
            self._set_menu_mode(0)
        except Exception:
            pass
        if hasattr(self, "_db_packages") and idx < len(self._db_packages):
            rate = float(self._db_packages[idx].get("price_per_pax", 0))
            pax_val = self.f_pay_pax.value() if hasattr(self, "f_pay_pax") else (self.f_pax.value() if hasattr(self, "f_pax") else 100)
            if hasattr(self, "f_pay_package_total"):
                self.f_pay_package_total.setValue(pax_val * rate)

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
        self._update_cost()

    def _build_step3(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        root_lay = QVBoxLayout(w)
        root_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        inner_w = QWidget()
        inner_w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner_w)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 0, 8, 0)

        lay.addWidget(_section_label("Payment Summary & Pricing Adjustments"))

        # Pax & Overall Package Total Adjustment Control Box
        pax_box = QFrame()
        pax_box.setObjectName("cardElevated")
        pax_lay = QHBoxLayout(pax_box)
        pax_lay.setContentsMargins(16, 10, 16, 10)
        pax_lay.setSpacing(14)

        lbl_pax_title = QLabel("👥 Guests (Pax):")
        lbl_pax_title.setStyleSheet("font-weight: 600; font-size: 13px;")
        
        self.f_pay_pax = QSpinBox()
        self.f_pay_pax.setRange(10, 2000)
        self.f_pay_pax.setValue(self.f_pax.value())
        self.f_pay_pax.setFixedHeight(34)
        self.f_pay_pax.setMinimumWidth(85)
        self.f_pay_pax.valueChanged.connect(self._on_pay_pax_changed)

        lbl_total_title = QLabel("📦 Overall Package Base Total (₱):")
        lbl_total_title.setStyleSheet("font-weight: 600; font-size: 13px;")

        self.f_pay_package_total = QDoubleSpinBox()
        self.f_pay_package_total.setRange(0.0, 10000000.0)
        self.f_pay_package_total.setDecimals(2)
        self.f_pay_package_total.setPrefix("₱ ")
        self.f_pay_package_total.setFixedHeight(34)
        self.f_pay_package_total.setMinimumWidth(150)
        
        pax_val = self.f_pax.value()
        initial_base_total = 0.0
        if getattr(self, "_db_packages", None) and getattr(self, "_selected_pkg", 0) is not None:
            if self._selected_pkg < len(self._db_packages):
                rate = float(self._db_packages[self._selected_pkg].get("price_per_pax", 0))
                initial_base_total = pax_val * rate
        self.f_pay_package_total.setValue(initial_base_total)
        self.f_pay_package_total.valueChanged.connect(lambda: self._update_cost())

        pax_lay.addWidget(lbl_pax_title)
        pax_lay.addWidget(self.f_pay_pax)
        pax_lay.addSpacing(10)
        pax_lay.addWidget(lbl_total_title)
        pax_lay.addWidget(self.f_pay_package_total)
        pax_lay.addStretch()
        lay.addWidget(pax_box)

        # Custom Add-ons & Adjustments Card
        addon_card = QFrame()
        addon_card.setObjectName("cardElevated")
        addon_lay = QVBoxLayout(addon_card)
        addon_lay.setContentsMargins(16, 12, 16, 12)
        addon_lay.setSpacing(10)

        addon_head = QHBoxLayout()
        addon_title = QLabel("Custom Add-ons & Price Adjustments")
        addon_title.setStyleSheet("font-weight: 700; font-size: 13px;")
        addon_head.addWidget(addon_title)
        addon_head.addStretch()

        btn_add_addon = QPushButton(" + Add Custom Add-on / Fee")
        btn_add_addon.setObjectName("secondaryButton")
        btn_add_addon.setIcon(btn_icon_secondary("plus"))
        btn_add_addon.clicked.connect(lambda: self._add_addon_row())
        addon_head.addWidget(btn_add_addon)
        addon_lay.addLayout(addon_head)

        self._addon_container = QVBoxLayout()
        self._addon_container.setSpacing(8)
        addon_lay.addLayout(self._addon_container)

        lay.addWidget(addon_card)

        # Cost Breakdown Card
        self._cost_box = QFrame()
        self._cost_box.setObjectName("costBox")
        cb_lay = QVBoxLayout(self._cost_box)
        cb_lay.setSpacing(6)

        cb_title = QLabel("COST BREAKDOWN")
        cb_title.setStyleSheet(_cost_breakdown_style())
        cb_lay.addWidget(cb_title)

        self._lbl_base      = QLabel()
        self._lbl_base.setStyleSheet(_cost_base_style())
        self._lbl_addons    = QLabel()
        self._lbl_addons.setStyleSheet(_price_style(12))
        self._lbl_total     = QLabel()
        self._lbl_total.setStyleSheet(_cost_total_style())
        self._lbl_deposit   = QLabel()
        self._lbl_deposit.setStyleSheet(_price_style(13))

        note = QLabel("Payments are recorded in the Billing module after booking is created.")
        note.setWordWrap(True)
        note.setStyleSheet(_muted_style(12) + " padding-top: 4px;")

        cb_lay.addWidget(self._lbl_base)
        cb_lay.addWidget(self._lbl_addons)
        cb_lay.addWidget(self._lbl_total)
        cb_lay.addWidget(self._lbl_deposit)
        cb_lay.addWidget(note)
        lay.addWidget(self._cost_box)

        self.f_pax.valueChanged.connect(self._sync_pay_pax)
        self._update_cost()

        lay.addStretch()
        scroll.setWidget(inner_w)
        root_lay.addWidget(scroll)
        return w

    def _on_pay_pax_changed(self, val: int):
        if hasattr(self, "f_pax") and self.f_pax.value() != val:
            self.f_pax.blockSignals(True)
            self.f_pax.setValue(val)
            self.f_pax.blockSignals(False)
            self._update_cost()

    def _sync_pay_pax(self, val: int):
        if hasattr(self, "f_pay_pax") and self.f_pay_pax.value() != val:
            self.f_pay_pax.blockSignals(True)
            self.f_pay_pax.setValue(val)
            self.f_pay_pax.blockSignals(False)

    def _add_addon_row(self, name: str = "", amount: float = 0.0):
        row_w = QWidget()
        row_lay = QHBoxLayout(row_w)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(10)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Description (e.g. Lechon Belly, Sound System, Discount)...")
        name_edit.setFixedHeight(34)
        if name:
            name_edit.setText(name)
        name_edit.textChanged.connect(lambda: self._update_cost())

        amt_edit = QLineEdit()
        amt_edit.setPlaceholderText("Amount (₱) e.g. 5000 or -1000")
        amt_edit.setFixedHeight(34)
        amt_edit.setFixedWidth(180)
        if amount != 0.0:
            amt_edit.setText(str(amount))
        amt_edit.textChanged.connect(lambda: self._update_cost())

        del_btn = QPushButton()
        del_btn.setIcon(get_icon("trash", color="#EF4444", size=QSize(14, 14)))
        del_btn.setFixedSize(34, 34)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(lambda: self._remove_addon_row(row_w))

        row_lay.addWidget(name_edit, 1)
        row_lay.addWidget(amt_edit)
        row_lay.addWidget(del_btn)

        self._addon_container.addWidget(row_w)
        self._addon_items.append((row_w, name_edit, amt_edit))
        self._update_cost()

    def _remove_addon_row(self, row_w: QWidget):
        self._addon_items = [(w, n, a) for w, n, a in self._addon_items if w != row_w]
        row_w.hide()
        row_w.deleteLater()
        self._update_cost()

    def _update_cost(self):
        pax = self.f_pay_pax.value() if hasattr(self, "f_pay_pax") else (self.f_pax.value() if hasattr(self, "f_pax") else 100)
        
        if hasattr(self, "f_pay_package_total"):
            base_total = self.f_pay_package_total.value()
        else:
            pkg_idx = getattr(self, "_selected_pkg", None)
            db_pkgs = getattr(self, "_db_packages", [])
            if getattr(self, "btn_custom", None) and self.btn_custom.isChecked():
                rate = 0.0
                for chk, item in getattr(self, "_custom_checks", []):
                    if chk.isChecked():
                        rate += float(item.get("price", 0))
                base_total = pax * rate
            else:
                if pkg_idx is not None and db_pkgs and pkg_idx < len(db_pkgs):
                    rate = float(db_pkgs[pkg_idx]["price_per_pax"])
                    base_total = pax * rate
                else:
                    base_total = 0.0

        # Sum custom add-ons
        addons_total = 0.0
        for _, n_edit, a_edit in getattr(self, "_addon_items", []):
            txt = a_edit.text().strip().replace(",", "")
            try:
                if txt:
                    addons_total += float(txt)
            except ValueError:
                pass

        grand_total = max(0.0, base_total + addons_total)
        self._last_grand_total = grand_total

        try:
            policy = repo.get_business_policy()
            pct = float(policy.get("min_downpayment_pct", 30))
            allow_zero = policy.get("allow_zero_downpayment", False)
        except Exception:
            pct = 30
            allow_zero = False
        deposit = round(grand_total * pct / 100, 2)

        rate_per_pax = (base_total / pax) if pax > 0 else 0.0
        self._lbl_base.setText(f"Base Package Total: ₱{base_total:,.2f}  (₱{rate_per_pax:,.2f}/pax for {pax} pax)")
        if addons_total != 0:
            sign = "+" if addons_total > 0 else "-"
            self._lbl_addons.setText(f"Custom Add-ons & Adjustments: {sign} ₱{abs(addons_total):,.2f}")
            self._lbl_addons.setVisible(True)
        else:
            self._lbl_addons.setVisible(False)

        self._lbl_total.setText(f"Grand Total: ₱{grand_total:,.2f}")
        if allow_zero:
            self._lbl_deposit.setText("No downpayment required.")
        else:
            self._lbl_deposit.setText(f"Required {pct:.0f}% Downpayment: ₱{deposit:,.2f}")

    def _refresh_step(self, direction=0):
        self._stack.setCurrentIndex(self._step)
        if direction:
            animate_slide_fade_in(
                self._stack.currentWidget(),
                offset_x=10 * direction,
                duration=200,
            )
        self._step_indicator.set_step(self._step)
        self._subtitle_lbl.setText(f"Step {self._step + 1} of {len(_STEPS)} — {_STEPS[self._step]}")
        self._step_hint.setText(f"{self._step + 1} / {len(_STEPS)}")
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
            sel = self.f_customer_search.get_selection()
            if not sel or not sel.get("name", "").strip():
                self.f_customer_search.set_error()
                return False
            self.f_customer_search.clear_error()
            if hasattr(self, "f_contact") and self.f_contact.text().strip():
                sel["contact"] = self.f_contact.text().strip()
            if hasattr(self, "f_email") and self.f_email.text().strip():
                sel["email"] = self.f_email.text().strip()
            if hasattr(self, "f_address") and self.f_address.text().strip():
                sel["address"] = self.f_address.text().strip()
                if hasattr(self, "f_venue") and not self.f_venue.text().strip():
                    self.f_venue.setText(self.f_address.text().strip())
        if self._step == 1:
            if not self.f_occasion.currentText().strip():
                self.f_occasion.setFocus()
                self.f_occasion.setStyleSheet("border: 1px solid #EF4444; border-radius: 8px;")
                return False
            self.f_occasion.setStyleSheet(_combo_style())
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
            self._refresh_step(direction=1)
        else:
            self._save()

    def _go_back(self):
        if self._step > 0:
            self._step -= 1
            self._refresh_step(direction=-1)

    def _save(self):
        self._overlay.show_overlay("Saving reservation & updating schedule...")
        self._btn_next.setText("  Saving...")
        self._btn_next.setEnabled(False)
        self._btn_back.setEnabled(False)
        QApplication.processEvents()

        menu_type = "package"
        db_pkgs = getattr(self, "_db_packages", [])
        pkg_idx = getattr(self, "_selected_pkg", None)

        if self.btn_custom.isChecked():
            menu_type = "custom"
            selected_items = [
                item.get("item") or item.get("name", "")
                for chk, item in getattr(self, "_custom_checks", [])
                if chk.isChecked()
            ]
            menu_value = ", ".join(selected_items) if selected_items else "Custom Menu"
            rate = sum(
                float(item.get("price", 0))
                for chk, item in getattr(self, "_custom_checks", [])
                if chk.isChecked()
            )
        else:
            menu_type = "package"
            if db_pkgs and pkg_idx is not None and pkg_idx < len(db_pkgs):
                menu_value = db_pkgs[pkg_idx]["name"]
                rate = float(db_pkgs[pkg_idx]["price_per_pax"])
            else:
                menu_value = "Standard Package"
                rate = 0.0

        pax = self.f_pay_pax.value() if hasattr(self, "f_pay_pax") else self.f_pax.value()
        total = getattr(self, "_last_grand_total", float(pax * rate))

        # Collect custom add-ons
        addon_summary_list = []
        for _, n_edit, a_edit in getattr(self, "_addon_items", []):
            name_txt = n_edit.text().strip()
            amt_txt = a_edit.text().strip().replace(",", "")
            try:
                amt_val = float(amt_txt) if amt_txt else 0.0
            except ValueError:
                amt_val = 0.0
            if name_txt or amt_val != 0.0:
                sign = "+" if amt_val >= 0 else "-"
                addon_summary_list.append(f"{name_txt or 'Custom Add-on'} ({sign}₱{abs(amt_val):,.2f})")

        notes_text = self.f_notes.toPlainText().strip()
        if addon_summary_list:
            addons_str = "Add-ons: " + ", ".join(addon_summary_list)
            notes_text = f"{notes_text}\n[{addons_str}]".strip() if notes_text else addons_str

        selected_customer = self.f_customer_search.get_selection() or {}
        orig_status = self._booking_data.get("status") if self._booking_data else "PENDING"
        orig_paid = float(self._booking_data.get("amount_paid") or 0.0) if self._booking_data else 0.0
        recorded_down = orig_paid if orig_paid > 0 else (getattr(self, "_last_deposit", 0.0) if hasattr(self, "_last_deposit") else 0.0)

        data = {
            "name":         selected_customer.get("name", ""),
            "contact":      self.f_contact.text().strip(),
            "email":        self.f_email.text().strip(),
            "address":      self.f_address.text().strip(),
            "occasion":     self.f_occasion.currentText().strip(),
            "venue":        self.f_venue.text().strip(),
            "date":         self.f_date.date().toString("MMM dd, yyyy"),
            "time":         self.f_time.time().toString("hh:mm AP"),
            "pax":          pax,
            "notes":        notes_text,
            "menu_type":    menu_type,
            "menu_value":   menu_value,
            "total":        total,
            "amount_paid":  recorded_down,
            "down_payment": recorded_down,
            "status":       orig_status or "PENDING",
        }
        self.booking_saved.emit(data)
        self.accept()
