"""
AccentManager — the app's single accent/brand color, swappable at runtime.

The color is substituted into the loaded QSS text by ThemeManager.apply(),
pushed into utils.icons.COLOR_PRIMARY (icons and the mascot read that module
attribute fresh on every use, so no signal is needed for them to pick it up —
only a repaint/redraw trigger), and persisted locally via QSettings since it's
a per-machine display preference, not shared business data.
"""
import re

from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtGui import QColor

PRESET_THEMES = [
    ("Rose",    "#E11D48"),   # default — matches the app's original brand color
    ("Crimson", "#DC2626"),
    ("Orange",  "#EA580C"),
    ("Amber",   "#D97706"),
    ("Emerald", "#059669"),
    ("Teal",    "#0D9488"),
    ("Sky",     "#0284C7"),
    ("Indigo",  "#4F46E5"),
    ("Violet",  "#7C3AED"),
    ("Pink",    "#DB2777"),
]

_DEFAULT_ACCENT = PRESET_THEMES[0][1]
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

_ORG, _APP = "Jayraldines", "CateringSystem"
_KEY_ACCENT = "appearance/accent_color"
_KEY_CUSTOM = "appearance/custom_colors"


def is_valid_hex(hex_color: str) -> bool:
    return bool(_HEX_RE.match((hex_color or "").strip()))


class AccentManager(QObject):
    accent_changed = Signal(str)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        settings = QSettings(_ORG, _APP)
        saved = settings.value(_KEY_ACCENT, _DEFAULT_ACCENT)
        self._current = saved if is_valid_hex(saved) else _DEFAULT_ACCENT
        custom = settings.value(_KEY_CUSTOM, [])
        self._custom_colors = [c for c in (custom or []) if is_valid_hex(c)]
        self._initialized = True
        self._push_to_icons()

    @property
    def current(self) -> str:
        return self._current

    @property
    def custom_colors(self) -> list:
        return list(self._custom_colors)

    def _push_to_icons(self):
        import utils.icons as icons
        icons.COLOR_PRIMARY = self._current

    def darker(self, hex_color: str = None, factor: int = 130) -> str:
        return QColor(hex_color or self._current).darker(factor).name()

    def set_accent(self, hex_color: str):
        hex_color = (hex_color or "").strip()
        if not is_valid_hex(hex_color) or hex_color == self._current:
            return
        self._current = hex_color
        self._push_to_icons()
        QSettings(_ORG, _APP).setValue(_KEY_ACCENT, hex_color)
        self.accent_changed.emit(hex_color)

        from utils.theme import ThemeManager
        ThemeManager().apply()

    def add_custom_color(self, hex_color: str):
        hex_color = (hex_color or "").strip().upper()
        if not is_valid_hex(hex_color) or hex_color in self._custom_colors:
            return
        self._custom_colors.append(hex_color)
        QSettings(_ORG, _APP).setValue(_KEY_CUSTOM, self._custom_colors)

    def remove_custom_color(self, hex_color: str):
        hex_color = (hex_color or "").strip().upper()
        if hex_color not in self._custom_colors:
            return
        self._custom_colors.remove(hex_color)
        QSettings(_ORG, _APP).setValue(_KEY_CUSTOM, self._custom_colors)
