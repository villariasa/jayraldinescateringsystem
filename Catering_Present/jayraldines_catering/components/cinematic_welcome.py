"""
components/cinematic_welcome.py
--------------------------------
Cinematic "epic movie intro" welcome screen shown after successful login.

Sequence (~3.5 s total):
  0.00 s  Black screen fades in
  0.35 s  Light rays begin sweeping across from the left
  0.70 s  Logo badge scales up from zero with a glow burst
  1.20 s  "Jayraldine's" title slides + fades in
  1.60 s  Subtitle line slides up + fades in
  2.10 s  Personalised welcome greeting appears  (e.g. "Welcome back, Jay")
  2.80 s  "ENTERING SYSTEM" tagline flickers on
  3.20 s  Full-screen white flash -> fades out -> MainWindow appears
"""

import math
import os

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPointF, QRectF, Signal, QObject, Property
)
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath,
    QPixmap, QRadialGradient, QPen, QBrush,
    QFontMetricsF
)
from PySide6.QtWidgets import QWidget, QApplication

try:
    from utils.paths import resource_path
except ImportError:
    def resource_path(*parts):
        return os.path.join(*parts)

try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "1.0"
    APP_NAME = "Jayraldine's Catering"


# ---------------------------------------------------------------------------
# Internal animated property helpers
# ---------------------------------------------------------------------------

