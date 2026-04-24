import os
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt, QSize
from PySide6.QtSvg import QSvgRenderer

_ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons", "svg")

ICON_MAP = {
    "dashboard":     "dashboard.svg",
    "orders":        "orders.svg",
    "customers":     "customers.svg",
    "menu":          "menu.svg",
    "inventory":     "inventory.svg",
    "kitchen":       "kitchen.svg",
    "billing":       "billing.svg",
    "reports":       "reports.svg",
    "settings":      "settings.svg",
    "bookings":      "bookings.svg",
    "calendar":      "calendar.svg",
    "plus":          "plus.svg",
    "export":        "export.svg",
    "filter":        "filter.svg",
    "trash":         "trash.svg",
    "check":         "check.svg",
    "chevron-left":  "chevron-left.svg",
    "chevron-right": "chevron-right.svg",
    "close":         "close.svg",
    "log-out":       "log-out.svg",
    "date-range":    "date-range.svg",
    "reset-zoom":    "reset-zoom.svg",
    "eye":           "eye.svg",
    "bell":          "bell.svg",
    "search":        "search.svg",
    "user":          "user.svg",
    "menu-collapse": "menu-collapse.svg",
    "trending-up":   "trending-up.svg",
}

DEFAULT_SIZE  = QSize(20, 20)
COLOR_MUTED   = "#9CA3AF"
COLOR_ACTIVE  = "#F9FAFB"
COLOR_PRIMARY = "#E11D48"
COLOR_DARK    = "#0B1220"
COLOR_GOLD    = "#F59E0B"


def get_icon(name: str, color: str = COLOR_MUTED, size: QSize = DEFAULT_SIZE) -> QIcon:
    svg_file = ICON_MAP.get(name)
    if not svg_file:
        return QIcon()
    svg_path = os.path.join(_ICONS_DIR, svg_file)
    if not os.path.exists(svg_path):
        return QIcon()

    with open(svg_path, "r", encoding="utf-8") as f:
        svg_data = f.read()

    svg_data = svg_data.replace('stroke="currentColor"', f'stroke="{color}"')
    svg_bytes = svg_data.encode("utf-8")

    icon = QIcon()
    for scale in (1, 2):
        px = QPixmap(QSize(size.width() * scale, size.height() * scale))
        px.fill(Qt.transparent)
        painter = QPainter(px)
        painter.setRenderHint(QPainter.Antialiasing)
        QSvgRenderer(svg_bytes).render(painter)
        painter.end()
        px.setDevicePixelRatio(scale)
        icon.addPixmap(px, QIcon.Normal)

    return icon


def nav_icon(name: str) -> QIcon:
    return get_icon(name, color=COLOR_MUTED, size=QSize(18, 18))


def nav_icon_active(name: str) -> QIcon:
    return get_icon(name, color=COLOR_ACTIVE, size=QSize(18, 18))


def btn_icon_primary(name: str) -> QIcon:
    return get_icon(name, color=COLOR_DARK, size=QSize(15, 15))


def btn_icon_secondary(name: str) -> QIcon:
    return get_icon(name, color=COLOR_ACTIVE, size=QSize(15, 15))


def btn_icon_muted(name: str) -> QIcon:
    return get_icon(name, color=COLOR_MUTED, size=QSize(15, 15))


def btn_icon_red(name: str) -> QIcon:
    return get_icon(name, color=COLOR_PRIMARY, size=QSize(15, 15))


def icon_sm(name: str, color: str = COLOR_MUTED) -> QIcon:
    return get_icon(name, color=color, size=QSize(14, 14))
