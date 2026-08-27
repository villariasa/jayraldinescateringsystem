"""
Standard Modern Vector Icon Generator for the Tablet Application.
Replaces keyboard emojis with pixel-perfect modern Lucide/Feather vector SVG paths.
"""
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon, QPainterPath, QBrush
from PySide6.QtCore import Qt, QRectF, QPointF


def _create_canvas(size: int = 24) -> tuple[QPixmap, QPainter, QPen]:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    pen = QPen(QColor("#94A3B8"), max(1.8, size / 12.0), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    return pix, painter, pen


def icon_user(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    # Head
    painter.drawEllipse(QRectF(s * 0.32, s * 0.12, s * 0.36, s * 0.36))
    # Body
    body_path = QPainterPath()
    body_path.moveTo(s * 0.18, s * 0.88)
    body_path.quadTo(s * 0.22, s * 0.60, s * 0.50, s * 0.60)
    body_path.quadTo(s * 0.78, s * 0.60, s * 0.82, s * 0.88)
    painter.drawPath(body_path)
    painter.end()
    return QIcon(pix)


def icon_user_plus(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    # Head
    painter.drawEllipse(QRectF(s * 0.22, s * 0.14, s * 0.34, s * 0.34))
    # Body
    body = QPainterPath()
    body.moveTo(s * 0.10, s * 0.86)
    body.quadTo(s * 0.14, s * 0.62, s * 0.39, s * 0.62)
    body.quadTo(s * 0.64, s * 0.62, s * 0.68, s * 0.86)
    painter.drawPath(body)
    # Plus sign
    painter.drawLine(s * 0.75, s * 0.32, s * 0.75, s * 0.52)
    painter.drawLine(s * 0.65, s * 0.42, s * 0.85, s * 0.42)
    painter.end()
    return QIcon(pix)


def icon_search(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawEllipse(QRectF(s * 0.16, s * 0.16, s * 0.50, s * 0.50))
    painter.drawLine(s * 0.54, s * 0.54, s * 0.84, s * 0.84)
    painter.end()
    return QIcon(pix)


def icon_phone(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    p = QPainterPath()
    p.moveTo(s * 0.22, s * 0.30)
    p.quadTo(s * 0.22, s * 0.78, s * 0.70, s * 0.78)
    p.lineTo(s * 0.80, s * 0.66)
    p.lineTo(s * 0.66, s * 0.56)
    p.lineTo(s * 0.58, s * 0.62)
    p.quadTo(s * 0.42, s * 0.46, s * 0.38, s * 0.42)
    p.lineTo(s * 0.44, s * 0.34)
    p.lineTo(s * 0.34, s * 0.20)
    p.closeSubpath()
    painter.drawPath(p)
    painter.end()
    return QIcon(pix)


def icon_mail(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawRoundedRect(QRectF(s * 0.14, s * 0.24, s * 0.72, s * 0.52), 4, 4)
    p = QPainterPath()
    p.moveTo(s * 0.16, s * 0.26)
    p.lineTo(s * 0.50, s * 0.52)
    p.lineTo(s * 0.84, s * 0.26)
    painter.drawPath(p)
    painter.end()
    return QIcon(pix)


def icon_map_pin(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    p = QPainterPath()
    p.moveTo(s * 0.50, s * 0.88)
    p.quadTo(s * 0.18, s * 0.52, s * 0.18, s * 0.36)
    p.arcTo(QRectF(s * 0.18, s * 0.14, s * 0.64, s * 0.64), 180, -180)
    p.quadTo(s * 0.82, s * 0.52, s * 0.50, s * 0.88)
    painter.drawPath(p)
    painter.drawEllipse(QRectF(s * 0.38, s * 0.32, s * 0.24, s * 0.24))
    painter.end()
    return QIcon(pix)


def icon_calendar(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawRoundedRect(QRectF(s * 0.15, s * 0.22, s * 0.70, s * 0.64), 4, 4)
    painter.drawLine(s * 0.15, s * 0.40, s * 0.85, s * 0.40)
    painter.drawLine(s * 0.32, s * 0.12, s * 0.32, s * 0.26)
    painter.drawLine(s * 0.68, s * 0.12, s * 0.68, s * 0.26)
    painter.end()
    return QIcon(pix)


def icon_clock(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    m = s * 0.15
    painter.drawEllipse(QRectF(m, m, s - 2 * m, s - 2 * m))
    painter.drawLine(s * 0.5, s * 0.5, s * 0.5, s * 0.30)
    painter.drawLine(s * 0.5, s * 0.5, s * 0.68, s * 0.50)
    painter.end()
    return QIcon(pix)


def icon_users(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    # Primary user
    painter.drawEllipse(QRectF(s * 0.26, s * 0.16, s * 0.30, s * 0.30))
    p1 = QPainterPath()
    p1.moveTo(s * 0.14, s * 0.84)
    p1.quadTo(s * 0.18, s * 0.60, s * 0.41, s * 0.60)
    p1.quadTo(s * 0.64, s * 0.60, s * 0.68, s * 0.84)
    painter.drawPath(p1)
    # Secondary user outline
    painter.drawArc(QRectF(s * 0.52, s * 0.22, s * 0.24, s * 0.24), 270 * 16, 180 * 16)
    p2 = QPainterPath()
    p2.moveTo(s * 0.66, s * 0.62)
    p2.quadTo(s * 0.82, s * 0.64, s * 0.86, s * 0.84)
    painter.drawPath(p2)
    painter.end()
    return QIcon(pix)


def icon_package(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    p = QPainterPath()
    p.moveTo(s * 0.50, s * 0.16)
    p.lineTo(s * 0.84, s * 0.34)
    p.lineTo(s * 0.84, s * 0.68)
    p.lineTo(s * 0.50, s * 0.86)
    p.lineTo(s * 0.16, s * 0.68)
    p.lineTo(s * 0.16, s * 0.34)
    p.closeSubpath()
    painter.drawPath(p)
    painter.drawLine(s * 0.50, s * 0.50, s * 0.50, s * 0.86)
    painter.drawLine(s * 0.50, s * 0.50, s * 0.84, s * 0.34)
    painter.drawLine(s * 0.50, s * 0.50, s * 0.16, s * 0.34)
    painter.end()
    return QIcon(pix)


def icon_utensils(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    # Fork
    painter.drawLine(s * 0.30, s * 0.18, s * 0.30, s * 0.84)
    painter.drawLine(s * 0.20, s * 0.18, s * 0.20, s * 0.40)
    painter.drawLine(s * 0.40, s * 0.18, s * 0.40, s * 0.40)
    painter.drawLine(s * 0.20, s * 0.40, s * 0.40, s * 0.40)
    # Knife
    kp = QPainterPath()
    kp.moveTo(s * 0.70, s * 0.18)
    kp.quadTo(s * 0.84, s * 0.30, s * 0.70, s * 0.52)
    kp.lineTo(s * 0.70, s * 0.84)
    painter.drawPath(kp)
    painter.end()
    return QIcon(pix)


def icon_sparkles(color: str = "#F59E0B", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    p = QPainterPath()
    # Large sparkle
    p.moveTo(s * 0.48, s * 0.16)
    p.quadTo(s * 0.48, s * 0.46, s * 0.18, s * 0.46)
    p.quadTo(s * 0.48, s * 0.46, s * 0.48, s * 0.76)
    p.quadTo(s * 0.48, s * 0.46, s * 0.78, s * 0.46)
    p.quadTo(s * 0.48, s * 0.46, s * 0.48, s * 0.16)
    painter.drawPath(p)
    # Small sparkle
    p2 = QPainterPath()
    p2.moveTo(s * 0.74, s * 0.60)
    p2.quadTo(s * 0.74, s * 0.74, s * 0.60, s * 0.74)
    p2.quadTo(s * 0.74, s * 0.74, s * 0.74, s * 0.88)
    p2.quadTo(s * 0.74, s * 0.74, s * 0.88, s * 0.74)
    p2.quadTo(s * 0.74, s * 0.74, s * 0.74, s * 0.60)
    painter.drawPath(p2)
    painter.end()
    return QIcon(pix)


def icon_credit_card(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawRoundedRect(QRectF(s * 0.14, s * 0.22, s * 0.72, s * 0.56), 4, 4)
    painter.drawLine(s * 0.14, s * 0.40, s * 0.86, s * 0.40)
    painter.drawLine(s * 0.26, s * 0.60, s * 0.44, s * 0.60)
    painter.end()
    return QIcon(pix)


def icon_clipboard_check(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawRoundedRect(QRectF(s * 0.20, s * 0.22, s * 0.60, s * 0.66), 4, 4)
    painter.drawRoundedRect(QRectF(s * 0.36, s * 0.14, s * 0.28, s * 0.14), 2, 2)
    # Checkmark inside
    p = QPainterPath()
    p.moveTo(s * 0.34, s * 0.54)
    p.lineTo(s * 0.46, s * 0.66)
    p.lineTo(s * 0.66, s * 0.44)
    painter.drawPath(p)
    painter.end()
    return QIcon(pix)


def icon_check(color: str = "#10B981", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    p = QPainterPath()
    p.moveTo(s * 0.22, s * 0.52)
    p.lineTo(s * 0.44, s * 0.74)
    p.lineTo(s * 0.80, s * 0.30)
    painter.drawPath(p)
    painter.end()
    return QIcon(pix)


def icon_x(color: str = "#EF4444", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawLine(s * 0.26, s * 0.26, s * 0.74, s * 0.74)
    painter.drawLine(s * 0.74, s * 0.26, s * 0.26, s * 0.74)
    painter.end()
    return QIcon(pix)


def icon_plus(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawLine(s * 0.50, s * 0.22, s * 0.50, s * 0.78)
    painter.drawLine(s * 0.22, s * 0.50, s * 0.78, s * 0.50)
    painter.end()
    return QIcon(pix)


def icon_sync(color: str = "#10B981", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    p1 = QPainterPath()
    p1.arcMoveTo(s * 0.18, s * 0.18, s * 0.64, s * 0.64, 45)
    p1.arcTo(s * 0.18, s * 0.18, s * 0.64, s * 0.64, 45, 120)
    painter.drawPath(p1)
    painter.drawLine(s * 0.72, s * 0.28, s * 0.78, s * 0.40)
    painter.drawLine(s * 0.72, s * 0.28, s * 0.58, s * 0.32)

    p2 = QPainterPath()
    p2.arcMoveTo(s * 0.18, s * 0.18, s * 0.64, s * 0.64, 225)
    p2.arcTo(s * 0.18, s * 0.18, s * 0.64, s * 0.64, 225, 120)
    painter.drawPath(p2)
    painter.drawLine(s * 0.28, s * 0.72, s * 0.22, s * 0.60)
    painter.drawLine(s * 0.28, s * 0.72, s * 0.42, s * 0.68)
    painter.end()
    return QIcon(pix)


def icon_download(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawLine(s * 0.50, s * 0.20, s * 0.50, s * 0.66)
    painter.drawLine(s * 0.32, s * 0.48, s * 0.50, s * 0.66)
    painter.drawLine(s * 0.68, s * 0.48, s * 0.50, s * 0.66)
    painter.drawLine(s * 0.20, s * 0.82, s * 0.80, s * 0.82)
    painter.end()
    return QIcon(pix)


def icon_upload(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawLine(s * 0.50, s * 0.66, s * 0.50, s * 0.20)
    painter.drawLine(s * 0.32, s * 0.38, s * 0.50, s * 0.20)
    painter.drawLine(s * 0.68, s * 0.38, s * 0.50, s * 0.20)
    painter.drawLine(s * 0.20, s * 0.82, s * 0.80, s * 0.82)
    painter.end()
    return QIcon(pix)


def icon_edit(color: str = "#94A3B8", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    p = QPainterPath()
    p.moveTo(s * 0.68, s * 0.18)
    p.lineTo(s * 0.82, s * 0.32)
    p.lineTo(s * 0.38, s * 0.76)
    p.lineTo(s * 0.20, s * 0.80)
    p.lineTo(s * 0.24, s * 0.62)
    p.closeSubpath()
    painter.drawPath(p)
    painter.end()
    return QIcon(pix)


def icon_trash(color: str = "#EF4444", size: int = 24) -> QIcon:
    pix, painter, pen = _create_canvas(size)
    pen.setColor(QColor(color))
    painter.setPen(pen)

    s = float(size)
    painter.drawLine(s * 0.18, s * 0.30, s * 0.82, s * 0.30)
    painter.drawRoundedRect(QRectF(s * 0.26, s * 0.30, s * 0.48, s * 0.56), 2, 2)
    painter.drawLine(s * 0.38, s * 0.18, s * 0.62, s * 0.18)
    painter.drawLine(s * 0.40, s * 0.44, s * 0.40, s * 0.72)
    painter.drawLine(s * 0.60, s * 0.44, s * 0.60, s * 0.72)
    painter.end()
    return QIcon(pix)
