"""
Color Theme Picker Component for Jayraldine's Catering System.
Provides clickable swatches for popular event themes and a custom QColorDialog picker.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QColorDialog, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


PRESET_THEME_COLORS = [
    ("#2563EB", "Royal Blue"),
    ("#059669", "Emerald Green"),
    ("#D97706", "Amber Gold"),
    ("#E11D48", "Rose Pink"),
    ("#7C3AED", "Royal Purple"),
    ("#0891B2", "Teal Cyan"),
    ("#DC2626", "Ruby Red"),
    ("#EA580C", "Sunset Orange"),
    ("#8B5CF6", "Lavender"),
    ("#1E3A8A", "Midnight Navy"),
    ("#475569", "Slate"),
]


class ColorThemeSelector(QWidget):
    color_changed = Signal(str)

    def __init__(self, initial_color: str = "#2563EB", parent=None):
        super().__init__(parent)
        self._current_color = initial_color if initial_color else "#2563EB"
        self._swatch_buttons = []
        self._build_ui()
        self.set_color(self._current_color)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Preset swatches arranged in 2 spacious rows so Custom button never compresses
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        for i, (hex_code, name) in enumerate(PRESET_THEME_COLORS):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(f"{name} ({hex_code})")
            btn.setProperty("hex_code", hex_code)
            btn.clicked.connect(lambda _, h=hex_code: self.set_color(h))
            self._swatch_buttons.append(btn)
            if i < 6:
                row1.addWidget(btn)
            else:
                row2.addWidget(btn)

        row1.addStretch()

        # Custom color button on row 2 with fixed comfortable width
        self.btn_custom = QPushButton("🎨 Custom Color...")
        self.btn_custom.setCursor(Qt.PointingHandCursor)
        self.btn_custom.setFixedHeight(28)
        self.btn_custom.setMinimumWidth(125)
        self.btn_custom.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                font-weight: 700;
                background: #F1F5F9;
                color: #1E293B;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background: #E2E8F0;
                border-color: #94A3B8;
            }
        """)
        self.btn_custom.clicked.connect(self._open_custom_dialog)
        row2.addWidget(self.btn_custom)
        row2.addStretch()

        layout.addLayout(row1)
        layout.addLayout(row2)

        # Active Color Preview Bar
        preview_row = QHBoxLayout()
        preview_row.setSpacing(8)

        self._preview_box = QFrame()
        self._preview_box.setFixedSize(18, 18)
        self._preview_box.setStyleSheet("border-radius: 4px; border: 1px solid rgba(0,0,0,0.2);")

        self._lbl_preview = QLabel()
        self._lbl_preview.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")

        preview_row.addWidget(self._preview_box)
        preview_row.addWidget(self._lbl_preview)
        preview_row.addStretch()
        layout.addLayout(preview_row)

    def _open_custom_dialog(self):
        initial = QColor(self._current_color)
        col = QColorDialog.getColor(initial, self, "Select Custom Booking Theme Color")
        if col.isValid():
            self.set_color(col.name().upper())

    def set_color(self, hex_code: str):
        if not hex_code:
            hex_code = "#2563EB"
        hex_code = hex_code.strip()
        if not hex_code.startswith("#"):
            hex_code = "#" + hex_code
        self._current_color = hex_code.upper()

        # Update swatch button highlights
        for btn in self._swatch_buttons:
            btn_hex = btn.property("hex_code")
            is_sel = (btn_hex.upper() == self._current_color)
            if is_sel:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {btn_hex};
                        border: 3px solid #0F172A;
                        border-radius: 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {btn_hex};
                        border: 1px solid rgba(0, 0, 0, 0.2);
                        border-radius: 14px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #64748B;
                    }}
                """)

        # Update preview box & label
        theme_name = next((name for h, name in PRESET_THEME_COLORS if h.upper() == self._current_color), "Custom Color")
        self._preview_box.setStyleSheet(f"background-color: {self._current_color}; border-radius: 4px; border: 1px solid rgba(0,0,0,0.25);")
        self._lbl_preview.setText(f"Active Theme: <b>{theme_name}</b> ({self._current_color})")

        self.color_changed.emit(self._current_color)

    def get_color(self) -> str:
        return self._current_color
