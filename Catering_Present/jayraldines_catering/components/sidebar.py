"""
Collapsible left navigation sidebar for the main application shell.

Defines :class:`Sidebar`, a QFrame containing the app logo, a set of
permission-gated navigation buttons (see ``_NAV_ITEMS``), and a user-profile
footer with an account menu (Change Password / Log Out). It can animate between
an expanded and a collapsed (icon-only) width, adapts to the active theme, and
emits :attr:`Sidebar.page_changed` to request navigation. Button visibility is
driven by the current session's module permissions.
"""
import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PySide6.QtCore import Signal, Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPixmap, QCursor

from utils.icons import nav_icon, nav_icon_active, get_icon
from utils.theme import ThemeManager
from utils.accent import AccentManager
from utils.paths import resource_path

from utils.auth import SessionManager

# Navigation button definitions: (label, icon name, page index, permission key).
# The page index is emitted via page_changed; the permission key gates
# visibility through SessionManager.has_permission(..., "view").
_NAV_ITEMS = [
    ("Customers", "customers", 2, "customers"),
    ("Menu",      "menu",      3, "menu"),
    ("Cash Flow", "trending-up", 5, "cashflow"),
    ("Expenses",  "billing",   8, "expenses"),
    ("Reports",   "reports",   7, "reports"),
    ("Settings",  "settings",  10, "settings"),
]

# Pixel widths for the two sidebar states (used by the collapse animation).
EXPANDED_WIDTH  = 250
COLLAPSED_WIDTH = 68


