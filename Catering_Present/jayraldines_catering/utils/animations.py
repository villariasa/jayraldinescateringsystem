# utils/animations.py
"""Reusable Qt/PySide6 UI animation helpers.

Provides lightweight fade, slide-fade, and dialog open animations plus dialog
centering. Animations are deliberately kept cheap and self-cleaning because
QGraphicsEffect-based rendering routes widgets through an offscreen buffer,
which hurts performance and can corrupt child repaints on weaker GPUs — so
effects are attached only for the duration of the animation and then removed.
"""
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
    """No-op shadow factory kept for API compatibility.

    Returns None intentionally so existing call sites keep working while the
    real drop-shadow effect stays disabled for the performance reason below.
    """
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
        # Drop the opacity effect once faded in so the widget renders normally
        # again (no lingering offscreen buffer) and release our references.
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass  # widget already destroyed by Qt
        widget._opacity_effect = None

    widget._fade_anim.finished.connect(_cleanup)
    widget._fade_anim.start()

    return widget._fade_anim


def _opacity_effect(widget):
    """Return an opacity effect for the widget, creating one if needed.

    Returns None when the widget already has a different (non-opacity) graphics
    effect, so we never clobber an effect the caller depends on.
    """
    effect = widget.graphicsEffect()
    # Bail out rather than overwrite an unrelated effect already installed.
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
        return None  # widget has an incompatible effect; skip animating
    effect.setOpacity(0.0)  # start fully transparent
    # Grouped so the cleanup fires when the whole animation completes.
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
    # Keep a reference on the widget so Python's GC doesn't collect the running
    # animation group mid-flight.
    widget._slide_fade_group = group
    group.start()
    return group


def _scaled_rect(rect: QRect, scale: float) -> QRect:
    """Return a copy of rect scaled about its center by the given factor.

    Width/height are clamped to at least 1px so zero-size rects never occur.
    """
    width = max(1, int(rect.width() * scale))
    height = max(1, int(rect.height() * scale))
    center = rect.center()
    return QRect(center.x() - width // 2, center.y() - height // 2, width, height)


def center_dialog_on_window(dialog):
    """Centers a dialog horizontally and vertically over the top-level MainWindow or screen."""
    from PySide6.QtWidgets import QApplication
    top_win = None
    # Prefer the dialog's own top-level window as the centering reference.
    if dialog.parent():
        top_win = dialog.parent().window()
    # Fall back to the active window if there's no usable parent window.
    if not top_win or top_win == dialog:
        top_win = QApplication.activeWindow()

    if top_win and top_win != dialog:
        # Center over the reference window's geometry.
        win_rect = top_win.geometry()
        x = win_rect.x() + (win_rect.width() - dialog.width()) // 2
        y = win_rect.y() + (win_rect.height() - dialog.height()) // 2
        dialog.move(x, y)
    else:
        # No window to anchor to — center on the primary screen instead.
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
        # Deferred to the next event-loop tick (see singleShot below) so the
        # dialog has been laid out and reports its real final geometry.
        final_rect = dialog.geometry()
        if final_rect.width() <= 1 or final_rect.height() <= 1:
            return  # not laid out yet; skip animating to avoid a bad start rect

        # Begin slightly scaled down and transparent, then grow to final size.
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

        # Hold a reference so the group survives until the animation finishes.
        dialog._dialog_open_group = group
        group.start()

    # Run on the next tick so geometry is valid before we animate it.
    QTimer.singleShot(0, run)