class _FloatHolder(QObject):
    """Thin QObject wrapper so QPropertyAnimation can drive a plain float."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._v = 0.0

    def get_v(self): return self._v
    def set_v(self, v): self._v = v

    value = Property(float, get_v, set_v)


# ---------------------------------------------------------------------------
# Main cinematic canvas
# ---------------------------------------------------------------------------

class CinematicCanvas(QWidget):
    """
    Custom-painted full-screen widget that plays the entire cinematic
    sequence using a single 30-fps paint loop + several QPropertyAnimations
    for individual element alphas / scales / offsets.
    """

    sequence_finished = Signal()

    def __init__(self, user_name: str = "Owner", parent=None):
        super().__init__(parent)
        self._user_name = user_name

        self.setStyleSheet("background: #000000;")

        # Logo pixmap
        logo_path = resource_path("assets", "logo.png")
        self._logo_px = None
        if os.path.exists(logo_path):
            self._logo_px = QPixmap(logo_path)

        # Animated state
        self._screen_alpha   = 0.0
        self._ray_progress   = 0.0
        self._logo_scale     = 0.0
        self._logo_glow      = 0.0
        self._title_alpha    = 0.0
        self._title_offset   = 40.0
        self._sub_alpha      = 0.0
        self._sub_offset     = 30.0
        self._welcome_alpha  = 0.0
        self._tagline_alpha  = 0.0
        self._flash_alpha    = 0.0
        self._shimmer_pos    = -0.5

        # Paint timer (30 fps)
        self._tick = 0
        self._paint_timer = QTimer(self)
        self._paint_timer.timeout.connect(self._on_tick)
        self._paint_timer.start(33)

        QTimer.singleShot(80, self._start_sequence)

    def _on_tick(self):
        self._tick += 1
        if self._ray_progress > 0.1:
            self._shimmer_pos = -0.5 + ((self._tick * 0.018) % 2.0)
        self.update()

    def _start_sequence(self):
        self._animate_attr("_screen_alpha", 0.0, 1.0, 400, QEasingCurve.InOutQuad)

        QTimer.singleShot(350, lambda: self._animate_attr(
            "_ray_progress", 0.0, 1.0, 900, QEasingCurve.OutCubic))

        QTimer.singleShot(700, lambda: self._animate_attr(
            "_logo_scale", 0.0, 1.0, 600, QEasingCurve.OutBack))

        QTimer.singleShot(800, lambda: self._animate_attr(
            "_logo_glow", 0.0, 1.0, 400, QEasingCurve.OutExpo,
            on_end=lambda: self._animate_attr(
                "_logo_glow", 1.0, 0.35, 700, QEasingCurve.OutQuad)))

        QTimer.singleShot(1200, lambda: (
            self._animate_attr("_title_alpha",  0.0,  1.0,  500, QEasingCurve.OutCubic),
            self._animate_attr("_title_offset", 40.0, 0.0,  500, QEasingCurve.OutQuint),
        ))

        QTimer.singleShot(1650, lambda: (
            self._animate_attr("_sub_alpha",   0.0,  1.0,  500, QEasingCurve.OutCubic),
            self._animate_attr("_sub_offset",  30.0, 0.0,  500, QEasingCurve.OutQuint),
        ))

        QTimer.singleShot(2100, lambda: self._animate_attr(
            "_welcome_alpha", 0.0, 1.0, 500, QEasingCurve.OutCubic))

        QTimer.singleShot(2800, lambda: self._animate_attr(
            "_tagline_alpha", 0.0, 1.0, 250, QEasingCurve.Linear))

        QTimer.singleShot(3200, self._flash_and_finish)

    def _flash_and_finish(self):
        self._animate_attr("_flash_alpha", 0.0, 1.0, 180, QEasingCurve.InQuad,
                           on_end=self._emit_finished)

    def _emit_finished(self):
        self._paint_timer.stop()
        self.sequence_finished.emit()

    def _animate_attr(self, attr: str, start: float, end: float,
                      duration: int, curve, on_end=None):
        holder = _FloatHolder(self)
        holder.set_v(start)
        setattr(self, attr, start)

        anim = QPropertyAnimation(holder, b"value", self)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(duration)
        anim.setEasingCurve(curve)

        def _sync(v):
            setattr(self, attr, v)

        anim.valueChanged.connect(_sync)
        if on_end:
            anim.finished.connect(on_end)

        setattr(self, f"_anim_{attr}", anim)
        anim.start()

    # -----------------------------------------------------------------------
    # Paint
    # -----------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        painter.fillRect(0, 0, w, h, QColor(0, 0, 0))

        screen_a = int(self._screen_alpha * 255)
        if screen_a <= 0:
            return

        # Background radial vignette
        rg = QRadialGradient(cx, cy, max(w, h) * 0.65)
        rg.setColorAt(0.0, QColor(18, 6, 30, screen_a))
        rg.setColorAt(0.5, QColor(10, 4, 18, screen_a))
        rg.setColorAt(1.0, QColor(0, 0, 0, screen_a))
        painter.fillRect(0, 0, w, h, QBrush(rg))

        # Light rays
        if self._ray_progress > 0:
            self._draw_light_rays(painter, cx, cy, w, h)

        # Logo
        logo_center_y = cy - 60
        if self._logo_scale > 0:
            self._draw_logo(painter, cx, logo_center_y)

        # Title
        title_y = logo_center_y + 70
        if self._title_alpha > 0:
            self._draw_title(painter, cx, title_y + self._title_offset, self._title_alpha)

        # Subtitle
        sub_y = title_y + 58
        if self._sub_alpha > 0:
            self._draw_subtitle(painter, cx, sub_y + self._sub_offset, self._sub_alpha)

        # Welcome greeting
        welcome_y = sub_y + 52
        if self._welcome_alpha > 0:
            self._draw_welcome(painter, cx, welcome_y, self._welcome_alpha)

        # Tagline
        if self._tagline_alpha > 0:
            self._draw_tagline(painter, cx, h - 60, self._tagline_alpha)

        # Shimmer
        if self._title_alpha > 0.5 and self._shimmer_pos > -0.4:
            self._draw_shimmer(painter, cx, w, title_y - 20, 200)

        # White flash
        if self._flash_alpha > 0:
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255, int(self._flash_alpha * 255)))

    # -----------------------------------------------------------------------
    # Drawing helpers
    # -----------------------------------------------------------------------

    def _draw_light_rays(self, p: QPainter, cx, cy, w, h):
        p.save()
        p.translate(cx, cy)
        num_rays = 14
        for i in range(num_rays):
            angle_deg = (360.0 / num_rays) * i + self._tick * 0.12
            angle_rad = math.radians(angle_deg)
            length = max(w, h) * 0.85
            spread = math.radians(3.5 + (i % 3) * 1.2)

            ray_a = int(self._ray_progress * (30 + (i % 5) * 8))
            if ray_a <= 0:
                continue

            path = QPainterPath()
            path.moveTo(0, 0)
            path.lineTo(
                math.cos(angle_rad - spread) * length,
                math.sin(angle_rad - spread) * length
            )
            path.lineTo(
                math.cos(angle_rad + spread) * length,
                math.sin(angle_rad + spread) * length
            )
            path.closeSubpath()

            ray_grad = QLinearGradient(
                QPointF(0, 0),
                QPointF(math.cos(angle_rad) * length, math.sin(angle_rad) * length)
            )
            ray_grad.setColorAt(0.0, QColor(220 + (i % 3) * 12, (i % 5) * 10, 40 + (i % 4) * 15, ray_a))
            ray_grad.setColorAt(0.4, QColor(255, 80, 120, ray_a // 2))
            ray_grad.setColorAt(1.0, QColor(180, 20, 60, 0))
            p.fillPath(path, QBrush(ray_grad))

        p.restore()

    def _draw_logo(self, p: QPainter, cx, cy):
        scale = self._logo_scale
        size = int(120 * scale)
        if size < 2:
            return
        p.save()

        # Glow halo
        if self._logo_glow > 0:
            for rf in [1.8, 1.4, 1.1]:
                gr = QRadialGradient(cx, cy, size * rf)
                ga = int(self._logo_glow * 180 / (rf ** 2))
                gr.setColorAt(0.0, QColor(225, 29, 72, ga))
                gr.setColorAt(0.5, QColor(251, 113, 133, ga // 3))
                gr.setColorAt(1.0, QColor(225, 29, 72, 0))
                p.fillRect(
                    int(cx - size * rf), int(cy - size * rf),
                    int(size * rf * 2), int(size * rf * 2),
                    QBrush(gr)
                )

        # Badge circle
        badge_r = size // 2 + 4
        bg = QRadialGradient(cx, cy - size * 0.1, badge_r)
        bg.setColorAt(0.0, QColor(40, 10, 25))
        bg.setColorAt(1.0, QColor(10, 2, 8))
        badge_rect = QRectF(cx - badge_r, cy - badge_r, badge_r * 2, badge_r * 2)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor(225, 29, 72, 180), 2))
        p.drawEllipse(badge_rect)

        # Logo or fallback "J"
        if self._logo_px and not self._logo_px.isNull():
            logo_size = int(size * 0.7)
            scaled = self._logo_px.scaled(logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(int(cx - scaled.width() / 2), int(cy - scaled.height() / 2), scaled)
        else:
            font = QFont("Segoe UI", int(size * 0.45), QFont.Black)
            p.setFont(font)
            p.setPen(QColor(255, 255, 255, int(self._logo_scale * 255)))
            p.drawText(badge_rect, Qt.AlignCenter, "J")

        p.restore()

    def _draw_title(self, p: QPainter, cx, y, alpha):
        p.save()
        text = "Jayraldine's"
        font = QFont("Segoe UI", 52, QFont.Black)
        font.setLetterSpacing(QFont.AbsoluteSpacing, -1.5)
        p.setFont(font)
        fm = QFontMetricsF(font)
        tw = fm.horizontalAdvance(text)
        th = fm.height()

        path = QPainterPath()
        path.addText(cx - tw / 2, y + fm.ascent() - th / 2, font, text)

        grad = QLinearGradient(cx - tw / 2, y, cx + tw / 2, y)
        a = int(alpha * 255)
        grad.setColorAt(0.0,  QColor(255, 255, 255, a))
        grad.setColorAt(0.45, QColor(251, 207, 232, a))
        grad.setColorAt(0.7,  QColor(255, 255, 255, a))
        grad.setColorAt(1.0,  QColor(254, 164, 194, a))
        p.fillPath(path, QBrush(grad))
        p.restore()

    def _draw_subtitle(self, p: QPainter, cx, y, alpha):
        p.save()
        text = "CATERING & EVENT MANAGEMENT SYSTEM"
        font = QFont("Segoe UI", 13, QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 4.0)
        p.setFont(font)
        p.setPen(QColor(251, 113, 133, int(alpha * 230)))
        fm = QFontMetricsF(font)
        p.drawText(QPointF(cx - fm.horizontalAdvance(text) / 2, y), text)
        p.restore()

    def _draw_welcome(self, p: QPainter, cx, y, alpha):
        p.save()
        text = f"Welcome back, {self._user_name}"
        font = QFont("Segoe UI", 19, QFont.Normal)
        font.setItalic(True)
        p.setFont(font)
        fm = QFontMetricsF(font)
        p.setPen(QColor(203, 213, 225, int(alpha * 210)))
        p.drawText(QPointF(cx - fm.horizontalAdvance(text) / 2, y), text)
        p.restore()

    def _draw_tagline(self, p: QPainter, cx, y, alpha):
        p.save()
        flicker = 0.85 + 0.15 * math.sin(self._tick * 0.6)
        text = "   ENTERING SYSTEM"
        font = QFont("Segoe UI", 10, QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 3.0)
        p.setFont(font)
        fm = QFontMetricsF(font)
        p.setPen(QColor(56, 189, 248, int(alpha * flicker * 200)))
        p.drawText(QPointF(cx - fm.horizontalAdvance(text) / 2, y), text)
        p.restore()

    def _draw_shimmer(self, p: QPainter, cx, w, start_y, span_h):
        p.save()
        sx = cx + (self._shimmer_pos - 0.5) * w * 1.2
        shimmer_w = 120
        sg = QLinearGradient(sx - shimmer_w, 0, sx + shimmer_w, 0)
        sg.setColorAt(0.0, QColor(255, 255, 255, 0))
        sg.setColorAt(0.5, QColor(255, 255, 255, 22))
        sg.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(int(sx - shimmer_w), int(start_y), int(shimmer_w * 2), int(span_h), QBrush(sg))
        p.restore()


# ---------------------------------------------------------------------------
# Public wrapper
# ---------------------------------------------------------------------------

class CinematicWelcome(QWidget):
    """
    Full-screen frameless window shown after login.

    Usage in main.py::

        welcome = CinematicWelcome(user_name="Jay")
        welcome.finished.connect(lambda: window.showFullScreen())
        welcome.showFullScreen()
    """

    finished = Signal()

    def __init__(self, user_name: str = "Owner", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("background: #000000;")

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        else:
            self.resize(1280, 800)

        self._canvas = CinematicCanvas(user_name=user_name, parent=self)
        self._canvas.setGeometry(self.rect())
        self._canvas.sequence_finished.connect(self._on_finished)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._canvas.setGeometry(self.rect())

    def _on_finished(self):
        self.close()
        self.finished.emit()
