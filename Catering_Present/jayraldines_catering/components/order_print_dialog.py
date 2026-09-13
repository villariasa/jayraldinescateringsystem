"""
Order Print & Export Dialog for Banquet Event Orders / Kitchen Slips.

Displays a clean, printable order slip containing:
- Customer Name
- Location / Venue
- Date & Time
- Pax (Guest Count)
- Packages & Itemized Dishes / Menu
- Additional Add-ons strictly WITHOUT price amounts ("walay price mount")
"""

import os
import re
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextBrowser, QFileDialog, QMessageBox, QApplication,
    QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QTextDocument, QFont

try:
    from PySide6.QtPrintSupport import QPrinter, QPrintDialog
    PRINTER_SUPPORT = True
except ImportError:
    PRINTER_SUPPORT = False

from utils.icons import get_icon
import utils.repository as repo
import utils.exporter as exporter
from components.dialogs import success


class OrderPrintDialog(QDialog):
    """
    Banquet Event Order (BEO) / Kitchen Order Slip Print & Export Dialog.
    """

    def __init__(self, booking_id_or_ref, parent=None):
        super().__init__(parent)
        self.booking_id_or_ref = booking_id_or_ref
        self._booking = self._load_booking_data(booking_id_or_ref)
        self._business = repo.get_business_info() or {
            "name": "Jayraldine's Catering Services",
            "address": "Cebu City, Philippines",
            "contact": "0912-345-6789",
            "email": "info@jayraldinescatering.com"
        }

        order_ref = self._booking.get("id") or self._booking.get("booking_ref") or "Order"
        self.setWindowTitle(f"Banquet Order Slip — {order_ref}")
        self.resize(760, 780)
        self.setMinimumSize(600, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #0B1220;
                color: #F8FAFC;
            }
        """)

        self._build_ui()

    def _load_booking_data(self, b_id) -> dict:
        """Fetch full booking details with dishes, package name, and additional charges."""
        data = None
        if isinstance(b_id, int):
            data = repo.get_booking_detail(b_id)
        elif isinstance(b_id, str):
            # Try to resolve by booking ref or numeric ID
            all_b = repo.get_all_bookings()
            match = next((b for b in all_b if b.get("id") == b_id or b.get("booking_ref") == b_id), None)
            if match and match.get("db_id"):
                data = repo.get_booking_detail(match["db_id"])
            elif match:
                data = match
        elif isinstance(b_id, dict):
            db_id = b_id.get("db_id")
            if db_id:
                data = repo.get_booking_detail(db_id)
            if not data:
                data = b_id

        if not data:
            data = {}
        return data

    def _build_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(20, 20, 20, 20)
        root_lay.setSpacing(14)

        # Header Bar
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("printer", color="#E11D48", size=QSize(28, 28)).pixmap(28, 28))
        header.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("Banquet Event Order & Kitchen Slip")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")
        sub_lbl = QLabel("Official order dispatch sheet with menu dishes & additional items (prices hidden)")
        sub_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        header.addLayout(title_col)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
                color: #EF4444;
                border-color: #EF4444;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        root_lay.addLayout(header)

        # Document Preview Container
        preview_card = QFrame()
        preview_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #334155;
            }
        """)
        p_lay = QVBoxLayout(preview_card)
        p_lay.setContentsMargins(4, 4, 4, 4)

        self._doc_browser = QTextBrowser()
        self._doc_browser.setOpenExternalLinks(False)
        self._doc_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                color: #0F172A;
                border: none;
                padding: 16px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
        """)
        self._html_content = self._generate_slip_html()
        self._doc_browser.setHtml(self._html_content)
        p_lay.addWidget(self._doc_browser)
        root_lay.addWidget(preview_card, 1)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        copy_btn = QPushButton("  Copy Slip Text")
        copy_btn.setIcon(get_icon("orders", color="#CBD5E1", size=QSize(16, 16)))
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setFixedHeight(38)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """)
        copy_btn.clicked.connect(self._copy_slip_text)
        bottom_bar.addWidget(copy_btn)

        bottom_bar.addStretch()

        pdf_btn = QPushButton("  Export PDF")
        pdf_btn.setIcon(get_icon("export", color="#FFFFFF", size=QSize(16, 16)))
        pdf_btn.setCursor(Qt.PointingHandCursor)
        pdf_btn.setFixedHeight(38)
        pdf_btn.setStyleSheet("""
            QPushButton {
                background: #0284C7;
                color: #FFFFFF;
                border: 1px solid #0369A1;
                border-radius: 6px;
                padding: 0 18px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0369A1;
            }
        """)
        pdf_btn.clicked.connect(self._export_pdf)
        bottom_bar.addWidget(pdf_btn)

        print_btn = QPushButton("  Print Order Slip")
        print_btn.setIcon(get_icon("printer", color="#FFFFFF", size=QSize(16, 16)))
        print_btn.setCursor(Qt.PointingHandCursor)
        print_btn.setFixedHeight(38)
        print_btn.setStyleSheet("""
            QPushButton {
                background: #E11D48;
                color: #FFFFFF;
                border: 1px solid #BE123C;
                border-radius: 6px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #BE123C;
            }
        """)
        print_btn.clicked.connect(self._print_order)
        bottom_bar.addWidget(print_btn)

        root_lay.addLayout(bottom_bar)

    def _get_clean_addons(self) -> list[str]:
        """Extract all additional add-ons strictly without price amounts."""
        add_ons = []
        raw_charges = self._booking.get("additional_charges") or []
        for chg in raw_charges:
            desc = str(chg.get("description") or "").strip()
            if desc:
                clean_desc = re.sub(r"\s*\([+-]?[^\)]*[\d,.]+[^\)]*\)\s*$", "", desc).strip()
                clean_desc = re.sub(r"[+-]?[₱P]\s*[\d,.]+", "", clean_desc).strip()
                if clean_desc and clean_desc not in add_ons:
                    add_ons.append(clean_desc)

        notes_str = str(self._booking.get("notes") or "").strip()
        m_addons = re.search(r"\[Add-ons:\s*(.*?)\]", notes_str, re.IGNORECASE)
        if m_addons:
            raw_addons = re.split(r"(?<=\))\s*,\s*", m_addons.group(1))
            for a in raw_addons:
                clean_a = re.sub(r"\s*\([+-]?[^\)]*[\d,.]+[^\)]*\)\s*$", "", a).strip()
                clean_a = re.sub(r"[+-]?[₱P]\s*[\d,.]+", "", clean_a).strip()
                if clean_a and clean_a not in add_ons:
                    add_ons.append(clean_a)

        return add_ons

    def _generate_slip_html(self) -> str:
        b = self._booking
        biz = self._business

        order_ref = str(b.get("id") or b.get("booking_ref") or "ORD-SLIP")
        cust_name = str(b.get("name") or b.get("customer_name") or "Valued Client")
        venue = str(b.get("venue") or b.get("address") or "To be confirmed")
        date_str = str(b.get("event_date") or b.get("date") or "TBA")
        raw_t = b.get("event_time") or b.get("time") or ""
        time_str = repo.format_time_ampm(raw_t) if raw_t else "TBA"
        pax = str(b.get("pax", 100))
        occasion = str(b.get("occasion") or "Banquet Catering")
        pkg_name = str(b.get("package_name") or b.get("menu_value") or "Standard Catering Package")
        motif = str(b.get("color_theme") or b.get("color") or "")
        contact = str(b.get("contact") or "")
        email = str(b.get("email") or "")

        # Clean notes
        notes_str = str(b.get("notes") or "").strip()
        clean_notes = re.sub(r"\n?\[Add-ons:\s*.*?\]", "", notes_str, flags=re.IGNORECASE).strip()

        # Dishes
        dishes = b.get("dishes") or []
        if not dishes and b.get("menu_value"):
            raw_dishes = [d.strip() for d in str(b["menu_value"]).split(",") if d.strip()]
            dishes = [{"name": rd, "category": "Selected Menu"} for rd in raw_dishes]

        by_cat = {}
        for d in dishes:
            cat = d.get("category") or "Menu Dishes"
            d_name = d.get("name") or d.get("item_name") or str(d)
            if d_name:
                by_cat.setdefault(cat, []).append(d_name)

        dishes_html = ""
        if by_cat:
            dishes_html += '<table style="width:100%; border-collapse:collapse; margin-top:8px;">'
            dishes_html += '<tr style="background-color:#E11D48; color:#FFFFFF;">'
            dishes_html += '<th style="padding:8px 12px; text-align:left; font-size:12px; width:30%;">Course / Category</th>'
            dishes_html += '<th style="padding:8px 12px; text-align:left; font-size:12px; width:70%;">Itemized Dishes & Menu</th>'
            dishes_html += '</tr>'

            for cat, items in by_cat.items():
                items_str = "<br/>".join([f"• <b>{it}</b>" for it in items])
                dishes_html += f"""
                <tr style="border-bottom:1px solid #E2E8F0;">
                    <td style="padding:8px 12px; vertical-align:top; font-size:12px; font-weight:bold; color:#0F172A; background-color:#F8FAFC;">{cat}</td>
                    <td style="padding:8px 12px; vertical-align:top; font-size:12px; color:#1E293B; line-height:1.5;">{items_str}</td>
                </tr>
                """
            dishes_html += '</table>'
        else:
            dishes_html = '<p style="font-size:12px; font-style:italic; color:#64748B;">Standard catering package inclusions apply.</p>'

        # Add-ons (walay price mount)
        add_ons = self._get_clean_addons()
        addons_html = ""
        if add_ons:
            addons_html += '<table style="width:100%; border-collapse:collapse; margin-top:8px;">'
            addons_html += '<tr style="background-color:#475569; color:#FFFFFF;">'
            addons_html += '<th style="padding:6px 10px; text-align:center; font-size:11px; width:8%;">#</th>'
            addons_html += '<th style="padding:6px 10px; text-align:left; font-size:11px; width:62%;">Item / Add-on Description</th>'
            addons_html += '<th style="padding:6px 10px; text-align:left; font-size:11px; width:30%;">Logistics Fulfillment</th>'
            addons_html += '</tr>'

            for i, a_item in enumerate(add_ons, 1):
                addons_html += f"""
                <tr style="border-bottom:1px solid #E2E8F0;">
                    <td style="padding:6px 10px; text-align:center; font-size:11px; color:#64748B; font-weight:bold;">{i}</td>
                    <td style="padding:6px 10px; font-size:12px; font-weight:bold; color:#0F172A;">{a_item}</td>
                    <td style="padding:6px 10px; font-size:11px; color:#64748B;">[  ] Prepared / In Van</td>
                </tr>
                """
            addons_html += '</table>'
        else:
            addons_html = '<p style="font-size:12px; font-style:italic; color:#64748B;">No additional add-on items specified for this event.</p>'

        remarks_html = ""
        if clean_notes:
            remarks_html = f"""
            <div style="margin-top:14px; padding:10px 14px; background-color:#FEF3C7; border:1px solid #FDE68A; border-radius:6px;">
                <div style="font-size:11px; font-weight:bold; color:#92400E; margin-bottom:4px;">SPECIAL INSTRUCTIONS & REMARKS:</div>
                <div style="font-size:12px; color:#78350F; line-height:1.4;">{clean_notes}</div>
            </div>
            """

        motif_badge = f'<span style="background-color:#F1F5F9; border-left:3px solid {motif or "#2563EB"}; padding:2px 8px; border-radius:4px; font-weight:bold;">{motif or "Standard"}</span>' if motif else "Standard"

        now_str = datetime.now().strftime("%b %d, %Y at %I:%M %p")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin:0; padding:0; color:#0F172A; }}
                h2 {{ margin:0 0 2px 0; color:#E11D48; font-size:20px; }}
                h4 {{ margin:16px 0 6px 0; color:#0F172A; font-size:13px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1.5px solid #CBD5E1; padding-bottom:3px; }}
                table.info-grid {{ width:100%; border-collapse:collapse; margin-top:8px; }}
                table.info-grid td {{ padding:7px 10px; font-size:12px; border:1px solid #E2E8F0; }}
                .label-cell {{ font-weight:bold; color:#475569; background-color:#F8FAFC; width:20%; }}
                .val-cell {{ color:#0F172A; width:30%; }}
            </style>
        </head>
        <body>
            <!-- Slip Header -->
            <table style="width:100%; border-bottom:2px solid #E11D48; padding-bottom:10px;">
                <tr>
                    <td style="vertical-align:top;">
                        <h2>{biz.get('name', "Jayraldine's Catering")}</h2>
                        <div style="font-size:11px; color:#64748B;">{biz.get('address', 'Cebu City')} · Tel: {biz.get('contact', '')}</div>
                    </td>
                    <td style="text-align:right; vertical-align:top;">
                        <div style="font-size:10px; font-weight:bold; color:#E11D48; letter-spacing:1px;">BANQUET EVENT ORDER</div>
                        <div style="font-size:18px; font-weight:900; color:#0F172A;">{order_ref}</div>
                        <div style="font-size:10px; color:#64748B;">Printed: {now_str}</div>
                    </td>
                </tr>
            </table>

            <!-- Event Information -->
            <h4>1. Event & Customer Details</h4>
            <table class="info-grid">
                <tr>
                    <td class="label-cell">Customer Name:</td>
                    <td class="val-cell"><b>{cust_name}</b></td>
                    <td class="label-cell">Event Date:</td>
                    <td class="val-cell"><b>{date_str}</b></td>
                </tr>
                <tr>
                    <td class="label-cell">Event Location:</td>
                    <td class="val-cell"><b>{venue}</b></td>
                    <td class="label-cell">Event Time:</td>
                    <td class="val-cell"><b>{time_str}</b></td>
                </tr>
                <tr>
                    <td class="label-cell">Occasion:</td>
                    <td class="val-cell">{occasion}</td>
                    <td class="label-cell">Guest Count:</td>
                    <td class="val-cell"><b>{pax} Pax</b></td>
                </tr>
                <tr>
                    <td class="label-cell">Contact Phone:</td>
                    <td class="val-cell">{contact or '—'}</td>
                    <td class="label-cell">Color Motif:</td>
                    <td class="val-cell">{motif_badge}</td>
                </tr>
            </table>

            <!-- Menu & Dishes -->
            <h4>2. Package & Selected Dishes: <span style="color:#E11D48;">{pkg_name}</span></h4>
            {dishes_html}

            <!-- Additional Add-ons (No Prices) -->
            <h4>3. Additional Items & Add-ons (No Rates Displayed)</h4>
            {addons_html}

            <!-- Special Remarks -->
            {remarks_html}

        </body>
        </html>
        """
        return html

    def _copy_slip_text(self):
        b = self._booking
        order_ref = str(b.get("id") or b.get("booking_ref") or "ORD-SLIP")
        cust_name = str(b.get("name") or b.get("customer_name") or "Valued Client")
        venue = str(b.get("venue") or b.get("address") or "TBA")
        date_str = str(b.get("event_date") or b.get("date") or "TBA")
        raw_t = b.get("event_time") or b.get("time") or ""
        time_str = repo.format_time_ampm(raw_t) if raw_t else "TBA"
        pax = str(b.get("pax", 100))
        pkg_name = str(b.get("package_name") or b.get("menu_value") or "Standard Package")

        dishes = b.get("dishes") or []
        dish_lines = []
        for d in dishes:
            d_name = d.get("name") or d.get("item_name") or str(d)
            if d_name:
                dish_lines.append(f"  • {d_name}")
        dishes_text = "\n".join(dish_lines) if dish_lines else "  • Standard Package Inclusions"

        add_ons = self._get_clean_addons()
        addon_lines = [f"  [{idx}] {a}" for idx, a in enumerate(add_ons, 1)]
        addons_text = "\n".join(addon_lines) if addon_lines else "  None"

        text = f"""==================================================
JAYRALDINE'S CATERING - BANQUET ORDER SLIP
Order Ref: {order_ref}
==================================================
CUSTOMER:    {cust_name}
LOCATION:    {venue}
DATE & TIME: {date_str} at {time_str}
PAX:         {pax} Guests
PACKAGE:     {pkg_name}

DISHES & MENU:
{dishes_text}

ADDITIONAL ITEMS (NO CHARGES):
{addons_text}
=================================================="""

        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        success(self, message="Order slip copied to clipboard!")

    def _export_pdf(self):
        order_ref = str(self._booking.get("id") or self._booking.get("booking_ref") or "order").replace("/", "-")
        default_name = f"Order_Slip_{order_ref}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Banquet Order Slip PDF",
            default_name,
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        ok = exporter.export_order_slip_pdf(file_path, self._booking, self._business)
        if ok:
            success(self, message=f"Order slip PDF exported successfully:\n{os.path.basename(file_path)}")
        else:
            # Fallback to Qt PDF print
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            self._doc_browser.document().print_(printer)
            success(self, message=f"Order slip PDF generated successfully:\n{os.path.basename(file_path)}")

    def _print_order(self):
        if not PRINTER_SUPPORT:
            QMessageBox.warning(self, "Printing Unsupported", "Qt Print Support is not installed on this workstation.")
            return

        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print Banquet Order Slip")
        if dialog.exec() == QPrintDialog.Accepted:
            self._doc_browser.document().print_(printer)
            success(self, message="Order slip sent to printer successfully.")
