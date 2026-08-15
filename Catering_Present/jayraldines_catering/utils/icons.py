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

_BUILTIN_SVGS = {
    "minimize": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "maximize": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>',
    "restore": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="9" width="13" height="12" rx="2"/><path d="M17 9V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h2"/></svg>',
    "fullscreen": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>',
    "close": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
}


def get_icon(name: str, color: str = COLOR_MUTED, size: QSize = DEFAULT_SIZE) -> QIcon:
    cache_key = (name, color, size.width(), size.height())
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    svg_data = None
    if name in _BUILTIN_SVGS:
        svg_data = _BUILTIN_SVGS[name]
    else:
        svg_file = ICON_MAP.get(name)
        if svg_file:
            svg_path = os.path.join(_icons_dir(), svg_file)
            if os.path.exists(svg_path):
                if svg_path not in _SVG_RAW_CACHE:
                    with open(svg_path, "r", encoding="utf-8") as f:
                        _SVG_RAW_CACHE[svg_path] = f.read()
                svg_data = _SVG_RAW_CACHE[svg_path]

    if not svg_data:
        return QIcon()

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

    _ICON_CACHE[cache_key] = icon
    return icon


def nav_icon(name: str) -> QIcon:
    return get_icon(name, color=COLOR_MUTED, size=QSize(18, 18))


def nav_icon_active(name: str) -> QIcon:
    return get_icon(name, color=COLOR_ACTIVE, size=QSize(18, 18))


def btn_icon_primary(name: str) -> QIcon:
    return get_icon(name, color="#FFFFFF", size=QSize(15, 15))


def btn_icon_secondary(name: str) -> QIcon:
    return get_icon(name, color=COLOR_ACTIVE, size=QSize(15, 15))


def btn_icon_muted(name: str) -> QIcon:
    return get_icon(name, color=COLOR_MUTED, size=QSize(15, 15))


def btn_icon_red(name: str) -> QIcon:
    return get_icon(name, color=COLOR_PRIMARY, size=QSize(15, 15))


def icon_sm(name: str, color: str = COLOR_MUTED) -> QIcon:
    return get_icon(name, color=color, size=QSize(14, 14))
