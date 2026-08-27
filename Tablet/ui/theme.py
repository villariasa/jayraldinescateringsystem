"""
Shared visual design system for the Tablet App — one place to tune colors,
spacing, and component styles instead of ad hoc inline styles scattered
across every screen.
"""

BG = "#0B1220"
CARD = "#141C2E"
CARD_ELEVATED = "#1A2438"
BORDER = "#263248"
BORDER_LIGHT = "#334155"
INPUT_BG = "#1A2438"

TEXT = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
TEXT_FAINT = "#64748B"

ACCENT = "#E11D48"
ACCENT_HOVER = "#F43F5E"
ACCENT_PRESS = "#BE123C"
GOLD = "#F59E0B"
GOLD_BG = "rgba(245, 158, 11, 0.12)"

SUCCESS = "#10B981"
SUCCESS_BG = "rgba(16, 185, 129, 0.12)"
WARNING = "#F59E0B"
DANGER = "#EF4444"
INFO = "#38BDF8"

RADIUS = 16
RADIUS_SM = 10

FONT_FAMILY = "'Segoe UI', 'Noto Sans', sans-serif"

GLOBAL_QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: {FONT_FAMILY};
    font-size: 14px;
    border: none;
}}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QMessageBox, QInputDialog, QFileDialog {{ background: {CARD}; }}
QLabel {{ color: {TEXT}; background: transparent; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {TEXT_FAINT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QTextBrowser {{
    font-size: 16px;
    padding: 12px 14px;
    border-radius: {RADIUS_SM}px;
    border: 1.5px solid {BORDER};
    background: {INPUT_BG};
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1.5px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox QAbstractItemView {{
    background: {CARD_ELEVATED}; color: {TEXT}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT}; padding: 4px;
}}
QDateEdit::drop-down, QTimeEdit::drop-down {{ border: none; width: 28px; }}
QCalendarWidget {{ background: {CARD_ELEVATED}; color: {TEXT}; }}
QCalendarWidget QToolButton {{ color: {TEXT}; background: transparent; }}
QCalendarWidget QAbstractItemView:enabled {{ background: {CARD}; color: {TEXT}; selection-background-color: {ACCENT}; }}

QRadioButton, QCheckBox {{
    color: {TEXT}; font-size: 15px; spacing: 10px; padding: 6px 2px;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 22px; height: 22px; border-radius: 6px; border: 2px solid {BORDER}; background: {INPUT_BG};
}}
QRadioButton::indicator {{ border-radius: 11px; }}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
    background: {ACCENT}; border: 2px solid {ACCENT};
}}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {{ border: 2px solid {ACCENT}; }}

QPushButton#Primary {{
    font-size: 16px; font-weight: 700; padding: 14px 24px; border-radius: {RADIUS_SM}px;
    background: {ACCENT}; color: white; border: none;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_PRESS}; }}
QPushButton#Primary:disabled {{ background: #334155; color: #64748B; }}

QPushButton#GoldPrimary {{
    font-size: 16px; font-weight: 800; padding: 15px 26px; border-radius: {RADIUS_SM}px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #D97706); color: #0F172A; border: none;
}}
QPushButton#GoldPrimary:hover {{ background: #FBBF24; }}
QPushButton#GoldPrimary:pressed {{ background: #B45309; }}

QPushButton#Secondary {{
    font-size: 15px; font-weight: 600; padding: 13px 22px; border-radius: {RADIUS_SM}px;
    background: {CARD_ELEVATED}; color: {TEXT}; border: 1.5px solid {BORDER};
}}
QPushButton#Secondary:hover {{ border: 1.5px solid {TEXT_FAINT}; background: #222F48; }}
QPushButton#Secondary:pressed {{ background: {BG}; }}

QPushButton#Ghost {{
    font-size: 13px; font-weight: 600; padding: 8px 14px; border-radius: 8px;
    background: transparent; color: {TEXT_MUTED}; border: 1px solid {BORDER};
}}
QPushButton#Ghost:hover {{ color: {TEXT}; border: 1px solid {TEXT_FAINT}; }}

