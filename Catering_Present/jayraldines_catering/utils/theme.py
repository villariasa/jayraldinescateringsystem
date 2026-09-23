"""Application theming: loads QSS stylesheets and swaps palette color tokens.

ThemeManager is a singleton that owns the active palette (dark/light or a named
theme palette), persists the choice via QSettings, and re-applies the compiled
stylesheet to every visible top-level window. Raw QSS templates are cached in
memory and their placeholder hex tokens are substituted with the live palette's
colors so a single template can render any palette without touching disk again.
"""
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, QSettings, QTimer
from utils.paths import resource_path
from utils.palette import get_palette, THEME_PALETTES

# Default brand accent tokens used as placeholders inside the QSS templates;
# these get replaced by the active palette's accent (and derived shades).
_BRAND_ACCENT = "#E11D48"
_BRAND_ACCENT_MID = "#BE123C"
_BRAND_ACCENT_DARK = "#9F1239"

# QSettings org/app identifiers and the key under which the palette is stored.
_ORG, _APP = "Jayraldines", "CateringSystem"
_KEY_THEME_PALETTE = "appearance/active_palette"

# In-memory template cache to eliminate repeated disk I/O on theme switches
_QSS_TEMPLATES = {}


class ThemeManager(QObject):
    """Singleton that manages the active theme palette and applied stylesheet.

    Emits theme_changing before the stylesheet swap (so overlays can render)
    and theme_changed after. Use the module-level singleton via ThemeManager().
    """
    theme_changing = Signal(str)  # emitted with the target palette id pre-swap
    theme_changed = Signal(str)   # emitted with the mode ("dark"/"light") post-swap

    _instance = None

    def __new__(cls):
        # Enforce a single shared instance across the whole application.
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # __init__ runs on every ThemeManager() call; guard so the singleton is
        # only really initialized once.
        if self._initialized:
            return
        super().__init__()
        # Restore the previously saved palette, defaulting to dark mode.
        settings = QSettings(_ORG, _APP)
        saved_palette = settings.value(_KEY_THEME_PALETTE, "dark_mode")
        # Guard against stale/invalid stored ids from older app versions.
        if saved_palette not in THEME_PALETTES:
            saved_palette = "dark_mode"
        self._palette_id = saved_palette
        self._palette = get_palette(self._palette_id)
        self._current = self._palette.get("mode", "dark")
        self._initialized = True

    @property
    def current(self) -> str:
        """Active mode string: "dark" or "light"."""
        return self._current

    @property
    def palette_id(self) -> str:
        """Identifier of the active palette (e.g. "dark_mode")."""
        return self._palette_id

    @property
    def palette(self) -> dict:
        """The active palette's color dict."""
        return self._palette

    def is_dark(self) -> bool:
        """True when the active mode is dark."""
        return self._current == "dark"

    def apply_palette(self, palette_id: str):
        """Switch to the named palette, persist it, and re-apply the stylesheet."""
        if palette_id in THEME_PALETTES:
            self._palette_id = palette_id
            self._palette = get_palette(palette_id)
            self._current = self._palette.get("mode", "dark")
            QSettings(_ORG, _APP).setValue(_KEY_THEME_PALETTE, palette_id)

            # Keep the accent manager in step with the palette's primary color;
            # "silent" avoids emitting its own change signal (apply() re-renders).
            from utils.accent import AccentManager
            AccentManager().set_accent_silent(self._palette["primary"])

        self.apply()

    def apply(self, theme: str = None):
        """Compile and apply the active (or given) theme to all visible windows.

        `theme` may be "dark"/"light" or a named palette id; when omitted the
        currently stored palette is re-applied. Emits theme_changing then
        theme_changed around the stylesheet swap.
        """
        if theme:
            # Resolve either a simple mode or an explicit palette id.
            if theme in ("dark", "light"):
                self._current = theme
                self._palette_id = "dark_mode" if theme == "dark" else "light_mode"
                self._palette = get_palette(self._palette_id)
            elif theme in THEME_PALETTES:
                self._palette_id = theme
                self._palette = get_palette(theme)
                self._current = self._palette.get("mode", "dark")

        # Notify listeners immediately so loading overlays render instantly
        target_palette_id = self._palette_id or ("dark_mode" if self._current == "dark" else "light_mode")
        self.theme_changing.emit(target_palette_id)

        app = QApplication.instance()
        if not app:
            # No running app (e.g. during early init/tests): just signal state.
            self.theme_changed.emit(self._current)
            return

        # Force initial paint of loading overlay
        app.processEvents()

        # Freeze repaints on visible windows while the stylesheet is swapped to
        # avoid flicker and partial-restyle artifacts; re-enabled in finally.
        top_windows = [w for w in app.topLevelWidgets() if w.isVisible()]
        for w in top_windows:
            try:
                w.setUpdatesEnabled(False)
            except Exception:
                pass  # window may be mid-destruction

        try:
            # Templates are keyed by mode; read from disk once then cache.
            tmpl_key = self._current
            if tmpl_key not in _QSS_TEMPLATES:
                path = resource_path("styles", "main.qss") if self._current == "dark" else resource_path("styles", "light.qss")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        _QSS_TEMPLATES[tmpl_key] = f.read()
                else:
                    # Cache the empty result too, so we don't retry disk each time.
                    _QSS_TEMPLATES[tmpl_key] = ""

            raw_qss = _QSS_TEMPLATES.get(tmpl_key, "")
            if raw_qss:
                # Replace palette placeholder tokens before applying.
                qss = self._apply_palette_substitutions(raw_qss)
                app.setStyleSheet(qss)
        finally:
            # Always restore repainting even if substitution/apply raised.
            for w in top_windows:
                try:
                    w.setUpdatesEnabled(True)
                except Exception:
                    pass

        self.theme_changed.emit(self._current)

    def _apply_palette_substitutions(self, qss: str) -> str:
        """Replace the template's placeholder hex tokens with palette colors.

        The dark/light QSS files are authored with fixed reference hex values
        (e.g. #0F172A); this maps each to the active palette's semantic color so
        one template renders any palette. Returns the substituted QSS string.
        """
        pal = self._palette
        from utils.accent import AccentManager
        # User-chosen accent overrides the palette primary when set.
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

        # Accent replacements: base accent plus two progressively darker shades
        # (for hover/pressed states) derived from it when the palette omits them.
        qss = qss.replace(_BRAND_ACCENT, accent_hex)
        qss = qss.replace(_BRAND_ACCENT_MID, pal.get("primary_hover", AccentManager().darker(accent_hex, 110)))
        qss = qss.replace(_BRAND_ACCENT_DARK, AccentManager().darker(accent_hex, 145))
        return qss

    def toggle(self):
        """Flip between dark and light mode and apply; returns the new mode."""
        new_mode = "light" if self._current == "dark" else "dark"
        self._palette_id = "light_mode" if new_mode == "light" else "dark_mode"
        self.apply_palette(self._palette_id)
        return self._current
