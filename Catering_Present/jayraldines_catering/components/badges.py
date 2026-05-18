# components/badges.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

def create_pill_badge(text, variant="success"):
    """Creates a modern, pill-shaped status badge."""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    
    base_style = "font-weight: 700; font-size: 11px; padding: 4px 12px; border-radius: 12px; border: 1px solid"
    if variant == "success":
        lbl.setStyleSheet(f"{base_style} #bbf7d0; background-color: #dcfce7; color: #166534;")
    elif variant == "warning":
        lbl.setStyleSheet(f"{base_style} #fef08a; background-color: #fef9c3; color: #854d0e;")
    elif variant == "danger":
        lbl.setStyleSheet(f"{base_style} #fecaca; background-color: #fee2e2; color: #b91c1c;")
        
    layout.addWidget(lbl)
    return widget