class Sidebar(QFrame):
    """Left navigation sidebar widget.

    Signals:
        page_changed(int): emitted with a page index when a nav button is
            clicked (once the sidebar is ready).
        logout_requested(): emitted when the user chooses Log Out.
        change_password_requested(): declared for external wiring (the sidebar
            itself opens the change-password dialog directly).
    """
    page_changed = Signal(int)
    logout_requested = Signal()
    change_password_requested = Signal()

    def __init__(self):
        """Build the full sidebar UI: logo/header with collapse toggle,
        permission-gated navigation buttons, the user-profile footer with its
        account menu, and the expand/collapse animations. Applies theme styles,
        refreshes permissions, and defers marking itself 'ready' (so early
        programmatic clicks are ignored)."""
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(EXPANDED_WIDTH)
        self._collapsed = False   # current expand/collapse state
        self._ready = False       # guards nav clicks until the first event loop tick

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Header Area
        self.logo_frame = QFrame(self)
        self.logo_frame.setObjectName("logoArea")
        self.logo_layout = QHBoxLayout(self.logo_frame)
        self.logo_layout.setContentsMargins(12, 14, 12, 14)
        self.logo_layout.setSpacing(8)

        self.logo_icon = QLabel(self.logo_frame)
        self.logo_icon.setCursor(Qt.PointingHandCursor)
        # When collapsed, clicking the logo re-expands the sidebar (it is the
        # only visible affordance in that state).
        self.logo_icon.mousePressEvent = lambda e: self.toggle_collapse() if self._collapsed else None
        logo_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_path):
            px = QPixmap(logo_path).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_icon.setPixmap(px)
        else:
            # Fallback glyph when the logo asset is missing from the bundle.
            self.logo_icon.setPixmap(get_icon("orders", color="#E11D48", size=QSize(26, 26)).pixmap(QSize(26, 26)))
        self.logo_icon.setFixedSize(30, 30)
        self.logo_icon.setAlignment(Qt.AlignCenter)
        self.logo_layout.addWidget(self.logo_icon)

        from version import __version__
        self.logo_text = QLabel(
            f"<div style='line-height:1.15;'>"
            f"<span style='font-size:12px;font-weight:700;color:#FFFFFF;'>Jayraldine's</span><br/>"
            f"<span style='font-size:10px;color:#9CA3AF;'>Catering v{__version__}</span>"
            f"</div>",
            self.logo_frame
        )
        self.logo_text.setTextFormat(Qt.RichText)
        self.logo_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.logo_layout.addWidget(self.logo_text)

        self.collapse_btn = QPushButton(self.logo_frame)
        self.collapse_btn.setObjectName("collapseBtn")
        self.collapse_btn.setText("")
        self.collapse_btn.setFixedSize(30, 30)
        self.collapse_btn.setIconSize(QSize(18, 18))
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        self.logo_layout.addWidget(self.collapse_btn)

        self.root_layout.addWidget(self.logo_frame)

        # Nav buttons
        self.buttons = []
        self.root_layout.addSpacing(8)

        # Build one checkable nav button per _NAV_ITEMS entry, stashing its
        # metadata on the widget via Qt properties for later lookup.
        for item in _NAV_ITEMS:
            text = item[0]
            icon_name = item[1]
            index = item[2]
            # Permission key defaults to the lowercased label if not provided.
            mod_key = item[3] if len(item) > 3 else text.lower()

            btn = QPushButton(f"   {text}", self)
            btn.setCheckable(True)
            btn.setIconSize(QSize(18, 18))
            btn.setIcon(nav_icon(icon_name))
            btn.setProperty("icon_name", icon_name)
            btn.setProperty("nav_label", text)
            btn.setProperty("page_index", index)
            btn.setProperty("perm_key", mod_key)

            # Pre-select the dashboard button (index 0) as the default page.
            if index == 0:
                btn.setChecked(True)
                btn.setIcon(nav_icon_active(icon_name))

            # Bind idx per-iteration so each button reports its own page index.
            btn.clicked.connect(lambda _, idx=index: self._on_nav_clicked(idx))
            self.root_layout.addWidget(btn)
            self.buttons.append(btn)

        self.root_layout.addStretch()

        # User Profile Footer
        self.user_frame = QFrame(self)
        self.user_frame.setObjectName("userProfileArea")
        self.user_frame.setCursor(Qt.PointingHandCursor)
        self.user_layout = QHBoxLayout(self.user_frame)
        self.user_layout.setContentsMargins(14, 12, 14, 12)
        self.user_layout.setSpacing(10)

        self.avatar = QLabel("U", self.user_frame)
        self.avatar.setObjectName("userAvatar")
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.user_layout.addWidget(self.avatar)

        self.user_info = QVBoxLayout()
        self.user_info.setSpacing(0)
        self.name_lbl  = QLabel("User", self.user_frame)
        self.name_lbl.setStyleSheet("font-weight: 700; color: #F8FAFC;")
        self.email_lbl = QLabel("Staff", self.user_frame)
        self.email_lbl.setStyleSheet("font-size: 10px; color: #94A3B8;")
        self.user_info.addWidget(self.name_lbl)
        self.user_info.addWidget(self.email_lbl)
        self.user_layout.addLayout(self.user_info)
        self.user_layout.addStretch()

        # Caret indicator — the whole row opens an account menu (Change Password / Log Out)
        self.logout_lbl = QLabel(self.user_frame)
        self.logout_lbl.setCursor(Qt.PointingHandCursor)
        self.logout_lbl.setToolTip("Account options")
        self.logout_lbl.setPixmap(
            get_icon("chevron-right", color="#94A3B8", size=QSize(16, 16)).pixmap(QSize(16, 16))
        )

        def _open_menu(event):
            """Mouse-press handler: open the account popup menu."""
            event.accept()
            self._show_user_menu()

        # Both the caret label and the whole footer row open the account menu.
        self.logout_lbl.mousePressEvent = _open_menu
        self.user_frame.mousePressEvent = _open_menu
        self.user_layout.addWidget(self.logout_lbl)

        self.root_layout.addWidget(self.user_frame)

        # Collapse/expand animations: animate both min and max width together
        # so the fixed-width frame smoothly resizes between the two states.
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._anim2 = QPropertyAnimation(self, b"maximumWidth")
        self._anim2.setDuration(200)
        self._anim2.setEasingCurve(QEasingCurve.OutCubic)

        self._apply_theme_styles()
        self.refresh_permissions()
        ThemeManager().theme_changed.connect(self._on_theme_changed)
        # Defer readiness to the next event-loop tick so any clicks emitted
        # during construction/layout don't trigger navigation.
        QTimer.singleShot(0, self._mark_ready)

    def _on_theme_changed(self, *_args):
        """Theme-change signal handler: re-apply themed styles, guarded by a
        shiboken validity check so a queued signal to a deleted widget is a
        no-op."""
        try:
            from shiboken6 import isValid
            if isValid(self):
                self._apply_theme_styles()
        except Exception:
            pass

    def _apply_theme_styles(self):
        """Restyle the theme-sensitive elements (user name/role labels, the
        collapse button, and the account caret icon) for the current light or
        dark theme, including the collapse button's icon tint which also
        depends on the collapsed state."""
        dark = ThemeManager().is_dark()
        self.name_lbl.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: %s;"
            % ("#F9FAFB" if dark else "#101828")
        )
        self.email_lbl.setStyleSheet(
            "font-size: 11px; color: %s;" % ("#6B7280" if dark else "#7A879E")
        )
        if dark:
            self.collapse_btn.setStyleSheet("""
                QPushButton#collapseBtn {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.16);
                    border-radius: 6px;
                }
                QPushButton#collapseBtn:hover {
                    background-color: rgba(225, 29, 72, 0.35);
                    border-color: #E11D48;
                }
            """)
            # Highlight the collapse icon when collapsed to hint it re-expands.
            btn_icon_col = "#38BDF8" if self._collapsed else "#F9FAFB"
        else:
            self.collapse_btn.setStyleSheet("""
                QPushButton#collapseBtn {
                    background-color: rgba(0, 0, 0, 0.05);
                    border: 1px solid rgba(0, 0, 0, 0.12);
                    border-radius: 6px;
                }
                QPushButton#collapseBtn:hover {
                    background-color: rgba(225, 29, 72, 0.18);
                    border-color: #E11D48;
                }
            """)
            btn_icon_col = "#0284C7" if self._collapsed else "#334155"

        self.collapse_btn.setIcon(get_icon("menu-collapse", color=btn_icon_col, size=QSize(18, 18)))
        self.collapse_btn.setIconSize(QSize(18, 18))

        muted = "#6B7280" if dark else "#7A879E"
        self.logout_lbl.setPixmap(
            get_icon("chevron-right", color=muted, size=QSize(16, 16)).pixmap(QSize(16, 16))
        )

    def _mark_ready(self):
        """Flip the readiness flag so nav clicks are honored (called one tick
        after construction)."""
        self._ready = True

    def handle_click(self, page_index: int):
        """Update the checked/active state and icon of every nav button so the
        one matching ``page_index`` is highlighted. Used both on user clicks and
        when navigation is driven externally (keeps the sidebar in sync)."""
        for btn in self.buttons:
            btn_idx = btn.property("page_index")
            icon_name = btn.property("icon_name")
            active = (btn_idx == page_index)
            btn.setChecked(active)
            btn.setIcon(nav_icon_active(icon_name) if active else nav_icon(icon_name))

    def _on_nav_clicked(self, index):
        """Handle a nav button click: ignore until ready, otherwise sync the
        highlight and emit :attr:`page_changed` to request navigation."""
        if not self._ready:
            return
        self.handle_click(index)
        self.page_changed.emit(index)

    def toggle_collapse(self):
        """Toggle between expanded and collapsed layouts, animating the width
        and adjusting margins/alignment, hiding or showing the logo text, user
        info and button labels, and converting labels to tooltips (and back)
        when collapsed."""
        self._collapsed = not self._collapsed
        target = COLLAPSED_WIDTH if self._collapsed else EXPANDED_WIDTH

        for anim in (self._anim, self._anim2):
            anim.setStartValue(self.width())
            anim.setEndValue(target)
            anim.start()

        dark = ThemeManager().is_dark()
        if self._collapsed:
            # Collapsed: center the icon, hide text/labels, use tooltips.
            self.logo_layout.setContentsMargins(0, 14, 0, 10)
            self.logo_layout.setAlignment(self.logo_icon, Qt.AlignCenter)
            self.logo_text.hide()
            self.logout_lbl.hide()
            self.collapse_btn.setToolTip("Expand Sidebar")
            btn_icon_col = "#38BDF8" if dark else "#0284C7"
            self.collapse_btn.setIcon(get_icon("menu-collapse", color=btn_icon_col, size=QSize(18, 18)))
            self.user_layout.setContentsMargins(0, 12, 0, 12)
            self.user_layout.setAlignment(self.avatar, Qt.AlignCenter)
            for w in (self.user_info.itemAt(i).widget() for i in range(self.user_info.count())):
                if w:
                    w.hide()
            for btn in self.buttons:
                btn.setText("")
                btn.setToolTip(btn.property("nav_label"))
        else:
            # Expanded: restore left-aligned layout, text/labels, no tooltips.
            self.logo_layout.setContentsMargins(12, 14, 12, 14)
            self.logo_layout.setAlignment(self.logo_icon, Qt.AlignLeft | Qt.AlignVCenter)
            self.logo_text.show()
            self.logout_lbl.show()
            self.collapse_btn.setToolTip("Collapse Sidebar")
            btn_icon_col = "#F9FAFB" if dark else "#334155"
            self.collapse_btn.setIcon(get_icon("menu-collapse", color=btn_icon_col, size=QSize(18, 18)))
            self.user_layout.setContentsMargins(14, 12, 14, 12)
            self.user_layout.setAlignment(self.avatar, Qt.AlignLeft | Qt.AlignVCenter)
            for w in (self.user_info.itemAt(i).widget() for i in range(self.user_info.count())):
                if w:
                    w.show()
            for btn in self.buttons:
                btn.setText("   " + btn.property("nav_label"))
                btn.setToolTip("")

    def update_user_display(self):
        """Refresh the footer to reflect the current session user: set the
        display name, a friendly role label ('ADMINISTRATOR' for admins), and
        the avatar initial. Falls back to sensible defaults when no user is
        logged in."""
        user = SessionManager.current_user() or {}
        name = user.get("display_name") or user.get("username", "Administrator")
        raw_role = user.get("role", "admin" if name.lower() == "admin" else "staff")
        if raw_role.lower() == "admin":
            role_text = "ADMINISTRATOR"
        else:
            role_text = raw_role.upper()
        self.name_lbl.setText(name)
        self.email_lbl.setText(f"Role: {role_text}")
        initial = name[0].upper() if name else "A"
        self.avatar.setText(initial)

    def refresh_permissions(self):
        """Show or hide each nav button based on the current user's 'view'
        permission for its module key (buttons without a key stay visible), then
        refresh the user footer. Call after login/logout or permission change."""
        for btn in self.buttons:
            perm_key = btn.property("perm_key")
            if perm_key:
                btn.setVisible(SessionManager.has_permission(perm_key, "view"))
            else:
                btn.setVisible(True)
        self.update_user_display()

    def _show_user_menu(self):
        """Popup account menu with clear Change Password / Log Out choices,
        anchored to the user footer (opens upward automatically at the bottom)."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtCore import QPoint
        dark = ThemeManager().is_dark()
        menu = QMenu(self)
        if dark:
            menu.setStyleSheet(
                "QMenu { background:#0F172A; color:#F8FAFC; border:1px solid rgba(255,255,255,0.14); "
                "border-radius:8px; padding:6px; } "
                "QMenu::item { padding:8px 16px; border-radius:6px; } "
                "QMenu::item:selected { background:rgba(56,189,248,0.18); } "
                "QMenu::separator { height:1px; background:rgba(255,255,255,0.10); margin:4px 8px; }"
            )
        else:
            menu.setStyleSheet(
                "QMenu { background:#FFFFFF; color:#101828; border:1px solid rgba(0,0,0,0.12); "
                "border-radius:8px; padding:6px; } "
                "QMenu::item { padding:8px 16px; border-radius:6px; } "
                "QMenu::item:selected { background:rgba(2,132,199,0.12); } "
                "QMenu::separator { height:1px; background:rgba(0,0,0,0.08); margin:4px 8px; }"
            )
        act_pass = menu.addAction(get_icon("settings", color="#94A3B8", size=QSize(15, 15)), "Change Password")
        menu.addSeparator()
        act_out = menu.addAction(get_icon("log-out", color="#F43F5E", size=QSize(15, 15)), "Log Out")

        # Anchor at the top-right of the footer; Qt flips it upward if there's no room below.
        anchor = self.user_frame.mapToGlobal(QPoint(self.user_frame.width() - 6, 0))
        chosen = menu.exec(anchor)
        # Route the chosen action: open change-password dialog or request logout.
        if chosen == act_pass:
            self._open_change_password()
        elif chosen == act_out:
            self.logout_requested.emit()

    def _open_change_password(self):
        """Open the modal 'change own password' dialog for the current user."""
        from components.user_management_panel import ChangeOwnPasswordDialog
        dlg = ChangeOwnPasswordDialog(self)
        dlg.exec()