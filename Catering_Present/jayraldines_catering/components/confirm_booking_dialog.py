"""
ConfirmBookingDialog — Booking Approval modal with auto-payment checkbox (checked by default),
payment method selector, and remarks.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QCheckBox, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, QSize
from utils.icons import get_icon, btn_icon_primary, btn_icon_secondary
from utils.theme import ThemeManager
from utils.accent import AccentManager
from utils.animations import animate_dialog_open, create_soft_shadow


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
        self.setMinimumWidth(500)
        self.setModal(True)

        self._booking = booking_info
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

        # Summary Box
        summary_box = QFrame()
        summary_box.setObjectName("cardElevated")
        s_lay = QVBoxLayout(summary_box)
        s_lay.setContentsMargins(14, 12, 14, 12)
        s_lay.setSpacing(4)

        tot_val = _parse_amount(self._booking.get("total", 0.0))
        lbl_date = QLabel(f"📅 Event Date: <b>{self._booking.get('date', '')}</b> ({self._booking.get('pax', '')} pax)")
        lbl_date.setStyleSheet("font-size: 12px;")
        lbl_tot = QLabel(f"💰 Grand Total Amount: <b>₱ {tot_val:,.2f}</b>")
        lbl_tot.setStyleSheet(f"font-size: 13px; color: {AccentManager().current}; font-weight: 700;")
        s_lay.addWidget(lbl_date)
        s_lay.addWidget(lbl_tot)
        inner.addWidget(summary_box)

        # CHECKBOX: Mark as Fully Paid (CHECKED BY DEFAULT!)
        self.chk_auto_pay = QCheckBox(" Mark booking as FULLY PAID upon confirmation")
        self.chk_auto_pay.setChecked(True) # Checked by default!
        self.chk_auto_pay.setStyleSheet(
            "QCheckBox { font-weight: 700; font-size: 13px; color: %s; padding: 4px 0; }"
            % ("#16A34A" if not ThemeManager().is_dark() else "#22C55E")
        )
        self.chk_auto_pay.toggled.connect(self._on_pay_toggled)
        inner.addWidget(self.chk_auto_pay)

        # Payment options frame
        self._pay_options_frame = QFrame()
        p_lay = QVBoxLayout(self._pay_options_frame)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(10)

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
        self.txt_remarks.setPlaceholderText("Full payment received upon booking confirmation...")
        self.txt_remarks.setFixedHeight(34)
        row_remarks.addWidget(lbl_remarks)
        row_remarks.addWidget(self.txt_remarks, 1)
        p_lay.addLayout(row_remarks)

        inner.addWidget(self._pay_options_frame)

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

    def _on_pay_toggled(self, checked: bool):
        self._pay_options_frame.setVisible(checked)

    def is_auto_pay_checked(self) -> bool:
        return self.chk_auto_pay.isChecked()

    def get_payment_method(self) -> str:
        return self.combo_method.currentText()

    def get_payment_remarks(self) -> str:
        return self.txt_remarks.text().strip() or "Full payment received upon booking confirmation."
