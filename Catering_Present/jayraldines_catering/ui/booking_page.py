import csv
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QHeaderView,
    QDialog, QFileDialog, QMessageBox, QInputDialog, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, btn_icon_red, get_icon
from utils.theme import ThemeManager
from components.booking_modal import BookingModal
from components.dialogs import confirm, success
from components.filter_popover import FilterPopover
import utils.repository as repo
from utils.session import get_actor
from utils.signals import app_events


_STATUS_COLORS = {
    "CONFIRMED": ("#22C55E", "rgba(34,197,94,.15)", "rgba(34,197,94,.3)"),
    "PENDING":   ("#F59E0B", "rgba(245,158,11,.15)", "rgba(245,158,11,.3)"),
    "CANCELLED": ("#EF4444", "rgba(239,68,68,.15)",  "rgba(239,68,68,.3)"),
}


class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")


def _status_badge(text):
    color, bg, border = _STATUS_COLORS.get(text, ("#9CA3AF", "rgba(156,163,175,.15)", "rgba(156,163,175,.3)"))
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-weight:700;font-size:11px;padding:4px 10px;border-radius:12px;"
        f"background:{bg};color:{color};border:1px solid {border};"
    )
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


def _action_buttons(status, on_approve, on_decline):
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(4, 0, 4, 0)
    row.setSpacing(6)
    if status == "PENDING":
        approve_btn = QPushButton()
        approve_btn.setIcon(get_icon("check", color="#22C55E", size=QSize(16, 16)))
        approve_btn.setIconSize(QSize(16, 16))
        approve_btn.setFixedSize(28, 28)
        approve_btn.setStyleSheet(
            "border-radius:14px;"
            "background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.3);"
        )
        approve_btn.setCursor(Qt.PointingHandCursor)
        approve_btn.setToolTip("Approve")
        approve_btn.clicked.connect(on_approve)
        row.addWidget(approve_btn)

        decline_btn = QPushButton()
        decline_btn.setIcon(get_icon("x-circle", color="#EF4444", size=QSize(16, 16)))
        decline_btn.setIconSize(QSize(16, 16))
        decline_btn.setFixedSize(28, 28)
        decline_btn.setStyleSheet(
            "border-radius:14px;"
            "background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3);"
        )
        decline_btn.setCursor(Qt.PointingHandCursor)
        decline_btn.setToolTip("Decline")
        decline_btn.clicked.connect(on_decline)
        row.addWidget(decline_btn)
    else:
        locked_lbl = QLabel("—")
        locked_lbl.setStyleSheet("font-size:13px;")
        row.addWidget(locked_lbl)
    row.addStretch()
    return widget


