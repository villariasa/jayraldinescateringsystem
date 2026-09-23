"""Application top bar and its animated pill navigation.

This module defines two widgets:

- ``AnimatedTopNav``: a compact "capsule" navigation bar whose active tab is
  highlighted by a floating gradient pill that slides between tabs with an
  animation. Tabs are permission-gated and can be hidden per user role.
- ``TopBar``: the full window header (a ``QFrame``) that hosts the page title,
  the embedded ``AnimatedTopNav``, a debounced search box, a live clock,
  theme toggle, notification button, user avatar, and window controls
  (minimize / fullscreen / close, the last with an optional DB backup).

Both widgets are theme-aware (light/dark via ``ThemeManager``) and emit signals
(``tab_selected``, ``search_changed``) that the main window connects to.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QLineEdit, QWidget, QMessageBox, QFileDialog, QSizePolicy
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
import sys
import os
import subprocess
from datetime import datetime
from utils.icons import get_icon
import utils.icons as icons
from utils.theme import ThemeManager
from utils.accent import AccentManager


# Maps a page/tab index to the title shown at the left of the top bar.
_PAGE_TITLES = {
    0: "Dashboard",
    1: "Orders",
    2: "Customers",
    3: "Menu",
    4: "Calendar",
    5: "Cash Flow",
    6: "Billing",
    7: "Reports",
    8: "Expenses",
    9: "AI Assistant",
    10: "Settings",
}

# Tabs shown in the pill navigation, each as (label, icon_name, page_index).
# Only a curated subset of pages appears here; the page_index ties back to _PAGE_TITLES.
_TOP_NAV_ITEMS = [
    ("Dashboard",    "dashboard", 0),
    ("Orders",       "orders",    1),
    ("Calendar",     "calendar",  4),
    ("Billing",      "billing",   6),
    ("AI Assist",    "search",    9),
]


class AnimatedTopNav(QWidget):
    """Modern pill capsule navigation bar with a smooth sliding indicator.

    Renders one flat button per entry in ``_TOP_NAV_ITEMS`` and a single floating
    gradient "pill" (``_indicator``) that animates to sit behind the active tab.
    Emits ``tab_selected(int)`` with the page index when a tab is clicked.
    """

    # Emitted with the page index of the tab the user clicked.
    tab_selected = Signal(int)

    def __init__(self, theme_mgr, parent=None):
        """Build the nav buttons, sliding indicator and animation, then size the capsule.

        Args:
            theme_mgr: ``ThemeManager`` used to pick light/dark styling.
            parent: Optional parent widget.

        Side effects: measures button widths from bold font metrics to fix each
        button's width, fixes the overall capsule width, applies the theme, and
        schedules an initial (non-animated) activation of tab 0.
        """
        super().__init__(parent)
        self._theme = theme_mgr
        self.setFixedHeight(36)
        self.setObjectName("topNavCapsule")

        self._active_index = 0
        self._buttons = {}   # page_index -> QPushButton

        # Floating sliding indicator pill
        self._indicator = QFrame(self)
        self._indicator.setObjectName("navPillIndicator")
        self._indicator.setStyleSheet("""
            QFrame#navPillIndicator {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #FB7185);
                border-radius: 7px;
            }
        """)
        self._indicator.hide()  # stays hidden until a visible tab is activated

        # Animate the pill's geometry so it glides between tabs rather than jumping.
        self._anim = QPropertyAnimation(self._indicator, b"geometry")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 2, 4, 2)
        self._layout.setSpacing(4)

        # Measure with the same bold font the buttons use so width math is accurate.
        from PySide6.QtGui import QFontMetrics
        measure_font = QFont("Segoe UI", 12)
        measure_font.setBold(True)
        fm = QFontMetrics(measure_font)

        total_btn_w = 0  # accumulated button widths, used to size the whole capsule
        for text, icon_name, index in _TOP_NAV_ITEMS:
            btn = QPushButton(f" {text}", self)
            btn.setObjectName("topNavTabClean")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setIconSize(QSize(15, 15))
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            # Generous width calculation: bold text width + icon (15) + padding (20) + safety margin (9) = 44px
            text_w = fm.horizontalAdvance(f" {text}")
            btn_w = max(text_w + 44, 90)
            btn.setFixedWidth(btn_w)
            total_btn_w += btn_w

            # Stash icon name / page index on the button for later restyling & lookup.
            btn.setProperty("icon_name", icon_name)
            btn.setProperty("tab_index", index)
            # idx=index default binds the current loop value into the lambda.
            btn.clicked.connect(lambda _, idx=index: self.tab_selected.emit(idx))
            self._layout.addWidget(btn)
            self._buttons[index] = btn

        # Capsule width = sum of buttons + inter-button spacing (4px) + side padding.
        capsule_w = total_btn_w + (len(_TOP_NAV_ITEMS) - 1) * 4 + 10
        self.setFixedWidth(capsule_w)
        self.setMinimumWidth(capsule_w)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._apply_theme()
        # Defer the first activation so button geometries are laid out before the
        # indicator is positioned (animate=False avoids a slide from nowhere).
        QTimer.singleShot(60, lambda: self.set_active_page(0, animate=False))

    def minimumSizeHint(self) -> QSize:
        """Force a fixed minimum size (current width x 36px) so layouts don't shrink it."""
        return QSize(self.width(), 36)

    def sizeHint(self) -> QSize:
        """Preferred size equals the minimum size hint (the capsule is fixed-size)."""
        return self.minimumSizeHint()

    def _apply_theme(self):
        """Apply the capsule's background/border stylesheet for the current theme."""
        dark = self._theme.is_dark()
        if dark:
            self.setStyleSheet("""
                QWidget#topNavCapsule {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 9px;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#topNavCapsule {
                    background-color: rgba(0, 0, 0, 0.04);
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 9px;
                }
            """)

    def refresh_permissions(self):
        """Show/hide tabs per the current user's permissions and re-fit the capsule.

        Each tab maps to a permission module (Dashboard is always visible); a tab
        is shown only if the session has "view" on its module. The capsule width
        is then recomputed from just the visible buttons.
        """
        from utils.auth import SessionManager
        # Tab page index -> permission module that gates it.
        perm_map = {
            0: "dashboard",
            1: "bookings",
            4: "bookings",
            6: "cashflow",
            9: "ai_chef_jay",
        }
        visible_w = 0
        visible_cnt = 0
        for idx, btn in self._buttons.items():
            mod = perm_map.get(idx, "dashboard")
            # Dashboard is always visible; other tabs require explicit "view" permission.
            is_vis = (mod == "dashboard") or SessionManager.has_permission(mod, "view")
            btn.setVisible(is_vis)
            if is_vis:
                visible_w += btn.width()
                visible_cnt += 1
        # Re-fit the capsule to only the visible tabs (+ spacing + padding).
        capsule_w = visible_w + max(0, visible_cnt - 1) * 4 + 8
        self.setFixedWidth(capsule_w)
        self.updateGeometry()

    def set_active_page(self, index: int, animate: bool = True):
        """Move the sliding pill to tab ``index`` and restyle every tab accordingly.

        If the target tab is visible, the indicator is shown and either animated
        or snapped to the tab's geometry (``animate`` only takes effect when the
        pill already has a valid position to move from). The active tab gets white
        bold text + coloured icon; the rest get muted text with a hover accent.
        If the target tab is hidden the indicator is hidden and all tabs muted.
        """
        self._active_index = index
        dark = self._theme.is_dark()
        target_btn = self._buttons.get(index)

        if target_btn and target_btn.isVisible():
            self._indicator.show()
            # Keep the pill behind the button labels: raise the pill, then the buttons.
            self._indicator.raise_()
            for btn in self._buttons.values():
                btn.raise_()

            target_geo = target_btn.geometry()
            if target_geo.isValid() and target_geo.width() > 0:
                # Animate only if the pill already occupies a real position; otherwise snap.
                if animate and self._indicator.isVisible() and self._indicator.geometry().width() > 0:
                    self._anim.stop()
                    self._anim.setStartValue(self._indicator.geometry())
                    self._anim.setEndValue(target_geo)
                    self._anim.start()
                else:
                    self._indicator.setGeometry(target_geo)

            for idx, btn in self._buttons.items():
                icon_name = btn.property("icon_name")
                if idx == index:  # active tab: white bold text over the pill
                    btn.setStyleSheet("QPushButton { background: transparent; color: #FFFFFF; font-weight: 700; border: none; padding: 0 10px; font-size: 12px; }")
                    btn.setIcon(get_icon(icon_name, color="#FFFFFF", size=QSize(15, 15)))
                else:
                    color_muted = "#94A3B8" if dark else "#64748B"
                    hover_color = "#F9FAFB" if dark else "#0F172A"
                    btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {color_muted}; font-weight: 600; border: none; padding: 0 10px; font-size: 12px; }} QPushButton:hover {{ color: {hover_color}; }}")
                    btn.setIcon(get_icon(icon_name, color=color_muted, size=QSize(15, 15)))
        else:
            # Active tab is hidden (e.g. no permission): hide pill, mute all tabs.
            self._indicator.hide()
            for idx, btn in self._buttons.items():
                icon_name = btn.property("icon_name")
                color_muted = "#94A3B8" if dark else "#64748B"
                btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {color_muted}; font-weight: 600; border: none; padding: 0 10px; font-size: 12px; }}")
                btn.setIcon(get_icon(icon_name, color=color_muted, size=QSize(15, 15)))

    def resizeEvent(self, event):
        """Re-snap the indicator to the active tab after a resize (no animation)."""
        super().resizeEvent(event)
        target_btn = self._buttons.get(self._active_index)
        if target_btn and target_btn.geometry().isValid() and target_btn.geometry().width() > 0:
            self._indicator.setGeometry(target_btn.geometry())


