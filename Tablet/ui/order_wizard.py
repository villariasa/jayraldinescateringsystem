"""
The full tablet order-creation wizard with clean professional typography:
Customer -> Package & Event -> Mix & Match Menu -> Upsell Add-ons -> Billing -> Preview -> Terms -> Receipt

Features:
- Live Sticky Cart Sidebar on the right showing real-time subtotal & selected dishes.
- Visual touchable cards with clear active highlights.
- Visual "Mix & Match" dish selector with category tabs and selection counters.
- "Would you like an add-on?" upselling cards for Lechon, Desserts, and Styling.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QScrollArea, QRadioButton, QButtonGroup, QCheckBox, QMessageBox,
    QTextEdit, QTextBrowser, QFileDialog, QSizePolicy, QStackedWidget,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QDate, QTime, QPropertyAnimation, QEasingCurve

import utils.repository as repo
import utils.exporter as exporter
import utils.terms as terms
from utils.session import get_actor
from ui import theme, icons
from ui.step_progress import StepProgress
from ui.components.address_search import AddressSearchWidget


def _card(elevated=False, accent=False):
    f = QFrame()
    theme.style_card(f, elevated=elevated, accent_border=accent)
    return f


def _nav_row(back_cb=None, next_cb=None, next_label="Next >", next_enabled=True):
    row = QHBoxLayout()
    row.setSpacing(14)
    if back_cb:
        back_btn = QPushButton("←  Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setMinimumHeight(46)
        back_btn.setMinimumWidth(120)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #132238;
                color: #CBD5E1;
                font-size: 14px;
                font-weight: 700;
                border-radius: 10px;
                border: 1px solid #1E293B;
                padding: 10px 20px;
            }
            QPushButton:hover { background: #182B46; color: #FFFFFF; border: 1px solid #334155; }
        """)
        back_btn.clicked.connect(back_cb)
        row.addWidget(back_btn)
    row.addStretch()
    next_btn = None
    if next_cb:
        next_btn = QPushButton(next_label)
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.setMinimumHeight(46)
        next_btn.setMinimumWidth(210)
        next_btn.setEnabled(next_enabled)
        next_btn.setStyleSheet("""
            QPushButton {
                background-color: #F43F5E;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 800;
                border-radius: 10px;
                border: none;
                padding: 12px 24px;
            }
            QPushButton:hover { background-color: #FB7185; }
            QPushButton:pressed { background-color: #E11D48; }
            QPushButton:disabled { background-color: #334155; color: #64748B; }
        """)
        next_btn.clicked.connect(next_cb)
        row.addWidget(next_btn)
    return row, next_btn