class BookingPage(QWidget):
    def __init__(self):
        super().__init__()
        db_rows = repo.get_all_bookings()
        self._bookings = db_rows if db_rows else []
        self._active_filter = "All"
        self._filter_popover = None
        self._build_ui()
        app_events().booking_saved.connect(self._refresh_bookings)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_bookings()

    def _refresh_bookings(self):
        db_rows = repo.get_all_bookings()
        if db_rows is not None:
            self._bookings = db_rows
            self._populate_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        header_row = QHBoxLayout()
        v = QVBoxLayout()
        v.setSpacing(4)
        title = QLabel("Orders & Bookings")
        title.setObjectName("pageTitle")
        sub = QLabel("Manage all catering reservations and upcoming events.")
        sub.setObjectName("subtitle")
        v.addWidget(title)
        v.addWidget(sub)
        header_row.addLayout(v)
        header_row.addStretch()

        self.btn_new = QPushButton("  New Booking")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.setIcon(btn_icon_primary("plus"))
        self.btn_new.setIconSize(QSize(15, 15))
        self.btn_new.clicked.connect(self._open_modal)
        header_row.addWidget(self.btn_new)
        layout.addLayout(header_row)

        table_card = AnimatedCard()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(24, 24, 24, 24)
        table_layout.setSpacing(16)

        t_head = QHBoxLayout()
        t_title = QLabel("Current Bookings")
        t_title.setObjectName("h2")
        t_head.addWidget(t_title)
        t_head.addStretch()

        self._btn_filter = QPushButton("  Filter")
        self._btn_filter.setObjectName("secondaryButton")
        self._btn_filter.setIcon(btn_icon_secondary("filter"))
        self._btn_filter.setIconSize(QSize(14, 14))
        self._btn_filter.clicked.connect(self._open_filter)

        btn_export = QPushButton("  Export")
        btn_export.setObjectName("secondaryButton")
        btn_export.setIcon(btn_icon_secondary("export"))
        btn_export.setIconSize(QSize(14, 14))
        btn_export.clicked.connect(self._export_csv)

        t_head.addWidget(self._btn_filter)
        t_head.addWidget(btn_export)
        table_layout.addLayout(t_head)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)
        self.cards_layout.setSpacing(12)

        self.scroll_area.setWidget(self.cards_container)
        table_layout.addWidget(self.scroll_area)
        layout.addWidget(table_card)

        self._populate_table()

    def _visible_bookings(self):
        f = self._active_filter
        if f == "All" or not f:
            return self._bookings
        if isinstance(f, list):
            return [b for b in self._bookings if b["status"] in f]
        return [b for b in self._bookings if b["status"] == f]

    def _populate_table(self, data=None):
        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = data if data is not None else self._visible_bookings()

        if not rows:
            empty_lbl = QLabel("No bookings found.")
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty_lbl)
        else:
            for b in rows:
                card = self._create_booking_card(b)
                self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _create_booking_card(self, b: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("entryCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(16)

        # Col 1: Date & Reference ID
        c1 = QVBoxLayout()
        c1.setSpacing(2)
        ref_lbl = QLabel(b["id"])
        ref_lbl.setStyleSheet("font-weight: 800; font-size: 13px; color: #E11D48;")
        date_lbl = QLabel(b["date"])
        date_lbl.setObjectName("subtitle")
        c1.addWidget(ref_lbl)
        c1.addWidget(date_lbl)
        lay.addLayout(c1, 1)

        # Col 2: Client Name & Pax
        c2 = QVBoxLayout()
        c2.setSpacing(2)
        name_lbl = QLabel(b["name"])
        name_lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
        pax_lbl = QLabel(f"{b['pax']} pax")
        pax_lbl.setObjectName("subtitle")
        c2.addWidget(name_lbl)
        c2.addWidget(pax_lbl)
        lay.addLayout(c2, 2)

        # Col 3: Total Amount
        c3 = QVBoxLayout()
        c3.setSpacing(2)
        tot_title = QLabel("TOTAL")
        tot_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #6B7280; letter-spacing: 0.5px;")
        tot_val = QLabel(str(b["total"]))
        tot_val.setStyleSheet("font-weight: 800; font-size: 14px; color: #F59E0B;")
        c3.addWidget(tot_title)
        c3.addWidget(tot_val)
        lay.addLayout(c3, 1)

        # Col 4: Status Badge & Reason/Approvals
        c4 = QVBoxLayout()
        c4.setSpacing(4)
        c4.setAlignment(Qt.AlignCenter)
        c4.addWidget(_status_badge(b["status"]), alignment=Qt.AlignLeft)
        if b["status"] == "CANCELLED" and b.get("cancellation_reason"):
            reason_lbl = QLabel(b["cancellation_reason"])
            reason_lbl.setStyleSheet("color:#DC2626;font-size:10px;font-style:italic;")
            reason_lbl.setWordWrap(True)
            c4.addWidget(reason_lbl)
        elif b["status"] == "PENDING":
            bref = b["id"]
            c4.addWidget(_action_buttons(
                b["status"],
                on_approve=lambda _, r=bref: self._approve_booking(r),
                on_decline=lambda _, r=bref: self._decline_booking(r)
            ))
        lay.addLayout(c4, 2)

        # Col 5: Actions (Edit, Delete, Confirmation)
        actions_w = QFrame()
        actions_w.setStyleSheet("background: transparent;")
        actions_l = QHBoxLayout(actions_w)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(6)

        bref = b["id"]

        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(13, 13)))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet("background:transparent;border:none;")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setToolTip("Edit booking")
        edit_btn.setEnabled(b["status"] == "PENDING")
        if b["status"] != "PENDING":
            edit_btn.setStyleSheet("background:transparent;border:none;opacity:0.3;")
        edit_btn.clicked.connect(lambda _, r=bref: self._edit_booking(r))

        del_btn = QPushButton()
        del_btn.setIcon(btn_icon_red("trash"))
        del_btn.setIconSize(QSize(13, 13))
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("border:none;background:transparent;")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip("Delete booking")
        del_btn.clicked.connect(lambda _, r=bref: self._delete_booking(r))

        confirm_btn = QPushButton()
        confirm_btn.setIcon(get_icon("bell", color="#9CA3AF", size=QSize(13, 13)))
        confirm_btn.setIconSize(QSize(13, 13))
        confirm_btn.setFixedSize(30, 30)
        confirm_btn.setStyleSheet("background:transparent;border:none;")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setToolTip("Send Confirmation Email")
        confirm_btn.setEnabled(b["status"] == "CONFIRMED")
        if b["status"] != "CONFIRMED":
            confirm_btn.setStyleSheet("background:transparent;border:none;opacity:0.3;")
        confirm_btn.clicked.connect(lambda _, r=bref: self._send_confirmation(r))

        actions_l.addWidget(edit_btn)
        actions_l.addWidget(del_btn)
        actions_l.addWidget(confirm_btn)
        lay.addWidget(actions_w)

        return card

    def _approve_booking(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b or b["status"] != "PENDING":
            return
        if b.get("db_id"):
            try:
                from datetime import datetime
                event_date = datetime.strptime(b["date"].strip(), "%b %d, %Y").date()
                cap = repo.check_date_capacity(event_date, exclude_id=b["db_id"])
                pax = int(b["pax"])
                if cap["booked_pax"] + pax > cap["max_pax"]:
                    QMessageBox.warning(
                        self, "Capacity Exceeded",
                        f"Cannot approve: this would put {cap['booked_pax'] + pax} pax on {b['date']}.\n"
                        f"Maximum daily capacity is {cap['max_pax']} pax."
                    )
                    return
            except Exception as exc:
                print(f"[capacity check] {exc}")
        if not confirm(self, title="Approve Booking",
                       message=f"Approve booking for '{b['name']}'?",
                       confirm_label="Approve"):
            return
        try:
            if b.get("db_id"):
                repo.update_booking_status(b["db_id"], "CONFIRMED")
                try:
                    detail = repo.get_booking_detail(b["db_id"])
                    if detail and detail.get("customer_id"):
                        repo.recalculate_loyalty(detail["customer_id"])
                except Exception:
                    pass
                try:
                    repo.sync_kitchen_from_bookings()
                except Exception:
                    pass
            b["status"] = "CONFIRMED"
            self._populate_table()
            success(self, message="Booking approved successfully.")
            repo.write_audit_log(get_actor(), "APPROVE", "bookings", b.get("db_id"), None, {"status": "CONFIRMED"})
            if b.get("db_id"):
                try:
                    repo.auto_create_invoice(b["db_id"])
                except Exception as exc:
                    print(f"[booking] auto_create_invoice failed: {exc}")
            try:
                repo.push_notification(
                    "success",
                    "Booking Confirmed",
                    f"Booking for {b.get('name', '')} on {b.get('date', '')} has been confirmed.",
                    "#22C55E",
                )
            except Exception:
                pass
            if b.get("db_id"):
                self._send_confirmation_auto(b)
            app_events().booking_saved.emit()
        except Exception as exc:
            QMessageBox.warning(self, "Cannot Approve", str(exc))

    def _decline_booking(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b or b["status"] != "PENDING":
            return
        reason, ok = QInputDialog.getText(
            self, "Cancellation Reason",
            f"Enter reason for declining booking for '{b['name']}' (optional):"
        )
        if not ok:
            return
        if not confirm(self, title="Decline Booking",
                       message=f"Decline booking for '{b['name']}'? This will mark it as Cancelled.",
                       confirm_label="Decline", danger=True):
            return
        b["status"] = "CANCELLED"
        if b.get("db_id"):
            repo.update_booking_status(b["db_id"], "CANCELLED", reason.strip() or None)
            repo.write_audit_log(get_actor(), "CANCEL", "bookings", b["db_id"], None, {"status": "CANCELLED", "reason": reason.strip()})
        self._populate_table()
        success(self, message="Booking declined.")

    def _send_confirmation_auto(self, b: dict) -> None:
        """Auto-trigger confirmation email on approval (best-effort, silent on failure)."""
        try:
            detail = repo.get_booking_detail(b["db_id"]) if b.get("db_id") else None
            if not detail:
                return
            biz = repo.get_business_info()
            booking_data = {**detail, "business_contact": biz.get("contact", "")}
            smtp = repo.get_smtp_config()
            if detail.get("email") and smtp.get("smtp_host"):
                from utils.mailer import send_booking_confirmation_email
                ok, _ = send_booking_confirmation_email(smtp, detail["email"], booking_data)
                if ok and detail.get("db_id"):
                    repo.log_confirmation_sent(detail["db_id"], "email")
        except Exception as exc:
            print(f"[booking] auto-confirm send failed: {exc}")

    def _send_confirmation(self, ref: str) -> None:
        """Manual resend of confirmation for a CONFIRMED booking."""
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b or b["status"] != "CONFIRMED" or not b.get("db_id"):
            QMessageBox.information(self, "Not Available",
                "Confirmation can only be resent for confirmed bookings with a database record.")
            return
        detail = repo.get_booking_detail(b["db_id"])
        if not detail:
            return
        biz = repo.get_business_info()
        booking_data = {**detail, "business_contact": biz.get("contact", "")}
        smtp = repo.get_smtp_config()
        errors = []
        sent_email = False
        if detail.get("email") and smtp.get("smtp_host"):
            from utils.mailer import send_booking_confirmation_email
            ok, err = send_booking_confirmation_email(smtp, detail["email"], booking_data)
            if ok:
                repo.log_confirmation_sent(detail["db_id"], "email")
                sent_email = True
            else:
                errors.append(f"Email: {err}")
        if sent_email:
            QMessageBox.information(self, "Confirmation Sent",
                f"Booking confirmation has been sent via email to:\n{detail['email']}")
        elif errors:
            QMessageBox.warning(self, "Send Failed", "\n".join(errors))
        else:
            QMessageBox.information(self, "No Channel",
                "No email configured for this booking.\n"
                "Ensure customer has an email and SMTP is configured in Settings.")

    def _delete_booking(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b:
            return
        if not confirm(self, title="Delete Booking",
                       message=f"Are you sure you want to delete booking for '{b['name']}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if b.get("db_id"):
            repo.delete_booking(b["db_id"])
        self._bookings = [x for x in self._bookings if x["id"] != ref]
        self._populate_table()
        success(self, message="Booking deleted successfully.")

    def _edit_booking(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b or b["status"] != "PENDING":
            return
        modal = BookingModal(self, booking_data=b)
        modal.booking_saved.connect(lambda data, orig=b: self._update_booking(orig, data))
        modal.exec()

    def _update_booking(self, orig, data):
        if orig.get("db_id"):
            repo.update_booking(orig["db_id"], data)
        orig.update({
            "name":  data["name"],
            "date":  data["date"],
            "pax":   str(data["pax"]),
            "total": f"₱ {data['total']:,}",
        })
        self._populate_table()
        success(self, message="Booking updated successfully.")

    def _open_modal(self):
        modal = BookingModal(self)
        modal.booking_saved.connect(self._add_booking)
        modal.exec()

    def _add_booking(self, data):
        result = repo.create_booking(data)
        bkg_id = result["booking_ref"] if result else f"BKG-{len(self._bookings) + 1:03d}"
        db_id  = result["booking_id"]  if result else None

        self._bookings.append({
            "db_id":  db_id,
            "date":   data["date"],
            "id":     bkg_id,
            "name":   data["name"],
            "pax":    str(data["pax"]),
            "total":  f"₱ {data['total']:,}",
            "status": data["status"],
        })
        self._populate_table()

        email_status = self._send_approval_request(data, bkg_id)
        if email_status is True:
            msg = f"Booking created successfully.\nConfirmation email sent to {data.get('email', '')}."
        elif email_status is False:
            msg = "Booking created successfully.\nCould not send confirmation email — check SMTP settings."
        else:
            msg = "Booking created successfully."
        success(self, message=msg)

        try:
            repo.push_notification(
                type_="info",
                title="New Booking Request",
                message=f"{data['name']} submitted a new booking request for {data['pax']} pax on {data['date']}.",
                color="#3B82F6"
            )
        except Exception as exc:
            print(f"[Notification] Failed to create in-app notification: {exc}")

        app_events().booking_saved.emit()

    def _send_approval_request(self, data: dict, bkg_ref: str):
        """Send a booking approval request email to the customer.
        Returns True on success, False on failure, None if email/SMTP not configured."""
        try:
            email = data.get("email", "")
            if not email or "@" not in email:
                return None
            smtp = repo.get_smtp_config()
            if not smtp.get("smtp_host"):
                return None
            biz = repo.get_business_info()
            booking_data = {
                **data,
                "booking_ref":      bkg_ref,
                "business_contact": biz.get("contact", ""),
                "business_name":    biz.get("name", "Jayraldine's Catering"),
                "event_date":       data.get("date", "—"),
                "event_time":       data.get("time", "—"),
            }
            from utils.mailer import send_booking_approval_request_email
            ok, err = send_booking_approval_request_email(smtp, email, booking_data)
            if ok:
                print(f"[booking] Approval request email sent to {email}")
                return True
            else:
                print(f"[booking] Approval request email failed: {err}")
                return False
        except Exception as exc:
            print(f"[booking] send_approval_request failed: {exc}")
            return False

    def _open_filter(self):
        if self._filter_popover is None:
            win = self.window()
            self._filter_popover = FilterPopover(
                parent=win if win else self,
                statuses=["All", "PENDING", "CONFIRMED", "CANCELLED"],
            )
            self._filter_popover.filter_applied.connect(self._on_filter_applied)
        self._filter_popover.toggle_anchored(self._btn_filter)

    def _on_filter_applied(self, result):
        status = result.get("statuses", ["All"])[0]
        self._active_filter = "All" if not status or status == "All" else status
        self._populate_table()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Bookings", "bookings.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Date", "Client", "Pax", "Total", "Status"])
            for b in self._bookings:
                writer.writerow([b["id"], b["date"], b["name"], b["pax"], b["total"], b["status"]])
        QMessageBox.information(self, "Export", f"Exported to:\n{path}")

    def filter_search(self, text):
        q = text.lower()
        filtered = [b for b in self._bookings if q in b["name"].lower() or q in b["id"].lower() or q in b["date"].lower()]
        self._populate_table(filtered)