class TopBar(QFrame):
    """The main window header hosting navigation, search, clock and window controls.

    Lays out (left to right): page title, animated pill navigation, a debounced
    search box, a live clock, theme toggle, notification button + badge, user
    avatar/name, and minimize/fullscreen/close buttons. Re-emits the nav's tab
    changes as ``tab_selected`` and the debounced search text as ``search_changed``.
    """

    # Debounced search text (emitted ~180ms after the user stops typing).
    search_changed = Signal(str)
    # Re-emitted from the embedded AnimatedTopNav when a tab is chosen.
    tab_selected = Signal(int)

    def __init__(self):
        """Construct and lay out every top-bar widget, then wire up timers/signals.

        Side effects: starts a 1s clock timer, applies theme styling, refreshes
        permission-gated tabs, and connects to theme/accent change signals.
        """
        super().__init__()
        self.setObjectName("topBar")
        self.setFixedHeight(56)
        self._theme = ThemeManager()

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(12, 0, 12, 0)
        self.main_layout.setSpacing(8)

        self.page_title = QLabel("Dashboard", self)
        self.page_title.setObjectName("h2")
        self.main_layout.addWidget(self.page_title)

        self.main_layout.addStretch()

        # Animated sliding top navigation
        self.top_nav = AnimatedTopNav(self._theme, self)
        self.top_nav.tab_selected.connect(self.tab_selected.emit)
        self.main_layout.addWidget(self.top_nav)

        self.main_layout.addStretch()

        # ✅ Responsive search bar (compact to leave ample room for tabs)
        self.search_wrap = QWidget(self)
        self.search_wrap.setMinimumWidth(80)
        self.search_wrap.setMaximumWidth(130)
        self.search_inner = QHBoxLayout(self.search_wrap)
        self.search_inner.setContentsMargins(0, 0, 0, 0)
        self.search_inner.setSpacing(0)
        self.search_box = QLineEdit(self.search_wrap)
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setFixedHeight(32)
        # Debounce: each keystroke restarts a 180ms one-shot timer; only when it
        # fires do we emit search_changed, so we don't re-query on every character.
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.timeout.connect(lambda: self.search_changed.emit(self.search_box.text()))
        self.search_box.textChanged.connect(lambda: self._search_debounce.start(180))
        self.search_inner.addWidget(self.search_box)
        self.main_layout.addWidget(self.search_wrap)

        self.clock_lbl = QLabel(self)
        self.clock_lbl.setObjectName("subtitle")
        self.clock_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.main_layout.addWidget(self.clock_lbl)

        # Update the clock label once per second (and once immediately).
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("notifBtn")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setToolTip("Toggle Light / Dark theme")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_icon()
        self.main_layout.addWidget(self.theme_btn)

        # ✅ Notification button
        self.notif_wrap = QWidget(self)
        self.notif_layout = QHBoxLayout(self.notif_wrap)
        self.notif_layout.setContentsMargins(0, 0, 0, 0)
        self.notif_layout.setSpacing(0)
        self.notif_btn = QPushButton(self.notif_wrap)
        self.notif_btn.setObjectName("notifBtn")
        self.notif_btn.setIcon(get_icon("bell", color="#9CA3AF", size=QSize(16, 16)))
        self.notif_btn.setIconSize(QSize(16, 16))
        self.notif_btn.setFixedSize(32, 32)
        self.notif_layout.addWidget(self.notif_btn)
        
        self.notif_badge = QLabel("0", self.notif_wrap)
        self.notif_badge.setObjectName("notifBadge")
        # Fixed height only - a fixed WIDTH clips 2+ digit counts (e.g. "10",
        # "99") since the stylesheet's horizontal padding has no room to grow.
        self.notif_badge.setFixedHeight(16)
        self.notif_badge.setMinimumWidth(16)
        self.notif_badge.setAlignment(Qt.AlignCenter)
        self.notif_badge.setVisible(False)
        self.notif_layout.addWidget(self.notif_badge)
        self.notif_layout.setAlignment(self.notif_badge, Qt.AlignTop)
        self.main_layout.addWidget(self.notif_wrap)

        self.divider = QFrame(self)
        self.divider.setFrameShape(QFrame.VLine)
        self.divider.setFixedHeight(20)
        self.main_layout.addWidget(self.divider)

        self.avatar = QLabel("O", self)
        self.avatar.setObjectName("userAvatar")
        self.avatar.setFixedSize(30, 30)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.avatar)

        self.owner_lbl = QLabel("Owner", self)
        self.owner_lbl.setObjectName("h3")
        self.main_layout.addWidget(self.owner_lbl)

        self.main_layout.addSpacing(6)

        self.min_btn = QPushButton(self)
        self.min_btn.setFixedSize(30, 30)
        self.min_btn.setToolTip("Minimize Window")
        self.min_btn.setCursor(Qt.PointingHandCursor)
        self.min_btn.setIcon(get_icon("minimize", color="#9CA3AF", size=QSize(14, 14)))
        self.min_btn.setIconSize(QSize(14, 14))
        self.min_btn.clicked.connect(self._minimize_window)
        self.main_layout.addWidget(self.min_btn)

        self.fs_btn = QPushButton(self)
        self.fs_btn.setFixedSize(30, 30)
        self.fs_btn.setToolTip("Toggle Fullscreen (F11)")
        self.fs_btn.setCursor(Qt.PointingHandCursor)
        self.fs_btn.setIcon(get_icon("maximize", color="#9CA3AF", size=QSize(14, 14)))
        self.fs_btn.setIconSize(QSize(14, 14))
        self.fs_btn.clicked.connect(self._toggle_window_fullscreen)
        self.main_layout.addWidget(self.fs_btn)

        self.close_btn = QPushButton(self)
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setIcon(get_icon("close", color="#EF4444", size=QSize(14, 14)))
        self.close_btn.setIconSize(QSize(14, 14))
        self.close_btn.setToolTip("Close Application")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self._confirm_close)
        self.main_layout.addWidget(self.close_btn)

        self._current_page_index = 0
        self._apply_theme_styles()
        self.refresh_permissions()
        # React to global theme and accent-colour changes.
        self._theme.theme_changed.connect(self._on_theme_changed)
        AccentManager().accent_changed.connect(self._on_accent_changed)

    def update_user_display(self):
        """Refresh the avatar initial and owner label from the current session user.

        Falls back to "Admin"/"A" when no user is set, and shortens the name to a
        single word (or "Admin") so it does not crowd the navigation tabs.
        """
        from utils.auth import SessionManager
        user = SessionManager.current_user() or {}
        name = user.get("display_name") or user.get("username", "Admin")
        # Keep name compact so it doesn't push or compress the navigation tabs
        if "admin" in name.lower():
            display_name = "Admin"
        else:
            parts = name.split()
            display_name = parts[0] if parts else name
        self.owner_lbl.setText(display_name)
        initial = name[0].upper() if name else "A"
        self.avatar.setText(initial)

    def refresh_permissions(self):
        """Re-apply tab visibility for the current user and refresh the user display."""
        self.top_nav.refresh_permissions()
        self.update_user_display()

    def _minimize_window(self):
        """Minimize the top-level window this bar belongs to."""
        w = self.window()
        if w:
            w.showMinimized()

    def _toggle_window_fullscreen(self):
        """Toggle the window between fullscreen and normal, then update the icon.

        Prefers the window's own ``_toggle_fullscreen`` if it defines one,
        otherwise falls back to Qt's showNormal/showFullScreen.
        """
        w = self.window()
        if w and hasattr(w, "_toggle_fullscreen"):
            w._toggle_fullscreen()
        elif w:
            if w.isFullScreen():
                w.showNormal()
            else:
                w.showFullScreen()
        self._update_fs_icon()

    def _update_fs_icon(self):
        """Sync the fullscreen button's icon and tooltip to the window's state."""
        w = self.window()
        is_fs = w.isFullScreen() if w else False
        dark = self._theme.is_dark()
        btn_color = "#9CA3AF" if dark else "#5B6B84"
        icon_name = "restore" if is_fs else "maximize"
        self.fs_btn.setIcon(get_icon(icon_name, color=btn_color, size=QSize(14, 14)))
        self.fs_btn.setToolTip("Exit Fullscreen (Esc)" if is_fs else "Toggle Fullscreen (F11)")

    def _on_theme_changed(self, *_args):
        """Re-style the bar when the app theme changes.

        Guarded with ``shiboken6.isValid`` because the signal may fire after this
        C++ object has been deleted; that case is ignored.
        """
        try:
            from shiboken6 import isValid
            if isValid(self):
                self._apply_theme_styles()
        except Exception:
            pass

    def _on_accent_changed(self, *_args):
        """Re-render the current page (to pick up the new accent) when it changes.

        Same deleted-object guard as ``_on_theme_changed``.
        """
        try:
            from shiboken6 import isValid
            if isValid(self):
                self.set_page(self._current_page_index, self.search_box.text())
        except Exception:
            pass

    def _apply_theme_styles(self):
        """Restyle the clock, divider, notification and window-control buttons per theme."""
        dark = self._theme.is_dark()
        btn_color = "#9CA3AF" if dark else "#5B6B84"
        hover_bg = "rgba(156,163,175,0.25)" if dark else "rgba(100,116,139,0.18)"

        self.clock_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: %s;"
            % btn_color
        )
        self.divider.setStyleSheet("color: %s;" % ("#243244" if dark else "#E4E9F1"))
        self.notif_btn.setIcon(get_icon(
            "bell", color=btn_color, size=QSize(16, 16)
        ))

        self.min_btn.setIcon(get_icon("minimize", color=btn_color, size=QSize(14, 14)))
        self.min_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {hover_bg}; }}"
        )

        self._update_fs_icon()
        self.fs_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {hover_bg}; }}"
        )

        self.close_btn.setIcon(get_icon("close", color="#EF4444", size=QSize(14, 14)))
        self.close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: rgba(239,68,68,0.25); }"
        )

    def resizeEvent(self, event):
        """Responsively hide the clock/owner/divider on narrow widths.

        These non-essential items are dropped first so the navigation tabs keep
        their space at lower window widths.
        """
        super().resizeEvent(event)
        w = self.width()
        # Protect top nav tabs from being squeezed: hide clock & owner on lower resolutions
        self.clock_lbl.setVisible(w >= 1180)
        self.owner_lbl.setVisible(w >= 1050)
        self.divider.setVisible(w >= 1050)

    def _confirm_close(self):
        """Confirm app close, offer a DB backup, and exit accordingly.

        Asks the user to confirm closing; if confirmed, prompts whether to back
        up the database first. "Yes" runs ``_do_backup`` (which exits on success),
        "No" exits immediately via ``sys.exit(0)``.
        """
        reply = QMessageBox.question(
            self, "Close Application",
            "Are you sure you want to close Jayraldine's Catering?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        backup_reply = QMessageBox.question(
            self, "Backup Database",
            "Do you want to backup the database before closing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if backup_reply == QMessageBox.Yes:
            self._do_backup()
        else:
            sys.exit(0)

    def _do_backup(self):
        """Prompt for a path and dump the PostgreSQL database via ``pg_dump``.

        On a successful dump the app exits. On failure (non-zero return,
        pg_dump missing, or any exception) the user is asked whether to close
        anyway without a backup. Returns early (cancels close) if no path is chosen.
        The DB password is passed to pg_dump via the ``PGPASSWORD`` env var.
        """
        # Suggest a timestamped filename so successive backups don't collide.
        default_name = f"jayraldines_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Database Backup", default_name, "SQL Files (*.sql);;All Files (*)"
        )
        if not path:
            return
        try:
            from utils.db import _CONFIG
            # pg_dump reads the password from PGPASSWORD rather than a prompt.
            env = os.environ.copy()
            env["PGPASSWORD"] = _CONFIG.get("password", "")
            result = subprocess.run(
                [
                    "pg_dump",
                    "-h", _CONFIG.get("host", "localhost"),
                    "-p", str(_CONFIG.get("port", 5432)),
                    "-U", _CONFIG.get("user", "postgres"),
                    "-F", "p",
                    "-f", path,
                    _CONFIG.get("dbname", "jayraldines_catering"),
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                QMessageBox.information(
                    self, "Backup Successful",
                    f"Database backed up successfully to:\n{path}"
                )
                sys.exit(0)
            else:
                err = result.stderr.strip() or "Unknown error"
                retry = QMessageBox.question(
                    self, "Backup Failed",
                    f"Backup failed:\n{err}\n\nClose anyway without backup?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if retry == QMessageBox.Yes:
                    sys.exit(0)
        except FileNotFoundError:
            retry = QMessageBox.question(
                self, "pg_dump Not Found",
                "pg_dump was not found on this system.\nClose anyway without backup?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if retry == QMessageBox.Yes:
                sys.exit(0)
        except Exception as exc:
            retry = QMessageBox.question(
                self, "Backup Error",
                f"An error occurred during backup:\n{exc}\n\nClose anyway without backup?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if retry == QMessageBox.Yes:
                sys.exit(0)

    def _toggle_theme(self):
        """Flip light/dark theme and refresh the toggle icon and nav styling."""
        new_theme = self._theme.toggle()
        self._update_theme_icon()
        self.top_nav._apply_theme()
        # Re-apply nav tab styles for the new theme without animating the pill.
        self.top_nav.set_active_page(getattr(self, "_current_page_index", 0), animate=False)

    def _update_theme_icon(self):
        """Set the theme button's icon/tooltip/style to reflect the active theme.

        Shows a sun (to switch to light) in dark mode and a moon (to switch to
        dark) in light mode.
        """
        if self._theme.is_dark():
            self.theme_btn.setText("")
            self.theme_btn.setIcon(get_icon("sun", color="#F59E0B", size=QSize(16, 16)))
            self.theme_btn.setToolTip("Switch to Light theme")
            self.theme_btn.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; }"
                "QPushButton:hover { background: rgba(255, 255, 255, 0.12); border-color: rgba(255, 255, 255, 0.2); }"
            )
        else:
            self.theme_btn.setText("")
            self.theme_btn.setIcon(get_icon("moon", color="#6366F1", size=QSize(16, 16)))
            self.theme_btn.setToolTip("Switch to Dark theme")
            self.theme_btn.setStyleSheet(
                "QPushButton { background: rgba(0, 0, 0, 0.04); border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 8px; }"
                "QPushButton:hover { background: rgba(0, 0, 0, 0.08); border-color: rgba(0, 0, 0, 0.15); }"
            )

    def _tick_clock(self):
        """Update the clock label with the current weekday, date and 12-hour time."""
        now = datetime.now()
        self.clock_lbl.setText(now.strftime("%a, %b %d  %I:%M %p"))

    def set_page(self, index: int, search_text: str = ""):
        """Programmatically switch the bar to page ``index``.

        Updates the page title and the active nav tab, and sets the search box
        text without emitting ``search_changed`` (signals are blocked so restoring
        a page's saved search does not re-trigger a query).
        """
        self._current_page_index = index
        self.page_title.setText(_PAGE_TITLES.get(index, ""))
        self.search_box.blockSignals(True)
        self.search_box.setText(search_text)
        self.search_box.blockSignals(False)
        self.top_nav.set_active_page(index, animate=True)
