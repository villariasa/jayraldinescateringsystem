# utils/animations.py
from PySide6.QtCore import QPropertyAnimation, QVariantAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

def create_soft_shadow(widget, radius=15, y_offset=4, opacity=20):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setColor(QColor(0, 0, 0, opacity))
    shadow.setOffset(0, y_offset)
    widget.setGraphicsEffect(shadow)
    return shadow

def apply_fade_in(widget, duration=600):
    """Applies a smooth fade-in effect to a widget on load."""
    # FIX: Attach to the widget so Python doesn't garbage collect them!
    widget._opacity_effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(widget._opacity_effect)
    
    widget._fade_anim = QPropertyAnimation(widget._opacity_effect, b"opacity", widget)
    widget._fade_anim.setDuration(duration)
    widget._fade_anim.setStartValue(0.0)
    widget._fade_anim.setEndValue(1.0)
    widget._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
    widget._fade_anim.start()
    
    return widget._fade_anim