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
from components.color_picker_widget import ColorThemeSelector


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
    def __init__(self, steps, parent=None):
        super().__init__(parent)
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
        self.setModal(True)

        from PySide6.QtWidgets import QApplication
        self.setFixedWidth(720)
        self.setMinimumHeight(480)
        self.setMaximumHeight(680)

        self._step = 0
        self._data = {}
        self._addon_items = []
        self._pkg_selected_dishes = {}
        self._occasions = repo.get_all_occasions()
        if self._edit_mode and self._booking_data:
            b_pkg_id = self._booking_data.get("package_id")
            b_dishes = self._booking_data.get("dishes") or []
            if b_pkg_id and b_dishes:
                self._pkg_selected_dishes[b_pkg_id] = [d.get("name") for d in b_dishes if d.get("name")]


        self.setStyleSheet(QApplication.instance().styleSheet() if QApplication.instance() else "")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._container = QFrame()
        self._container.setObjectName("modalCard")

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(28, 18, 28, 16)
        container_layout.setSpacing(12)

        from components.loading_overlay import LoadingOverlay
        self._overlay = LoadingOverlay(parent=self._container, text="Saving reservation & updating schedule...")

        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
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
        close_btn.setFixedSize(30, 30)
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
        self._step_widgets = [None, None, None, None]
        self._step_widgets[0] = self._build_step0()
        self._step_widgets[1] = self._build_step1()
        self._stack.addWidget(self._step_widgets[0])
        self._stack.addWidget(self._step_widgets[1])
        for _ in range(2):
            self._stack.addWidget(QWidget())



        # Responsive Scroll Area for Stacked Content (Guarantees footer is always visible on PC/small screens)
        stack_scroll = QScrollArea()
        stack_scroll.setWidgetResizable(True)
        stack_scroll.setFrameShape(QFrame.NoFrame)
        stack_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar:vertical { width: 6px; }")
        stack_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        stack_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        stack_scroll.setWidget(self._stack)
        container_layout.addWidget(stack_scroll, 1)

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

    def _ensure_step_built(self, idx: int):
        if idx < 0 or idx >= len(self._step_widgets):
            return None
        if self._step_widgets[idx] is not None:
            return self._step_widgets[idx]
        builders = [self._build_step0, self._build_step1, self._build_step2, self._build_step3]
        w = builders[idx]()
        self._step_widgets[idx] = w
        old = self._stack.widget(idx)
        self._stack.removeWidget(old)
        self._stack.insertWidget(idx, w)
        if old:
            old.deleteLater()
        return w

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240, auto_center=True)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(60, lambda: self._ensure_step_built(2))
        QTimer.singleShot(150, lambda: self._ensure_step_built(3))



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
        self.f_occasion.setEditable(True)
        if self.f_occasion.lineEdit():
            self.f_occasion.lineEdit().setPlaceholderText("Select or Type Occasion...")
        self.f_occasion.setStyleSheet(_combo_style())
        self._occasions = repo.get_all_occasions()
        self.f_occasion.addItems(self._occasions)
        v1.addWidget(self.f_occasion)
        v2 = QVBoxLayout()
        v2.addWidget(_field_label("Venue (Leave blank or 'To be followed')"))
        self.f_venue = _input("Event Location / Venue")
        v2.addWidget(self.f_venue)
        row1.addLayout(v1)
        row1.addLayout(v2)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(12)

        v3 = QVBoxLayout()
        v3.setSpacing(4)
        v3.addWidget(_field_label("Event Date *"))
        self.f_date = QDateEdit(QDate.currentDate())
        self.f_date.setCalendarPopup(True)
        self.f_date.setFixedHeight(38)
        self.f_date.setMinimumWidth(115)
        v3.addWidget(self.f_date)

        v4 = QVBoxLayout()
        v4.setSpacing(4)
        v4.addWidget(_field_label("Start Time"))
        self.f_time = QTimeEdit(QTime(18, 0))
        self.f_time.setDisplayFormat("hh:mm AP")
        self.f_time.setFixedHeight(38)
        self.f_time.setMinimumWidth(105)
        v4.addWidget(self.f_time)

        v4b = QVBoxLayout()
        v4b.setSpacing(4)
        end_top = QHBoxLayout()
        end_top.setContentsMargins(0, 0, 0, 0)
        end_top.setSpacing(4)
        self.chk_end_time = QCheckBox("Set End Time")
        self.chk_end_time.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8;")
        end_top.addWidget(self.chk_end_time)
        v4b.addLayout(end_top)
        self.f_end_time = QTimeEdit(QTime(22, 0))
        self.f_end_time.setDisplayFormat("hh:mm AP")
        self.f_end_time.setFixedHeight(38)
        self.f_end_time.setMinimumWidth(105)
        self.f_end_time.setEnabled(False)
        self.chk_end_time.toggled.connect(self.f_end_time.setEnabled)
        v4b.addWidget(self.f_end_time)

        v5 = QVBoxLayout()
        v5.setSpacing(4)
        v5.addWidget(_field_label("No. of Pax *"))
        self.f_pax = QSpinBox()
        self.f_pax.setRange(10, 2000)
        self.f_pax.setValue(100)
        self.f_pax.setFixedHeight(38)
        self.f_pax.setMinimumWidth(90)
        v5.addWidget(self.f_pax)

        row2.addLayout(v3, 3)
        row2.addLayout(v4, 2)
        row2.addLayout(v4b, 2)
        row2.addLayout(v5, 2)
        lay.addLayout(row2)

        # Date Conflict / Availability Notification Banner
        self.lbl_date_warning = QLabel()
        self.lbl_date_warning.setWordWrap(True)
        self.lbl_date_warning.hide()
        lay.addWidget(self.lbl_date_warning)
        self.f_date.dateChanged.connect(self._check_date_availability)

        lay.addWidget(_field_label("Event Theme / Motif & Special Notes"))
        self.f_notes = QTextEdit()
        self.f_notes.setPlaceholderText("e.g. Purple & Gold theme, Twin Babies, Dusty Blue & Blush Pink motif, Big Venue setup...")
        self.f_notes.setFixedHeight(65)
        self.f_notes.setStyleSheet(_notes_style())
        lay.addWidget(self.f_notes)

        lay.addWidget(_field_label("🎨 Color Theme / Motif"))
        init_color = str(self._booking_data.get("color_theme") or self._booking_data.get("color") or "#2563EB") if (self._edit_mode and self._booking_data) else "#2563EB"
        self.f_color_picker = ColorThemeSelector(initial_color=init_color)
        lay.addWidget(self.f_color_picker)
        lay.addStretch()

        if self._edit_mode:
            raw_date = str(self._booking_data.get("date") or self._booking_data.get("event_date") or "")
            for fmt in ("MMM dd, yyyy", "yyyy-MM-dd", "yyyy-MM-dd HH:mm:ss", "MM/dd/yyyy"):
                d = QDate.fromString(raw_date, fmt)
                if d.isValid():
                    self.f_date.setDate(d)
                    break
            raw_time = str(self._booking_data.get("time") or self._booking_data.get("event_time") or "")
            for fmt in ("h:mm AP", "hh:mm AP", "h:mm A", "hh:mm A", "HH:mm:ss", "HH:mm"):
                t = QTime.fromString(raw_time, fmt)
                if t.isValid():
                    self.f_time.setTime(t)
                    break
            raw_end = str(self._booking_data.get("event_end_time") or self._booking_data.get("end_time") or "")
            if raw_end:
                for fmt in ("h:mm AP", "hh:mm AP", "h:mm A", "hh:mm A", "HH:mm:ss", "HH:mm"):
                    t_end = QTime.fromString(raw_end, fmt)
                    if t_end.isValid():
                        self.f_end_time.setTime(t_end)
                        self.chk_end_time.setChecked(True)
                        break
            try:
                self.f_pax.setValue(int(self._booking_data.get("pax", 100)))
            except (ValueError, TypeError):
                pass
            notes_raw = str(self._booking_data.get("notes", "") or "")
            import re
            clean_notes = re.sub(r"\n?\[Add-ons:\s*.*?\]", "", notes_raw).strip()
            self.f_notes.setPlainText(clean_notes)

            # Robust case-insensitive occasion selection
            occasion_val = str(self._booking_data.get("occasion", "") or "").strip()
            found_idx = -1
            for i in range(self.f_occasion.count()):
                if self.f_occasion.itemText(i).strip().lower() == occasion_val.lower():
                    found_idx = i
                    break
            if found_idx >= 0:
                self.f_occasion.setCurrentIndex(found_idx)
            elif occasion_val:
                self.f_occasion.insertItem(0, occasion_val)
                self.f_occasion.setCurrentIndex(0)

            self.f_venue.setText(self._booking_data.get("venue", ""))
            if self._booking_data.get("color_theme") or self._booking_data.get("color"):
                self.f_color_picker.set_color(self._booking_data.get("color_theme") or self._booking_data.get("color") or "#2563EB")

        # Initial date conflict check
        self._check_date_availability()
        return w

    def _check_date_availability(self):
        if not hasattr(self, "lbl_date_warning") or not hasattr(self, "f_date"):
            return
        try:
            d_val = self.f_date.date().toPython()
            summary = repo.get_date_bookings_summary(d_val)
            if summary.get("count", 0) > 0:
                bk_list = summary.get("bookings", [])
                events_str = "; ".join([f"{b['occasion']} ({b['time']}, {b['pax']}p)" for b in bk_list[:3]])
                if len(bk_list) > 3:
                    events_str += f" and {len(bk_list)-3} more"
                self.lbl_date_warning.setText(
                    f"⚠️ <b>Schedule Warning:</b> {summary['count']} event(s) already booked on this date ({summary['total_pax']} total pax).<br/>"
                    f"<span style='opacity:0.9;'>Existing: {events_str}</span>"
                )
                self.lbl_date_warning.setStyleSheet(
                    "background: rgba(245, 158, 11, 0.16); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.4); "
                    "border-radius: 8px; padding: 7px 12px; font-size: 11.5px; margin-top: 4px;"
                )
                self.lbl_date_warning.show()
            else:
                self.lbl_date_warning.hide()
        except Exception:
            self.lbl_date_warning.hide()

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
        pkg_lay.setSpacing(12)
        pkg_lay.setContentsMargins(0, 0, 8, 0)
        self._pkg_btns = []
        self._pkg_dish_checks = []
        self._db_packages = repo.get_all_packages()
        if not self._db_packages:
            empty_lbl = QLabel("No packages defined yet.\nAsk the owner to add packages in the Menu section.")
            empty_lbl.setStyleSheet("color: #98A2B3; font-size: 13px; font-style: italic; padding: 20px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            pkg_lay.addWidget(empty_lbl)
        else:
            pkg_cards_lbl = QLabel("1. Choose Package Tier:")
            pkg_cards_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #E11D48; margin-top: 4px;")
            pkg_lay.addWidget(pkg_cards_lbl)

            self._pkg_cards = []
            for i, pkg in enumerate(self._db_packages):
                name = pkg["name"]
                desc = str(pkg.get("description") or "").strip()
                pkg_id = pkg.get("id")
                card = QFrame()
                card.setObjectName("packageCard")
                card.setStyleSheet(_package_card_style(selected=(i == 0)))
                card.setCursor(Qt.PointingHandCursor)
                card_lay = QHBoxLayout(card)
                card_lay.setContentsMargins(16, 12, 16, 12)
                card_lay.setSpacing(12)

                info = QVBoxLayout()
                info.setSpacing(3)
                n_lbl = QLabel(name)
                n_lbl.setStyleSheet(_package_name_style())

                display_desc = desc if desc else "Min set: 1 Set (4 dishes good for 22 person)"
                if len(display_desc) > 85:
                    display_desc = display_desc[:82].rstrip() + "..."

                d_lbl = QLabel(display_desc)
                d_lbl.setStyleSheet(_package_desc_style())
                d_lbl.setWordWrap(True)
                if desc:
                    d_lbl.setToolTip(desc)

                dish_badge = QLabel("🍽️ Click to customize menu")
                dish_badge.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8; background: rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 2px 6px;")
                card._dish_badge = dish_badge

                info.addWidget(n_lbl)
                info.addWidget(d_lbl)
                info.addWidget(dish_badge)
                card_lay.addLayout(info, 1)

                price_val = float(pkg.get("price_per_pax", 0))
                p_lbl = QLabel(f"₱{price_val:,.2f}/set")
                p_lbl.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #E11D48; margin-right: 6px;")
                card_lay.addWidget(p_lbl)

                actions_layout = QHBoxLayout()
                actions_layout.setSpacing(6)

                sel_btn = QPushButton("Selected" if i == 0 else "Select")
                sel_btn.setObjectName("primaryButton" if i == 0 else "secondaryButton")
                sel_btn.setMinimumWidth(88)
                sel_btn.setCursor(Qt.PointingHandCursor)
                sel_btn.clicked.connect(lambda _, idx=i, c=card: self._select_package(idx, c, open_popup=True))
                actions_layout.addWidget(sel_btn)

                menu_btn = QPushButton("🍽️ Dishes")
                menu_btn.setToolTip("Customize dishes for this package")
                menu_btn.setCursor(Qt.PointingHandCursor)
                menu_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(225, 29, 72, 0.12);
                        color: #E11D48;
                        border: 1px solid rgba(225, 29, 72, 0.3);
                        border-radius: 6px;
                        font-size: 11.5px;
                        font-weight: 700;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background: rgba(225, 29, 72, 0.22);
                    }
                """)
                menu_btn.clicked.connect(lambda _, idx=i, c=card: (self._select_package(idx, c, open_popup=False), self._open_package_menu_popup(idx)))
                actions_layout.addWidget(menu_btn)

                card_lay.addLayout(actions_layout)

                # Clicking card also selects and opens popup
                card.mousePressEvent = lambda e, idx=i, c=card: self._select_package(idx, c, open_popup=True)

                self._pkg_btns.append((card, sel_btn))
                self._pkg_cards.append(card)
                pkg_lay.addWidget(card)

            # ── Package Dishes & Customizer Box ───────────────────────────────
            self._pkg_dishes_box = QFrame()
            self._pkg_dishes_box.setObjectName("cardElevated")
            self._pkg_dishes_box.setStyleSheet(
                "QFrame#cardElevated { background: rgba(255, 255, 255, 0.04); border: 1.5px solid rgba(225, 29, 72, 0.35); border-radius: 12px; padding: 14px; }"
                if not _is_light() else
                "QFrame#cardElevated { background: #F8FAFC; border: 1.5px solid #F4A6B8; border-radius: 12px; padding: 14px; }"
            )
            dishes_box_lay = QVBoxLayout(self._pkg_dishes_box)
            dishes_box_lay.setContentsMargins(14, 12, 14, 12)
            dishes_box_lay.setSpacing(10)

            dh_row = QHBoxLayout()
            dh_row.setSpacing(8)
            self._pkg_dishes_title = QLabel("🍽️ Package Dishes & Menu Customizer")
            self._pkg_dishes_title.setStyleSheet("font-weight: 700; font-size: 13.5px;")
            dh_row.addWidget(self._pkg_dishes_title)
            dh_row.addStretch()

            btn_popup = QPushButton("🍽️ Open Selection Popup")
            btn_popup.setCursor(Qt.PointingHandCursor)
            btn_popup.setStyleSheet("background: #E11D48; color: white; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 6px; border: none;")
            btn_popup.clicked.connect(lambda: self._open_package_menu_popup(self._selected_pkg))
            dh_row.addWidget(btn_popup)

            btn_reset_defaults = QPushButton("✓ Defaults")
            btn_reset_defaults.setCursor(Qt.PointingHandCursor)
            btn_reset_defaults.setStyleSheet("font-size: 11px; padding: 3px 8px; border-radius: 6px;")
            btn_reset_defaults.clicked.connect(self._reset_pkg_dishes_to_default)
            dh_row.addWidget(btn_reset_defaults)

            btn_sel_all = QPushButton("Select All")
            btn_sel_all.setCursor(Qt.PointingHandCursor)
            btn_sel_all.setStyleSheet("font-size: 11px; padding: 3px 8px; border-radius: 6px;")
            btn_sel_all.clicked.connect(self._select_all_pkg_dishes)
            dh_row.addWidget(btn_sel_all)

            btn_clr_all = QPushButton("Clear")
            btn_clr_all.setCursor(Qt.PointingHandCursor)
            btn_clr_all.setStyleSheet("font-size: 11px; padding: 3px 8px; border-radius: 6px;")
            btn_clr_all.clicked.connect(self._clear_all_pkg_dishes)
            dh_row.addWidget(btn_clr_all)
            dishes_box_lay.addLayout(dh_row)

            self._pkg_dishes_count_lbl = QLabel("")
            self._pkg_dishes_count_lbl.setStyleSheet("font-size: 12px; color: #10B981; font-weight: 600;")
            dishes_box_lay.addWidget(self._pkg_dishes_count_lbl)

            self._pkg_dishes_list_w = QWidget()
            self._pkg_dishes_list_w.setStyleSheet("background: transparent;")
            self._pkg_dishes_list_lay = QVBoxLayout(self._pkg_dishes_list_w)
            self._pkg_dishes_list_lay.setContentsMargins(0, 0, 0, 0)
            self._pkg_dishes_list_lay.setSpacing(6)
            dishes_box_lay.addWidget(self._pkg_dishes_list_w)

            pkg_lay.addWidget(self._pkg_dishes_box)

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
        self.menu_stack.addWidget(custom_w)

        self.btn_pkg.clicked.connect(lambda: self._set_menu_mode(0))
        self.btn_custom.clicked.connect(lambda: self._set_menu_mode(1))

        lay.addWidget(self.menu_stack, 1)
        self._selected_pkg = 0 if self._db_packages else None
        if self._selected_pkg is not None:
            self._update_package_dishes(self._selected_pkg)
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

    def _select_package(self, idx, clicked_card=None, open_popup=True):
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

        for i, (card, btn) in enumerate(getattr(self, "_pkg_btns", [])):
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

        self._update_package_dishes(idx)
        self._update_cost()
        self._update_pkg_card_badges()

        if open_popup:
            self._open_package_menu_popup(idx)

    def _open_package_menu_popup(self, pkg_idx: int):
        db_pkgs = getattr(self, "_db_packages", [])
        if not db_pkgs or pkg_idx is None or pkg_idx >= len(db_pkgs):
            return
        pkg = db_pkgs[pkg_idx]
        pkg_id = pkg.get("id")

        if not hasattr(self, "_pkg_selected_dishes"):
            self._pkg_selected_dishes = {}

        current_selected = self._pkg_selected_dishes.get(pkg_id)
        if current_selected is None:
            if getattr(self, "_edit_mode", False) and self._booking_data and self._booking_data.get("dishes"):
                current_selected = [d.get("name") for d in self._booking_data["dishes"] if d.get("name")]
            else:
                default_items = repo.get_package_items(pkg_id)
                current_selected = [p.get("item_name") for p in default_items if p.get("item_name")]

        from components.package_menu_dialog import PackageMenuSelectionDialog
        dlg = PackageMenuSelectionDialog(pkg, selected_names=current_selected, parent=self)
        if dlg.exec() == QDialog.Accepted:
            chosen = dlg.get_selected_dishes()
            self._pkg_selected_dishes[pkg_id] = chosen

            # Sync inline checkboxes
            if hasattr(self, "_pkg_dish_checks"):
                sel_lowers = {s.strip().lower() for s in chosen}
                for chk, itm in self._pkg_dish_checks:
                    name = (itm.get("item") or itm.get("name") or itm.get("item_name", "")).strip().lower()
                    chk.blockSignals(True)
                    chk.setChecked(name in sel_lowers)
                    chk.blockSignals(False)
                cnt = sum(1 for chk, _ in self._pkg_dish_checks if chk.isChecked())
                if hasattr(self, "_pkg_dishes_count_lbl"):
                    self._pkg_dishes_count_lbl.setText(f"✓ {cnt} dishes selected for this package order")

            self._update_pkg_card_badges()

    def _update_pkg_card_badges(self):
        db_pkgs = getattr(self, "_db_packages", [])
        cards = getattr(self, "_pkg_cards", [])
        for i, card in enumerate(cards):
            if i < len(db_pkgs):
                pkg = db_pkgs[i]
                pkg_id = pkg.get("id")
                chosen = getattr(self, "_pkg_selected_dishes", {}).get(pkg_id)
                if hasattr(card, "_dish_badge"):
                    if chosen is not None and len(chosen) > 0:
                        card._dish_badge.setText(f"✓ {len(chosen)} dishes selected (Click to customize)")
                        card._dish_badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #10B981; background: rgba(16, 185, 129, 0.12); border-radius: 4px; padding: 2px 6px;")
                    else:
                        card._dish_badge.setText("🍽️ Click to customize menu")
                        card._dish_badge.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8; background: rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 2px 6px;")

    def _update_package_dishes(self, pkg_idx: int):
        if not hasattr(self, "_pkg_dishes_box") or not hasattr(self, "_pkg_dishes_list_lay"):
            return
        # Clear existing dish items
        while self._pkg_dishes_list_lay.count():
            item = self._pkg_dishes_list_lay.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.deleteLater()
                elif item.layout():
                    while item.layout().count():
                        sub = item.layout().takeAt(0)
                        if sub.widget():
                            sub.widget().deleteLater()

        self._pkg_dish_checks = []
        db_pkgs = getattr(self, "_db_packages", [])
        if not db_pkgs or pkg_idx >= len(db_pkgs):
            self._pkg_dishes_box.setVisible(False)
            return

        pkg = db_pkgs[pkg_idx]
        pkg_id = pkg["id"]
        if hasattr(self, "_pkg_dishes_title"):
            self._pkg_dishes_title.setText(f"🍽️ Dishes & Menu for: {pkg['name']}")

        default_items = repo.get_package_items(pkg_id)
        default_names = {p["item_name"].strip().lower() for p in default_items if p.get("item_name")}

        # Check existing selected dishes cache first
        if hasattr(self, "_pkg_selected_dishes") and pkg_id in self._pkg_selected_dishes:
            prechecked = {s.strip().lower() for s in self._pkg_selected_dishes[pkg_id] if s}
        elif getattr(self, "_edit_mode", False) and self._booking_data and self._booking_data.get("dishes"):
            booked_names = {d.get("name", "").strip().lower() for d in self._booking_data["dishes"] if d.get("name")}
            prechecked = booked_names
        else:
            prechecked = default_names

        # Seed cache if not yet set
        if not hasattr(self, "_pkg_selected_dishes"):
            self._pkg_selected_dishes = {}
        if pkg_id not in self._pkg_selected_dishes:
            self._pkg_selected_dishes[pkg_id] = [p["item_name"] for p in default_items if p.get("item_name")]

        all_items = repo.get_available_menu_items()
        if not all_items:
            all_items = default_items

        # Group items by category
        by_cat = {}
        for itm in all_items:
            cat = itm.get("category") or "Main Course"
            by_cat.setdefault(cat, []).append(itm)

        cat_order = ["Main Course", "Appetizer", "Soup", "Salad", "Dessert", "Drinks", "Other"]
        sorted_cats = sorted(by_cat.keys(), key=lambda c: cat_order.index(c) if c in cat_order else 99)

        for cat in sorted_cats:
            cat_hdr = QLabel(f"● {cat.upper()}")
            cat_hdr.setStyleSheet("font-size: 11px; font-weight: 700; color: #E11D48; margin-top: 8px; margin-bottom: 2px; letter-spacing: 0.5px;")
            self._pkg_dishes_list_lay.addWidget(cat_hdr)

            for item in by_cat[cat]:
                i_name = item.get("item") or item.get("name") or item.get("item_name", "")
                if not i_name:
                    continue
                row = QHBoxLayout()
                row.setContentsMargins(6, 2, 6, 2)
                row.setSpacing(10)

                chk = QCheckBox(i_name)
                chk.setStyleSheet(_checkbox_item_style())
                if i_name.strip().lower() in prechecked:
                    chk.setChecked(True)

                chk.toggled.connect(self._on_pkg_dish_toggled)

                is_default_badge = QLabel("Package Default" if i_name.strip().lower() in default_names else "")
                is_default_badge.setStyleSheet("font-size: 10px; font-weight: 600; color: #10B981; background: rgba(16, 185, 129, 0.1); border-radius: 4px; padding: 1px 6px;")
                if not is_default_badge.text():
                    is_default_badge.hide()

                row.addWidget(chk)
                row.addWidget(is_default_badge)
                row.addStretch()

                self._pkg_dish_checks.append((chk, item))
                self._pkg_dishes_list_lay.addLayout(row)

        self._pkg_dishes_box.setVisible(True)
        self._on_pkg_dish_toggled()
        self._update_pkg_card_badges()

    def _on_pkg_dish_toggled(self):
        cnt = sum(1 for chk, _ in getattr(self, "_pkg_dish_checks", []) if chk.isChecked())
        if hasattr(self, "_pkg_dishes_count_lbl"):
            self._pkg_dishes_count_lbl.setText(f"✓ {cnt} dishes selected for this package order")
        pkg_idx = getattr(self, "_selected_pkg", 0)
        db_pkgs = getattr(self, "_db_packages", [])
        if db_pkgs and pkg_idx is not None and pkg_idx < len(db_pkgs):
            pkg_id = db_pkgs[pkg_idx]["id"]
            if not hasattr(self, "_pkg_selected_dishes"):
                self._pkg_selected_dishes = {}
            self._pkg_selected_dishes[pkg_id] = [
                itm.get("item") or itm.get("name") or itm.get("item_name", "")
                for chk, itm in getattr(self, "_pkg_dish_checks", []) if chk.isChecked()
            ]
            self._update_pkg_card_badges()

    def _reset_pkg_dishes_to_default(self):
        pkg_idx = getattr(self, "_selected_pkg", 0)
        db_pkgs = getattr(self, "_db_packages", [])
        if not db_pkgs or pkg_idx >= len(db_pkgs):
            return
        pkg_id = db_pkgs[pkg_idx]["id"]
        default_items = repo.get_package_items(pkg_id)
        default_names = {p["item_name"].strip().lower() for p in default_items if p.get("item_name")}
        for chk, itm in getattr(self, "_pkg_dish_checks", []):
            name = (itm.get("item") or itm.get("name") or itm.get("item_name", "")).strip().lower()
            chk.setChecked(name in default_names)
        if not hasattr(self, "_pkg_selected_dishes"):
            self._pkg_selected_dishes = {}
        self._pkg_selected_dishes[pkg_id] = [p["item_name"] for p in default_items if p.get("item_name")]
        self._on_pkg_dish_toggled()

    def _select_all_pkg_dishes(self):
        for chk, _ in getattr(self, "_pkg_dish_checks", []):
            chk.setChecked(True)
        self._on_pkg_dish_toggled()

    def _clear_all_pkg_dishes(self):
        for chk, _ in getattr(self, "_pkg_dish_checks", []):
            chk.setChecked(False)
        self._on_pkg_dish_toggled()

    def _build_step3(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
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
        addon_title.setStyleSheet("font-weight: 700; font-size: 13.5px;")
        addon_head.addWidget(addon_title)
        addon_head.addStretch()

        btn_add_addon = QPushButton("  + Add Custom Add-on / Fee")
        btn_add_addon.setIcon(get_icon("plus", color="#FFFFFF", size=QSize(14, 14)))
        btn_add_addon.setIconSize(QSize(14, 14))
        btn_add_addon.setCursor(Qt.PointingHandCursor)
        btn_add_addon.setFixedHeight(34)
        btn_add_addon.setMinimumWidth(210)
        btn_add_addon.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                font-weight: 700;
                background-color: #2563EB;
                color: #FFFFFF;
                border: 1px solid #3B82F6;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
                border-color: #60A5FA;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
        """)
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
        cb_lay.setSpacing(8)
        cb_lay.setContentsMargins(16, 14, 16, 14)

        cb_title = QLabel("COST BREAKDOWN")
        cb_title.setStyleSheet(_cost_breakdown_style())
        cb_lay.addWidget(cb_title)

        self._lbl_base      = QLabel()
        self._lbl_base.setStyleSheet(_cost_base_style())
        cb_lay.addWidget(self._lbl_base)

        # Itemized Add-ons breakdown card
        self._addon_breakdown_box = QFrame()
        self._addon_breakdown_box.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)
        self._addon_breakdown_lay = QVBoxLayout(self._addon_breakdown_box)
        self._addon_breakdown_lay.setContentsMargins(6, 6, 6, 6)
        self._addon_breakdown_lay.setSpacing(5)
        cb_lay.addWidget(self._addon_breakdown_box)
        self._addon_breakdown_box.setVisible(False)

        self._lbl_addons    = QLabel()
        self._lbl_addons.setStyleSheet("font-size: 13px; font-weight: 700; color: #F59E0B;")
        cb_lay.addWidget(self._lbl_addons)

        self._lbl_total     = QLabel()
        self._lbl_total.setStyleSheet("font-size: 16px; font-weight: 800; color: #38BDF8; padding-top: 4px;")
        cb_lay.addWidget(self._lbl_total)

        self._lbl_deposit   = QLabel()
        self._lbl_deposit.setStyleSheet(_price_style(13))
        cb_lay.addWidget(self._lbl_deposit)

        note = QLabel("Payments are recorded in the Billing module after booking is created.")
        note.setWordWrap(True)
        note.setStyleSheet(_muted_style(12) + " padding-top: 4px;")
        cb_lay.addWidget(note)

        lay.addWidget(self._cost_box)

        # Pre-populate existing add-ons if in edit mode
        if self._edit_mode and self._booking_data:
            notes_str = str(self._booking_data.get("notes") or "")
            if "[Add-ons:" in notes_str:
                import re
                m = re.search(r"\[Add-ons:\s*(.*?)\]", notes_str, re.DOTALL)
                if m:
                    addon_body = m.group(1)
                    pattern = r"([^,(]+)\s*\(([+-]?)\s*₱?([\d,]+(?:\.\d+)?)\)"
                    for match in re.finditer(pattern, addon_body):
                        desc = match.group(1).strip()
                        sign = match.group(2)
                        amt_str = match.group(3).replace(",", "")
                        try:
                            val = float(amt_str)
                            if sign == "-":
                                val = -val
                            self._add_addon_row(desc, val)
                        except ValueError:
                            pass

        self.f_pax.valueChanged.connect(self._sync_pay_pax)
        self._update_cost()

        lay.addStretch()
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

        # Sum custom add-ons & collect items for itemized breakdown
        addons_total = 0.0
        addon_rows_data = []
        for _, n_edit, a_edit in getattr(self, "_addon_items", []):
            name_txt = n_edit.text().strip()
            amt_txt = a_edit.text().strip().replace(",", "")
            try:
                amt_val = float(amt_txt) if amt_txt else 0.0
            except ValueError:
                amt_val = 0.0
            if name_txt or amt_val != 0.0:
                addons_total += amt_val
                addon_rows_data.append((name_txt or "Custom Add-on", amt_val))

        # Clear existing breakdown item widgets
        if hasattr(self, "_addon_breakdown_lay"):
            while self._addon_breakdown_lay.count():
                child = self._addon_breakdown_lay.takeAt(0)
                if child:
                    if child.widget():
                        child.widget().deleteLater()
                    elif child.layout():
                        while child.layout().count():
                            sub = child.layout().takeAt(0)
                            if sub.widget():
                                sub.widget().deleteLater()

            if addon_rows_data:
                lbl_hdr = QLabel("<b>➕ Itemized Add-ons & Adjustments:</b>")
                lbl_hdr.setStyleSheet("font-size: 12px; color: #F59E0B; margin-bottom: 2px;")
                self._addon_breakdown_lay.addWidget(lbl_hdr)

                for desc, amt in addon_rows_data:
                    row_h = QHBoxLayout()
                    row_h.setContentsMargins(4, 2, 4, 2)
                    sign = "+" if amt >= 0 else "-"
                    lbl_desc = QLabel(f"• {desc}")
                    lbl_desc.setStyleSheet("font-size: 12.5px; color: #FFFFFF; font-weight: 600;")
                    lbl_val = QLabel(f"{sign}₱{abs(amt):,.2f}")
                    lbl_val.setStyleSheet("font-size: 13px; font-weight: 800; color: #F59E0B;" if amt >= 0 else "font-size: 13px; font-weight: 800; color: #10B981;")
                    row_h.addWidget(lbl_desc, 1)
                    row_h.addWidget(lbl_val)
                    self._addon_breakdown_lay.addLayout(row_h)

                self._addon_breakdown_box.setVisible(True)
            else:
                self._addon_breakdown_box.setVisible(False)

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
            self._lbl_addons.setText(f"Custom Add-ons Total: {sign} ₱{abs(addons_total):,.2f}")
            self._lbl_addons.setVisible(True)
        else:
            self._lbl_addons.setVisible(False)

        self._lbl_total.setText(f"Grand Total: ₱{grand_total:,.2f}")
        if allow_zero:
            self._lbl_deposit.setText("No downpayment required.")
        else:
            self._lbl_deposit.setText(f"Required {pct:.0f}% Downpayment: ₱{deposit:,.2f}")

    def _refresh_step(self, direction=0):
        self._ensure_step_built(self._step)
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
                # Do NOT auto-copy customer home address into venue — venue is event location!
        if self._step == 1:
            if not self.f_occasion.currentText().strip():
                self.f_occasion.setFocus()
                self.f_occasion.setStyleSheet("border: 1px solid #EF4444; border-radius: 8px;")
                return False
            self.f_occasion.setStyleSheet(_combo_style())
            # Venue is optional / TBA: if left blank, automatically set to 'To be followed'
            if hasattr(self, "f_venue") and not self.f_venue.text().strip():
                self.f_venue.setText("To be followed")
            if hasattr(self, "f_venue"):
                self.f_venue.setStyleSheet("")
        return True

    def _go_next(self):
        if not self._validate_current():
            return
        if self._step < len(_STEPS) - 1:
            self._step += 1
            if self._step == 3:
                # Recalculate package total based on current step 3 selection if not manually overridden
                pax = self.f_pax.value()
                if self.btn_custom.isChecked():
                    rate = sum(float(item.get("price", 0)) for chk, item in getattr(self, "_custom_checks", []) if chk.isChecked())
                else:
                    pkg_idx = getattr(self, "_selected_pkg", None)
                    db_pkgs = getattr(self, "_db_packages", [])
                    rate = float(db_pkgs[pkg_idx]["price_per_pax"]) if (pkg_idx is not None and db_pkgs and pkg_idx < len(db_pkgs)) else 0.0
                if hasattr(self, "f_pay_package_total"):
                    self.f_pay_package_total.setValue(pax * rate)
                self._update_cost()
            self._refresh_step(direction=1)
        else:
            self._save()

    def _go_back(self):
        if self._step > 0:
            self._step -= 1
            self._refresh_step(direction=-1)

    def _save(self):
        venue_val = self.f_venue.text().strip() if hasattr(self, "f_venue") else ""
        if not venue_val or venue_val.lower() in ("tbd", "tba", "client venue"):
            venue_val = "To be followed"

        self._overlay.show_overlay("Saving reservation & updating schedule...")
        self._btn_next.setText("  Saving...")
        self._btn_next.setEnabled(False)
        self._btn_back.setEnabled(False)
        QApplication.processEvents()

        menu_type = "package"
        db_pkgs = getattr(self, "_db_packages", [])
        pkg_idx = getattr(self, "_selected_pkg", None)
        selected_dishes = []
        package_id = None

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
            selected_dishes = [it for it in selected_items if it]
        else:
            menu_type = "package"
            if db_pkgs and pkg_idx is not None and pkg_idx < len(db_pkgs):
                pkg_obj = db_pkgs[pkg_idx]
                menu_value = pkg_obj["name"]
                rate = float(pkg_obj["price_per_pax"])
                package_id = pkg_obj.get("id")
            else:
                menu_value = "Standard Package"
                rate = 0.0

            if package_id and package_id in getattr(self, "_pkg_selected_dishes", {}):
                selected_dishes = self._pkg_selected_dishes[package_id]
            else:
                selected_dishes = [
                    dish.get("item") or dish.get("name") or dish.get("item_name", "")
                    for chk, dish in getattr(self, "_pkg_dish_checks", [])
                    if chk.isChecked() and (dish.get("item") or dish.get("name") or dish.get("item_name"))
                ]
            if not selected_dishes and package_id:
                default_items = repo.get_package_items(package_id)
                selected_dishes = [p["item_name"] for p in default_items if p.get("item_name")]

        pax = self.f_pay_pax.value() if hasattr(self, "f_pay_pax") else self.f_pax.value()
        
        # Collect custom add-ons and calculate total add-on amount
        addon_summary_list = []
        addons_total = 0.0
        for chk, spin, cat, name, price in getattr(self, "_extra_addon_rows", []):
            if chk.isChecked():
                qty = spin.value()
                amt = price * qty
                addons_total += amt
                qty_str = f" x{qty}" if qty > 1 else ""
                addon_summary_list.append(f"{name}{qty_str} (₱{amt:,.0f})")

        # Package base total
        if hasattr(self, "f_pay_package_total") and self.f_pay_package_total.value() > 0:
            base_total = self.f_pay_package_total.value()
        else:
            base_total = float(pax * rate)

        grand_total = max(0.0, base_total + addons_total)
        total = grand_total

        notes_text = self.f_notes.toPlainText().strip()
        if addon_summary_list:
            addons_str = "Add-ons: " + ", ".join(addon_summary_list)
            notes_text = f"{notes_text}\n[{addons_str}]".strip() if notes_text else addons_str

        selected_customer = self.f_customer_search.get_selection() or {}
        orig_status = self._booking_data.get("status") if self._booking_data else "PENDING"
        orig_paid = float(self._booking_data.get("amount_paid") or 0.0) if self._booking_data else 0.0
        recorded_down = orig_paid if orig_paid > 0 else (getattr(self, "_last_deposit", 0.0) if hasattr(self, "_last_deposit") else 0.0)

        end_time_val = self.f_end_time.time().toString("hh:mm AP") if (hasattr(self, "chk_end_time") and self.chk_end_time.isChecked()) else ""

        data = {
            "db_id":           self._booking_data.get("db_id") if self._booking_data else None,
            "name":            selected_customer.get("name", ""),
            "contact":         self.f_contact.text().strip(),
            "email":           self.f_email.text().strip(),
            "address":         self.f_address.text().strip(),
            "occasion":        self.f_occasion.currentText().strip(),
            "venue":           venue_val,
            "date":            self.f_date.date().toString("MMM dd, yyyy"),
            "time":            self.f_time.time().toString("hh:mm AP"),
            "event_time":      self.f_time.time().toString("hh:mm AP"),
            "end_time":        end_time_val,
            "event_end_time":  end_time_val,
            "pax":             pax,
            "notes":           notes_text,
            "menu_type":       menu_type,
            "menu_value":      menu_value,
            "package_id":      package_id,
            "selected_dishes": selected_dishes,
            "total":           total,
            "amount_paid":     recorded_down,
            "down_payment":    recorded_down,
            "color_theme":     self.f_color_picker.get_color() if hasattr(self, "f_color_picker") else "#2563EB",
            "color":           self.f_color_picker.get_color() if hasattr(self, "f_color_picker") else "#2563EB",
            "status":          orig_status or "PENDING",
        }
        self.booking_saved.emit(data)
        self.accept()
