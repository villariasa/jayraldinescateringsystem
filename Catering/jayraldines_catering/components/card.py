# components/card.py
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
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.valueChanged.connect(self._animate_shadow)

    def _animate_shadow(self, value):
        # Dynamically increase blur and offset to simulate Z-index lift
        self.shadow.setBlurRadius(15 + (value * 1.5))
        self.shadow.setOffset(0, 3 + (value / 2))
        self.shadow.setColor(QColor(0, 0, 0, 15 + int(value / 2)))

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(0)
        self.anim.setEndValue(10)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(10)
        self.anim.setEndValue(0)
        self.anim.start()
        super().leaveEvent(event)