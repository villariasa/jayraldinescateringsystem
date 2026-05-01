from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QButtonGroup, QScrollArea
)
from PySide6.QtCore import Qt, QSize, QPoint, QEvent, Signal
from PySide6.QtGui import QColor

from utils.icons import get_icon


class FilterChip(QPushButton):
    def __init__(self, label, value):
        super().__init__(label)
        self.value = value
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        self._update_style()
        self.toggled.connect(lambda _: self._update_style())

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet(
                "background: rgba(225,29,72,0.15); color: #E11D48;"
                " border: 1px solid rgba(225,29,72,0.4); border-radius: 14px;"
                " font-size: 12px; font-weight: 700; padding: 0 12px;"
            )
        else:
            self.setStyleSheet(
                "background: transparent; color: #9CA3AF;"
                " border: 1px solid #374151; border-radius: 14px;"
                " font-size: 12px; font-weight: 600; padding: 0 12px;"
            )


class FilterPopover(QFrame):
    """
    Lightweight filter popover anchored to a button.
    Emits filter_applied(dict) when Apply is clicked.
    Supports: status chips, date range text chips.

    Usage:
        fp = FilterPopover(parent=main_window, statuses=["All","PENDING","CONFIRMED","CANCELLED"])
        fp.filter_applied.connect(my_slot)
        # In button click handler:
        fp.toggle_anchored(filter_btn)
    """

    filter_applied = Signal(dict)

    def __init__(self, parent=None, statuses=None, categories=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._statuses   = statuses or []
        self._categories = categories or []
        self._status_chips = []
        self._cat_chips    = []
        self._build_ui()
        self.hide()
        if parent:
            parent.installEventFilter(self)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        inner = QFrame()
        inner.setObjectName("card")
        inner.setFixedWidth(300)
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(20, 18, 20, 18)
        inner_lay.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Filters")
        title.setObjectName("h3")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(13, 13)))
        close_btn.setIconSize(QSize(13, 13))
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        inner_lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        inner_lay.addWidget(div)

        if self._statuses:
            status_lbl = QLabel("STATUS")
            status_lbl.setStyleSheet(
                "color: #6B7280; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
            )
            inner_lay.addWidget(status_lbl)

            chips_row = QHBoxLayout()
            chips_row.setSpacing(6)
            chips_row.setAlignment(Qt.AlignLeft)
            self._status_chips = []
            self._status_group = QButtonGroup(self)
            self._status_group.setExclusive(True)
            for s in self._statuses:
                chip = FilterChip(s, s)
                if s == "All":
                    chip.setChecked(True)
                self._status_chips.append(chip)
                self._status_group.addButton(chip)
                chip.toggled.connect(lambda checked, c=chip: self._on_chip_toggled(c, checked))
                chips_row.addWidget(chip)
            chips_row.addStretch()
            inner_lay.addLayout(chips_row)

        if self._categories:
            cat_lbl = QLabel("CATEGORY")
            cat_lbl.setStyleSheet(
                "color: #6B7280; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
            )
            inner_lay.addWidget(cat_lbl)

            cat_wrap = QWidget()
            cat_lay = QHBoxLayout(cat_wrap)
            cat_lay.setContentsMargins(0, 0, 0, 0)
            cat_lay.setSpacing(6)
            cat_lay.setAlignment(Qt.AlignLeft)
            self._cat_chips = []
            for c in self._categories:
                chip = FilterChip(c, c)
                self._cat_chips.append(chip)
                chip.toggled.connect(lambda _: self._emit())
                cat_lay.addWidget(chip)
            cat_lay.addStretch()
            inner_lay.addWidget(cat_wrap)

        lay.addWidget(inner)

    def _on_chip_toggled(self, chip, checked):
        if checked:
            self._emit()

    def _emit(self):
        checked = next((c.value for c in self._status_chips if c.isChecked()), "All")
        selected_cats = [c.value for c in self._cat_chips if c.isChecked()]
        self.filter_applied.emit({"statuses": [checked], "categories": selected_cats})

    def show_anchored(self, anchor_btn):
        from PySide6.QtWidgets import QApplication
        global_pos = anchor_btn.mapToGlobal(QPoint(0, anchor_btn.height() + 6))
        x = global_pos.x()
        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            pw = self.sizeHint().width()
            x = max(sg.left() + 4, min(x, sg.right() - pw - 4))
        self.move(x, global_pos.y())
        self.raise_()
        self.show()

    def toggle_anchored(self, anchor_btn):
        if self.isVisible():
            self.hide()
        else:
            self.show_anchored(anchor_btn)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and self.isVisible():
            pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            local = self.mapFromGlobal(pos)
            if not self.rect().contains(local):
                self.hide()
        return False
