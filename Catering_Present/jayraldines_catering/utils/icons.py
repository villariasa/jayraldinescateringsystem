import os
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt, QSize
from PySide6.QtSvg import QSvgRenderer
from utils.paths import resource_path

_ICONS_DIR: str = ""


def _icons_dir() -> str:
    global _ICONS_DIR
    if not _ICONS_DIR:
        _ICONS_DIR = resource_path("assets", "icons", "svg")
    return _ICONS_DIR

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
    "edit":          "edit.svg",
    "x-circle":      "x-circle.svg",
}

DEFAULT_SIZE  = QSize(20, 20)
COLOR_MUTED   = "#9CA3AF"
COLOR_ACTIVE  = "#F9FAFB"
COLOR_PRIMARY = "#E11D48"
COLOR_DARK    = "#0B1220"
COLOR_GOLD    = "#F59E0B"

_SVG_RAW_CACHE: dict[str, str] = {}
_ICON_CACHE: dict[tuple, QIcon] = {}


def get_icon(name: str, color: str = COLOR_MUTED, size: QSize = DEFAULT_SIZE) -> QIcon:
    cache_key = (name, color, size.width(), size.height())
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    svg_file = ICON_MAP.get(name)
    if not svg_file:
        return QIcon()
    svg_path = os.path.join(_icons_dir(), svg_file)
    if not os.path.exists(svg_path):
        return QIcon()

    if svg_path not in _SVG_RAW_CACHE:
        with open(svg_path, "r", encoding="utf-8") as f:
            _SVG_RAW_CACHE[svg_path] = f.read()

    svg_data = _SVG_RAW_CACHE[svg_path].replace('stroke="currentColor"', f'stroke="{color}"')
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

    _ICON_CACHE[cache_key] = icon
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
