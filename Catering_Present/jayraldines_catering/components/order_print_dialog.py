"""
Order Print & Export Dialog for Banquet Event Orders / Kitchen Slips.

Displays a clean, printable order slip (or slips) containing:
- Date | Name | Time | Pax summary strip
- Selected package & itemized dishes / menu (highlighted, larger text)
- Additional Add-ons strictly WITHOUT price amounts ("walay price mount")

Supports printing ONE booking (full A4 page) or TWO+ bookings (paired two
per A4 page, each occupying half the page; an odd one out gets its own full
page) - pass either a single booking id/ref/dict or a list of them.
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
    from PySide6.QtGui import QPageSize, QPageLayout
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
    Accepts one booking (id/ref/dict) or a list of them.
    """

    def __init__(self, booking_ids_or_refs, parent=None):
        super().__init__(parent)
        if isinstance(booking_ids_or_refs, (list, tuple, set)):
            raw_list = list(booking_ids_or_refs)
        else:
            raw_list = [booking_ids_or_refs]
        self._bookings = [self._load_booking_data(b) for b in raw_list]
        self._business = repo.get_business_info() or {
            "name": "Jayraldine's Catering Services",
            "address": "Cebu City, Philippines",
            "contact": "0912-345-6789",
            "email": "info@jayraldinescatering.com"
        }

        n = len(self._bookings)
        if n == 1:
            order_ref = self._bookings[0].get("id") or self._bookings[0].get("booking_ref") or "Order"
            self.setWindowTitle(f"Banquet Order Slip — {order_ref}")
        else:
            self.setWindowTitle(f"Banquet Order Slips — {n} Orders")
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
        n = len(self._bookings)
        title_lbl = QLabel("Banquet Event Order & Kitchen Slip" if n == 1 else f"Banquet Event Orders ({n})")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")
        sub_txt = ("Official order dispatch sheet with menu dishes & additional items (prices hidden)" if n == 1
                   else "A4, two orders per page (half page each) - official dispatch sheets, prices hidden")
        sub_lbl = QLabel(sub_txt)
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

        print_btn = QPushButton("  Print Order Slip" if len(self._bookings) == 1 else "  Print Order Slips")
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

    @staticmethod
    def _configure_a4(printer):
        """Force A4 paper size on the given QPrinter, regardless of whatever
        the OS default printer/page size happens to be."""
        try:
            printer.setPageSize(QPageSize(QPageSize.A4))
        except Exception:
            try:
                printer.setPageSize(QPrinter.A4)
            except Exception:
                pass

    def _get_clean_addons(self, booking: dict) -> list[str]:
        """Extract all additional add-ons strictly without price amounts."""
        add_ons = []
        raw_charges = booking.get("additional_charges") or []
        for chg in raw_charges:
            desc = str(chg.get("description") or "").strip()
            if desc:
                clean_desc = re.sub(r"\s*\([+-]?[^\)]*[\d,.]+[^\)]*\)\s*$", "", desc).strip()
                clean_desc = re.sub(r"[+-]?[₱P]\s*[\d,.]+", "", clean_desc).strip()
                if clean_desc and clean_desc not in add_ons:
                    add_ons.append(clean_desc)

        notes_str = str(booking.get("notes") or "").strip()
        m_addons = re.search(r"\[Add-ons:\s*(.*?)\]", notes_str, re.IGNORECASE)
        if m_addons:
            raw_addons = re.split(r"(?<=\))\s*,\s*", m_addons.group(1))
            for a in raw_addons:
                clean_a = re.sub(r"\s*\([+-]?[^\)]*[\d,.]+[^\)]*\)\s*$", "", a).strip()
                clean_a = re.sub(r"[+-]?[₱P]\s*[\d,.]+", "", clean_a).strip()
                if clean_a and clean_a not in add_ons:
                    add_ons.append(clean_a)

        return add_ons

    def _build_dishes_html(self, booking: dict, compact: bool = False) -> str:
        dishes = booking.get("dishes") or []
        if not dishes and booking.get("menu_value"):
            raw_dishes = [d.strip() for d in str(booking["menu_value"]).split(",") if d.strip()]
            dishes = [{"name": rd, "category": "Selected Menu"} for rd in raw_dishes]

        by_cat = {}
        for d in dishes:
            cat = d.get("category") or "Menu Dishes"
            d_name = d.get("name") or d.get("item_name") or str(d)
            if d_name:
                by_cat.setdefault(cat, []).append(d_name)

        # Larger, highlighted styling so the selected food/menu stands out
        # from the rest of the slip, per the print-layout spec.
        item_font = "13px" if not compact else "12px"
        cat_font = "12px" if not compact else "11px"

        if by_cat:
            html = '<table style="width:100%; border-collapse:collapse; margin-top:6px; background-color:#FFFBEB; border:2px solid #F59E0B; border-radius:4px;">'
            html += '<tr style="background-color:#F59E0B; color:#FFFFFF;">'
            html += f'<th style="padding:7px 12px; text-align:left; font-size:{cat_font}; width:28%;">Course / Category</th>'
            html += f'<th style="padding:7px 12px; text-align:left; font-size:{cat_font}; width:72%;">Selected Food &amp; Menu</th>'
            html += '</tr>'
            for cat, items in by_cat.items():
                items_str = "<br/>".join([f"● <b>{it}</b>" for it in items])
                html += f"""
                <tr style="border-bottom:1px solid #FDE68A;">
                    <td style="padding:8px 12px; vertical-align:top; font-size:{cat_font}; font-weight:bold; color:#78350F;">{cat}</td>
                    <td style="padding:8px 12px; vertical-align:top; font-size:{item_font}; font-weight:700; color:#7C2D12; line-height:1.6;">{items_str}</td>
                </tr>
                """
            html += '</table>'
        else:
            html = '<p style="font-size:12px; font-style:italic; color:#64748B;">Standard catering package inclusions apply.</p>'
        return html

    def _build_addons_html(self, booking: dict, compact: bool = False) -> str:
        add_ons = self._get_clean_addons(booking)
        font_sz = "11px" if compact else "12px"
        if add_ons:
            html = '<table style="width:100%; border-collapse:collapse; margin-top:6px;">'
            html += '<tr style="background-color:#475569; color:#FFFFFF;">'
            html += '<th style="padding:5px 10px; text-align:center; font-size:11px; width:8%;">#</th>'
            html += '<th style="padding:5px 10px; text-align:left; font-size:11px; width:62%;">Item / Add-on Description</th>'
            html += '<th style="padding:5px 10px; text-align:left; font-size:11px; width:30%;">Logistics</th>'
            html += '</tr>'
            for i, a_item in enumerate(add_ons, 1):
                html += f"""
                <tr style="border-bottom:1px solid #E2E8F0;">
                    <td style="padding:5px 10px; text-align:center; font-size:{font_sz}; color:#64748B; font-weight:bold;">{i}</td>
                    <td style="padding:5px 10px; font-size:{font_sz}; font-weight:bold; color:#0F172A;">{a_item}</td>
                    <td style="padding:5px 10px; font-size:11px; color:#64748B;">[  ] Prepared / In Van</td>
                </tr>
                """
            html += '</table>'
        else:
            html = '<p style="font-size:11px; font-style:italic; color:#64748B;">No additional add-on items specified.</p>'
        return html

    def _build_slip_body(self, booking: dict, compact: bool = False) -> str:
        """One order's content: Date | Name | Time | Pax summary strip, then
        package/menu (highlighted) and add-ons. `compact` shrinks fonts/
        spacing for the two-per-page half-page layout."""
        biz = self._business
        order_ref = str(booking.get("id") or booking.get("booking_ref") or "ORD-SLIP")
        cust_name = str(booking.get("name") or booking.get("customer_name") or "Valued Client")
        venue = str(booking.get("venue") or booking.get("address") or "To be confirmed")
        date_str = str(booking.get("event_date") or booking.get("date") or "TBA")
        raw_t = booking.get("event_time") or booking.get("time") or ""
        time_str = repo.format_time_ampm(raw_t) if raw_t else "TBA"
        pax = str(booking.get("pax", 100))
        occasion = str(booking.get("occasion") or "Banquet Catering")
        pkg_name = str(booking.get("package_name") or booking.get("menu_value") or "Standard Catering Package")
        contact = str(booking.get("contact") or "")

        notes_str = str(booking.get("notes") or "").strip()
        clean_notes = re.sub(r"\n?\[Add-ons:\s*.*?\]", "", notes_str, flags=re.IGNORECASE).strip()

        dishes_html = self._build_dishes_html(booking, compact=compact)
        addons_html = self._build_addons_html(booking, compact=compact)

        h_title = "16px" if not compact else "13px"
        h_ref = "13px" if not compact else "11px"
        strip_font = "14px" if not compact else "12px"
        section_font = "12px" if not compact else "10.5px"

        remarks_html = ""
        if clean_notes and not compact:
            remarks_html = f"""
            <div style="margin-top:10px; padding:8px 12px; background-color:#FEF3C7; border:1px solid #FDE68A; border-radius:6px;">
                <div style="font-size:10.5px; font-weight:bold; color:#92400E; margin-bottom:3px;">SPECIAL INSTRUCTIONS &amp; REMARKS:</div>
                <div style="font-size:11.5px; color:#78350F; line-height:1.4;">{clean_notes}</div>
            </div>
            """

        now_str = datetime.now().strftime("%b %d, %Y at %I:%M %p")

        return f"""
        <table style="width:100%; border-bottom:2px solid #E11D48; padding-bottom:6px;">
            <tr>
                <td style="vertical-align:top;">
                    <div style="font-size:{h_title}; font-weight:900; color:#E11D48;">{biz.get('name', "Jayraldine's Catering")}</div>
                    <div style="font-size:9.5px; color:#64748B;">{biz.get('address', 'Cebu City')} · Tel: {biz.get('contact', '')}</div>
                </td>
                <td style="text-align:right; vertical-align:top;">
                    <div style="font-size:9px; font-weight:bold; color:#E11D48; letter-spacing:1px;">BANQUET EVENT ORDER</div>
                    <div style="font-size:{h_ref}; font-weight:900; color:#0F172A;">{order_ref}</div>
                    {'' if compact else f'<div style="font-size:9px; color:#64748B;">Printed: {now_str}</div>'}
                </td>
            </tr>
        </table>

        <!-- Date | Name | Time | Pax summary strip. Background is set on the
             <tr>/<td> elements, NOT the outer <table> - Qt's rich-text print
             pipeline does not reliably paint a background-color declared on
             the <table> tag itself (confirmed: the dishes table below uses a
             <tr>-level background and prints fine), which was leaving the
             white value text invisible against an unpainted white page. -->
        <table style="width:100%; border-collapse:collapse; margin-top:8px; border-radius:4px;">
            <tr style="background-color:#0F172A;">
                <td style="padding:7px 10px; text-align:center; background-color:#0F172A; color:#94A3B8; font-size:9px; font-weight:bold; text-transform:uppercase;">Date<br/>
                    <span style="color:#FFFFFF; font-size:{strip_font}; font-weight:800;">{date_str}</span>
                </td>
                <td style="padding:7px 10px; text-align:center; background-color:#0F172A; color:#94A3B8; font-size:9px; font-weight:bold; text-transform:uppercase; border-left:1px solid #334155;">Name<br/>
                    <span style="color:#FFFFFF; font-size:{strip_font}; font-weight:800;">{cust_name}</span>
                </td>
                <td style="padding:7px 10px; text-align:center; background-color:#0F172A; color:#94A3B8; font-size:9px; font-weight:bold; text-transform:uppercase; border-left:1px solid #334155;">Time<br/>
                    <span style="color:#FFFFFF; font-size:{strip_font}; font-weight:800;">{time_str}</span>
                </td>
                <td style="padding:7px 10px; text-align:center; background-color:#0F172A; color:#94A3B8; font-size:9px; font-weight:bold; text-transform:uppercase; border-left:1px solid #334155;">Pax<br/>
                    <span style="color:#FFFFFF; font-size:{strip_font}; font-weight:800;">{pax}</span>
                </td>
            </tr>
        </table>

        <table style="width:100%; margin-top:6px;">
            <tr>
                <td style="font-size:{section_font}; color:#475569;"><b>Venue:</b> {venue}</td>
                <td style="font-size:{section_font}; color:#475569; text-align:right;"><b>Occasion:</b> {occasion}{f' · <b>Contact:</b> {contact}' if contact and not compact else ''}</td>
            </tr>
        </table>

        <div style="margin-top:{'10px' if not compact else '6px'}; font-size:{section_font}; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.4px;">
            Package: <span style="color:#E11D48;">{pkg_name}</span>
        </div>
        {dishes_html}

        {'' if compact else f'<div style="margin-top:10px; font-size:{section_font}; font-weight:700; color:#0F172A; text-transform:uppercase;">Additional Items &amp; Add-ons (No Rates Shown)</div>'}
        {addons_html if not compact else ''}
        {remarks_html}
        """

    def _generate_slip_html(self) -> str:
        base_style = """
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin:0; padding:0; color:#0F172A; }
            </style>
        """

        n = len(self._bookings)
        if n <= 1:
            booking = self._bookings[0] if self._bookings else {}
            body = self._build_slip_body(booking, compact=False)
            return f"<!DOCTYPE html><html><head>{base_style}</head><body>{body}</body></html>"

        # 2+ orders: pair them two-per-A4-page (half page each). An odd one
        # out at the end gets its own full page.
        pages_html = []
        i = 0
        while i < n:
            pair = self._bookings[i:i + 2]
            if len(pair) == 2:
                half_a = self._build_slip_body(pair[0], compact=True)
                half_b = self._build_slip_body(pair[1], compact=True)
                page = f"""
                <div style="padding:10px 6px;">{half_a}</div>
                <div style="text-align:center; color:#94A3B8; font-size:10px; margin:2px 0; border-top:2px dashed #CBD5E1;">✂ — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — ✂</div>
                <div style="padding:10px 6px;">{half_b}</div>
                """
            else:
                page = f'<div style="padding:14px 8px;">{self._build_slip_body(pair[0], compact=False)}</div>'
            pages_html.append(page)
            i += 2

        joined = '<div style="page-break-after: always;"></div>'.join(pages_html)
        return f"<!DOCTYPE html><html><head>{base_style}</head><body>{joined}</body></html>"

    def _copy_slip_text(self):
        blocks = []
        for booking in self._bookings:
            order_ref = str(booking.get("id") or booking.get("booking_ref") or "ORD-SLIP")
            cust_name = str(booking.get("name") or booking.get("customer_name") or "Valued Client")
            venue = str(booking.get("venue") or booking.get("address") or "TBA")
            date_str = str(booking.get("event_date") or booking.get("date") or "TBA")
            raw_t = booking.get("event_time") or booking.get("time") or ""
            time_str = repo.format_time_ampm(raw_t) if raw_t else "TBA"
            pax = str(booking.get("pax", 100))
            pkg_name = str(booking.get("package_name") or booking.get("menu_value") or "Standard Package")

            dishes = booking.get("dishes") or []
            dish_lines = []
            for d in dishes:
                d_name = d.get("name") or d.get("item_name") or str(d)
                if d_name:
                    dish_lines.append(f"  • {d_name}")
            dishes_text = "\n".join(dish_lines) if dish_lines else "  • Standard Package Inclusions"

            add_ons = self._get_clean_addons(booking)
            addon_lines = [f"  [{idx}] {a}" for idx, a in enumerate(add_ons, 1)]
            addons_text = "\n".join(addon_lines) if addon_lines else "  None"

            blocks.append(f"""==================================================
JAYRALDINE'S CATERING - BANQUET ORDER SLIP
Order Ref: {order_ref}
==================================================
DATE:        {date_str}
NAME:        {cust_name}
TIME:        {time_str}
PAX:         {pax} Guests
LOCATION:    {venue}
PACKAGE:     {pkg_name}

DISHES & MENU:
{dishes_text}

ADDITIONAL ITEMS (NO CHARGES):
{addons_text}
==================================================""")

        text = "\n\n".join(blocks)
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        success(self, message="Order slip copied to clipboard!" if len(self._bookings) == 1 else "Order slips copied to clipboard!")

    def _export_pdf(self):
        if len(self._bookings) == 1:
            order_ref = str(self._bookings[0].get("id") or self._bookings[0].get("booking_ref") or "order").replace("/", "-")
            default_name = f"Order_Slip_{order_ref}.pdf"
        else:
            default_name = f"Order_Slips_{len(self._bookings)}_orders.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Banquet Order Slip PDF",
            default_name,
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        # Always render the exported PDF from the exact same HTML document
        # shown in the on-screen preview (and used for Print) - a separate
        # ReportLab-based PDF path used to exist here for single orders, which
        # silently produced a DIFFERENT layout (no Date|Name|Time|Pax strip,
        # red instead of amber dish header, no half-page pairing) than what
        # the user saw in the preview. Using one shared rendering pipeline
        # guarantees the exported PDF always matches the preview exactly.
        printer = QPrinter(QPrinter.HighResolution)
        self._configure_a4(printer)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)
        self._print_document(printer)
        success(self, message=f"Order slip PDF exported successfully:\n{os.path.basename(file_path)}")

    def _print_order(self):
        if not PRINTER_SUPPORT:
            QMessageBox.warning(self, "Printing Unsupported", "Qt Print Support is not installed on this workstation.")
            return

        printer = QPrinter(QPrinter.HighResolution)
        self._configure_a4(printer)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print Banquet Order Slip" if len(self._bookings) == 1 else "Print Banquet Order Slips")
        if dialog.exec() == QPrintDialog.Accepted:
            self._print_document(printer)
            success(self, message="Order slip sent to printer successfully." if len(self._bookings) == 1 else "Order slips sent to printer successfully.")

    def _print_document(self, printer):
        # document().print_(printer) renders the QTextDocument at whatever
        # layout width it currently has from being displayed in the on-screen
        # QTextBrowser - it does NOT reliably rescale to fill the printer's
        # page, so the slip came out tiny in the corner of the A4 page.
        # Manually painting via QPainter + drawContents(), with an explicit
        # scale factor computed from the printer's actual page width, gives
        # full deterministic control and guarantees the content fills the
        # page - this is Qt's own recommended technique for this exact case.
        from PySide6.QtGui import QPainter
        from PySide6.QtCore import QRectF

        doc = self._doc_browser.document()
        page_rect = printer.pageRect(QPrinter.DevicePixel)
        doc_size = doc.size()
        if page_rect.width() <= 0 or page_rect.height() <= 0 or doc_size.width() <= 0 or doc_size.height() <= 0:
            doc.print_(printer)
            return

        scale = page_rect.width() / doc_size.width()
        page_height_doc_units = page_rect.height() / scale
        total_height = doc_size.height()

        painter = QPainter()
        if not painter.begin(printer):
            doc.print_(printer)
            return
        try:
            y_offset = 0.0
            first_page = True
            while y_offset < total_height:
                if not first_page:
                    printer.newPage()
                first_page = False
                painter.save()
                painter.scale(scale, scale)
                painter.translate(0, -y_offset)
                slice_height = min(page_height_doc_units, total_height - y_offset)
                doc.drawContents(painter, QRectF(0, y_offset, doc_size.width(), slice_height))
                painter.restore()
                y_offset += page_height_doc_units
        finally:
            painter.end()
