# components/card.py
"""Hover-reactive card frame that animates its drop shadow to fake a lift effect."""

from PySide6.QtWidgets import QFrame
from PySide6.QtCore import QVariantAnimation, QEasingCurve
from utils.animations import create_soft_shadow

class HoverCard(QFrame):
    """A premium card that smoothly lifts and increases shadow on hover."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("saasCard")

        # Base shadow
        self.shadow = create_soft_shadow(self, radius=15, y_offset=3, opacity=15)

        # Smooth transition animation
        # Drives a 0->10 value on hover (and back) that _animate_shadow maps to shadow params.
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.valueChanged.connect(self._animate_shadow)

    def _animate_shadow(self, value):
        """Grow the shadow's blur/offset/opacity in step with the animation value."""
        # Stop agad if shadow not initialized
        if not hasattr(self, "shadow") or self.shadow is None:
            return

        try:
            # Dynamically increase blur and offset to simulate Z-index lift
            # (higher value => larger, softer, darker shadow, reading as "closer").
            self.shadow.setBlurRadius(15 + (value * 1.5))
            self.shadow.setOffset(0, 3 + (value / 2))
            self.shadow.setColor(QColor(0, 0, 0, 15 + int(value / 2)))
        except RuntimeError:
            # Qt may delete the effect internally (newer PySide behavior)
            return

    def enterEvent(self, event):
        """Animate the shadow up (lift) when the cursor enters the card."""
        # Restart from 0 each time so rapid enter/leave doesn't jump mid-animation.
        self.anim.stop()
        self.anim.setStartValue(0)
        self.anim.setEndValue(10)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Animate the shadow back down when the cursor leaves the card."""
        self.anim.stop()
        self.anim.setStartValue(10)
        self.anim.setEndValue(0)
        self.anim.start()
        super().leaveEvent(event)