# utils/animations.py
from PySide6.QtCore import (
    QPoint,
    QRect,
    QTimer,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QVariantAnimation,
    QEasingCurve,
)
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


def _opacity_effect(widget):
    effect = widget.graphicsEffect()
    if effect is not None and not isinstance(effect, QGraphicsOpacityEffect):
        return None
    if effect is None:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    return effect


def animate_slide_fade_in(widget, offset_x=10, offset_y=0, duration=220):
    """Lightweight slide/fade animation used for stacked content changes."""
    effect = _opacity_effect(widget)
    final_pos = widget.pos()
    start_pos = final_pos + QPoint(offset_x, offset_y)

    widget.move(start_pos)
    widget.show()

    group = QParallelAnimationGroup(widget)

    pos_anim = QPropertyAnimation(widget, b"pos", group)
    pos_anim.setDuration(duration)
    pos_anim.setStartValue(start_pos)
    pos_anim.setEndValue(final_pos)
    pos_anim.setEasingCurve(QEasingCurve.OutCubic)
    group.addAnimation(pos_anim)

    if effect is not None:
        effect.setOpacity(0.0)
        fade_anim = QPropertyAnimation(effect, b"opacity", group)
        fade_anim.setDuration(duration)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(fade_anim)

    widget._slide_fade_group = group
    group.start()
    return group


def _scaled_rect(rect: QRect, scale: float) -> QRect:
    width = max(1, int(rect.width() * scale))
    height = max(1, int(rect.height() * scale))
    center = rect.center()
    return QRect(center.x() - width // 2, center.y() - height // 2, width, height)


def animate_dialog_open(dialog, duration=240):
    """Subtle modal scale/fade-in without changing the app theme."""
    def run():
        final_rect = dialog.geometry()
        if final_rect.width() <= 1 or final_rect.height() <= 1:
            return

        start_rect = _scaled_rect(final_rect, 0.96)
        dialog.setWindowOpacity(0.0)
        dialog.setGeometry(start_rect)

        group = QParallelAnimationGroup(dialog)

        geo_anim = QPropertyAnimation(dialog, b"geometry", group)
        geo_anim.setDuration(duration)
        geo_anim.setStartValue(start_rect)
        geo_anim.setEndValue(final_rect)
        geo_anim.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(geo_anim)

        fade_anim = QPropertyAnimation(dialog, b"windowOpacity", group)
        fade_anim.setDuration(duration)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(fade_anim)

        dialog._dialog_open_group = group
        group.start()

    QTimer.singleShot(0, run)