QPushButton#Danger {{
    font-size: 13px; font-weight: 600; padding: 8px 14px; border-radius: 8px;
    background: transparent; color: {DANGER}; border: 1.5px solid {DANGER};
}}
QPushButton#Danger:hover {{ background: rgba(239,68,68,0.12); }}
"""

_card_counter = [0]


def card_frame_style(elevated: bool = False, accent_border: bool = False) -> str:
    bg = CARD_ELEVATED if elevated else CARD
    border = ACCENT if accent_border else BORDER
    return f"background: {bg}; border-radius: {RADIUS}px; border: 1px solid {border};"


def style_card(frame, elevated: bool = False, accent_border: bool = False) -> None:
    _card_counter[0] += 1
    name = f"ThemeCard{_card_counter[0]}"
    frame.setObjectName(name)
    bg = CARD_ELEVATED if elevated else CARD
    border = ACCENT if accent_border else BORDER
    frame.setStyleSheet(f"QFrame#{name} {{ background: {bg}; border-radius: {RADIUS}px; border: 1.5px solid {border}; }}")


def style_dish_card(frame, selected: bool = False) -> None:
    _card_counter[0] += 1
    name = f"DishCard{_card_counter[0]}"
    frame.setObjectName(name)
    if selected:
        bg = "#251824"
        border = ACCENT
    else:
        bg = CARD
        border = BORDER
    frame.setStyleSheet(
        f"QFrame#{name} {{ background: {bg}; border-radius: {RADIUS_SM}px; border: 2px solid {border}; }}"
    )


def heading_style(size: int = 22) -> str:
    return f"font-size: {size}px; font-weight: 800; color: {TEXT};"


def subtitle_style(size: int = 13) -> str:
    return f"font-size: {size}px; color: {TEXT_MUTED};"


def pill_style(color: str, bg_alpha: float = 0.12) -> str:
    return (
        f"font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 8px; "
        f"background: rgba(255,255,255,{bg_alpha}); color: {color}; border: 1px solid {color};"
    )


STATUS_COLORS = {"Paid": SUCCESS, "Partial": WARNING, "Unpaid": DANGER}


def create_fullscreen_icon(color: str = "#E2E8F0", size: int = 24) -> "QIcon":
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon
    from PySide6.QtCore import Qt
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
    painter.setPen(pen)

    c = 5
    m = 3
    s = size - m
    # Top-Left corner
    painter.drawLine(m, m + c, m, m)
    painter.drawLine(m, m, m + c, m)
    # Top-Right corner
    painter.drawLine(s - c, m, s, m)
    painter.drawLine(s, m, s, m + c)
    # Bottom-Left corner
    painter.drawLine(m, s - c, m, s)
    painter.drawLine(m, s, m + c, s)
    # Bottom-Right corner
    painter.drawLine(s - c, s, s, s)
    painter.drawLine(s, s - c, s, s)

    painter.end()
    return QIcon(pix)


def create_shield_icon(color: str = "#94A3B8", size: int = 24) -> "QIcon":
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon, QPainterPath
    from PySide6.QtCore import Qt
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)

    path = QPainterPath()
    path.moveTo(size * 0.5, size * 0.15)
    path.lineTo(size * 0.85, size * 0.28)
    path.quadTo(size * 0.85, size * 0.65, size * 0.5, size * 0.88)
    path.quadTo(size * 0.15, size * 0.65, size * 0.15, size * 0.28)
    path.closeSubpath()
    painter.drawPath(path)
    painter.end()
    return QIcon(pix)


def create_clock_icon(color: str = "#94A3B8", size: int = 24) -> "QIcon":
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon
    from PySide6.QtCore import Qt
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)

    m = size * 0.15
    s = size - 2 * m
    painter.drawEllipse(m, m, s, s)
    center = size * 0.5
    painter.drawLine(center, center, center, size * 0.3)
    painter.drawLine(center, center, size * 0.68, center)
    painter.end()
    return QIcon(pix)


def create_sync_icon(color: str = "#10B981", size: int = 24) -> "QIcon":
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon, QPainterPath
    from PySide6.QtCore import Qt
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)

    # Top arc
    path1 = QPainterPath()
    path1.arcMoveTo(size * 0.18, size * 0.18, size * 0.64, size * 0.64, 45)
    path1.arcTo(size * 0.18, size * 0.18, size * 0.64, size * 0.64, 45, 120)
    painter.drawPath(path1)
    # Top arrow
    painter.drawLine(size * 0.72, size * 0.28, size * 0.78, size * 0.40)
    painter.drawLine(size * 0.72, size * 0.28, size * 0.58, size * 0.32)

    # Bottom arc
    path2 = QPainterPath()
    path2.arcMoveTo(size * 0.18, size * 0.18, size * 0.64, size * 0.64, 225)
    path2.arcTo(size * 0.18, size * 0.18, size * 0.64, size * 0.64, 225, 120)
    painter.drawPath(path2)
    # Bottom arrow
    painter.drawLine(size * 0.28, size * 0.72, size * 0.22, size * 0.60)
    painter.drawLine(size * 0.28, size * 0.72, size * 0.42, size * 0.68)

    painter.end()
    return QIcon(pix)


def create_chevron_right_icon(color: str = "#64748B", size: int = 20) -> "QIcon":
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon
    from PySide6.QtCore import Qt
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)

    painter.drawLine(size * 0.38, size * 0.25, size * 0.62, size * 0.5)
    painter.drawLine(size * 0.62, size * 0.5, size * 0.38, size * 0.75)
    painter.end()
    return QIcon(pix)



