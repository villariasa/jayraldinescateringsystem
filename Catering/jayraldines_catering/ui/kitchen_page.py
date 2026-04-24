from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QSize

from utils.icon_manager import btn_icon_primary


class KitchenPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Kitchen")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        root.addLayout(header)

        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(16)

        for status, color in [
            ("Queued",      "#F59E0B"),
            ("In Progress", "#3B82F6"),
            ("Ready",       "#22C55E"),
        ]:
            col_frame = QFrame()
            col_frame.setObjectName("card")
            col_layout = QVBoxLayout(col_frame)
            col_layout.setContentsMargins(16, 16, 16, 16)
            col_layout.setSpacing(12)

            col_title = QLabel(status)
            col_title.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 13px;")
            col_layout.addWidget(col_title)

            divider = QFrame()
            divider.setObjectName("divider")
            col_layout.addWidget(divider)

            col_layout.addStretch()
            cols_layout.addWidget(col_frame)

        root.addLayout(cols_layout)
