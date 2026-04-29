import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from utils.paths import resource_path

_DARK_QSS  = resource_path("styles", "main.qss")
_LIGHT_QSS = resource_path("styles", "light.qss")


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
        path = _DARK_QSS if self._current == "dark" else _LIGHT_QSS
        app = QApplication.instance()
        if app and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        self.theme_changed.emit(self._current)

    def toggle(self):
        self._current = "light" if self._current == "dark" else "dark"
        self.apply()
        return self._current
