"""
ChefMascot — an interactive hand-painted (QPainter, no image assets) chef character
that floats freely over the AI Assistant page. Draggable anywhere on the page,
reacts to hovering, eye-tracking, clicking, squishing, double-click spins, right-click
actions, idle auto-quips, and assistant state (idle, thinking, happy, confused).
"""
import os
import math
import random

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect, QMenu
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, Signal, QPoint, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QPixmap

from utils.theme import ThemeManager
from utils.accent import AccentManager
from utils.animations import create_soft_shadow
from utils.paths import resource_path
import utils.icons as icons

COLOR_GOLD = "#F59E0B"

_CHEF_QUOTES = [
    "Bon Appétit! How can I assist your catering today? 👨‍🍳",
    "Did someone say Lechon & Catering packages? 🍖",
    "Ask me about sales, bookings, or recipes! 📊",
    "Checking inventory... everything looks delicious! 🥗",
    "Pro tip: Track your high-margin packages in Analytics! 📈",
    "Ready to cook up some business insights! 💡",
    "Need to schedule an event? I can guide you! 📅",
    "You're doing awesome! Let's make today profitable! ⭐",
    "Psst — you can drag me anywhere on this page! 🖐️",
    "Right-click me if you want options. 📋",
]

_DRAG_THRESHOLD = 6


class SpeechBubble(QWidget):
    """Floating tooltip speech bubble that tracks the mascot as it moves."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)

        self._label = QLabel("", self)
        self._label.setWordWrap(True)
        self._label.setMaximumWidth(240)
        self._update_style()
        layout.addWidget(self._label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def _update_style(self):
        dark = ThemeManager().is_dark()
        bg = "#1F2937" if dark else "#FFFFFF"
        fg = "#F9FAFB" if dark else "#0F172A"
        border = "#374151" if dark else "#E2E8F0"
        self._label.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: 1px solid {border}; "
            f"border-radius: 12px; padding: 8px 12px; font-size: 12px; font-weight: 600;"
        )

    def popup_at(self, global_pos: QPoint, text: str, duration_ms: int = 3500):
        self._update_style()
        self._label.setText(text)
        self.adjustSize()
        self.reposition(global_pos)
        self.show()
        self._timer.start(duration_ms)

    def reposition(self, global_pos: QPoint):
        """Re-anchor above global_pos without touching the text or hide timer —
        used to keep the bubble glued to the mascot while it's being dragged."""
        x = global_pos.x() - self.width() // 2
        y = global_pos.y() - self.height() - 6
        self.move(x, y)


