import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from utils.paths import resource_path

_BRAND_ACCENT = "#E11D48"
_BRAND_ACCENT_MID = "#BE123C"    # secondary gradient/hover stop, baked into the QSS
_BRAND_ACCENT_DARK = "#9F1239"   # darkest gradient stop, baked into the QSS


class ThemeManager(QObject):
    theme_changed = Signal(str)

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
        self._current = "dark"
        self._initialized = True

    @property
    def current(self) -> str:
        return self._current

    def is_dark(self) -> bool:
        return self._current == "dark"

    def apply(self, theme: str = None):
        if theme:
            self._current = theme
        path = resource_path("styles", "main.qss") if self._current == "dark" else resource_path("styles", "light.qss")
        app = QApplication.instance()
        if app and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
            qss = self._with_accent(qss)
            app.setStyleSheet(qss)
        self.theme_changed.emit(self._current)

    @staticmethod
    def _with_accent(qss: str) -> str:
        """Swap the baked-in brand accent literals for the user's chosen color."""
        from utils.accent import AccentManager
        accent = AccentManager()
        accent_hex = accent.current
        if accent_hex == _BRAND_ACCENT:
            return qss
        qss = qss.replace(_BRAND_ACCENT, accent_hex)
        qss = qss.replace(_BRAND_ACCENT_MID, accent.darker(accent_hex, 110))
        qss = qss.replace(_BRAND_ACCENT_DARK, accent.darker(accent_hex, 145))
        return qss

    def toggle(self):
        self._current = "light" if self._current == "dark" else "dark"
        self.apply()
        return self._current
