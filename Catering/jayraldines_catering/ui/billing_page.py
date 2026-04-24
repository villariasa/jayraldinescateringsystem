from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QSize

from utils.icon_manager import btn_icon_primary, btn_icon_secondary


class BillingPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Billing")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        new_btn = QPushButton("  New Invoice")
        new_btn.setObjectName("primaryButton")
        new_btn.setIcon(btn_icon_primary("plus"))
        new_btn.setIconSize(QSize(15, 15))
        header.addWidget(new_btn)

        export_btn = QPushButton("  Export")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        header.addWidget(export_btn)

        root.addLayout(header)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["Invoice #", "Customer", "Event Date", "Amount", "Paid", "Status"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        card_layout.addWidget(table)

        root.addWidget(card)