class ChefMascot(QWidget):
    clicked = Signal()
    resetRequested = Signal()

    def __init__(self, parent=None, size: int = 84):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.OpenHandCursor)

        self._bob_offset = 0.0
        self._tilt_angle = 0.0
        self._scale = 1.0
        self._eye_scale = 1.0
        self._eye_offset_x = 0.0
        self._eye_offset_y = 0.0
        self._hat_offset = 0.0

        self._pixmap = None
        img_path = resource_path("assets", "chef_anime_avatar.png")
        if not os.path.exists(img_path):
            img_path = resource_path("assets", "chef_anime.jpg")
        if os.path.exists(img_path):
            self._pixmap = QPixmap(img_path)

        self._is_hovered = False
        self._expression = "normal"  # "normal", "wink", "surprised", "happy", "confused"
        self._quote_bubble = SpeechBubble(self)

        self._state = "idle"
        self._idle_anim = None
        self._thinking_anim = None
        self._bounce_anim = None
        self._squish_anim = None
        self._spin_anim = None
        self._confused_anim = None

        self._dragging = False
        self._was_dragged = False
        self._press_global = None
        self._press_widget_pos = None

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start(3200)

        self._reset_expr_timer = QTimer(self)
        self._reset_expr_timer.setSingleShot(True)
        self._reset_expr_timer.timeout.connect(self._reset_expression)

        self._idle_quip_timer = QTimer(self)
        self._idle_quip_timer.timeout.connect(self._maybe_idle_quip)
        self._idle_quip_timer.start(random.randint(45000, 75000))

        create_soft_shadow(self, radius=14, y_offset=6, opacity=35)
        ThemeManager().theme_changed.connect(self._on_theme_or_accent_changed)
        AccentManager().accent_changed.connect(self._on_theme_or_accent_changed)

        self.set_state("idle")

    def _on_theme_or_accent_changed(self, *_args):
        try:
            from shiboken6 import isValid
            if isValid(self):
                self.update()
        except Exception:
            pass

    # ── Qt properties for QPropertyAnimation ────────────────────────

    def _get_bob(self):
        return self._bob_offset

    def _set_bob(self, v):
        self._bob_offset = v
        self.update()

    bob_offset = Property(float, _get_bob, _set_bob)

    def _get_tilt(self):
        return self._tilt_angle

    def _set_tilt(self, v):
        self._tilt_angle = v
        self.update()

    tilt_angle = Property(float, _get_tilt, _set_tilt)

    def _get_scale(self):
        return self._scale

    def _set_scale(self, v):
        self._scale = v
        self.update()

    scale_factor = Property(float, _get_scale, _set_scale)

    def _get_hat_offset(self):
        return self._hat_offset

    def _set_hat_offset(self, v):
        self._hat_offset = v
        self.update()

    hat_offset_prop = Property(float, _get_hat_offset, _set_hat_offset)

    def _get_eye_scale(self):
        return self._eye_scale

    def _set_eye_scale(self, v):
        self._eye_scale = v
        self.update()

    eye_scale_prop = Property(float, _get_eye_scale, _set_eye_scale)

    # ── Free-floating drag support ──────────────────────────────────────

    def has_been_moved(self) -> bool:
        return self._was_dragged

    def clamp_to_parent(self):
        parent = self.parentWidget()
        if parent is None:
            return
        max_x = max(0, parent.width() - self.width())
        max_y = max(0, parent.height() - self.height())
        x = min(max(self.x(), 0), max_x)
        y = min(max(self.y(), 0), max_y)
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._quote_bubble.isVisible():
            self._quote_bubble.reposition(self.mapToGlobal(QPoint(self.width() // 2, 0)))

    def _show_quote(self, text: str, duration_ms: int = 3200):
        pos = self.mapToGlobal(QPoint(self.width() // 2, 0))
        self._quote_bubble.popup_at(pos, text, duration_ms=duration_ms)

    def say(self, text: str, duration_ms: int = 3200):
        self._show_quote(text, duration_ms=duration_ms)

    def reset_to_header(self):
        self._was_dragged = False
        self._press_widget_pos = None
        self.resetRequested.emit()
        self.say("Back home!", duration_ms=2500)

    # ── Interactive Mouse Events ────────────────────────────────────────

    def enterEvent(self, event):
        super().enterEvent(event)
        self._is_hovered = True
        if not self._dragging:
            self._animate_scale(1.12, duration=200, easing=QEasingCurve.OutBack)
            self._pop_hat(4.0)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._is_hovered = False
        if not self._dragging:
            self._animate_scale(1.0, duration=200)
        self._eye_offset_x = 0.0
        self._eye_offset_y = 0.0
        self.update()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        if event.buttons() & Qt.LeftButton and self._press_global is not None:
            delta = event.globalPosition().toPoint() - self._press_global
            if not self._dragging and delta.manhattanLength() > _DRAG_THRESHOLD:
                self._dragging = True
                self._was_dragged = True
                self.setCursor(Qt.ClosedHandCursor)
                self._quote_bubble.hide()
            if self._dragging:
                parent = self.parentWidget()
                new_pos = self._press_widget_pos + delta
                if parent is not None:
                    max_x = max(0, parent.width() - self.width())
                    max_y = max(0, parent.height() - self.height())
                    new_pos.setX(min(max(new_pos.x(), 0), max_x))
                    new_pos.setY(min(max(new_pos.y(), 0), max_y))
                self.move(new_pos)
                return

        if self._is_hovered:
            center = QPoint(self.width() // 2, self.height() // 2)
            mouse_pos = event.pos()
            dx = mouse_pos.x() - center.x()
            dy = mouse_pos.y() - center.y()
            dist = math.hypot(dx, dy) or 1.0
            max_offset = 3.5
            self._eye_offset_x = (dx / dist) * min(max_offset, abs(dx) * 0.15)
            self._eye_offset_y = (dy / dist) * min(max_offset, abs(dy) * 0.15)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_widget_pos = self.pos()
            self._dragging = False
            self._animate_scale(0.92, duration=100, easing=QEasingCurve.InQuad)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            was_dragging = self._dragging
            self._dragging = False
            self._press_global = None
            self.setCursor(Qt.OpenHandCursor if not self._is_hovered else Qt.PointingHandCursor)

            if was_dragging:
                self._animate_scale(1.0, duration=380, easing=QEasingCurve.OutElastic)
            else:
                target_scale = 1.12 if self._is_hovered else 1.0
                self._animate_scale(target_scale, duration=450, easing=QEasingCurve.OutElastic)

                self.clicked.emit()
                exprs = ["wink", "happy", "surprised"]
                self._expression = random.choice(exprs)
                self._reset_expr_timer.start(2400)
                self._show_quote(random.choice(_CHEF_QUOTES))
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_spin_flip()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        say_act = menu.addAction("Say something 💬")
        spin_act = menu.addAction("Spin! 🌀")
        menu.addSeparator()
        reset_act = menu.addAction("Reset position 📍")
        chosen = menu.exec(event.globalPos())
        if chosen == say_act:
            self._show_quote(random.choice(_CHEF_QUOTES))
        elif chosen == spin_act:
            self._start_spin_flip()
        elif chosen == reset_act:
            self._was_dragged = False
            self.resetRequested.emit()

    def _reset_expression(self):
        self._expression = "normal"
        self.update()

    def _maybe_idle_quip(self):
        self._idle_quip_timer.start(random.randint(45000, 90000))
        if self._state != "idle" or self._dragging or not self.isVisible():
            return
        if random.random() < 0.6:
            self._show_quote(random.choice(_CHEF_QUOTES), duration_ms=3000)

    def _animate_scale(self, target: float, duration: int = 200, easing=QEasingCurve.OutQuad):
        if self._squish_anim and self._squish_anim.state() == QPropertyAnimation.Running:
            self._squish_anim.stop()
        anim = QPropertyAnimation(self, b"scale_factor", self)
        anim.setDuration(duration)
        anim.setEndValue(target)
        anim.setEasingCurve(easing)
        anim.start()
        self._squish_anim = anim

    def _pop_hat(self, offset: float):
        anim = QPropertyAnimation(self, b"hat_offset_prop", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setKeyValueAt(0.5, -offset)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutBack)
        anim.start()

    def _start_spin_flip(self):
        if self._spin_anim and self._spin_anim.state() == QPropertyAnimation.Running:
            return
        anim = QPropertyAnimation(self, b"tilt_angle", self)
        anim.setDuration(550)
        anim.setStartValue(0.0)
        anim.setEndValue(360.0)
        anim.setEasingCurve(QEasingCurve.OutBack)
        anim.finished.connect(lambda: self._set_tilt(0.0))
        anim.start()
        self._spin_anim = anim
        self._pop_hat(10.0)
        self._expression = "happy"
        self._reset_expr_timer.start(1200)

    # ── State Machine ───────────────────────────────────────────────────

    def set_state(self, state: str):
        if state not in ("idle", "thinking", "happy", "confused"):
            return
        for anim in (self._idle_anim, self._thinking_anim, self._bounce_anim, self._confused_anim):
            if anim is not None:
                anim.stop()
        self._tilt_angle = 0.0

        if state == "thinking":
            self._state = "thinking"
            self._start_thinking()
        elif state == "happy":
            self._state = "happy"
            self._start_bounce()
        elif state == "confused":
            self._state = "confused"
            self._start_confused()
        else:
            self._state = "idle"
            self._expression = "normal"
            self._start_idle()

    def _start_idle(self):
        anim = QPropertyAnimation(self, b"bob_offset", self)
        anim.setDuration(1600)
        anim.setStartValue(0.0)
        anim.setKeyValueAt(0.5, -6.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.setLoopCount(-1)
        self._idle_anim = anim
        anim.start()

    def _start_thinking(self):
        anim = QPropertyAnimation(self, b"tilt_angle", self)
        anim.setDuration(500)
        anim.setStartValue(-8.0)
        anim.setKeyValueAt(0.5, 8.0)
        anim.setEndValue(-8.0)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.setLoopCount(-1)
        self._thinking_anim = anim
        anim.start()

    def _start_bounce(self):
        anim = QPropertyAnimation(self, b"scale_factor", self)
        anim.setDuration(450)
        anim.setStartValue(1.0)
        anim.setKeyValueAt(0.4, 1.25)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutBack)
        anim.finished.connect(lambda: self.set_state("idle"))
        self._bounce_anim = anim
        anim.start()
        self._expression = "happy"
        self._reset_expr_timer.start(1600)

    def _start_confused(self):
        self._expression = "confused"
        anim = QPropertyAnimation(self, b"tilt_angle", self)
        anim.setDuration(500)
        anim.setStartValue(-7.0)
        anim.setKeyValueAt(0.25, 7.0)
        anim.setKeyValueAt(0.5, -5.0)
        anim.setKeyValueAt(0.75, 3.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.finished.connect(lambda: self.set_state("idle"))
        anim.setLoopCount(4)
        anim.start()

    def _blink(self):
        anim = QPropertyAnimation(self, b"eye_scale_prop", self)
        anim.setDuration(160)
        anim.setStartValue(1.0)
        anim.setKeyValueAt(0.5, 0.05)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self._blink_anim = anim

    def _bounce(self, target_scale: float):
        anim = QPropertyAnimation(self, b"scale_prop", self)
        anim.setDuration(220)
        anim.setStartValue(self._scale)
        anim.setEndValue(target_scale)
        anim.setEasingCurve(QEasingCurve.OutBack)
        anim.start()

    def _tilt_to(self, target_deg: float):
        anim = QPropertyAnimation(self, b"tilt_angle", self)
        anim.setDuration(180)
        anim.setStartValue(self._tilt_angle)
        anim.setEndValue(target_deg)
        anim.setEasingCurve(QEasingCurve.OutQuad)
        anim.start()

    def _pop_hat(self, offset: float):
        anim = QPropertyAnimation(self, b"hat_offset_prop", self)
        anim.setDuration(180)
        anim.setStartValue(self._hat_offset)
        anim.setEndValue(offset)
        anim.setEasingCurve(QEasingCurve.OutBack)
        anim.start()

    def _maybe_idle_quip(self):
        if self._state == "idle" and not self._dragging and not self._is_hovered:
            quips = [
                "Hungry for sales growth? Ask me anything!",
                "Check out today's capacity on the Dashboard!",
                "Chef Jay tip: Always follow up with pending invoices!",
                "I'm here anytime you need instant catering reports!",
            ]
            self.say(random.choice(quips), duration_ms=4000)
            self._blink()
        self._idle_quip_timer.setInterval(random.randint(45000, 75000))

    # ── Painting ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        dark = ThemeManager().is_dark()
        outline = QColor("#1F2937" if not dark else "#0B1220")

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        cx, cy = self._size / 2, self._size / 2 + self._bob_offset
        p.translate(cx, cy)
        p.rotate(self._tilt_angle)
        p.scale(self._scale, self._scale)
        p.translate(-self._size / 2, -self._size / 2)

        if self._pixmap and not self._pixmap.isNull():
            # 1. Outer glowing accent border
            border_color = QColor(AccentManager().current)
            p.setPen(QPen(border_color, 3 if self._is_hovered else 2.2))
            p.setBrush(QBrush(QColor("#FFFFFF" if not dark else "#1E293B")))
            p.drawEllipse(3, 3, self._size - 6, self._size - 6)

            # 2. Render Anime Chef Avatar inside circular clip
            clip_path = QPainterPath()
            clip_path.addEllipse(5, 5, self._size - 10, self._size - 10)
            p.save()
            p.setClipPath(clip_path)
            p.drawPixmap(5, 5, self._size - 10, self._size - 10, self._pixmap)
            p.restore()

            # 3. Interactive Blinking Eyelid Overlay over Anime Chef Eyes
            if self._eye_scale < 0.95:
                eyelid_alpha = int((1.0 - max(0.0, self._eye_scale)) * 255)
                skin_tone = QColor("#F4CDAE" if not dark else "#D8A47F")
                skin_tone.setAlpha(min(255, max(0, eyelid_alpha)))
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(skin_tone))

                # Smooth skin-tone eyelid arc over anime eyes
                left_eye_rect = QRectF(self._size * 0.38, self._size * 0.40, self._size * 0.12, self._size * 0.09)
                right_eye_rect = QRectF(self._size * 0.52, self._size * 0.38, self._size * 0.12, self._size * 0.09)
                p.drawEllipse(left_eye_rect)
                p.drawEllipse(right_eye_rect)

                # Closed eyelash line detail during full blink
                if self._eye_scale < 0.35:
                    lash_pen = QPen(QColor("#2C1D11" if not dark else "#0F172A"), 1.8)
                    lash_pen.setCapStyle(Qt.RoundCap)
                    p.setPen(lash_pen)
                    p.drawLine(QPointF(self._size * 0.38, self._size * 0.45), QPointF(self._size * 0.50, self._size * 0.45))
                    p.drawLine(QPointF(self._size * 0.52, self._size * 0.43), QPointF(self._size * 0.64, self._size * 0.43))

        p.end()
