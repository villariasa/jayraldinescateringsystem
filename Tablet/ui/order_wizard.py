"""
The full tablet order-creation wizard (Tablet-mode.md sections 1-10, 13):

Customer -> Package -> Menu -> Additional Charges -> Billing -> Preview
-> Terms & Conditions -> Confirm -> Receipt -> Export

Nothing is written to the database until Confirm (after Terms acceptance) -
the draft lives entirely in self._draft until then, so an abandoned order
never leaves a half-finished row behind.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QScrollArea, QRadioButton, QButtonGroup, QCheckBox, QMessageBox,
    QTextEdit, QTextBrowser, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QTime

import utils.repository as repo
import utils.exporter as exporter
import utils.terms as terms
from utils.session import get_actor
from ui import theme
from ui.step_progress import StepProgress


def _card(elevated=False, accent=False):
    f = QFrame()
    theme.style_card(f, elevated=elevated, accent_border=accent)
    return f


def _nav_row(back_cb=None, next_cb=None, next_label="Next", next_enabled=True):
    row = QHBoxLayout()
    if back_cb:
        back_btn = QPushButton("←  Back")
        back_btn.setObjectName("Secondary")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setMinimumHeight(50)
        back_btn.clicked.connect(back_cb)
        row.addWidget(back_btn)
    row.addStretch()
    next_btn = None
    if next_cb:
        next_btn = QPushButton(next_label)
        next_btn.setObjectName("Primary")
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.setMinimumHeight(50)
        next_btn.setMinimumWidth(200)
        next_btn.setEnabled(next_enabled)
        next_btn.clicked.connect(next_cb)
        row.addWidget(next_btn)
    return row, next_btn


class OrderWizard(QWidget):
    def __init__(self, on_finish):
        super().__init__()
        self._on_finish = on_finish  # called with no args when wizard is closed/cancelled/done
        self._draft = {
            "customer_id": None, "customer_name": "", "contact": "", "email": "", "address": "",
            "event_date": QDate.currentDate().addDays(14).toString("yyyy-MM-dd"), "event_time": "18:00",
            "venue": "", "occasion": "", "pax": 60,
            "package_id": None, "package_name": "", "base_total": 0.0,
            "menu_selections": [], "additional_charges": [],
            "down_payment": 0.0, "payment_method": "Cash", "notes": "",
        }
        self._confirmed_order = None
        self._build_ui()
        self.goto_customer_step()

    def _build_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(36, 24, 36, 24)
        self._root.setSpacing(18)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        self._step_lbl = QLabel()
        self._step_lbl.setStyleSheet(theme.heading_style(22))
        title_box.addWidget(self._step_lbl)
        header.addLayout(title_box)
        header.addStretch()
        self._cancel_btn = QPushButton("✕  Cancel Order")
        self._cancel_btn.setObjectName("Danger")
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._cancel)
        header.addWidget(self._cancel_btn, alignment=Qt.AlignTop)
        self._root.addLayout(header)

        self._stepper = StepProgress()
        self._root.addWidget(self._stepper)

        self._body_scroll = QScrollArea()
        self._body_scroll.setWidgetResizable(True)
        self._body_scroll.setFrameShape(QFrame.NoFrame)
        self._root.addWidget(self._body_scroll, 1)

        self._nav_container = QVBoxLayout()
        self._root.addLayout(self._nav_container)
        self._nav_widget = None

    def _center_wrap(self, inner: QWidget, max_width: int = 780) -> QWidget:
        """Centers wizard content with a comfortable reading width instead of
        stretching every field across a full tablet-width screen."""
        outer = QWidget()
        lay = QHBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0)
        inner.setMaximumWidth(max_width)
        inner.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        lay.addStretch()
        lay.addWidget(inner)
        lay.addStretch()
        return outer

    def _set_body(self, widget: QWidget, step_title: str, step_index: int = None):
        self._step_lbl.setText(step_title)
        self._body_scroll.setWidget(self._center_wrap(widget))
        if step_index is not None:
            self._stepper.set_current(step_index)
            self._stepper.setVisible(True)
        else:
            self._stepper.setVisible(False)

    def _set_nav(self, row_layout):
        # Swap in a fresh container widget rather than picking apart the old
        # layout's children with deleteLater() — deleteLater() only takes
        # effect on the next event-loop tick, so the old buttons could still
        # render (stacked behind the new ones) for one frame. hide() takes
        # effect immediately, so do that first.
        if self._nav_widget is not None:
            self._nav_widget.hide()
            self._nav_container.removeWidget(self._nav_widget)
            self._nav_widget.deleteLater()

        container = QWidget()
        container.setLayout(row_layout)
        self._nav_container.addWidget(container)
        self._nav_widget = container

    def _cancel(self):
        if QMessageBox.question(self, "Cancel Order", "Discard this order? Nothing has been saved yet.",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._on_finish()

    def _field_label(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {theme.TEXT_MUTED}; margin-top: 6px;")
        return l

    # ── Step 1: Customer ──────────────────────────────────────────────

    def goto_customer_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)

        intro = QLabel("Who is this order for?")
        intro.setStyleSheet(theme.subtitle_style(14))
        lay.addWidget(intro)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)
        new_btn = QPushButton("＋  New Customer")
        existing_btn = QPushButton("🔍  Existing Customer")
        for b in (new_btn, existing_btn):
            b.setObjectName("Secondary")
            b.setMinimumHeight(58)
            b.setCursor(Qt.PointingHandCursor)
        mode_row.addWidget(new_btn)
        mode_row.addWidget(existing_btn)
        lay.addLayout(mode_row)

        form_frame = _card()
        form_lay = QVBoxLayout(form_frame)
        form_lay.setContentsMargins(22, 22, 22, 22)
        form_lay.setSpacing(8)
        lay.addWidget(form_frame)
        lay.addStretch()

        name_in = QLineEdit(self._draft["customer_name"])
        name_in.setPlaceholderText("Full Name")
        contact_in = QLineEdit(self._draft["contact"])
        contact_in.setPlaceholderText("Contact Number")
        email_in = QLineEdit(self._draft["email"])
        email_in.setPlaceholderText("Email (optional)")
        address_in = QLineEdit(self._draft["address"])
        address_in.setPlaceholderText("Address")

        def highlight(btn, active):
            btn.setObjectName("Primary" if active else "Secondary")
            btn.setStyleSheet("")  # force re-polish via objectName QSS
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        def show_new_customer_form():
            self._draft["customer_id"] = None
            highlight(new_btn, True)
            highlight(existing_btn, False)
            while form_lay.count():
                item = form_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            form_lay.addWidget(self._field_label("CUSTOMER DETAILS"))
            for w in (name_in, contact_in, email_in, address_in):
                form_lay.addWidget(w)

        def show_existing_customer_search():
            self._draft["customer_id"] = None
            highlight(new_btn, False)
            highlight(existing_btn, True)
            while form_lay.count():
                item = form_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            form_lay.addWidget(self._field_label("SEARCH CUSTOMERS"))
            search_in = QLineEdit()
            search_in.setPlaceholderText("Search by name or contact number...")
            form_lay.addWidget(search_in)

            results_container = QVBoxLayout()
            results_container.setSpacing(8)
            results_widget = QWidget()
            results_widget.setLayout(results_container)
            form_lay.addWidget(results_widget)

            def do_search():
                while results_container.count():
                    item = results_container.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                found = repo.search_customers(search_in.text())
                if not found:
                    empty = QLabel("No matching customers.")
                    empty.setStyleSheet(theme.subtitle_style())
                    results_container.addWidget(empty)
                for c in found:
                    btn = QPushButton(f"{c['name']}   •   {c['contact'] or 'no contact'}")
                    btn.setObjectName("Secondary")
                    btn.setMinimumHeight(48)
                    btn.setCursor(Qt.PointingHandCursor)

                    def select(_, cust=c):
                        self._draft.update({
                            "customer_id": cust["id"], "customer_name": cust["name"],
                            "contact": cust["contact"], "email": cust["email"], "address": cust["address"],
                        })
                        self.goto_event_step()

                    btn.clicked.connect(select)
                    results_container.addWidget(btn)

            search_in.textChanged.connect(lambda _: do_search())
            do_search()

        new_btn.clicked.connect(lambda: show_new_customer_form())
        existing_btn.clicked.connect(lambda: show_existing_customer_search())
        show_new_customer_form()

        def next_step():
            if self._draft.get("customer_id") is None:
                name = name_in.text().strip()
                if not name:
                    QMessageBox.warning(self, "Missing Name", "Please enter the customer's name.")
                    return
                dup = repo.find_possible_duplicate_customer(contact_in.text().strip(), name)
                if dup and QMessageBox.question(
                    self, "Possible Existing Customer",
                    f"A customer with this contact information may already exist:\n\n{dup['name']} ({dup['contact']})\n\nUse this existing customer instead?",
                    QMessageBox.Yes | QMessageBox.No,
                ) == QMessageBox.Yes:
                    self._draft.update({"customer_id": dup["id"], "customer_name": dup["name"], "contact": dup["contact"]})
                else:
                    self._draft.update({
                        "customer_name": name, "contact": contact_in.text().strip(),
                        "email": email_in.text().strip(), "address": address_in.text().strip(),
                    })
            self.goto_event_step()

        row, _ = _nav_row(next_cb=next_step, next_label="Next: Event Details  →")
        self._set_nav(row)
        self._set_body(page, "Step 1 — Customer", step_index=0)

    # ── Step 2: Event details + Package ─────────────────────────────────

    def goto_event_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)

        form = _card()
        flay = QVBoxLayout(form)
        flay.setContentsMargins(22, 22, 22, 22)
        flay.setSpacing(8)

        date_edit = QDateEdit(QDate.fromString(self._draft["event_date"], "yyyy-MM-dd"))
        date_edit.setCalendarPopup(True)
        time_edit = QTimeEdit(QTime.fromString(self._draft["event_time"], "HH:mm"))
        venue_in = QLineEdit(self._draft["venue"])
        venue_in.setPlaceholderText("Venue")
        occasion_in = QLineEdit(self._draft["occasion"])
        occasion_in.setPlaceholderText("Occasion (e.g. Wedding, Birthday)")
        pax_in = QSpinBox()
        pax_in.setRange(1, 5000)
        pax_in.setValue(int(self._draft["pax"]))

        flay.addWidget(self._field_label("EVENT DETAILS"))
        grid = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Event Date"))
        col1.addWidget(date_edit)
        col1.addWidget(QLabel("Venue"))
        col1.addWidget(venue_in)
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Event Time"))
        col2.addWidget(time_edit)
        col2.addWidget(QLabel("Occasion"))
        col2.addWidget(occasion_in)
        grid.addLayout(col1)
        grid.addLayout(col2)
        flay.addLayout(grid)
        flay.addWidget(QLabel("Guests (Pax)"))
        flay.addWidget(pax_in)
        lay.addWidget(form)

        pkg_card = _card()
        pkg_lay = QVBoxLayout(pkg_card)
        pkg_lay.setContentsMargins(22, 22, 22, 22)
        pkg_lay.setSpacing(10)
        pkg_lay.addWidget(self._field_label("SELECT PACKAGE"))

        pkg_group = QButtonGroup(page)
        packages = repo.get_packages()
        selected_pkg = {"id": self._draft.get("package_id")}

        if not packages:
            warn = QLabel("⚠  No packages available. Go to Home → 'Import Master Data' first.")
            warn.setStyleSheet(f"color:{theme.WARNING}; font-size: 14px;")
            warn.setWordWrap(True)
            pkg_lay.addWidget(warn)

        for pkg in packages:
            opt = QFrame()
            theme.style_card(opt, elevated=True)
            opt_lay = QHBoxLayout(opt)
            opt_lay.setContentsMargins(14, 10, 14, 10)
            btn = QRadioButton()
            if pkg["id"] == self._draft.get("package_id"):
                btn.setChecked(True)
            btn.toggled.connect(lambda checked, p=pkg: selected_pkg.update(p) if checked else None)
            pkg_group.addButton(btn)
            opt_lay.addWidget(btn)

            info = QVBoxLayout()
            name_lbl = QLabel(pkg["name"])
            name_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
            desc_lbl = QLabel(pkg.get("description") or "")
            desc_lbl.setStyleSheet(theme.subtitle_style())
            desc_lbl.setWordWrap(True)
            info.addWidget(name_lbl)
            if pkg.get("description"):
                info.addWidget(desc_lbl)
            opt_lay.addLayout(info, 1)

            price_lbl = QLabel(f"₱{pkg['price_per_pax']:,.2f}/pax\nmin {pkg['min_pax']} pax")
            price_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {theme.ACCENT};")
            price_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            opt_lay.addWidget(price_lbl)

            pkg_lay.addWidget(opt)

        lay.addWidget(pkg_card)
        lay.addStretch()

        def next_step():
            if not venue_in.text().strip():
                QMessageBox.warning(self, "Missing Venue", "Please enter the event venue.")
                return
            if not selected_pkg.get("id"):
                QMessageBox.warning(self, "No Package Selected", "Please select a catering package.")
                return
            self._draft.update({
                "event_date": date_edit.date().toString("yyyy-MM-dd"),
                "event_time": time_edit.time().toString("HH:mm"),
                "venue": venue_in.text().strip(), "occasion": occasion_in.text().strip(),
                "pax": pax_in.value(), "package_id": selected_pkg["id"], "package_name": selected_pkg.get("name", ""),
                "base_total": float(selected_pkg.get("price_per_pax", 0)) * pax_in.value(),
            })
            self.goto_menu_step()

        row, _ = _nav_row(back_cb=self.goto_customer_step, next_cb=next_step, next_label="Next: Menu  →")
        self._set_nav(row)
        self._set_body(page, "Step 2 — Event & Package", step_index=1)

    # ── Step 3: Menu selection ──────────────────────────────────────────

    def goto_menu_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)

        choices = repo.get_package_menu_choices(self._draft["package_id"])
        selections = {}  # category -> selected item dict

        if not choices:
            info = _card()
            il = QVBoxLayout(info)
            il.setContentsMargins(20, 20, 20, 20)
            lbl = QLabel("This package has no configured menu choices. You may continue without selecting specific items.")
            lbl.setStyleSheet(theme.subtitle_style(14))
            lbl.setWordWrap(True)
            il.addWidget(lbl)
            lay.addWidget(info)

        for category, items in choices.items():
            cat_card = _card()
            cat_lay = QVBoxLayout(cat_card)
            cat_lay.setContentsMargins(20, 16, 20, 16)
            cat_lay.setSpacing(6)

            cat_lbl = QLabel(category)
            cat_lbl.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {theme.ACCENT};")
            cat_lay.addWidget(cat_lbl)

            group = QButtonGroup(page)
            for item in items:
                text = item["name"] + (f"   (+₱{item['price']:,.2f})" if item["price"] else "")
                btn = QRadioButton(text)
                existing = next((m for m in self._draft["menu_selections"] if m["category"] == category and m["item_name"] == item["name"]), None)
                if existing:
                    btn.setChecked(True)
                btn.toggled.connect(lambda checked, c=category, it=item: selections.update({c: it}) if checked else None)
                group.addButton(btn)
                cat_lay.addWidget(btn)

            lay.addWidget(cat_card)

        lay.addStretch()

        def next_step():
            self._draft["menu_selections"] = [
                {"item_name": it["name"], "category": cat, "price": it["price"], "quantity": 1}
                for cat, it in selections.items()
            ]
            self.goto_charges_step()

        row, _ = _nav_row(back_cb=self.goto_event_step, next_cb=next_step, next_label="Next: Additional Charges  →")
        self._set_nav(row)
        self._set_body(page, "Step 3 — Menu Selection", step_index=2)

    # ── Step 4: Additional Charges ───────────────────────────────────────

    def goto_charges_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)

        info = QLabel("Add any extra items, menu changes, or discounts. Use a negative amount for a discount.")
        info.setStyleSheet(theme.subtitle_style(14))
        info.setWordWrap(True)
        lay.addWidget(info)

        form_card = _card()
        form = QHBoxLayout(form_card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)
        desc_in = QLineEdit()
        desc_in.setPlaceholderText("Description (e.g. Additional Lechon, Discount - Loyalty)")
        amt_in = QDoubleSpinBox()
        amt_in.setRange(-1_000_000, 1_000_000)
        amt_in.setDecimals(2)
        amt_in.setPrefix("₱ ")
        amt_in.setFixedWidth(170)
        add_btn = QPushButton("＋ Add")
        add_btn.setObjectName("Primary")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setMinimumHeight(48)
        form.addWidget(desc_in, 3)
        form.addWidget(amt_in, 1)
        form.addWidget(add_btn)
        lay.addWidget(form_card)

        list_container = QVBoxLayout()
        list_container.setSpacing(8)
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
                row_l.setContentsMargins(16, 12, 16, 12)
                lbl = QLabel(c["description"])
                lbl.setStyleSheet("font-size: 14px; font-weight: 600;")
                is_discount = c["amount"] < 0
                amt_lbl = QLabel(f"− ₱{abs(c['amount']):,.2f}" if is_discount else f"₱{c['amount']:,.2f}")
                amt_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {theme.WARNING if is_discount else theme.SUCCESS};")
                del_btn = QPushButton("Remove")
                del_btn.setObjectName("Danger")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.clicked.connect(lambda _, idx=i: (self._draft["additional_charges"].pop(idx), refresh_list()))
                row_l.addWidget(lbl, 3)
                row_l.addWidget(amt_lbl, 1)
                row_l.addWidget(del_btn)
                list_container.addWidget(row_f)

        def add_charge():
            desc = desc_in.text().strip()
            amt = amt_in.value()
            if not desc or amt == 0:
                QMessageBox.warning(self, "Invalid Entry", "Enter a description and a non-zero amount.")
                return
            self._draft["additional_charges"].append({"description": desc, "amount": amt})
            desc_in.clear()
            amt_in.setValue(0)
            refresh_list()

        add_btn.clicked.connect(add_charge)
        refresh_list()
        lay.addStretch()

        row, _ = _nav_row(back_cb=self.goto_menu_step, next_cb=self.goto_billing_step, next_label="Next: Billing  →")
        self._set_nav(row)
        self._set_body(page, "Step 4 — Additional Charges", step_index=3)

    # ── Step 5: Billing ─────────────────────────────────────────────────

    def goto_billing_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)

        charges_sum = sum(c["amount"] for c in self._draft["additional_charges"])
        total = self._draft["base_total"] + charges_sum

        summary = _card(accent=True)
        slay = QVBoxLayout(summary)
        slay.setContentsMargins(22, 18, 22, 18)
        slay.setSpacing(8)
        for label, val, big in [
            ("Base Package Price", self._draft["base_total"], False),
            ("Additional Charges / Discounts", charges_sum, False),
            ("Final Order Total", total, True),
        ]:
            row = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet("font-size: 14px;" if not big else "font-size: 15px; font-weight: 700;")
            v = QLabel(f"₱{val:,.2f}")
            v.setStyleSheet(f"font-size: {'22px' if big else '15px'}; font-weight: 800; color: {theme.ACCENT if big else theme.TEXT};")
            v.setAlignment(Qt.AlignRight)
            row.addWidget(l)
            row.addWidget(v)
            slay.addLayout(row)
        lay.addWidget(summary)

        form = _card()
        flay = QVBoxLayout(form)
        flay.setContentsMargins(22, 20, 22, 20)
        flay.setSpacing(6)
        flay.addWidget(self._field_label("DOWN PAYMENT"))
        dp_in = QDoubleSpinBox()
        dp_in.setRange(0, 10_000_000)
        dp_in.setDecimals(2)
        dp_in.setPrefix("₱ ")
        dp_in.setValue(float(self._draft.get("down_payment") or 0.0))
        flay.addWidget(dp_in)

        flay.addWidget(self._field_label("PAYMENT METHOD"))
        method_in = QComboBox()
        method_in.addItems(["Cash", "GCash", "Maya", "Bank Transfer", "Other"])
        method_in.setCurrentText(self._draft.get("payment_method", "Cash"))
        flay.addWidget(method_in)

        flay.addWidget(self._field_label("NOTES"))
        notes_in = QTextEdit(self._draft.get("notes", ""))
        notes_in.setFixedHeight(80)
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

        row, _ = _nav_row(back_cb=self.goto_charges_step, next_cb=next_step, next_label="Next: Preview  →")
        self._set_nav(row)
        self._set_body(page, "Step 5 — Billing", step_index=4)

    # ── Step 6: Order Preview ────────────────────────────────────────────

    def goto_preview_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)

        charges_sum = sum(c["amount"] for c in self._draft["additional_charges"])
        total = self._draft["base_total"] + charges_sum
        balance = max(0.0, total - self._draft["down_payment"])

        card = _card()
        clay = QVBoxLayout(card)
        clay.setContentsMargins(24, 22, 24, 22)
        clay.setSpacing(10)

        def row(label, value, big=False):
            r = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet(theme.subtitle_style(13))
            v = QLabel(str(value))
            v.setStyleSheet(f"font-size: {'16px' if big else '14px'}; font-weight: {'800' if big else '600'};")
            v.setAlignment(Qt.AlignRight)
            v.setWordWrap(True)
            r.addWidget(l, 2)
            r.addWidget(v, 3)
            clay.addLayout(r)

        row("Customer", self._draft["customer_name"])
        row("Contact", self._draft["contact"] or "—")
        row("Event", f"{self._draft['occasion']} — {self._draft['event_date']} {self._draft['event_time']}")
        row("Venue", self._draft["venue"])
        row("Guests", self._draft["pax"])
        row("Package", self._draft["package_name"])
        if self._draft["menu_selections"]:
            row("Selected Menu", ", ".join(f"{m['category']}: {m['item_name']}" for m in self._draft["menu_selections"]))
        if self._draft["additional_charges"]:
            row("Additional Charges", ", ".join(f"{c['description']} (₱{c['amount']:,.2f})" for c in self._draft["additional_charges"]))
        lay.addWidget(card)

        totals = _card(accent=True)
        tlay = QVBoxLayout(totals)
        tlay.setContentsMargins(24, 20, 24, 20)
        tlay.setSpacing(8)

        def trow(label, value, size="15px", color=None):
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
        trow("Down Payment", f"₱{self._draft['down_payment']:,.2f}", color=theme.SUCCESS)
        trow("Remaining Balance", f"₱{balance:,.2f}", size="20px", color=theme.ACCENT)
        lay.addWidget(totals)

        lay.addStretch()

        row_nav, _ = _nav_row(back_cb=self.goto_billing_step, next_cb=self.goto_terms_step, next_label="Next: Terms && Conditions  →")
        self._set_nav(row_nav)
        self._set_body(page, "Step 6 — Order Preview", step_index=5)

    # ── Step 7: Terms & Conditions ───────────────────────────────────────

    def goto_terms_step(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)

        header_card = _card(accent=True)
        hlay = QVBoxLayout(header_card)
        hlay.setContentsMargins(22, 18, 22, 18)
        title = QLabel("📋  " + terms.TERMS_TITLE)
        title.setStyleSheet(theme.heading_style(17))
        title.setWordWrap(True)
        hlay.addWidget(title)
        sub = QLabel("Please read the Catering Terms and Conditions below before confirming this order.")
        sub.setStyleSheet(theme.subtitle_style(13))
        sub.setWordWrap(True)
        hlay.addWidget(sub)
        lay.addWidget(header_card)

        text_card = _card()
        text_card.setMinimumHeight(360)
        tlay = QVBoxLayout(text_card)
        tlay.setContentsMargins(4, 4, 4, 4)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setStyleSheet(
            f"border: none; background: transparent; font-size: 14px; padding: 18px; color: {theme.TEXT};"
        )
        html_body = terms.TERMS_TEXT.strip().replace("\n\n", "</p><p>").replace("\n", "<br>")
        browser.setHtml(
            f"<div style='line-height:1.6;'><p>{html_body}</p>"
            f"<p style='color:{theme.TEXT_FAINT}; font-size:12px; margin-top:16px;'>Terms version {terms.CURRENT_TERMS_VERSION}</p></div>"
        )
        tlay.addWidget(browser)
        lay.addWidget(text_card, 1)

        ack_card = QFrame()
        theme.style_card(ack_card, elevated=True, accent_border=True)
        alay = QHBoxLayout(ack_card)
        alay.setContentsMargins(20, 16, 20, 16)
        ack_cb = QCheckBox(terms.TERMS_ACKNOWLEDGEMENT_LABEL)
        ack_cb.setStyleSheet("font-size: 15px; font-weight: 700;")
        alay.addWidget(ack_cb)
        lay.addWidget(ack_card)

        row, next_btn = _nav_row(back_cb=self.goto_preview_step, next_cb=self._confirm_order,
                                 next_label="✔  Confirm Order", next_enabled=False)
        ack_cb.toggled.connect(lambda checked: next_btn.setEnabled(checked))
        self._set_nav(row)
        self._set_body(page, "Step 7 — Terms & Conditions", step_index=6)

    # ── Confirm -> write to DB, then Receipt/Export step ─────────────────

    def _confirm_order(self):
        draft = dict(self._draft)
        draft["actor"] = get_actor()
        try:
            result = repo.create_order(draft)
        except Exception as exc:
            QMessageBox.critical(self, "Order Failed", f"Could not save the order:\n{exc}")
            return
        repo.record_terms_acknowledgement(result["booking_id"], terms.CURRENT_TERMS_VERSION, draft["customer_name"])
        self._confirmed_order = repo.get_order_detail(result["booking_id"])
        self.goto_receipt_step()

    def goto_receipt_step(self):
        self._cancel_btn.hide()  # the order is already saved — nothing left to cancel

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(18)
        lay.setContentsMargins(0, 20, 0, 0)

        card = _card(accent=True)
        clay = QVBoxLayout(card)
        clay.setContentsMargins(30, 28, 30, 28)
        clay.setSpacing(14)

        ok_lbl = QLabel(f"✔  Order Confirmed")
        ok_lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {theme.SUCCESS};")
        clay.addWidget(ok_lbl)

        ref_lbl = QLabel(self._confirmed_order["booking_ref"])
        ref_lbl.setStyleSheet(f"font-size: 15px; color: {theme.TEXT_MUTED};")
        clay.addWidget(ref_lbl)

        status_colors = theme.STATUS_COLORS
        summary = QLabel(
            f"Customer: <b>{self._confirmed_order['customer_name']}</b><br>"
            f"Total: <b>₱{self._confirmed_order['total']:,.2f}</b> &nbsp;·&nbsp; "
            f"Paid: <b style='color:{theme.SUCCESS}'>₱{self._confirmed_order['paid']:,.2f}</b> &nbsp;·&nbsp; "
            f"Balance: <b style='color:{theme.ACCENT}'>₱{self._confirmed_order['balance']:,.2f}</b><br>"
            f"Status: <b style='color:{status_colors.get(self._confirmed_order['status'], theme.TEXT)}'>{self._confirmed_order['status']}</b>"
        )
        summary.setStyleSheet("font-size: 14px;")
        clay.addWidget(summary)
        lay.addWidget(card)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        print_btn = QPushButton("🖨  Print / Save Receipt PDF")
        print_btn.setObjectName("Primary")
        print_btn.setMinimumHeight(56)
        print_btn.setCursor(Qt.PointingHandCursor)
        print_btn.clicked.connect(self._print_receipt)
        btn_row.addWidget(print_btn)

        done_btn = QPushButton("Done — Back to Home")
        done_btn.setObjectName("Secondary")
        done_btn.setMinimumHeight(56)
        done_btn.setCursor(Qt.PointingHandCursor)
        done_btn.clicked.connect(lambda: self._on_finish())
        btn_row.addWidget(done_btn)
        lay.addLayout(btn_row)

        lay.addStretch()
        self._set_nav(QHBoxLayout())
        self._set_body(page, "Step 8 — Receipt", step_index=None)

    def _print_receipt(self):
        default_name = f"receipt_{self._confirmed_order['booking_ref']}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save Receipt PDF", default_name, "PDF Files (*.pdf)")
        if not path:
            return
        ok = exporter.export_order_receipt_pdf(path, self._confirmed_order)
        if ok:
            QMessageBox.information(self, "Receipt Saved", f"Receipt saved to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed", "Could not generate the receipt PDF. Make sure reportlab is installed.")
