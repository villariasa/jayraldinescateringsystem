# components/badges.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from utils.theme import ThemeManager

_LIGHT = {
    "success": ("rgba(22,163,74,0.10)",  "rgba(22,163,74,0.30)",  "#15803D"),
    "warning": ("rgba(217,119,6,0.10)",  "rgba(217,119,6,0.30)",  "#B45309"),
    "danger":  ("rgba(220,38,38,0.08)",  "rgba(220,38,38,0.30)",  "#B91C1C"),
    "info":    ("rgba(37,99,235,0.08)",  "rgba(37,99,235,0.30)",  "#1D4ED8"),
}

_DARK = {
    "success": ("rgba(34,197,94,0.15)",  "rgba(34,197,94,0.35)",  "#4ADE80"),
    "warning": ("rgba(245,158,11,0.15)", "rgba(245,158,11,0.35)", "#FBBF24"),
    "danger":  ("rgba(239,68,68,0.15)",  "rgba(239,68,68,0.35)",  "#F87171"),
    "info":    ("rgba(59,130,246,0.15)", "rgba(59,130,246,0.35)", "#60A5FA"),
}


def create_pill_badge(text, variant="success"):
    """Creates a modern, pill-shaped status badge (theme-aware)."""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)

    palette = _DARK if ThemeManager().is_dark() else _LIGHT
    bg, border, fg = palette.get(variant, palette["success"])
    lbl.setStyleSheet(
        f"font-weight: 700; font-size: 11px; padding: 4px 12px; border-radius: 12px;"
        f" border: 1px solid {border}; background-color: {bg}; color: {fg};"
    )

    layout.addWidget(lbl)
    return widget
