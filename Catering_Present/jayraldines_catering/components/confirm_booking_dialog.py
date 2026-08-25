"""
ConfirmBookingDialog — Booking Approval modal with flexible payment options:
- No payment today (confirm booking only)
- Custom payment / Down payment (enter exact amount or use 25%/50% preset buttons)
- Mark as Fully Paid (pays remaining balance)
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QCheckBox, QComboBox, QLineEdit, QRadioButton, QButtonGroup,
    QDoubleSpinBox, QWidget
)
from PySide6.QtCore import Qt, QSize
from utils.icons import get_icon, btn_icon_primary, btn_icon_secondary
from utils.theme import ThemeManager
from utils.accent import AccentManager
from utils.animations import animate_dialog_open, create_soft_shadow
from components.color_picker_widget import ColorThemeSelector


def _parse_amount(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("₱", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


class ConfirmBookingDialog(QDialog):
    def __init__(self, booking_info: dict, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(540)
        self.setModal(True)

        self._booking = booking_info
        self._tot_val = _parse_amount(self._booking.get("total") or self._booking.get("total_amount") or 0.0)
        self._paid_val = _parse_amount(self._booking.get("amount_paid") or self._booking.get("down_payment") or 0.0)
        self._rem_val = max(0.0, self._tot_val - self._paid_val)

        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("modalCard")
        create_soft_shadow(container, radius=32, y_offset=8, opacity=45)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(24, 24, 24, 20)
        inner.setSpacing(14)

        # Header Row
        head_row = QHBoxLayout()
        icon_lbl = QLabel("✅")
        icon_lbl.setStyleSheet("font-size: 24px;")
        head_row.addWidget(icon_lbl)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        title = QLabel("Confirm & Approve Booking")
        title.setObjectName("h2")
        sub = QLabel(f"Ref: {self._booking.get('id', '')}  |  Customer: {self._booking.get('name', '')}")
        sub.setObjectName("subtitle")
        v_head.addWidget(title)
        v_head.addWidget(sub)
        head_row.addLayout(v_head, 1)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#98A2B3", size=QSize(14, 14)))
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        head_row.addWidget(close_btn, alignment=Qt.AlignTop)
        inner.addLayout(head_row)

        div = QFrame()
        div.setObjectName("divider")
        inner.addWidget(div)

        # Summary Box (Total, Paid, Remaining Balance)
        summary_box = QFrame()
        summary_box.setObjectName("cardElevated")
        s_lay = QVBoxLayout(summary_box)
        s_lay.setContentsMargins(16, 12, 16, 12)
        s_lay.setSpacing(6)

        lbl_date = QLabel(f"📅 Event Date: <b>{self._booking.get('date', '')}</b> ({self._booking.get('pax', '')} pax)")
        lbl_date.setStyleSheet("font-size: 12px;")
        s_lay.addWidget(lbl_date)

        r_amounts = QHBoxLayout()
        lbl_tot = QLabel(f"Total: <b>₱ {self._tot_val:,.2f}</b>")
        lbl_tot.setStyleSheet("font-size: 12px; color: #64748B;")

        lbl_paid = QLabel(f"Already Paid: <b>₱ {self._paid_val:,.2f}</b>")
        lbl_paid.setStyleSheet("font-size: 12px; color: #16A34A;")

        lbl_rem = QLabel(f"Balance Due: <b>₱ {self._rem_val:,.2f}</b>")
        lbl_rem.setStyleSheet(f"font-size: 13px; color: {AccentManager().current}; font-weight: 800;")

        r_amounts.addWidget(lbl_tot)
        r_amounts.addWidget(lbl_paid)
        r_amounts.addWidget(lbl_rem)
        s_lay.addLayout(r_amounts)

        # Show add-on breakdown if present in notes
        notes_txt = str(self._booking.get("notes") or "")
        if "[Add-ons:" in notes_txt:
            import re
            m = re.search(r"\[Add-ons:\s*(.*?)\]", notes_txt, re.DOTALL)
            if m:
                addons_str = m.group(1).strip()
                lbl_addons_bk = QLabel(f"➕ <b>Add-ons & Adjustments:</b> {addons_str}")
                lbl_addons_bk.setWordWrap(True)
                lbl_addons_bk.setStyleSheet("font-size: 11.5px; color: #D97706; background: rgba(245, 158, 11, 0.08); border-radius: 4px; padding: 4px 6px; margin-top: 2px;")
                s_lay.addWidget(lbl_addons_bk)

        inner.addWidget(summary_box)

        # Mode Selector (Radio Group)
        lbl_select = QLabel("Payment Action on Approval:")
        lbl_select.setStyleSheet("font-weight: 700; font-size: 13px;")
        inner.addWidget(lbl_select)

        self.btn_group = QButtonGroup(self)

        self.rb_none = QRadioButton(" No payment received today (keep balance as ₱%s)" % f"{self._rem_val:,.2f}")
        self.rb_none.setChecked(True)
        self.rb_none.setStyleSheet("font-weight: 600; font-size: 12.5px;")

        self.rb_custom = QRadioButton(" Record Down Payment / Custom Amount")
        self.rb_custom.setStyleSheet("font-weight: 600; font-size: 12.5px; color: #2563EB;")

        self.rb_full = QRadioButton(" Mark as FULLY PAID (receive full balance ₱%s)" % f"{self._rem_val:,.2f}")
        self.rb_full.setStyleSheet("font-weight: 700; font-size: 12.5px; color: #16A34A;")

        self.btn_group.addButton(self.rb_none, 0)
        self.btn_group.addButton(self.rb_custom, 1)
        self.btn_group.addButton(self.rb_full, 2)

        inner.addWidget(self.rb_none)
        inner.addWidget(self.rb_custom)
        inner.addWidget(self.rb_full)

        # Payment options frame
        self._pay_options_frame = QFrame()
        p_lay = QVBoxLayout(self._pay_options_frame)
        p_lay.setContentsMargins(12, 10, 12, 10)
        p_lay.setSpacing(10)
        self._pay_options_frame.setStyleSheet("""
            QFrame {
                background: rgba(30, 41, 59, 0.04);
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 8px;
            }
        """)

        # Amount Input Row + Preset Buttons
        row_amt = QHBoxLayout()
        lbl_amt = QLabel("Payment Amount (₱):")
        lbl_amt.setStyleSheet("font-weight: 700; font-size: 12px;")

        self.num_amount = QDoubleSpinBox()
        self.num_amount.setRange(0.0, max(1.0, self._tot_val * 2))
        self.num_amount.setDecimals(2)
        self.num_amount.setSingleStep(1000.0)
        self.num_amount.setValue(0.0)
        self.num_amount.setFixedHeight(34)
        self.num_amount.setStyleSheet("QDoubleSpinBox { font-size: 14px; font-weight: 700; color: #0F172A; background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 2px 8px; }")

        row_amt.addWidget(lbl_amt)
        row_amt.addWidget(self.num_amount, 1)

        # Quick Preset Buttons
        btn_preset_25 = QPushButton("25% DP")
        btn_preset_25.setCursor(Qt.PointingHandCursor)
        btn_preset_25.setFixedHeight(32)
        btn_preset_25.setStyleSheet("QPushButton { font-size: 11px; font-weight: 700; background: #E2E8F0; color: #1E293B; border-radius: 6px; padding: 0 8px; } QPushButton:hover { background: #CBD5E1; }")
        btn_preset_25.clicked.connect(lambda: self._set_preset(0.25))

        btn_preset_50 = QPushButton("50% DP")
        btn_preset_50.setCursor(Qt.PointingHandCursor)
        btn_preset_50.setFixedHeight(32)
        btn_preset_50.setStyleSheet("QPushButton { font-size: 11px; font-weight: 700; background: #E2E8F0; color: #1E293B; border-radius: 6px; padding: 0 8px; } QPushButton:hover { background: #CBD5E1; }")
        btn_preset_50.clicked.connect(lambda: self._set_preset(0.50))

        btn_preset_full = QPushButton("Full Balance")
        btn_preset_full.setCursor(Qt.PointingHandCursor)
        btn_preset_full.setFixedHeight(32)
        btn_preset_full.setStyleSheet("QPushButton { font-size: 11px; font-weight: 700; background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; border-radius: 6px; padding: 0 8px; } QPushButton:hover { background: #BBF7D0; }")
        btn_preset_full.clicked.connect(lambda: self._set_preset(1.0))

        row_amt.addWidget(btn_preset_25)
        row_amt.addWidget(btn_preset_50)
        row_amt.addWidget(btn_preset_full)
        p_lay.addLayout(row_amt)

        # Payment Method Selector
        row_method = QHBoxLayout()
        lbl_method = QLabel("Payment Method:")
        lbl_method.setStyleSheet("font-weight: 600; font-size: 12px;")
        self.combo_method = QComboBox()
        self.combo_method.addItems(["Cash", "GCash", "Bank Transfer", "Credit Card", "Check"])
        self.combo_method.setFixedHeight(34)
        row_method.addWidget(lbl_method)
        row_method.addWidget(self.combo_method, 1)
        p_lay.addLayout(row_method)

        # Remarks / Notes
        row_remarks = QHBoxLayout()
        lbl_remarks = QLabel("Payment Remarks:")
        lbl_remarks.setStyleSheet("font-weight: 600; font-size: 12px;")
        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("e.g. 50% down payment received upon booking confirmation...")
        self.txt_remarks.setFixedHeight(34)
        row_remarks.addWidget(lbl_remarks)
        row_remarks.addWidget(self.txt_remarks, 1)
        p_lay.addLayout(row_remarks)

        inner.addWidget(self._pay_options_frame)
        self._pay_options_frame.hide()

        # Wire Signals
        self.btn_group.idToggled.connect(self._on_mode_changed)

        # ── Color Theme Picker ───────────────────────────────────────────────
        div2 = QFrame()
        div2.setObjectName("divider")
        inner.addWidget(div2)

        lbl_theme = QLabel("🎨  Assign Event Color Theme")
        lbl_theme.setStyleSheet("font-weight: 700; font-size: 13px;")
        inner.addWidget(lbl_theme)

        initial_color = str(self._booking.get("color_theme") or self._booking.get("color") or "#2563EB")
        self._color_picker = ColorThemeSelector(initial_color=initial_color)
        inner.addWidget(self._color_picker)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_confirm = QPushButton(" Confirm & Approve Booking")
        self.btn_confirm.setObjectName("primaryButton")
        self.btn_confirm.setIcon(btn_icon_primary("check"))
        self.btn_confirm.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_confirm)

        inner.addLayout(btn_row)
        outer.addWidget(container)

    def _on_mode_changed(self, mode_id: int, checked: bool):
        if not checked:
            return
        if mode_id == 0:  # No Payment
            self._pay_options_frame.hide()
            self.num_amount.setValue(0.0)
        elif mode_id == 1:  # Custom / Down Payment
            self._pay_options_frame.show()
            self.num_amount.setReadOnly(False)
            if self.num_amount.value() <= 0:
                self.num_amount.setValue(round(self._tot_val * 0.5, 2))
        elif mode_id == 2:  # Fully Paid
            self._pay_options_frame.show()
            self.num_amount.setValue(self._rem_val)
            self.num_amount.setReadOnly(True)

    def _set_preset(self, ratio: float):
        if ratio >= 1.0:
            val = self._rem_val
        else:
            val = round(self._tot_val * ratio, 2)
        self.num_amount.setValue(val)
        if self.btn_group.checkedId() == 0:
            self.rb_custom.setChecked(True)

    def get_payment_amount(self) -> float:
        mode = self.btn_group.checkedId()
        if mode == 0:
            return 0.0
        elif mode == 2:
            return self._rem_val
        return max(0.0, float(self.num_amount.value()))

    def is_auto_pay_checked(self) -> bool:
        """Compatibility helper: returns True if fully paid option selected."""
        return self.btn_group.checkedId() == 2 or (self.get_payment_amount() >= self._rem_val and self._rem_val > 0)

    def get_payment_method(self) -> str:
        return self.combo_method.currentText()

    def get_payment_remarks(self) -> str:
        r = self.txt_remarks.text().strip()
        if r:
            return r
        mode = self.btn_group.checkedId()
        if mode == 2:
            return "Full payment received upon booking confirmation."
        amt = self.get_payment_amount()
        if amt > 0:
            return f"Payment of ₱{amt:,.2f} received upon booking confirmation."
        return "Booking confirmed."

    def get_color_theme(self) -> str:
        """Return the selected hex color theme string."""
        return self._color_picker.get_color()


class BatchConfirmBookingDialog(QDialog):
    """
    BatchConfirmBookingDialog — Batch Approval modal with flexible payment options:
    - No payment today (confirm bookings only, keep balance)
    - Record Down Payment / Fixed Amount per Booking
    - Mark all as FULLY PAID (receive full balance)
    """
    def __init__(self, pending_bookings: list, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(560)
        self.setModal(True)

        self._bookings = pending_bookings
        self._count = len(pending_bookings)

        self._tot_val = sum(_parse_amount(b.get("total") or b.get("total_amount") or 0.0) for b in self._bookings)
        self._paid_val = sum(_parse_amount(b.get("amount_paid") or b.get("down_payment") or 0.0) for b in self._bookings)
        self._rem_val = max(0.0, self._tot_val - self._paid_val)

        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("modalCard")
        create_soft_shadow(container, radius=32, y_offset=8, opacity=45)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(24, 24, 24, 20)
        inner.setSpacing(14)

        # Header Row
        head_row = QHBoxLayout()
        icon_lbl = QLabel("✅")
        icon_lbl.setStyleSheet("font-size: 24px;")
        head_row.addWidget(icon_lbl)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        title = QLabel(f"Batch Confirm Bookings ({self._count})")
        title.setObjectName("h2")
        sub = QLabel(f"Approving {self._count} pending booking(s) simultaneously")
        sub.setObjectName("subtitle")
        v_head.addWidget(title)
        v_head.addWidget(sub)
        head_row.addLayout(v_head, 1)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#98A2B3", size=QSize(14, 14)))
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        head_row.addWidget(close_btn, alignment=Qt.AlignTop)
        inner.addLayout(head_row)

        div = QFrame()
        div.setObjectName("divider")
        inner.addWidget(div)

        # Summary Box
        summary_box = QFrame()
        summary_box.setObjectName("cardElevated")
        s_lay = QVBoxLayout(summary_box)
        s_lay.setContentsMargins(16, 12, 16, 12)
        s_lay.setSpacing(6)

        lbl_count = QLabel(f"📋 Selected Bookings: <b>{self._count} orders</b>")
        lbl_count.setStyleSheet("font-size: 12px;")
        s_lay.addWidget(lbl_count)

        r_amounts = QHBoxLayout()
        lbl_tot = QLabel(f"Total Value: <b>₱ {self._tot_val:,.2f}</b>")
        lbl_tot.setStyleSheet("font-size: 12px; color: #64748B;")

        lbl_paid = QLabel(f"Already Paid: <b>₱ {self._paid_val:,.2f}</b>")
        lbl_paid.setStyleSheet("font-size: 12px; color: #16A34A;")

        lbl_rem = QLabel(f"Total Balance Due: <b>₱ {self._rem_val:,.2f}</b>")
        lbl_rem.setStyleSheet(f"font-size: 13px; color: {AccentManager().current}; font-weight: 800;")

        r_amounts.addWidget(lbl_tot)
        r_amounts.addWidget(lbl_paid)
        r_amounts.addWidget(lbl_rem)
        s_lay.addLayout(r_amounts)
        inner.addWidget(summary_box)

        # Payment Action Selector
        lbl_select = QLabel("Payment Action on Batch Approval:")
        lbl_select.setStyleSheet("font-weight: 700; font-size: 13px;")
        inner.addWidget(lbl_select)

        self.btn_group = QButtonGroup(self)

        self.rb_none = QRadioButton(f" No payment received today (confirm only — keep remaining balances)")
        self.rb_none.setChecked(True)
        self.rb_none.setStyleSheet("font-weight: 600; font-size: 12.5px;")

        self.rb_custom = QRadioButton(" Record Down Payment / Fixed Amount per Booking")
        self.rb_custom.setStyleSheet("font-weight: 600; font-size: 12.5px; color: #2563EB;")

        self.rb_full = QRadioButton(f" Mark ALL as FULLY PAID (receive full balance ₱{self._rem_val:,.2f})")
        self.rb_full.setStyleSheet("font-weight: 700; font-size: 12.5px; color: #16A34A;")

        self.btn_group.addButton(self.rb_none, 0)
        self.btn_group.addButton(self.rb_custom, 1)
        self.btn_group.addButton(self.rb_full, 2)

        inner.addWidget(self.rb_none)
        inner.addWidget(self.rb_custom)
        inner.addWidget(self.rb_full)

        # Payment Options Frame (Amount, Method, Remarks)
        self._pay_options_frame = QFrame()
        p_lay = QVBoxLayout(self._pay_options_frame)
        p_lay.setContentsMargins(12, 10, 12, 10)
        p_lay.setSpacing(10)
        self._pay_options_frame.setStyleSheet("""
            QFrame {
                background: rgba(30, 41, 59, 0.04);
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 8px;
            }
        """)

        # Amount Input Row + Preset Buttons
        self.row_amt_widget = QWidget()
        row_amt = QHBoxLayout(self.row_amt_widget)
        row_amt.setContentsMargins(0, 0, 0, 0)
        lbl_amt = QLabel("DP Amount per Booking (₱):")
        lbl_amt.setStyleSheet("font-weight: 700; font-size: 12px;")

        self.num_amount = QDoubleSpinBox()
        self.num_amount.setRange(0.0, 1000000.0)
        self.num_amount.setDecimals(2)
        self.num_amount.setSingleStep(1000.0)
        self.num_amount.setValue(5000.0)
        self.num_amount.setFixedHeight(34)
        self.num_amount.setStyleSheet("QDoubleSpinBox { font-size: 14px; font-weight: 700; color: #0F172A; background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 2px 8px; }")

        row_amt.addWidget(lbl_amt)
        row_amt.addWidget(self.num_amount, 1)

        btn_dp_2k = QPushButton("₱2,000 DP")
        btn_dp_2k.setCursor(Qt.PointingHandCursor)
        btn_dp_2k.setFixedHeight(32)
        btn_dp_2k.setStyleSheet("QPushButton { font-size: 11px; font-weight: 700; background: #E2E8F0; color: #1E293B; border-radius: 6px; padding: 0 8px; } QPushButton:hover { background: #CBD5E1; }")
        btn_dp_2k.clicked.connect(lambda: self.num_amount.setValue(2000.0))

        btn_dp_5k = QPushButton("₱5,000 DP")
        btn_dp_5k.setCursor(Qt.PointingHandCursor)
        btn_dp_5k.setFixedHeight(32)
        btn_dp_5k.setStyleSheet("QPushButton { font-size: 11px; font-weight: 700; background: #E2E8F0; color: #1E293B; border-radius: 6px; padding: 0 8px; } QPushButton:hover { background: #CBD5E1; }")
        btn_dp_5k.clicked.connect(lambda: self.num_amount.setValue(5000.0))

        row_amt.addWidget(btn_dp_2k)
        row_amt.addWidget(btn_dp_5k)
        p_lay.addWidget(self.row_amt_widget)

        # Payment Method Selector
        row_method = QHBoxLayout()
        lbl_method = QLabel("Payment Method:")
        lbl_method.setStyleSheet("font-weight: 600; font-size: 12px;")
        self.combo_method = QComboBox()
        self.combo_method.addItems(["Cash", "GCash", "Bank Transfer", "Credit Card", "Check"])
        self.combo_method.setFixedHeight(34)
        row_method.addWidget(lbl_method)
        row_method.addWidget(self.combo_method, 1)
        p_lay.addLayout(row_method)

        # Remarks / Notes
        row_remarks = QHBoxLayout()
        lbl_remarks = QLabel("Payment Remarks:")
        lbl_remarks.setStyleSheet("font-weight: 600; font-size: 12px;")
        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("e.g. Batch confirmation payment recorded...")
        self.txt_remarks.setFixedHeight(34)
        row_remarks.addWidget(lbl_remarks)
        row_remarks.addWidget(self.txt_remarks, 1)
        p_lay.addLayout(row_remarks)

        inner.addWidget(self._pay_options_frame)
        self._pay_options_frame.hide()

        # Wire Signals
        self.btn_group.idToggled.connect(self._on_mode_changed)

        # ── Color Theme Picker ───────────────────────────────────────────────
        div2 = QFrame()
        div2.setObjectName("divider")
        inner.addWidget(div2)

        lbl_theme = QLabel("🎨  Assign Color Theme (applied to all selected bookings)")
        lbl_theme.setStyleSheet("font-weight: 700; font-size: 13px;")
        inner.addWidget(lbl_theme)

        self._color_picker = ColorThemeSelector(initial_color="#2563EB")
        inner.addWidget(self._color_picker)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_confirm = QPushButton(f" Confirm {self._count} Booking(s)")
        self.btn_confirm.setObjectName("primaryButton")
        self.btn_confirm.setIcon(btn_icon_primary("check"))
        self.btn_confirm.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_confirm)

        inner.addLayout(btn_row)
        outer.addWidget(container)

    def _on_mode_changed(self, mode_id: int, checked: bool):
        if not checked:
            return
        if mode_id == 0:  # No Payment
            self._pay_options_frame.hide()
        elif mode_id == 1:  # Down Payment / Custom Amount
            self._pay_options_frame.show()
            self.row_amt_widget.show()
        elif mode_id == 2:  # Fully Paid
            self._pay_options_frame.show()
            self.row_amt_widget.hide()

    def get_action_mode(self) -> str:
        mode = self.btn_group.checkedId()
        if mode == 1:
            return "downpayment"
        elif mode == 2:
            return "full"
        return "none"

    def get_payment_amount_per_booking(self) -> float:
        if self.btn_group.checkedId() == 1:
            return max(0.0, float(self.num_amount.value()))
        return 0.0

    def get_payment_method(self) -> str:
        return self.combo_method.currentText()

    def get_payment_remarks(self) -> str:
        r = self.txt_remarks.text().strip()
        if r:
            return r
        mode = self.get_action_mode()
        if mode == "full":
            return "Batch full payment received upon confirmation."
        elif mode == "downpayment":
            return f"Batch down payment of ₱{self.get_payment_amount_per_booking():,.2f} recorded upon confirmation."
        return "Batch booking confirmation (Unpaid)."

    def get_color_theme(self) -> str:
        """Return the selected hex color theme string to apply to all confirmed bookings."""
        return self._color_picker.get_color()
