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
    # QGraphicsDropShadowEffect forces full software rasterization on older
    # Intel HD (4600 etc.) GPUs — disabled globally for performance.
    # Visual appearance is maintained via CSS border/background styles.
    return None

def apply_fade_in(widget, duration=600):
    """Applies a smooth fade-in effect to a widget on load.
    The effect is removed once the fade completes (see animate_slide_fade_in)."""
    # FIX: Attach to the widget so Python doesn't garbage collect them!
    widget._opacity_effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(widget._opacity_effect)

    widget._fade_anim = QPropertyAnimation(widget._opacity_effect, b"opacity", widget)
    widget._fade_anim.setDuration(duration)
    widget._fade_anim.setStartValue(0.0)
    widget._fade_anim.setEndValue(1.0)
    widget._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _cleanup():
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass
        widget._opacity_effect = None

    widget._fade_anim.finished.connect(_cleanup)
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


def animate_slide_fade_in(widget, offset_x=0, offset_y=0, duration=220):
    """Lightweight fade animation used for stacked content changes.

    The QGraphicsOpacityEffect is REMOVED when the fade completes — a
    lingering effect forces the widget to render through an offscreen
    buffer, which corrupts child repaints (inputs vanishing on hover).
    """
    effect = _opacity_effect(widget)
    if effect is None:
        return None
    effect.setOpacity(0.0)
    group = QParallelAnimationGroup(widget)
    fade_anim = QPropertyAnimation(effect, b"opacity", group)
    fade_anim.setDuration(duration)
    fade_anim.setStartValue(0.0)
    fade_anim.setEndValue(1.0)
    fade_anim.setEasingCurve(QEasingCurve.OutCubic)
    group.addAnimation(fade_anim)

    def _cleanup():
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass  # widget already destroyed
        widget._slide_fade_group = None

    group.finished.connect(_cleanup)
    widget._slide_fade_group = group
    group.start()
    return group


def _scaled_rect(rect: QRect, scale: float) -> QRect:
    width = max(1, int(rect.width() * scale))
    height = max(1, int(rect.height() * scale))
    center = rect.center()
    return QRect(center.x() - width // 2, center.y() - height // 2, width, height)


def center_dialog_on_window(dialog):
    """Centers a dialog horizontally and vertically over the top-level MainWindow or screen."""
    from PySide6.QtWidgets import QApplication
    top_win = None
    if dialog.parent():
        top_win = dialog.parent().window()
    if not top_win or top_win == dialog:
        top_win = QApplication.activeWindow()

    if top_win and top_win != dialog:
        win_rect = top_win.geometry()
        x = win_rect.x() + (win_rect.width() - dialog.width()) // 2
        y = win_rect.y() + (win_rect.height() - dialog.height()) // 2
        dialog.move(x, y)
    else:
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            x = avail.x() + (avail.width() - dialog.width()) // 2
            y = avail.y() + (avail.height() - dialog.height()) // 2
            dialog.move(x, y)


def animate_dialog_open(dialog, duration=240, auto_center=True):
    """Subtle modal scale/fade-in with automatic true centering over MainWindow."""
    if auto_center:
        center_dialog_on_window(dialog)

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