class OrderWizard(QWidget):
    def __init__(self, on_finish, on_toggle_fullscreen=None):
        super().__init__()
        self._on_finish = on_finish
        self._on_toggle_fullscreen = on_toggle_fullscreen
        self._draft = {
            "customer_id": None, "customer_name": "", "contact": "", "email": "", "address": "",
            "event_date": QDate.currentDate().addDays(14).toString("yyyy-MM-dd"), "event_time": "18:00",
            "venue": "", "occasion": "Birthday", "pax": 100,
            "package_id": None, "package_name": "", "base_total": 0.0,
            "menu_selections": [], "additional_charges": [],
            "down_payment": 0.0, "payment_method": "Cash", "notes": "",
        }
        self._confirmed_order = None
        self._build_ui()
        self.goto_customer_step()

    def _build_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(28, 18, 28, 18)
        self._root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignVCenter)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setAlignment(Qt.AlignVCenter)
        self._step_lbl = QLabel()
        self._step_lbl.setStyleSheet(theme.heading_style(20))
        self._step_sub_lbl = QLabel("Tap items to customize your catering package")
        self._step_sub_lbl.setStyleSheet(theme.subtitle_style(12))
        title_box.addWidget(self._step_lbl)
        title_box.addWidget(self._step_sub_lbl)
        header.addLayout(title_box)
        header.addStretch()

        right_actions = QHBoxLayout()
        right_actions.setSpacing(10)
        right_actions.setAlignment(Qt.AlignVCenter)

        if self._on_toggle_fullscreen:
            fs_btn = QPushButton()
            fs_btn.setIcon(theme.create_fullscreen_icon("#CBD5E1", 20))
            fs_btn.setToolTip("Toggle Fullscreen (F11)")
            fs_btn.setObjectName("Secondary")
            fs_btn.setFixedSize(40, 40)
            fs_btn.setCursor(Qt.PointingHandCursor)
            fs_btn.clicked.connect(self._on_toggle_fullscreen)
            right_actions.addWidget(fs_btn, alignment=Qt.AlignVCenter)

        self._cancel_btn = QPushButton("Cancel Order")
        self._cancel_btn.setObjectName("Danger")
        self._cancel_btn.setFixedHeight(40)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._cancel)
        right_actions.addWidget(self._cancel_btn, alignment=Qt.AlignVCenter)

        header.addLayout(right_actions)
        self._root.addLayout(header)

        # Stepper Progress Bar
        self._stepper = StepProgress()
        self._root.addWidget(self._stepper)

        # Main Split Content (Left: Step Form, Right: Sticky Cart Sidebar)
        self._split_lay = QHBoxLayout()
        self._split_lay.setSpacing(20)

        # Left Step Content Container
        self._body_scroll = QScrollArea()
        self._body_scroll.setWidgetResizable(True)
        self._body_scroll.setFrameShape(QFrame.NoFrame)
        self._split_lay.addWidget(self._body_scroll, 3)

        # Right Sticky Cart Sidebar
        self._cart_card = _card(elevated=True, accent=True)
        self._cart_card.setMinimumWidth(290)
        self._cart_card.setMaximumWidth(340)
        self._cart_lay = QVBoxLayout(self._cart_card)
        self._cart_lay.setContentsMargins(18, 16, 18, 16)
        self._cart_lay.setSpacing(10)
        self._build_cart_sidebar()
        self._split_lay.addWidget(self._cart_card, 1)

        self._root.addLayout(self._split_lay, 1)

        # Navigation Bar
        self._nav_container = QVBoxLayout()
        self._root.addLayout(self._nav_container)
        self._nav_widget = None

    def _build_cart_sidebar(self):
        # Header with Live status indicator
        cart_head = QHBoxLayout()
        cart_head.setContentsMargins(4, 2, 4, 2)
        cart_title = QLabel("Live Event Summary")
        cart_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")
        cart_head.addWidget(cart_title)
        cart_head.addStretch()

        live_dot = QLabel()
        live_dot.setFixedSize(8, 8)
        live_dot.setStyleSheet("background-color: #10B981; border-radius: 4px;")
        cart_head.addWidget(live_dot)
        self._cart_lay.addLayout(cart_head)

        # Scrollable items area in sidebar
        self._cart_items_scroll = QScrollArea()
        self._cart_items_scroll.setWidgetResizable(True)
        self._cart_items_scroll.setFrameShape(QFrame.NoFrame)
        self._cart_items_widget = QWidget()
        self._cart_items_lay = QVBoxLayout(self._cart_items_widget)
        self._cart_items_lay.setContentsMargins(0, 4, 0, 4)
        self._cart_items_lay.setSpacing(8)
        self._cart_items_scroll.setWidget(self._cart_items_widget)
        self._cart_lay.addWidget(self._cart_items_scroll, 1)

        # Totals box
        totals_box = QFrame()
        totals_box.setStyleSheet("background: #0B1220; border: 1px solid #1E293B; border-radius: 10px; padding: 10px;")
        tlay = QVBoxLayout(totals_box)
        tlay.setSpacing(6)

        r1 = QHBoxLayout()
        sub_tag = QLabel("Subtotal:")
        sub_tag.setStyleSheet("color: #94A3B8; font-size: 13px;")
        r1.addWidget(sub_tag)
        self._cart_subtotal_lbl = QLabel("₱0.00")
        self._cart_subtotal_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")
        self._cart_subtotal_lbl.setAlignment(Qt.AlignRight)
        r1.addWidget(self._cart_subtotal_lbl)
        tlay.addLayout(r1)

        r2 = QHBoxLayout()
        dp_tag = QLabel("50% Downpayment:")
        dp_tag.setStyleSheet("color: #94A3B8; font-size: 12px;")
        r2.addWidget(dp_tag)
        self._cart_dp_lbl = QLabel("₱0.00")
        self._cart_dp_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #F59E0B;")
        self._cart_dp_lbl.setAlignment(Qt.AlignRight)
        r2.addWidget(self._cart_dp_lbl)
        tlay.addLayout(r2)

        self._cart_lay.addWidget(totals_box)
        self.update_cart_sidebar()

    def update_cart_sidebar(self):
        # Clear items
        while self._cart_items_lay.count():
            item = self._cart_items_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Customer & Package Info Cards
        pkg_name = self._draft.get("package_name") or "No Package Selected"
        pax = int(self._draft.get("pax", 100))
        base_tot = float(self._draft.get("base_total", 0.0))

        # Package Card
        pkg_box = QFrame()
        pkg_box.setStyleSheet("background: #0B1220; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        play = QVBoxLayout(pkg_box)
        play.setSpacing(2)
        ptag = QLabel("PACKAGE")
        ptag.setStyleSheet("font-size: 10px; font-weight: 800; color: #94A3B8; letter-spacing: 1.2px;")
        pname = QLabel(pkg_name)
        pname.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        pname.setWordWrap(True)
        play.addWidget(ptag)
        play.addWidget(pname)
        self._cart_items_lay.addWidget(pkg_box)

        # Guests Card
        guests_box = QFrame()
        guests_box.setStyleSheet("background: #0B1220; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        glay = QVBoxLayout(guests_box)
        glay.setSpacing(2)
        gtag = QLabel("GUESTS")
        gtag.setStyleSheet("font-size: 10px; font-weight: 800; color: #94A3B8; letter-spacing: 1.2px;")
        gpax = QLabel(f"{pax} Pax")
        gpax.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        glay.addWidget(gtag)
        glay.addWidget(gpax)
        self._cart_items_lay.addWidget(guests_box)

        # Selected Dishes
        menu_items = self._draft.get("menu_selections", [])
        charges = self._draft.get("additional_charges", [])

        if not menu_items and not charges:
            # Empty placeholder matching screenshot
            ph_box = QFrame()
            ph_lay = QVBoxLayout(ph_box)
            ph_lay.setContentsMargins(10, 20, 10, 20)
            ph_lay.setSpacing(10)
            ph_lay.setAlignment(Qt.AlignCenter)

            ph_icon = QLabel()
            ph_icon.setFixedSize(36, 36)
            ph_icon.setAlignment(Qt.AlignCenter)
            ph_icon.setPixmap(icons.icon_utensils("#64748B", 28).pixmap(28, 28))
            ph_lay.addWidget(ph_icon, alignment=Qt.AlignCenter)

            ph_text = QLabel("Menu, add-ons, and\ncharges will fill in here as\nyou go through the steps.")
            ph_text.setStyleSheet("font-size: 11px; color: #64748B; line-height: 1.4;")
            ph_text.setAlignment(Qt.AlignCenter)
            ph_lay.addWidget(ph_text)
            self._cart_items_lay.addWidget(ph_box)
        else:
            if menu_items:
                dish_hdr = QLabel(f"Included Dishes ({len(menu_items)})")
                dish_hdr.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; margin-top: 4px;")
                self._cart_items_lay.addWidget(dish_hdr)
                for m in menu_items:
                    dl = QLabel(f"• {m['item_name']}")
                    dl.setStyleSheet("font-size: 12px; color: #E2E8F0;")
                    dl.setWordWrap(True)
                    self._cart_items_lay.addWidget(dl)

            if charges:
                chg_hdr = QLabel(f"Add-ons & Extras ({len(charges)})")
                chg_hdr.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {theme.GOLD}; margin-top: 4px;")
                self._cart_items_lay.addWidget(chg_hdr)
                for c in charges:
                    is_disc = c["amount"] < 0
                    sign = "- " if is_disc else "+ "
                    col = theme.WARNING if is_disc else theme.SUCCESS
                    cl = QLabel(f"• {c['description']} ({sign}₱{abs(c['amount']):,.2f})")
                    cl.setStyleSheet(f"font-size: 11px; color: {col};")
                    cl.setWordWrap(True)
                    self._cart_items_lay.addWidget(cl)

        self._cart_items_lay.addStretch()

        # Calculate totals
        charges_sum = sum(c["amount"] for c in charges)
        total = base_tot + charges_sum
        dp = round(total * 0.50, 2)
        self._cart_subtotal_lbl.setText(f"₱{total:,.2f}")
        self._cart_dp_lbl.setText(f"₱{dp:,.2f}")

    def _set_body(self, widget: QWidget, step_title: str, step_subtitle: str = "", step_index: int = None, show_cart: bool = True):
        self._step_lbl.setText(step_title)
        self._step_sub_lbl.setText(step_subtitle or "Tap items to customize your catering package")
        self._body_scroll.setWidget(widget)
        self._cart_card.setVisible(show_cart)
        if step_index is not None:
            self._stepper.set_current(step_index)
            self._stepper.setVisible(True)
        else:
            self._stepper.setVisible(False)
        self.update_cart_sidebar()

        # Smooth Page Fade-In Transition
        self._fade_eff = QGraphicsOpacityEffect(self._body_scroll)
        self._body_scroll.setGraphicsEffect(self._fade_eff)
        self._fade_anim = QPropertyAnimation(self._fade_eff, b"opacity")
        self._fade_anim.setDuration(160)
        self._fade_anim.setStartValue(0.15)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()

    def _set_nav(self, row_layout):
        if self._nav_widget is not None:
            self._nav_widget.hide()
            self._nav_container.removeWidget(self._nav_widget)
            self._nav_widget.deleteLater()

        container = QWidget()
        container.setLayout(row_layout)
        self._nav_container.addWidget(container)
        self._nav_widget = container

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        is_portrait = w < 850
        if hasattr(self, "_split_lay") and hasattr(self, "_cart_card"):
            if is_portrait:
                self._split_lay.setDirection(QHBoxLayout.TopToBottom)
                self._cart_card.setMaximumWidth(16777215)
                self._cart_card.setMinimumWidth(0)
            else:
                self._split_lay.setDirection(QHBoxLayout.LeftToRight)
                self._cart_card.setMinimumWidth(290)
                self._cart_card.setMaximumWidth(340)

    def _cancel(self):
        if QMessageBox.question(self, "Cancel Order", "Discard this order? Nothing has been saved yet.",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._on_finish()

    def _field_label(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {theme.TEXT_MUTED}; letter-spacing: 0.5px; margin-top: 4px;")
        return l

    # ── Step 1: Customer Info ──────────────────────────────────────────

    def goto_customer_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        lay.setContentsMargins(10, 10, 10, 10)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)
        new_btn = QPushButton("New Customer")
        new_btn.setIcon(icons.icon_user_plus("#FFFFFF", 18))
        existing_btn = QPushButton("Search Existing Customer")
        existing_btn.setIcon(icons.icon_search("#94A3B8", 18))
        for b in (new_btn, existing_btn):
            b.setMinimumHeight(48)
            b.setCursor(Qt.PointingHandCursor)
        mode_row.addWidget(new_btn)
        mode_row.addWidget(existing_btn)
        lay.addLayout(mode_row)

        form_frame = _card(elevated=True)
        form_lay = QVBoxLayout(form_frame)
        form_lay.setContentsMargins(20, 20, 20, 20)
        form_lay.setSpacing(12)

        # ── Selection Summary Banner (when an existing customer is picked) ──
        selected_banner = QFrame()
        selected_banner.setStyleSheet(f"background: #064E3B; border: 1.5px solid {theme.SUCCESS}; border-radius: 8px; padding: 10px 14px;")
        sb_lay = QHBoxLayout(selected_banner)
        sb_lay.setContentsMargins(10, 8, 10, 8)
        sb_lbl = QLabel()
        sb_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ECFDF5;")
        sb_clear_btn = QPushButton("Change / New Customer")
        sb_clear_btn.setObjectName("Secondary")
        sb_clear_btn.setFixedHeight(34)
        sb_clear_btn.setCursor(Qt.PointingHandCursor)
        sb_lay.addWidget(sb_lbl, 1)
        sb_lay.addWidget(sb_clear_btn)
        selected_banner.setVisible(False)
        form_lay.addWidget(selected_banner)

        # ── Page 0: New Customer Inputs ──
        new_cust_widget = QWidget()
        new_cust_lay = QVBoxLayout(new_cust_widget)
        new_cust_lay.setContentsMargins(0, 0, 0, 0)
        new_cust_lay.setSpacing(10)
        new_cust_lay.addWidget(self._field_label("CUSTOMER CONTACT DETAILS"))

        name_in = QLineEdit(self._draft["customer_name"])
        name_in.setPlaceholderText("Customer Full Name *")
        name_in.setMinimumHeight(46)
        contact_in = QLineEdit(self._draft["contact"])
        contact_in.setPlaceholderText("Contact Number (e.g. 0917-123-4567)")
        contact_in.setMinimumHeight(46)
        email_in = QLineEdit(self._draft["email"])
        email_in.setPlaceholderText("Email Address (optional)")
        email_in.setMinimumHeight(46)
        address_widget = AddressSearchWidget(placeholder="Select Delivery / Billing Address...")
        if self._draft["address"]:
            address_widget.set_value(self._draft["address"])

        for w in (name_in, contact_in, email_in, address_widget):
            new_cust_lay.addWidget(w)
        form_lay.addWidget(new_cust_widget)

        # ── Page 1: Existing Customer Search ──
        search_cust_widget = QWidget()
        search_cust_lay = QVBoxLayout(search_cust_widget)
        search_cust_lay.setContentsMargins(0, 0, 0, 0)
        search_cust_lay.setSpacing(10)
        search_cust_lay.addWidget(self._field_label("SEARCH CUSTOMER DIRECTORY"))

        search_in = QLineEdit()
        search_in.setPlaceholderText("Type name, phone number, or address...")
        search_in.setMinimumHeight(46)
        search_cust_lay.addWidget(search_in)

        results_container = QVBoxLayout()
        results_container.setSpacing(6)
        results_widget = QWidget()
        results_widget.setLayout(results_container)
        search_cust_lay.addWidget(results_widget)
        search_cust_widget.setVisible(False)
        form_lay.addWidget(search_cust_widget)

        lay.addWidget(form_frame)
        lay.addStretch()

        def highlight(btn, active, is_new=True):
            if active:
                icon_color = "#FFFFFF"
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F43F5E;
                        color: #FFFFFF;
                        font-size: 14px;
                        font-weight: 800;
                        border-radius: 10px;
                        border: none;
                        padding: 8px 16px;
                    }
                    QPushButton:hover { background-color: #FB7185; }
                """)
            else:
                icon_color = "#94A3B8"
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #132238;
                        color: #94A3B8;
                        font-size: 14px;
                        font-weight: 700;
                        border-radius: 10px;
                        border: 1px solid #1E293B;
                        padding: 8px 16px;
                    }
                    QPushButton:hover { background-color: #182B46; color: #FFFFFF; border: 1px solid #334155; }
                """)
            btn.setIcon(icons.icon_user_plus(icon_color, 18) if is_new else icons.icon_search(icon_color, 18))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        def show_new_mode():
            highlight(new_btn, True, is_new=True)
            highlight(existing_btn, False, is_new=False)
            new_cust_widget.setVisible(True)
            search_cust_widget.setVisible(False)

        def show_search_mode():
            highlight(new_btn, False, is_new=True)
            highlight(existing_btn, True, is_new=False)
            new_cust_widget.setVisible(False)
            search_cust_widget.setVisible(True)
            do_search()

        def do_search():
            while results_container.count():
                item = results_container.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            found = repo.search_customers(search_in.text())
            if not found:
                empty = QLabel("No matching customers found in directory.")
                empty.setStyleSheet(theme.subtitle_style(12))
                results_container.addWidget(empty)
            for c in found[:8]:
                btn = QPushButton(f"{c['name']}   —   {c['contact'] or 'No phone'}   ({c['address'] or 'No address'})")
                btn.setObjectName("Secondary")
                btn.setMinimumHeight(46)
                btn.setCursor(Qt.PointingHandCursor)

                def select(_, cust=c):
                    self._draft.update({
                        "customer_id": cust["id"], "customer_name": cust["name"],
                        "contact": cust["contact"], "email": cust["email"], "address": cust["address"],
                    })
                    name_in.setText(cust["name"])
                    contact_in.setText(cust["contact"] or "")
                    email_in.setText(cust["email"] or "")
                    address_widget.set_value(cust["address"] or "")
                    sb_lbl.setText(f"Selected Existing Customer: {cust['name']} ({cust['contact'] or 'No phone'})")
                    selected_banner.setVisible(True)
                    show_new_mode()

                btn.clicked.connect(select)
                results_container.addWidget(btn)

        def clear_selection():
            self._draft["customer_id"] = None
            selected_banner.setVisible(False)
            name_in.clear()
            contact_in.clear()
            email_in.clear()
            address_widget.clear()

        sb_clear_btn.clicked.connect(clear_selection)
        search_in.textChanged.connect(lambda _: do_search())
        new_btn.clicked.connect(show_new_mode)
        existing_btn.clicked.connect(show_search_mode)

        if self._draft.get("customer_id") and self._draft.get("customer_name"):
            sb_lbl.setText(f"Selected Existing Customer: {self._draft['customer_name']} ({self._draft.get('contact') or ''})")
            selected_banner.setVisible(True)

        show_new_mode()

        def next_step():
            name = name_in.text().strip()
            if not name:
                QMessageBox.warning(self, "Missing Name", "Please enter customer name.")
                return
            self._draft.update({
                "customer_name": name, "contact": contact_in.text().strip(),
                "email": email_in.text().strip(), "address": address_widget.get_full_address(),
            })
            self.goto_event_step()

        row, _ = _nav_row(next_cb=next_step, next_label="Next: Package & Event >")
        self._set_nav(row)
        self._set_body(page, "Step 1 — Customer Info", "Enter client contact details", step_index=0)

    # ── Step 2: Package & Event Details ─────────────────────────────────

    def goto_event_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        lay.setContentsMargins(10, 10, 10, 10)

        # Event Information Card
        evt_card = _card(elevated=True)
        evt_lay = QVBoxLayout(evt_card)
        evt_lay.setContentsMargins(18, 16, 18, 16)
        evt_lay.setSpacing(10)
        evt_lay.addWidget(self._field_label("EVENT DATE & LOCATION"))

        drow = QHBoxLayout()
        drow.setSpacing(12)

        dbox = QVBoxLayout()
        dbox.setSpacing(4)
        dlbl = QLabel("Event Date:")
        dlbl.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setMinimumHeight(44)
        init_date = QDate.fromString(self._draft["event_date"], "yyyy-MM-dd") if self._draft["event_date"] else QDate.currentDate().addDays(7)
        date_edit.setDate(init_date)
        dbox.addWidget(dlbl)
        dbox.addWidget(date_edit)
        drow.addLayout(dbox, 1)

        tbox = QVBoxLayout()
        tbox.setSpacing(4)
        tlbl = QLabel("Event Time:")
        tlbl.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        time_edit = QTimeEdit()
        time_edit.setMinimumHeight(44)
        init_time = QTime.fromString(self._draft["event_time"], "HH:mm") if self._draft["event_time"] else QTime(12, 0)
        time_edit.setTime(init_time)
        tbox.addWidget(tlbl)
        tbox.addWidget(time_edit)
        drow.addLayout(tbox, 1)

        pbox = QVBoxLayout()
        pbox.setSpacing(4)
        plbl = QLabel("Guest Count (Pax):")
        plbl.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        pax_in = QSpinBox()
        pax_in.setRange(10, 2000)
        pax_in.setValue(self._draft["pax"] or 50)
        pax_in.setMinimumHeight(44)
        pbox.addWidget(plbl)
        pbox.addWidget(pax_in)
        drow.addLayout(pbox, 1)
        evt_lay.addLayout(drow)

        venue_widget = AddressSearchWidget(placeholder="Event Venue / Location (Dropdown)...")
        if self._draft["venue"]:
            venue_widget.set_value(self._draft["venue"])
        evt_lay.addWidget(venue_widget)

        occasion_in = QLineEdit(self._draft["occasion"])
        occasion_in.setPlaceholderText("Occasion (e.g. Wedding, Birthday, Corporate Gala)")
        occasion_in.setMinimumHeight(44)
        evt_lay.addWidget(occasion_in)
        lay.addWidget(evt_card)

        # Package Selection Card
        pkg_card = _card(elevated=True)
        pkg_lay = QVBoxLayout(pkg_card)
        pkg_lay.setContentsMargins(18, 16, 18, 16)
        pkg_lay.setSpacing(10)
        pkg_lay.addWidget(self._field_label("SELECT BUFFET PACKAGE"))

        packages = repo.get_packages()
        selected_pkg = {"id": self._draft.get("package_id"), "name": self._draft.get("package_name"), "price_per_pax": 0.0}

        if not packages:
            warn = QLabel("No packages available. Please add packages in Owner Settings or import master data.")
            warn.setStyleSheet(f"color:{theme.WARNING}; font-size: 13px;")
            pkg_lay.addWidget(warn)

        pkg_frames = []
        for pkg in packages:
            pf = QFrame()
            is_active = pkg["id"] == self._draft.get("package_id")
            theme.style_dish_card(pf, selected=is_active)
            play = QHBoxLayout(pf)
            play.setContentsMargins(14, 12, 14, 12)
            play.setSpacing(12)

            info_box = QVBoxLayout()
            info_box.setSpacing(3)
            p_name = QLabel(f"{pkg['name']}")
            p_name.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
            p_desc = QLabel(pkg.get("description") or "Complete Buffet Service + Free Drinks")
            p_desc.setStyleSheet(theme.subtitle_style(12))
            p_desc.setWordWrap(True)
            info_box.addWidget(p_name)
            info_box.addWidget(p_desc)
            play.addLayout(info_box, 3)

            price_tag = QVBoxLayout()
            price_tag.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            p_amt = QLabel(f"₱{pkg['price_per_pax']:,.2f} / pax")
            p_amt.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {theme.GOLD};")
            p_min = QLabel(f"Min: {pkg['min_pax']} Pax")
            p_min.setStyleSheet("font-size: 11px; color: #94A3B8;")
            price_tag.addWidget(p_amt)
            price_tag.addWidget(p_min)
            play.addLayout(price_tag, 1)

            select_btn = QPushButton("Selected" if is_active else "Select")
            select_btn.setObjectName("Primary" if is_active else "Secondary")
            select_btn.setMinimumHeight(42)
            select_btn.setMinimumWidth(100)
            select_btn.setCursor(Qt.PointingHandCursor)

            def make_select(p=pkg, frame=pf, sbtn=select_btn):
                def do_sel():
                    selected_pkg.update(p)
                    for of, ob in pkg_frames:
                        theme.style_dish_card(of, selected=False)
                        ob.setObjectName("Secondary")
                        ob.setText("Select")
                        ob.style().unpolish(ob)
                        ob.style().polish(ob)
                    theme.style_dish_card(frame, selected=True)
                    sbtn.setObjectName("Primary")
                    sbtn.setText("Selected")
                    sbtn.style().unpolish(sbtn)
                    sbtn.style().polish(sbtn)
                    self._draft.update({
                        "package_id": p["id"], "package_name": p["name"],
                        "base_total": float(p.get("price_per_pax", 0)) * pax_in.value(),
                    })
                    pp_spin.setValue(float(p.get("price_per_pax", 0)))
                    tot_spin.setValue(float(p.get("price_per_pax", 0)) * pax_in.value())
                    self.update_cart_sidebar()
                return do_sel

            select_btn.clicked.connect(make_select())
            play.addWidget(select_btn)
            pkg_frames.append((pf, select_btn))
            pkg_lay.addWidget(pf)

        lay.addWidget(pkg_card)

        # ── PACKAGE PRICING CONTROLS (OWNER / USER CAN TYPE CUSTOM PRICE) ──
        price_card = _card(elevated=True)
        price_lay = QVBoxLayout(price_card)
        price_lay.setContentsMargins(18, 16, 18, 16)
        price_lay.setSpacing(10)
        price_lay.addWidget(self._field_label("PACKAGE PRICING (EDITABLE / CUSTOM AMOUNT)"))

        prow = QHBoxLayout()
        prow.setSpacing(14)

        pp_box = QVBoxLayout()
        pp_box.setSpacing(4)
        pp_lbl = QLabel("Price Per Pax (₱):")
        pp_lbl.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        pp_spin = QDoubleSpinBox()
        pp_spin.setRange(0.0, 50000.0)
        pp_spin.setDecimals(2)
        pp_spin.setMinimumHeight(44)
        init_ppp = float(selected_pkg.get("price_per_pax") or (float(self._draft.get("base_total") or 0.0) / max(1, pax_in.value())) or 350.0)
        pp_spin.setValue(init_ppp)
        pp_box.addWidget(pp_lbl)
        pp_box.addWidget(pp_spin)
        prow.addLayout(pp_box, 1)

        tot_box = QVBoxLayout()
        tot_box.setSpacing(4)
        tot_lbl = QLabel("Package Base Total (₱):")
        tot_lbl.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        tot_spin = QDoubleSpinBox()
        tot_spin.setRange(0.0, 10000000.0)
        tot_spin.setDecimals(2)
        tot_spin.setMinimumHeight(44)
        init_base = float(self._draft.get("base_total") or (pp_spin.value() * pax_in.value()))
        tot_spin.setValue(init_base)
        tot_box.addWidget(tot_lbl)
        tot_box.addWidget(tot_spin)
        prow.addLayout(tot_box, 1)

        price_lay.addLayout(prow)
        lay.addWidget(price_card)

        # Wire Real-Time Pricing Synchronization
        is_syncing = False

        def on_ppp_changed(val):
            nonlocal is_syncing
            if is_syncing:
                return
            is_syncing = True
            selected_pkg["price_per_pax"] = val
            calc_tot = round(val * pax_in.value(), 2)
            tot_spin.setValue(calc_tot)
            self._draft["base_total"] = calc_tot
            self.update_cart_sidebar()
            is_syncing = False

        def on_tot_changed(val):
            nonlocal is_syncing
            if is_syncing:
                return
            is_syncing = True
            calc_ppp = round(val / max(1, pax_in.value()), 2)
            pp_spin.setValue(calc_ppp)
            selected_pkg["price_per_pax"] = calc_ppp
            self._draft["base_total"] = val
            self.update_cart_sidebar()
            is_syncing = False

        def on_pax_changed(val):
            nonlocal is_syncing
            self._draft["pax"] = val
            if is_syncing:
                return
            is_syncing = True
            calc_tot = round(pp_spin.value() * val, 2)
            tot_spin.setValue(calc_tot)
            self._draft["base_total"] = calc_tot
            self.update_cart_sidebar()
            is_syncing = False

        pp_spin.valueChanged.connect(on_ppp_changed)
        tot_spin.valueChanged.connect(on_tot_changed)
        pax_in.valueChanged.connect(on_pax_changed)

        lay.addStretch()

        def next_step():
            venue_val = venue_widget.get_full_address()
            if not venue_val:
                QMessageBox.warning(self, "Missing Venue", "Please enter or select the event venue location.")
                return
            if not selected_pkg.get("id"):
                QMessageBox.warning(self, "No Package Selected", "Please tap 'Select' on a catering package.")
                return
            self._draft.update({
                "event_date": date_edit.date().toString("yyyy-MM-dd"),
                "event_time": time_edit.time().toString("HH:mm"),
                "venue": venue_val, "occasion": occasion_in.text().strip(),
                "pax": pax_in.value(), "package_id": selected_pkg["id"], "package_name": selected_pkg.get("name", ""),
                "base_total": tot_spin.value(),
            })
            self.goto_menu_step()

        row, _ = _nav_row(back_cb=self.goto_customer_step, next_cb=next_step, next_label="Next: Menu Selection >")
        self._set_nav(row)
        self._set_body(page, "Step 2 — Package & Event", "Choose your buffet tier and guest count", step_index=1)

    # ── Step 3: Multi-Category Menu Selection & Add-ons ──────────────────

    def goto_menu_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        lay.setContentsMargins(10, 10, 10, 10)

        choices = repo.get_package_menu_choices(self._draft.get("package_id"))
        
        # Build existing selections lookup by (category, item_name)
        selected_items_map = {}
        for m in self._draft.get("menu_selections", []):
            key = (m.get("category", ""), m.get("item_name", ""))
            selected_items_map[key] = m

        if not choices:
            info = _card()
            il = QVBoxLayout(info)
            il.setContentsMargins(20, 20, 20, 20)
            lbl = QLabel("No specific dish choices found. You can add items in Owner Settings or tap Next to continue.")
            lbl.setStyleSheet(theme.subtitle_style(13))
            il.addWidget(lbl)
            lay.addWidget(info)

        for category, items in choices.items():
            cat_card = _card(elevated=True)
            cat_lay = QVBoxLayout(cat_card)
            cat_lay.setContentsMargins(18, 14, 18, 14)
            cat_lay.setSpacing(8)

            cat_hdr = QHBoxLayout()
            cat_lbl = QLabel(f"CATEGORY: {category.upper()}")
            cat_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #F8FAFC; letter-spacing: 0.5px;")
            cat_hdr.addWidget(cat_lbl)
            cat_hdr.addStretch()

            count_lbl = QLabel("0 Selected")
            count_lbl.setStyleSheet(theme.pill_style(theme.GOLD))
            cat_hdr.addWidget(count_lbl)
            cat_lay.addLayout(cat_hdr)

            cat_item_checkboxes = []

            def update_cat_count(c_lbl=count_lbl, c_boxes=cat_item_checkboxes):
                c = sum(1 for cb, _ in c_boxes if cb.isChecked())
                c_lbl.setText(f"{c} Selected" if c > 0 else "Optional")
                c_lbl.setStyleSheet(theme.pill_style(theme.SUCCESS if c > 0 else theme.TEXT_MUTED))

            for item in items:
                df = QFrame()
                key = (category, item["name"])
                is_selected = key in selected_items_map
                theme.style_dish_card(df, selected=is_selected)
                dlay = QHBoxLayout(df)
                dlay.setContentsMargins(12, 10, 12, 10)
                dlay.setSpacing(10)

                chk = QCheckBox()
                chk.setChecked(is_selected)
                chk.setCursor(Qt.PointingHandCursor)
                chk.setStyleSheet("QCheckBox::indicator { width: 22px; height: 22px; }")
                dlay.addWidget(chk)

                dinfo = QVBoxLayout()
                dinfo.setSpacing(2)
                dname = QLabel(item["name"])
                dname.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
                dinfo.addWidget(dname)
                if item.get("description"):
                    ddesc = QLabel(item["description"])
                    ddesc.setStyleSheet(theme.subtitle_style(11))
                    dinfo.addWidget(ddesc)
                dlay.addLayout(dinfo, 1)

                if item.get("price") and item["price"] > 0:
                    dprice = QLabel(f"+ ₱{item['price']:,.2f} add-on")
                    dprice.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {theme.GOLD};")
                    dlay.addWidget(dprice)

                def make_chk_handler(cat=category, it=item, frame=df, cbox=chk, cb_list=cat_item_checkboxes, clbl=count_lbl):
                    def on_toggled(checked):
                        theme.style_dish_card(frame, selected=checked)
                        mkey = (cat, it["name"])
                        if checked:
                            selected_items_map[mkey] = {
                                "item_name": it["name"], "category": cat,
                                "price": it.get("price", 0.0), "quantity": 1,
                            }
                        else:
                            selected_items_map.pop(mkey, None)
                        self._draft["menu_selections"] = list(selected_items_map.values())
                        update_cat_count(clbl, cb_list)
                        self.update_cart_sidebar()
                    return on_toggled

                chk.toggled.connect(make_chk_handler())
                cat_item_checkboxes.append((chk, item))
                cat_lay.addWidget(df)

            update_cat_count(count_lbl, cat_item_checkboxes)
            lay.addWidget(cat_card)

        lay.addStretch()

        def next_step():
            self._draft["menu_selections"] = list(selected_items_map.values())
            self.goto_charges_step()

        row, _ = _nav_row(back_cb=self.goto_event_step, next_cb=next_step, next_label="Next: Add-ons & Extras >")
        self._set_nav(row)
        self._set_body(page, "Step 3 — Menu Dishes & Add-ons", "Select any number of dishes across buffet categories", step_index=2)

    # ── Step 4: Upselling & Add-ons ──────────────────────────────────────

    def goto_charges_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        lay.setContentsMargins(10, 10, 10, 10)

        # Recommendation Banner
        rec_card = _card(elevated=True, accent=True)
        rlay = QVBoxLayout(rec_card)
        rlay.setContentsMargins(18, 14, 18, 14)
        rlay.setSpacing(10)

        rtitle = QLabel("POPULAR EVENT ADD-ONS & UPGRADES")
        rtitle.setStyleSheet("font-size: 13px; font-weight: 800; color: #F59E0B; letter-spacing: 0.5px;")
        rlay.addWidget(rtitle)

        rec_items = [
            ("Whole Roast Lechon Platter (15kg)", 6500.00),
            ("Premium Dessert Bar Buffet (3 Desserts)", 3500.00),
            ("Unlimited Fruit Juice & Iced Tea Station", 2000.00),
            ("Themed Floral Backdrop Arch", 4500.00),
            ("Sound System with Microphones & Lights", 3000.00),
        ]

        rec_grid = QVBoxLayout()
        rec_grid.setSpacing(6)
        for r_name, r_price in rec_items:
            rf = QFrame()
            rf.setStyleSheet("background: #1E293B; border-radius: 8px; padding: 6px 12px;")
            rflay = QHBoxLayout(rf)
            rflay.setContentsMargins(8, 4, 8, 4)

            lbl = QLabel(r_name)
            lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
            prc = QLabel(f"₱{r_price:,.2f}")
            prc.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {theme.GOLD};")

            add_rec_btn = QPushButton(" Add")
            add_rec_btn.setIcon(icons.icon_plus("#94A3B8", 14))
            add_rec_btn.setObjectName("Secondary")
            add_rec_btn.setFixedSize(78, 34)
            add_rec_btn.setCursor(Qt.PointingHandCursor)

            def make_add_rec(name=r_name, amt=r_price):
                def do_add():
                    self._draft["additional_charges"].append({"description": name, "amount": amt})
                    refresh_list()
                    self.update_cart_sidebar()
                return do_add

            add_rec_btn.clicked.connect(make_add_rec())

            rflay.addWidget(lbl, 3)
            rflay.addWidget(prc, 1)
            rflay.addWidget(add_rec_btn)
            rec_grid.addWidget(rf)

        rlay.addLayout(rec_grid)
        lay.addWidget(rec_card)

        # Custom Charge / Discount Form
        custom_card = _card()
        cform = QHBoxLayout(custom_card)
        cform.setContentsMargins(16, 12, 16, 12)
        cform.setSpacing(8)

        desc_in = QLineEdit()
        desc_in.setPlaceholderText("Custom Add-on or Discount Description")
        desc_in.setMinimumHeight(44)
        amt_in = QDoubleSpinBox()
        amt_in.setRange(-1_000_000, 1_000_000)
        amt_in.setDecimals(2)
        amt_in.setPrefix("₱ ")
        amt_in.setFixedWidth(160)
        amt_in.setMinimumHeight(44)

        add_custom_btn = QPushButton("  Add Custom")
        add_custom_btn.setIcon(icons.icon_plus("#FFFFFF", 16))
        add_custom_btn.setObjectName("Primary")
        add_custom_btn.setMinimumHeight(44)
        add_custom_btn.setCursor(Qt.PointingHandCursor)

        cform.addWidget(desc_in, 3)
        cform.addWidget(amt_in, 1)
        cform.addWidget(add_custom_btn)
        lay.addWidget(custom_card)

        # Active Add-ons List
        list_container = QVBoxLayout()
        list_container.setSpacing(6)
        list_widget = QWidget()
        list_widget.setLayout(list_container)
        lay.addWidget(list_widget)

        def refresh_list():
            while list_container.count():
                item = list_container.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for i, c in enumerate(self._draft["additional_charges"]):
                row_f = _card(elevated=True)
                row_l = QHBoxLayout(row_f)
                row_l.setContentsMargins(14, 8, 14, 8)
                lbl = QLabel(c["description"])
                lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
                is_discount = c["amount"] < 0
                amt_lbl = QLabel(f"- ₱{abs(c['amount']):,.2f}" if is_discount else f"₱{c['amount']:,.2f}")
                amt_lbl.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {theme.WARNING if is_discount else theme.SUCCESS};")
                del_btn = QPushButton(" Remove")
                del_btn.setIcon(icons.icon_trash("#F87171", 14))
                del_btn.setObjectName("Danger")
                del_btn.setCursor(Qt.PointingHandCursor)

                def make_del(idx=i):
                    def do_del():
                        self._draft["additional_charges"].pop(idx)
                        refresh_list()
                        self.update_cart_sidebar()
                    return do_del

                del_btn.clicked.connect(make_del())
                row_l.addWidget(lbl, 3)
                row_l.addWidget(amt_lbl, 1)
                row_l.addWidget(del_btn)
                list_container.addWidget(row_f)
            self.update_cart_sidebar()

        def add_charge():
            desc = desc_in.text().strip()
            amt = amt_in.value()
            if not desc or amt == 0:
                QMessageBox.warning(self, "Invalid Entry", "Enter description and amount.")
                return
            self._draft["additional_charges"].append({"description": desc, "amount": amt})
            desc_in.clear()
            amt_in.setValue(0)
            refresh_list()

        add_custom_btn.clicked.connect(add_charge)
        refresh_list()
        lay.addStretch()

        row, _ = _nav_row(back_cb=self.goto_menu_step, next_cb=self.goto_billing_step, next_label="Next: Billing & Payment >")
        self._set_nav(row)
        self._set_body(page, "Step 4 — Add-ons & Extras", "Enhance your event with lechon, drinks, or decor", step_index=3)

    # ── Step 5: Billing & Payment Presets ────────────────────────────────

    def goto_billing_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        lay.setContentsMargins(10, 10, 10, 10)

        charges_sum = sum(c["amount"] for c in self._draft["additional_charges"])
        total = self._draft["base_total"] + charges_sum
        req_downpayment = round(total * 0.50, 2)

        summary = _card(accent=True)
        slay = QVBoxLayout(summary)
        slay.setContentsMargins(20, 16, 20, 16)
        slay.setSpacing(6)

        stitle = QLabel("BILLING BREAKDOWN")
        stitle.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {theme.GOLD}; letter-spacing: 0.5px;")
        slay.addWidget(stitle)

        for label, val, big in [
            ("Base Buffet Package", self._draft["base_total"], False),
            ("Additional Charges / Add-ons", charges_sum, False),
            ("Final Event Total", total, True),
        ]:
            row = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet("font-size: 13px;" if not big else "font-size: 16px; font-weight: 800;")
            v = QLabel(f"₱{val:,.2f}")
            v.setStyleSheet(f"font-size: {'20px' if big else '14px'}; font-weight: 800; color: {theme.ACCENT if big else theme.TEXT};")
            v.setAlignment(Qt.AlignRight)
            row.addWidget(l)
            row.addWidget(v)
            slay.addLayout(row)
        lay.addWidget(summary)

        form = _card(elevated=True)
        flay = QVBoxLayout(form)
        flay.setContentsMargins(20, 18, 20, 18)
        flay.setSpacing(8)

        flay.addWidget(self._field_label("QUICK AUTO-FILL PAYMENT OPTION"))
        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)

        dp_preset_btn = QPushButton(f"50% Downpayment (₱{req_downpayment:,.2f})")
        dp_preset_btn.setIcon(icons.icon_credit_card("#94A3B8", 16))
        dp_preset_btn.setObjectName("Secondary")
        dp_preset_btn.setMinimumHeight(48)
        dp_preset_btn.setCursor(Qt.PointingHandCursor)

        full_preset_btn = QPushButton(f"Fully Paid (₱{total:,.2f})")
        full_preset_btn.setIcon(icons.icon_check("#10B981", 16))
        full_preset_btn.setObjectName("Secondary")
        full_preset_btn.setMinimumHeight(48)
        full_preset_btn.setCursor(Qt.PointingHandCursor)

        preset_row.addWidget(dp_preset_btn)
        preset_row.addWidget(full_preset_btn)
        flay.addLayout(preset_row)

        flay.addWidget(self._field_label("DOWN PAYMENT AMOUNT (₱)"))
        dp_in = QDoubleSpinBox()
        dp_in.setRange(0, 10_000_000)
        dp_in.setDecimals(2)
        dp_in.setPrefix("₱ ")
        dp_in.setMinimumHeight(46)
        dp_in.setValue(float(self._draft.get("down_payment") or req_downpayment))
        flay.addWidget(dp_in)

        dp_preset_btn.clicked.connect(lambda: dp_in.setValue(req_downpayment))
        full_preset_btn.clicked.connect(lambda: dp_in.setValue(total))

        flay.addWidget(self._field_label("PAYMENT METHOD"))
        method_in = QComboBox()
        method_in.addItems(["Cash", "GCash", "Maya", "Bank Transfer", "Check", "Other"])
        method_in.setMinimumHeight(44)
        method_in.setCurrentText(self._draft.get("payment_method", "Cash"))
        flay.addWidget(method_in)

        flay.addWidget(self._field_label("SPECIAL EVENT INSTRUCTIONS / NOTES"))
        notes_in = QTextEdit(self._draft.get("notes", ""))
        notes_in.setFixedHeight(70)
        flay.addWidget(notes_in)
        lay.addWidget(form)
        lay.addStretch()

        def next_step():
            if dp_in.value() > total:
                QMessageBox.warning(self, "Invalid Down Payment", "Down payment cannot exceed the order total.")
                return
            self._draft.update({
                "down_payment": dp_in.value(), "payment_method": method_in.currentText(),
                "notes": notes_in.toPlainText().strip(),
            })
            self.goto_preview_step()

        row, _ = _nav_row(back_cb=self.goto_charges_step, next_cb=next_step, next_label="Next: Order Review >")
        self._set_nav(row)
        self._set_body(page, "Step 5 — Billing & Payment", "Set downpayment amount and payment method", step_index=4)

    # ── Step 6: Order Preview ────────────────────────────────────────────

    def goto_preview_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        lay.setContentsMargins(10, 10, 10, 10)

        charges_sum = sum(c["amount"] for c in self._draft["additional_charges"])
        total = self._draft["base_total"] + charges_sum
        balance = max(0.0, total - self._draft["down_payment"])

        card = _card(elevated=True)
        clay = QVBoxLayout(card)
        clay.setContentsMargins(20, 18, 20, 18)
        clay.setSpacing(8)

        def row(label, value, big=False):
            r = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet(theme.subtitle_style(12))
            v = QLabel(str(value))
            v.setStyleSheet(f"font-size: {'15px' if big else '13px'}; font-weight: {'800' if big else '700'}; color: #FFFFFF;")
            v.setAlignment(Qt.AlignRight)
            v.setWordWrap(True)
            r.addWidget(l, 2)
            r.addWidget(v, 3)
            clay.addLayout(r)

        row("Client Name", self._draft["customer_name"])
        row("Contact", self._draft["contact"] or "-")
        row("Event Schedule", f"{self._draft['occasion']} — {self._draft['event_date']} {self._draft['event_time']}")
        row("Venue Location", self._draft["venue"])
        row("Headcount (Pax)", f"{self._draft['pax']} Guests")
        row("Selected Package", self._draft["package_name"])
        if self._draft["menu_selections"]:
            row("Menu Items", ", ".join(f"{m['item_name']}" for m in self._draft["menu_selections"]))
        if self._draft["additional_charges"]:
            row("Add-ons", ", ".join(f"{c['description']} (₱{c['amount']:,.2f})" for c in self._draft["additional_charges"]))
        lay.addWidget(card)

        totals = _card(accent=True)
        tlay = QVBoxLayout(totals)
        tlay.setContentsMargins(20, 16, 20, 16)
        tlay.setSpacing(6)

        def trow(label, value, size="14px", color=None):
            r = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet(f"font-size: {size}; font-weight: 700;")
            v = QLabel(str(value))
            v.setStyleSheet(f"font-size: {size}; font-weight: 800; color: {color or theme.TEXT};")
            v.setAlignment(Qt.AlignRight)
            r.addWidget(l)
            r.addWidget(v)
            tlay.addLayout(r)

        trow("Total Amount", f"₱{total:,.2f}")
        trow("Down Payment Paid", f"₱{self._draft['down_payment']:,.2f}", color=theme.SUCCESS)
        trow("Remaining Balance Due", f"₱{balance:,.2f}", size="18px", color=theme.ACCENT)
        lay.addWidget(totals)
        lay.addStretch()

        row_nav, _ = _nav_row(back_cb=self.goto_billing_step, next_cb=self._confirm_order, next_label="Confirm & Place Order >")
        confirm_btn = row_nav.itemAt(row_nav.count() - 1).widget()
        if isinstance(confirm_btn, QPushButton):
            confirm_btn.setIcon(icons.icon_check("#FFFFFF", 18))
        self._set_nav(row_nav)
        self._set_body(page, "Step 6 — Order Review", "Verify event details and confirm order", step_index=5)

    # ── Confirm -> write to DB, then Receipt step ────────────────────────

    def _confirm_order(self):
        draft = dict(self._draft)
        draft["actor"] = get_actor()
        try:
            result = repo.create_order(draft)
        except Exception as exc:
            QMessageBox.critical(self, "Order Failed", f"Could not save order:\n{exc}")
            return
        repo.record_terms_acknowledgement(result["booking_id"], terms.CURRENT_TERMS_VERSION, draft["customer_name"])
        self._confirmed_order = repo.get_order_detail(result["booking_id"])
        self.goto_receipt_step()

    def goto_receipt_step(self):
        self._cancel_btn.hide()

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)
        lay.setContentsMargins(10, 10, 10, 10)

        card = _card(accent=True)
        clay = QVBoxLayout(card)
        clay.setContentsMargins(28, 24, 28, 24)
        clay.setSpacing(12)

        ok_lbl = QLabel("ORDER CONFIRMED SUCCESSFULLY")
        ok_lbl.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {theme.SUCCESS};")
        clay.addWidget(ok_lbl)

        ref_lbl = QLabel(f"Booking Reference: {self._confirmed_order['booking_ref']}")
        ref_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {theme.GOLD};")
        clay.addWidget(ref_lbl)

        status_colors = theme.STATUS_COLORS
        summary = QLabel(
            f"Client: <b>{self._confirmed_order['customer_name']}</b><br>"
            f"Total: <b>₱{self._confirmed_order['total']:,.2f}</b> &nbsp;·&nbsp; "
            f"Paid: <b style='color:{theme.SUCCESS}'>₱{self._confirmed_order['paid']:,.2f}</b> &nbsp;·&nbsp; "
            f"Balance: <b style='color:{theme.ACCENT}'>₱{self._confirmed_order['balance']:,.2f}</b><br>"
            f"Status: <b style='color:{status_colors.get(self._confirmed_order['status'], theme.TEXT)}'>{self._confirmed_order['status']}</b>"
        )
        summary.setStyleSheet("font-size: 14px; line-height: 1.5;")
        clay.addWidget(summary)
        lay.addWidget(card)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        print_btn = QPushButton("  Print / Save Receipt PDF")
        print_btn.setIcon(icons.icon_download("#FFFFFF", 18))
        print_btn.setObjectName("Primary")
        print_btn.setMinimumHeight(54)
        print_btn.setCursor(Qt.PointingHandCursor)
        print_btn.clicked.connect(self._print_receipt)
        btn_row.addWidget(print_btn)

        done_btn = QPushButton("  Done — Back to Home")
        done_btn.setIcon(icons.icon_check("#94A3B8", 18))
        done_btn.setObjectName("Secondary")
        done_btn.setMinimumHeight(54)
        done_btn.setCursor(Qt.PointingHandCursor)
        done_btn.clicked.connect(lambda: self._on_finish())
        btn_row.addWidget(done_btn)
        lay.addLayout(btn_row)

        lay.addStretch()
        self._set_nav(QHBoxLayout())
        self._set_body(page, "Order Complete", "Thank you for choosing Jayraldine's Catering", step_index=None, show_cart=False)

    def _print_receipt(self):
        default_name = f"receipt_{self._confirmed_order['booking_ref']}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save Receipt PDF", default_name, "PDF Files (*.pdf)")
        if not path:
            return
        ok = exporter.export_order_receipt_pdf(path, self._confirmed_order)
        if ok:
            QMessageBox.information(self, "Receipt Saved", f"Receipt saved to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed", "Could not generate receipt PDF. Make sure reportlab is installed.")
