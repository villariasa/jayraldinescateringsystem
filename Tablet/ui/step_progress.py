"""A horizontal step indicator for the order wizard."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from ui import theme, icons

STEPS = ["Customer", "Event & Package", "Menu", "Charges", "Billing", "Preview"]


class StepProgress(QWidget):
    def __init__(self):
        super().__init__()
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)
        self._labels = []
        self._build()

    def _build(self):
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels = []

        for i, name in enumerate(STEPS):
            num_lbl = QLabel(str(i + 1))
            num_lbl.setFixedSize(28, 28)
            num_lbl.setAlignment(Qt.AlignCenter)

            text_lbl = QLabel(name)
            text_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {theme.TEXT_FAINT};")

            col = QWidget()
            from PySide6.QtWidgets import QVBoxLayout
            col_lay = QVBoxLayout(col)
            col_lay.setContentsMargins(0, 0, 0, 0)
            col_lay.setSpacing(4)
            col_lay.setAlignment(Qt.AlignHCenter)
            col_lay.addWidget(num_lbl, alignment=Qt.AlignHCenter)
            col_lay.addWidget(text_lbl, alignment=Qt.AlignHCenter)

            self._lay.addWidget(col)
            self._labels.append((num_lbl, text_lbl))

            if i < len(STEPS) - 1:
                line = QFrame()
                line.setFixedHeight(2)
                line.setStyleSheet(f"background: {theme.BORDER};")
                self._lay.addWidget(line, 1)

    def set_current(self, index: int):
        """index is 0-based into STEPS."""
        for i, (num_lbl, text_lbl) in enumerate(self._labels):
            if i < index:
                num_lbl.setStyleSheet(
                    "background: #10B981; color: white; border-radius: 14px;"
                )
                num_lbl.setPixmap(icons.icon_check("#FFFFFF", 16).pixmap(16, 16))
                text_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #10B981;")
            elif i == index:
                num_lbl.setStyleSheet(
                    "background: #F43F5E; color: white; border-radius: 14px; font-weight: 800; font-size: 13px;"
                )
                num_lbl.setText(str(i + 1))
                text_lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #FFFFFF;")
            else:
                num_lbl.setStyleSheet(
                    "background: #132238; color: #64748B; border-radius: 14px; font-weight: 700; font-size: 13px; border: 1.5px solid #1E293B;"
                )
                num_lbl.setText(str(i + 1))
                text_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
