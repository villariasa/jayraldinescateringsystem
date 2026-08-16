import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, QSettings
from utils.paths import resource_path
from utils.palette import get_palette, THEME_PALETTES

_BRAND_ACCENT = "#E11D48"
_BRAND_ACCENT_MID = "#BE123C"
_BRAND_ACCENT_DARK = "#9F1239"

_ORG, _APP = "Jayraldines", "CateringSystem"
_KEY_THEME_PALETTE = "appearance/active_palette"


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
        settings = QSettings(_ORG, _APP)
        saved_palette = settings.value(_KEY_THEME_PALETTE, "dark_mode")
        if saved_palette not in THEME_PALETTES:
            saved_palette = "dark_mode"
        self._palette_id = saved_palette
        self._palette = get_palette(self._palette_id)
        self._current = self._palette.get("mode", "dark")
        self._initialized = True

    @property
    def current(self) -> str:
        return self._current

    @property
    def palette_id(self) -> str:
        return self._palette_id

    @property
    def palette(self) -> dict:
        return self._palette

    def is_dark(self) -> bool:
        return self._current == "dark"

    def apply_palette(self, palette_id: str):
        if palette_id in THEME_PALETTES:
            self._palette_id = palette_id
            self._palette = get_palette(palette_id)
            self._current = self._palette.get("mode", "dark")
            QSettings(_ORG, _APP).setValue(_KEY_THEME_PALETTE, palette_id)

            # Sync primary accent
            from utils.accent import AccentManager
            AccentManager().set_accent_silent(self._palette["primary"])

        self.apply()

    def apply(self, theme: str = None):
        if theme:
            if theme in ("dark", "light"):
                self._current = theme
                self._palette_id = "dark_mode" if theme == "dark" else "light_mode"
                self._palette = get_palette(self._palette_id)
            elif theme in THEME_PALETTES:
                self._palette_id = theme
                self._palette = get_palette(theme)
                self._current = self._palette.get("mode", "dark")

        path = resource_path("styles", "main.qss") if self._current == "dark" else resource_path("styles", "light.qss")
        app = QApplication.instance()
        if app and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
            qss = self._apply_palette_substitutions(qss)
            app.setStyleSheet(qss)
        self.theme_changed.emit(self._current)

    def _apply_palette_substitutions(self, qss: str) -> str:
        pal = self._palette
        from utils.accent import AccentManager
        accent_hex = AccentManager().current or pal.get("primary", _BRAND_ACCENT)

        # Base token replacements for dark/light templates
        if self._current == "dark":
            # Dark base tokens
            qss = qss.replace("#0F172A", pal.get("background", "#0F172A"))
            qss = qss.replace("#1E293B", pal.get("surface", "#1E293B"))
            qss = qss.replace("#111827", pal.get("sidebar_bg", "#111827"))
            qss = qss.replace("#243244", pal.get("surface_hover", "#243244"))
            qss = qss.replace("#334155", pal.get("border", "#334155"))
            qss = qss.replace("#F8FAFC", pal.get("text_primary", "#F8FAFC"))
            qss = qss.replace("#94A3B8", pal.get("text_secondary", "#94A3B8"))
        else:
            # Light base tokens (smooth eye-friendly neutral tones)
            qss = qss.replace("#F8FAFC", pal.get("background", "#F1F5F9"))
            qss = qss.replace("#F1F5F9", pal.get("background", "#F1F5F9"))
            qss = qss.replace("#FFFFFF", pal.get("surface", "#FFFFFF"))
            qss = qss.replace("#E2E8F0", pal.get("border", "#E2E8F0"))
            qss = qss.replace("#0F172A", pal.get("text_primary", "#0F172A"))
            qss = qss.replace("#64748B", pal.get("text_secondary", "#64748B"))

        # Accent replacements
        qss = qss.replace(_BRAND_ACCENT, accent_hex)
        qss = qss.replace(_BRAND_ACCENT_MID, pal.get("primary_hover", AccentManager().darker(accent_hex, 110)))
        qss = qss.replace(_BRAND_ACCENT_DARK, AccentManager().darker(accent_hex, 145))
        return qss

    def toggle(self):
        new_mode = "light" if self._current == "dark" else "dark"
        self._palette_id = "light_mode" if new_mode == "light" else "dark_mode"
        self.apply_palette(self._palette_id)
        return self._current
