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
import html
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

# Fixed reference width ("CSS px") the slip's HTML is built against - also
# used to pin the QTextDocument's layout width right before printing (see
# _print_document), so the printed/exported output is always measured
# against the SAME width the HTML was designed for, regardless of whatever
# size the on-screen preview widget happens to be at that moment.
_SLIP_LAYOUT_WIDTH = 800
# A4 portrait = 210mm x 297mm -> height:width ratio = 297/210 = 1.41429.
# Half of A4's height at the SAME reference width, in the same "css px"
# units - the order container is forced to exactly this height so its
# bottom border lands on the true vertical midpoint of the printed page,
# not merely "however tall the content naturally is."
_SLIP_HALF_HEIGHT = round(_SLIP_LAYOUT_WIDTH * (297 / 210) / 2)


def is_food_set_pkg(pkg_name: str) -> bool:
    if not pkg_name:
        return False
    name = str(pkg_name).strip().lower()
    return any(k in name for k in ["food set", "food pack", "foodset", "foodpack", "set of dish"]) or name.startswith("set ") or " set" in name


class OrderPrintDialog(QDialog):
    """
    Banquet Booking Agreement & Order Slip / Kitchen Dispatch Dialog.
    Accepts one booking (id/ref/dict) or a list of them.
    Defaults to the official client Booking Agreement & Order Slip (Up & Down format:
    Upper Order details, Package & Menu, Financials, Signatures; Lower Terms & Conditions).
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
            "address": "121 Katipunan St. Brgy Calamba Cebu City",
            "contact": "(032) 255-3113, (032) 238-9417 · Globe 0917-6519555, 0917-1051528",
            "email": "info@jayraldinescatering.com"
        }
        self._current_mode = "agreement"  # "agreement" (default) or "kitchen"

        n = len(self._bookings)
        if n == 1:
            order_ref = self._bookings[0].get("id") or self._bookings[0].get("booking_ref") or "Order"
            self.setWindowTitle(f"Booking Agreement & Order Slip — {order_ref}")
        else:
            self.setWindowTitle(f"Booking Agreements & Order Slips — {n} Orders")
        self.resize(780, 800)
        self.setMinimumSize(640, 600)
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
        root_lay.setSpacing(12)

        # Header Bar
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("printer", color="#E11D48", size=QSize(28, 28)).pixmap(28, 28))
        header.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        n = len(self._bookings)
        self._title_lbl = QLabel("Booking Agreement & Order Slip" if n == 1 else f"Booking Agreements & Order Slips ({n})")
        self._title_lbl.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")
        sub_txt = ("Official Client Booking Agreement with prices, dishes, terms & conditions (Manual Paper Format)" if n == 1
                   else "A4 Booking Agreements - official client agreements with menu, financials & terms")
        self._sub_lbl = QLabel(sub_txt)
        self._sub_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_col.addWidget(self._title_lbl)
        title_col.addWidget(self._sub_lbl)
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

        # Mode Switcher Bar
        mode_bar = QHBoxLayout()
        mode_bar.setSpacing(8)

        self._btn_mode_agreement = QPushButton("  📄 Booking Agreement & Order Slip")
        self._btn_mode_agreement.setCursor(Qt.PointingHandCursor)
        self._btn_mode_agreement.setFixedHeight(34)
        self._btn_mode_agreement.clicked.connect(lambda: self._set_mode("agreement"))

        self._btn_mode_kitchen = QPushButton("  🍳 Kitchen Dispatch Slip")
        self._btn_mode_kitchen.setCursor(Qt.PointingHandCursor)
        self._btn_mode_kitchen.setFixedHeight(34)
        self._btn_mode_kitchen.clicked.connect(lambda: self._set_mode("kitchen"))

        mode_bar.addWidget(self._btn_mode_agreement)
        mode_bar.addWidget(self._btn_mode_kitchen)
        mode_bar.addStretch()
        root_lay.addLayout(mode_bar)

        self._update_mode_buttons()

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

        copy_btn = QPushButton("  Copy Details")
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

        self._print_btn = QPushButton("  Print Order Slip" if len(self._bookings) == 1 else "  Print Order Slips")
        self._print_btn.setIcon(get_icon("printer", color="#FFFFFF", size=QSize(16, 16)))
        self._print_btn.setCursor(Qt.PointingHandCursor)
        self._print_btn.setFixedHeight(38)
        self._print_btn.setStyleSheet("""
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
        self._print_btn.clicked.connect(self._print_order)
        bottom_bar.addWidget(self._print_btn)

        root_lay.addLayout(bottom_bar)

    def _set_mode(self, mode: str):
        if self._current_mode == mode:
            return
        self._current_mode = mode
        self._update_mode_buttons()
        n = len(self._bookings)
        if mode == "agreement":
            self._title_lbl.setText("Booking Agreement & Order Slip" if n == 1 else f"Booking Agreements & Order Slips ({n})")
            self._sub_lbl.setText("Official Client Booking Agreement with prices, dishes, terms & conditions (Manual Paper Format)")
            self._print_btn.setText("  Print Agreement" if n == 1 else f"  Print Agreements ({n})")
        else:
            self._title_lbl.setText("Kitchen Dispatch Slip" if n == 1 else f"Kitchen Dispatch Slips ({n})")
            self._sub_lbl.setText("Official order dispatch sheet with menu dishes & additional items (prices hidden)")
            self._print_btn.setText("  Print Kitchen Slip" if n == 1 else f"  Print Kitchen Slips ({n})")
        self._html_content = self._generate_slip_html()
        self._doc_browser.setHtml(self._html_content)

    def _update_mode_buttons(self):
        if self._current_mode == "agreement":
            self._btn_mode_agreement.setStyleSheet("""
                QPushButton {
                    background-color: #BE123C;
                    color: #FFFFFF;
                    border: 1px solid #E11D48;
                    border-radius: 6px;
                    padding: 0 16px;
                    font-weight: 700;
                    font-size: 12px;
                }
            """)
            self._btn_mode_kitchen.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.06);
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 0 16px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.12);
                    color: #FFFFFF;
                }
            """)
        else:
            self._btn_mode_agreement.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.06);
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 0 16px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.12);
                    color: #FFFFFF;
                }
            """)
            self._btn_mode_kitchen.setStyleSheet("""
                QPushButton {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    border: 1px solid #0369A1;
                    border-radius: 6px;
                    padding: 0 16px;
                    font-weight: 700;
                    font-size: 12px;
                }
            """)

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

    def _build_dishes_table_2col(self, booking: dict, compact: bool = False, pad_scale: float = 1.0) -> str:
        """Renders MENU SELECTIONS with only the dish names in a clean, enlarged bullet list without category headers."""
        dishes = booking.get("dishes") or []
        if not dishes and booking.get("menu_value"):
            raw_dishes = [d.strip() for d in str(booking["menu_value"]).split(",") if d.strip()]
            dishes = [{"name": rd} for rd in raw_dishes]

        dish_names = []
        seen = set()
        for d in dishes:
            d_name = d.get("name") or d.get("item_name") or (f"Item #{d['item_id']}" if d.get("item_id") else None)
            if d_name:
                key = d_name.strip().lower()
                if key not in seen:
                    seen.add(key)
                    dish_names.append(d_name.strip())

        ps = pad_scale if not compact else 1.0
        sec_title_font = "12px" if not compact else "10px"
        count = len(dish_names)
        if compact:
            item_font = "12px" if count <= 7 else "10.5px"
            item_gap = "5px"
        else:
            if count <= 6:
                item_font = "15.5px"
                item_gap = f"{round(10 * ps)}px"
            elif count <= 9:
                item_font = "13.5px"
                item_gap = f"{round(7 * ps)}px"
            else:
                item_font = "12px"
                item_gap = f"{round(5 * ps)}px"

        html_parts = [
            f'<div style="font-size:{sec_title_font}; font-weight:800; color:#000000; text-transform:uppercase; letter-spacing:0.4px; margin-bottom:8px;">MENU SELECTIONS</div>'
        ]

        if dish_names:
            items_html = "".join([
                f'<div style="font-size:{item_font}; font-weight:800; color:#000000; margin-bottom:{item_gap}; line-height:1.35;">&bull; {it}</div>'
                for it in dish_names
            ])
            html_parts.append(items_html)
        else:
            html_parts.append(f"""
            <div style="font-size:{item_font}; font-style:italic; color:#666666;">Standard catering package inclusions apply.</div>
            """)

        return "".join(html_parts)

    _build_foods_grid_html = _build_dishes_table_2col
    _build_dishes_html = _build_dishes_table_2col

    def _build_addons_html(self, booking: dict, compact: bool = False) -> str:
        add_ons = self._get_clean_addons(booking)
        font_sz = "11.5px" if compact else "12px"
        if add_ons:
            items_html = "".join(
                f'<div style="font-size:{font_sz}; color:#000000; margin-bottom:2px;">&#8226; {a}</div>'
                for a in add_ons
            )
            html = f'<div style="margin-top:3px;">{items_html}</div>'
        else:
            html = '<p style="font-size:11px; font-style:italic; color:#666666; margin:2px 0 0 0;">No additional add-on items specified.</p>'
        return html

    def _build_slip_body(self, booking: dict, compact: bool = False, pad_scale: float = 1.0) -> str:
        """One order's content formatted according to the two-column layout:
        Top header with PACKAGE on right, DATE NAME TIME PAX strip,
        VENUE + ADDITIONAL INSTRUCTIONS on left, and Category | Menu 2-column table on right."""
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
        is_food_set = is_food_set_pkg(pkg_name)
        pax_lbl = "SET" if is_food_set else "PAX"
        contact = str(booking.get("contact") or "")

        notes_str = str(booking.get("notes") or "").strip()
        clean_notes = re.sub(r"\n?\[Add-ons:\s*.*?\]", "", notes_str, flags=re.IGNORECASE).strip()

        add_ons = self._get_clean_addons(booking)
        foods_grid_html = self._build_dishes_table_2col(booking, compact=compact, pad_scale=pad_scale)

        ps = pad_scale if not compact else 1.0
        h_title   = "22px" if not compact else "16px"
        strip_lbl = "9px"  if not compact else "8px"
        strip_val = "15px" if not compact else "12px"
        section_lbl = "11px" if not compact else "9.5px"
        venue_val = "15px" if not compact else "12px"
        body_font = "11.5px" if not compact else "10px"

        printed_on_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

        # Additional instructions content (clean notes + clean add-on items)
        instr_parts = []
        if clean_notes:
            instr_parts.append(f'<div style="font-size:{body_font}; font-style:italic; color:#000000; line-height:1.35; margin-bottom:4px;">{clean_notes}</div>')
        if add_ons:
            items_html = "".join(
                f'<div style="font-size:{body_font}; color:#000000; margin-bottom:2px;">&#8226; {a}</div>'
                for a in add_ons
            )
            instr_parts.append(f'<div style="margin-top:2px;">{items_html}</div>')
        if not instr_parts:
            instr_parts.append(f'<div style="font-size:10.5px; font-style:italic; color:#666666;">No additional instructions or add-ons specified.</div>')
        instructions_html = "".join(instr_parts)

        strip_pad = "2px 4px 3px 4px" if not compact else "2px 3px 2px 3px"

        gap_top = f"{round(8 * ps)}px" if not compact else "5px"
        gap_section = f"{round(14 * ps)}px" if not compact else "8px"
        gap_footer = f"{round(18 * ps)}px" if not compact else "10px"

        return f"""
        <!-- Top Section: Business Header on Left, PACKAGE on Right -->
        <table width="100%" style="width:100%; border-collapse:collapse;">
            <tr>
                <td style="vertical-align:top;">
                    <div style="font-size:{h_title}; font-weight:900; color:#E11D48; line-height:1.1;">{biz.get('name', "Jayraldine's Catering")}</div>
                    <div style="font-size:10px; color:#000000; margin-top:2px;">{biz.get('address', '518 V Rama Ave, Cebu City')} &middot; Tel: {biz.get('contact', '+63 912 345 6789')}</div>
                </td>
                <td style="text-align:right; vertical-align:top;">
                    <div style="font-size:10.5px; font-weight:800; color:#444444; text-transform:uppercase; letter-spacing:0.5px;">PACKAGE</div>
                    <div style="font-size:14px; font-weight:900; color:#000000; text-transform:uppercase; margin-top:2px;">{pkg_name}</div>
                </td>
            </tr>
        </table>

        <!-- Summary Strip: DATE NAME TIME PAX -->
        <table width="100%" style="width:100%; border-collapse:collapse; margin-top:{gap_top}; border:1.5px solid #000000;">
            <tr>
                <td style="padding:{strip_pad}; text-align:center; color:#000000; border-right:1px solid #000000; width:25%; vertical-align:middle;">
                    <div style="font-size:{strip_lbl}; font-weight:700; text-transform:uppercase; line-height:1.0; margin:0;">DATE</div>
                    <div style="font-size:{strip_val}; font-weight:800; line-height:1.1; margin-top:1px;">{date_str}</div>
                </td>
                <td style="padding:{strip_pad}; text-align:center; color:#000000; border-right:1px solid #000000; width:35%; vertical-align:middle;">
                    <div style="font-size:{strip_lbl}; font-weight:700; text-transform:uppercase; line-height:1.0; margin:0;">NAME</div>
                    <div style="font-size:{strip_val}; font-weight:800; text-transform:uppercase; line-height:1.1; margin-top:1px;">{cust_name}</div>
                </td>
                <td style="padding:{strip_pad}; text-align:center; color:#000000; border-right:1px solid #000000; width:22%; vertical-align:middle;">
                    <div style="font-size:{strip_lbl}; font-weight:700; text-transform:uppercase; line-height:1.0; margin:0;">TIME</div>
                    <div style="font-size:{strip_val}; font-weight:800; line-height:1.1; margin-top:1px;">{time_str}</div>
                </td>
                <td style="padding:{strip_pad}; text-align:center; color:#000000; width:18%; vertical-align:middle;">
                    <div style="font-size:{strip_lbl}; font-weight:700; text-transform:uppercase; line-height:1.0; margin:0;">{pax_lbl}</div>
                    <div style="font-size:{strip_val}; font-weight:800; line-height:1.1; margin-top:1px;">{pax}</div>
                </td>
            </tr>
        </table>

        <!-- Main Body: Two-Column Split matching wireframe -->
        <table width="100%" style="width:100%; border-collapse:collapse; margin-top:{gap_top};">
            <tr>
                <!-- Left Column: VENUE, ADDITIONAL INSTRUCTIONS, EVENT ORDER, PRINTED ON -->
                <td style="width:44%; vertical-align:top; padding-right:14px;">
                    <div style="font-size:{section_lbl}; font-weight:800; color:#000000; text-transform:uppercase; letter-spacing:0.3px;">VENUE</div>
                    <div style="font-size:{venue_val}; font-weight:800; color:#000000; margin-top:2px; line-height:1.2;">{venue}</div>
                    <div style="font-size:{body_font}; color:#222222; margin-top:4px;"><b>Occasion:</b> {occasion}</div>
                    {f'<div style="font-size:{body_font}; color:#222222; margin-top:2px;"><b>Contact:</b> {contact}</div>' if contact else ''}

                    <div style="margin-top:{gap_section};">
                        <div style="font-size:{section_lbl}; font-weight:800; color:#000000; text-transform:uppercase; letter-spacing:0.3px;">ADDITIONAL INSTRUCTIONS</div>
                        <div style="margin-top:3px;">
                            {instructions_html}
                        </div>
                    </div>

                    <div style="margin-top:{gap_footer};">
                        <div style="font-size:{section_lbl}; font-weight:800; color:#000000; text-transform:uppercase;">EVENT ORDER: <span style="font-size:12px; font-weight:900;">{order_ref}</span></div>
                        <div style="font-size:9.5px; font-weight:700; color:#555555; text-transform:uppercase; margin-top:2px;">PRINTED ON: {printed_on_str}</div>
                    </div>
                </td>

                <!-- Right Column: Category | Menu (strictly 2 columns) -->
                <td style="width:56%; vertical-align:top;">
                    {foods_grid_html}
                </td>
            </tr>
        </table>

        <!-- Bottom separator rule -->
        <hr style="border:none; border-top:1.5px solid #000000; margin-top:14px; margin-bottom:0;"/>
        """

    _BASE_STYLE = """
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin:0; padding:0; color:#000000; }
        </style>
    """

    def _measure_height(self, body_html: str) -> float:
        """Real rendered height (in the same reference-width doc units used
        everywhere else) of a fully-built HTML fragment, via a throwaway
        QTextDocument - this is what makes the container sizing below a
        measured, code-verifiable calculation instead of a guess."""
        scratch = QTextDocument()
        scratch.setHtml(f"<!DOCTYPE html><html><head>{self._BASE_STYLE}</head><body>{body_html}</body></html>")
        scratch.setTextWidth(_SLIP_LAYOUT_WIDTH)
        return scratch.size().height()

    def _build_order_container(self, booking: dict) -> str:
        """One order, laid out to ACTUALLY fill a half-A4 box when its
        content is short enough to fit one - not just a fixed-height outer
        wrapper around a small, natural-sized block:

        1. Render at pad_scale=1.0 (normal spacing) and measure its real
           height.
        2. If that's already >= half-page height, this is a LONG order -
           leave it completely unconstrained (no forced height at all) so
           it's free to run toward a full page, or paginate further, with
           no risk of clipping/overlap.
        3. Otherwise it's a SHORT order - iteratively grow pad_scale (more
           whitespace between sections and dish-table rows, font size never
           touched) and re-measure, converging on the multiplier that makes
           the content's OWN height approach the half-page target. The
           outer box still gets an explicit height as a hard guarantee the
           bottom border lands exactly on the target line even if the
           whitespace growth alone doesn't converge perfectly (e.g. a
           1-dish order has too little content to stretch tastefully all
           the way there).
        """
        # NO outer wrapping <table> around the real content anymore - that
        # was the actual bug. Qt's rich-text table layout does not reliably
        # size a NESTED table by percentage/attribute; wrapping the whole
        # order in an extra <table width="..."> made Qt shrink that outer
        # table to its own content's natural width regardless of what was
        # specified, which is exactly why the dishes table (and everything
        # else) ended up crammed into a narrow left column with a huge
        # unused gap on the right. The strip/dishes/venue elements are
        # width:100% block-level children placed DIRECTLY in <body> (whose
        # width is already pinned via doc.setTextWidth(_SLIP_LAYOUT_WIDTH)
        # in _print_document/_measure_height) - that direct-child placement
        # is what makes width:100% actually span the full page reliably.
        body = self._build_slip_body(booking, compact=False, pad_scale=1.0)
        natural_h = self._measure_height(body)

        if natural_h <= 0 or natural_h >= _SLIP_HALF_HEIGHT:
            # Long order (or measurement failed) - return as-is, completely
            # unconstrained; _print_document's pagination handles overflow
            # if it runs past a full page.
            return body

        # Short order - converge pad_scale so the content's OWN height
        # approaches the half-page target (grows whitespace between
        # sections and dish-table row padding, never font size).
        scale = 1.0
        h = natural_h
        for _ in range(6):
            if h <= 0:
                break
            if abs(_SLIP_HALF_HEIGHT - h) <= 4:
                break
            scale = min(scale * (_SLIP_HALF_HEIGHT / h), 6.0)
            body = self._build_slip_body(booking, compact=False, pad_scale=scale)
            h = self._measure_height(body)
            if h >= _SLIP_HALF_HEIGHT:
                break

        # Top up any remaining shortfall with a trailing spacer whose OWN
        # width is irrelevant - as a block-level element it still occupies
        # exactly its declared height in the page's vertical flow, without
        # ever wrapping (and therefore never width-constraining) the real
        # content above it. The measured deficit makes this an exact,
        # calculated top-up, not a guessed constant.
        deficit = max(0, round(_SLIP_HALF_HEIGHT - h))
        spacer = f'<table height="{deficit}" style="height:{deficit}px;"><tr><td height="{deficit}" style="padding:0;"></td></tr></table>' if deficit > 0 else ""
        return body + spacer

    def _build_booking_agreement_page(self, booking: dict) -> str:
        biz = self._business or {}
        biz_name = html.escape(str(biz.get("name") or "Jayraldine's Catering Services")).upper()
        order_ref = html.escape(str(booking.get("id") or booking.get("booking_ref") or "ORD-SLIP"))
        cust_name = html.escape(str(booking.get("name") or booking.get("customer_name") or "Valued Client"))
        address = html.escape(str(booking.get("address") or booking.get("venue") or "—"))
        contact = html.escape(str(booking.get("contact") or booking.get("phone") or "—"))
        event_date = html.escape(str(booking.get("event_date") or booking.get("date") or "—"))
        event_time = html.escape(str(booking.get("event_time") or booking.get("time") or "—"))
        venue = html.escape(str(booking.get("venue") or "—"))
        occasion = html.escape(str(booking.get("occasion") or "—"))
        motif = html.escape(str(booking.get("motif") or booking.get("color_theme") or "Standard Motif"))
        pax = str(booking.get("pax") or 0)
        pkg_name = html.escape(str(booking.get("package_name") or booking.get("menu_type") or "Catering Package"))
        is_food_set = is_food_set_pkg(pkg_name)
        notes = html.escape(str(booking.get("notes") or booking.get("special_instructions") or ""))
        issue_date = html.escape(str(booking.get("created_at") or datetime.now().strftime("%Y-%m-%d")))

        def _peso(v):
            try:
                val = float(str(v).replace("₱", "").replace(",", "").strip())
                return f"PHP {val:,.2f}"
            except Exception:
                return "PHP 0.00"

        total_str = _peso(booking.get("total_amount") or booking.get("total") or 0)
        paid_val = booking.get("amount_paid") or booking.get("down_payment") or booking.get("paid") or 0
        down_str = _peso(paid_val)
        try:
            tot_f = float(str(booking.get("total_amount") or booking.get("total") or 0).replace("₱", "").replace(",", "").strip())
            paid_f = float(str(paid_val).replace("₱", "").replace(",", "").strip())
            bal_f = max(0.0, tot_f - paid_f)
            bal_str = f"PHP {bal_f:,.2f}"
        except Exception:
            bal_f = 0.0
            bal_str = "PHP 0.00"

        status_str = html.escape(str(booking.get("status") or ("PAID" if bal_f == 0 else "PARTIAL" if paid_f > 0 else "PENDING")).upper())
        pay_mode = html.escape(str(booking.get("payment_mode") or "Cash"))

        # Dishes
        dishes = booking.get("dishes") or []
        if not dishes and booking.get("menu_value"):
            raw_dishes = [d.strip() for d in str(booking["menu_value"]).split(",") if d.strip()]
            dishes = [{"name": rd} for rd in raw_dishes]

        dish_items_html = []
        for idx, d in enumerate(dishes[:10], 1):
            d_name = html.escape(d.get("name") or d.get("item_name") or str(d))
            dish_items_html.append(f"""
                <tr>
                    <td style="width:20px; font-weight:800; color:#E11D48; font-size:11.5px; padding:2px 0; vertical-align:top;">{idx}.</td>
                    <td style="font-size:11.5px; color:#0F172A; padding:2px 0; vertical-align:top;">{d_name}</td>
                </tr>
            """)
        if not dish_items_html:
            dish_items_html.append('<tr><td colspan="2" style="font-size:11.5px; color:#64748B; font-style:italic; padding:4px 0;">Standard Package Inclusions</td></tr>')

        # Add-ons
        addons_html = []
        raw_charges = booking.get("additional_charges") or []
        for c in raw_charges[:5]:
            desc = html.escape(str(c.get("description") or "Add-on"))
            amt_str = _peso(c.get("amount") or 0)
            addons_html.append(f"""
                <tr>
                    <td style="font-size:11px; color:#1E293B; padding:2px 0; vertical-align:top;">• {desc}</td>
                    <td style="font-size:11px; font-weight:700; color:#BE123C; text-align:right; padding:2px 0; vertical-align:top;">{amt_str}</td>
                </tr>
            """)

        addons_section = ""
        if addons_html:
            addons_section = f"""
                <div style="margin-top:10px;">
                    <div style="font-size:11.5px; font-weight:800; color:#0F172A; text-transform:uppercase; border-bottom:1px solid #CBD5E1; padding-bottom:2px; margin-bottom:4px;">ADD-ONS &amp; EXTRAS:</div>
                    <table width="100%" style="width:100%; border-collapse:collapse;">
                        {''.join(addons_html)}
                    </table>
                </div>
            """

        instructions_block = ""
        if notes:
            instructions_block = f"""
                <tr>
                    <td style="font-weight:700; color:#475569; font-size:11px; padding:2.5px 0; vertical-align:top;">Special Instr:</td>
                    <td style="font-size:11px; color:#0F172A; padding:2.5px 0; vertical-align:top;">{notes}</td>
                </tr>
            """

        return f"""
        <div style="box-sizing:border-box; width:{_SLIP_LAYOUT_WIDTH}px; padding:16px 20px; background:#FFFFFF; color:#0F172A; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <!-- HEADER (Top) -->
            <div style="text-align:center; margin-bottom:10px;">
                <div style="font-size:20px; font-weight:900; color:#E11D48; letter-spacing:0.5px;">{biz_name}</div>
                <div style="font-size:13px; font-weight:900; color:#0F172A; text-decoration:underline; margin-top:2px; letter-spacing:0.5px;">BOOKING AGREEMENT</div>
                <div style="font-size:9.5px; color:#64748B; margin-top:3px;">Booking Ref: <b>{order_ref}</b> &nbsp;|&nbsp; Date Issued: {issue_date}</div>
            </div>
            <hr style="border:none; border-top:1px solid #CBD5E1; margin:0 0 12px 0;" />

            <!-- UPPER SECTION (THE ORDER - 2 COLUMNS) -->
            <table width="100%" style="width:100%; border-collapse:collapse;">
                <tr>
                    <!-- Left Sub-Column: Customer Details, Financials, Signatures -->
                    <td style="width:48%; vertical-align:top; padding-right:14px;">
                        <table width="100%" style="width:100%; border-collapse:collapse;">
                            <tr>
                                <td style="width:100px; font-weight:700; color:#475569; font-size:11px; padding:2.5px 0; vertical-align:top;">Name:</td>
                                <td style="font-size:11.5px; font-weight:800; color:#0F172A; padding:2.5px 0; vertical-align:top;">{cust_name}</td>
                            </tr>
                            <tr>
                                <td style="font-weight:700; color:#475569; font-size:11px; padding:2.5px 0; vertical-align:top;">Address:</td>
                                <td style="font-size:11px; color:#0F172A; padding:2.5px 0; vertical-align:top;">{address}</td>
                            </tr>
                            <tr>
                                <td style="font-weight:700; color:#475569; font-size:11px; padding:2.5px 0; vertical-align:top;">Contact #:</td>
                                <td style="font-size:11px; color:#0F172A; padding:2.5px 0; vertical-align:top;">{contact}</td>
                            </tr>
                            <tr>
                                <td style="font-weight:700; color:#475569; font-size:11px; padding:2.5px 0; vertical-align:top;">Function Date:</td>
                                <td style="font-size:11px; font-weight:800; color:#0F172A; padding:2.5px 0; vertical-align:top;">{event_date} ({event_time})</td>
                            </tr>
                            <tr>
                                <td style="font-weight:700; color:#475569; font-size:11px; padding:2.5px 0; vertical-align:top;">Venue:</td>
                                <td style="font-size:11px; color:#0F172A; padding:2.5px 0; vertical-align:top;">{venue}</td>
                            </tr>
                            <tr>
                                <td style="font-weight:700; color:#475569; font-size:11px; padding:2.5px 0; vertical-align:top;">Occasion / Motif:</td>
                                <td style="font-size:11px; color:#0F172A; padding:2.5px 0; vertical-align:top;">{occasion} &middot; {motif}</td>
                            </tr>
                            <tr>
                                <td style="font-weight:700; color:#475569; font-size:11px; padding:2.5px 0; vertical-align:top;">No. of Sets:</td>
                                <td style="font-size:11px; font-weight:800; color:#0F172A; padding:2.5px 0; vertical-align:top;">{pax} Set(s) @ {pkg_name}</td>
                            </tr>
                            {instructions_block}
                        </table>

                        <!-- Financial Box -->
                        <div style="margin-top:10px; padding:8px 12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px;">
                            <table width="100%" style="width:100%; border-collapse:collapse;">
                                <tr>
                                    <td style="font-weight:700; color:#475569; font-size:11px; padding:2px 0;">Total Amount:</td>
                                    <td style="font-size:11.5px; font-weight:900; color:#0F172A; text-align:right; padding:2px 0;">{total_str}</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:700; color:#475569; font-size:11px; padding:2px 0;">Downpayment:</td>
                                    <td style="font-size:11.5px; font-weight:900; color:#16A34A; text-align:right; padding:2px 0;">{down_str}</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:700; color:#475569; font-size:11px; padding:2px 0;">Balance Due:</td>
                                    <td style="font-size:12px; font-weight:900; color:{'#E11D48' if bal_f > 0 else '#16A34A'}; text-align:right; padding:2px 0;">{bal_str}</td>
                                </tr>
                                <tr>
                                    <td colspan="2" style="font-size:9px; color:#64748B; padding-top:3px; border-top:1px dashed #CBD5E1;">Status: <b>{status_str}</b> &nbsp;|&nbsp; Mode: <b>{pay_mode}</b></td>
                                </tr>
                            </table>
                        </div>

                        <!-- Signatures -->
                        <div style="margin-top:12px;">
                            <table width="100%" style="width:100%; border-collapse:collapse;">
                                <tr>
                                    <td style="font-weight:800; font-size:10px; color:#0F172A; width:75px;">CONFORME:</td>
                                    <td style="border-bottom:1px solid #64748B; width:130px;">&nbsp;</td>
                                    <td style="font-weight:800; font-size:10px; color:#0F172A; width:40px; text-align:right; padding-right:4px;">Date:</td>
                                    <td style="border-bottom:1px solid #64748B; width:65px;">&nbsp;</td>
                                </tr>
                                <tr>
                                    <td></td>
                                    <td style="font-size:8px; color:#64748B; text-align:center; padding-top:2px;">Client Signature</td>
                                    <td></td>
                                    <td></td>
                                </tr>
                                <tr>
                                    <td style="font-weight:800; font-size:10px; color:#0F172A; padding-top:6px;">NOTED BY:</td>
                                    <td style="border-bottom:1px solid #64748B; padding-top:6px;">&nbsp;</td>
                                    <td style="font-weight:800; font-size:10px; color:#0F172A; text-align:right; padding-right:4px; padding-top:6px;">Date:</td>
                                    <td style="border-bottom:1px solid #64748B; padding-top:6px;">&nbsp;</td>
                                </tr>
                                <tr>
                                    <td></td>
                                    <td style="font-size:8px; color:#64748B; text-align:center; padding-top:2px;">Catering Representative</td>
                                    <td></td>
                                    <td></td>
                                </tr>
                            </table>
                        </div>
                    </td>

                    <!-- Right Sub-Column: Package Inclusions, Numbered Menu, Add-ons -->
                    <td style="width:52%; vertical-align:top; border-left:1px solid #E2E8F0; padding-left:14px;">
                        <!-- Package Banner -->
                        <div style="background:#FFF1F2; border:1px solid #FECDD3; border-radius:6px; padding:6px 10px; margin-bottom:8px;">
                            <div style="font-size:12px; font-weight:900; color:#BE123C; text-transform:uppercase;">{pkg_name}</div>
                            <div style="font-size:9.5px; color:#475569; margin-top:1px;">{f"Quantity: <b>{pax}</b> Set(s)" if is_food_set else f"Good for <b>{pax}</b> Guests"}</div>
                        </div>

                        <!-- Menu Header & Dishes -->
                        <div style="font-size:11.5px; font-weight:900; color:#0F172A; text-transform:uppercase; border-bottom:1.5px solid #0F172A; padding-bottom:2px; margin-bottom:4px;">MENU:</div>
                        <table width="100%" style="width:100%; border-collapse:collapse;">
                            {''.join(dish_items_html)}
                        </table>

                        {addons_section}
                    </td>
                </tr>
            </table>

            <!-- LOWER SECTION (TERMS AND CONDITIONS) -->
            <hr style="border:none; border-top:2px solid #E11D48; margin:14px 0 8px 0;" />
            <div style="font-size:12px; font-weight:900; color:#0F172A; margin-bottom:5px;">Terms and Conditions</div>
            <table width="100%" style="width:100%; border-collapse:collapse; font-size:10px; color:#334155; line-height:1.3;">
                <tr>
                    <td style="width:14px; vertical-align:top; font-weight:800; color:#E11D48; padding:1.5px 0;">&bull;</td>
                    <td style="vertical-align:top; padding:1.5px 0 3px 4px;">The client shall pay 50% downpayment upon reservation of booking and shall pay the full amount 3 days before the date of the event.</td>
                </tr>
                <tr>
                    <td style="width:14px; vertical-align:top; font-weight:800; color:#E11D48; padding:1.5px 0;">&bull;</td>
                    <td style="vertical-align:top; padding:1.5px 0 3px 4px;"><b>Mode of payment.</b> The client shall personally pay in Cash for the downpayment and full payment. If cash is not available, the client shall also pay through Bank Transfer or Gcash.</td>
                </tr>
                <tr>
                    <td style="width:14px; vertical-align:top; font-weight:800; color:#E11D48; padding:1.5px 0;">&bull;</td>
                    <td style="vertical-align:top; padding:1.5px 0 3px 4px;"><b>Failure to pay.</b> A failure to make payment according to the terms of the payment will be considered a cancellation of the event and the provisions for cancellation will apply: (15) days before the event - 20% charge, (7) days - 30%, (3) days - 50%.</td>
                </tr>
                <tr>
                    <td style="width:14px; vertical-align:top; font-weight:800; color:#E11D48; padding:1.5px 0;">&bull;</td>
                    <td style="vertical-align:top; padding:1.5px 0 3px 4px;">Any Food and Drinks or any consumables that is NOT prepared by JAY-RALDINE SERVICES brought by the client will <b>FREE US ON ANY LIABILITIES</b> due to food poisoning and spoilage. We charged Corkage Fee for bringing outside Food and Drinks. Precise time should be place in the BOOKING AGREEMENT and shall be strictly follow to avoid poisoning and spoilage.</td>
                </tr>
            </table>

            <!-- FOOTER INVITATION BOX -->
            <div style="margin-top:10px; padding:8px 14px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; text-align:center;">
                <div style="font-size:10px; font-weight:900; color:#BE123C; letter-spacing:0.3px;">WE INVITE YOU TO SEE HOW WE CAN HELP YOUR EVENT THE BEST IT CAN POSSIBLY BE!!!</div>
                <div style="font-size:9.5px; color:#1E293B; margin-top:2px;">Located at 121 Katipunan St. Brgy Calamba Cebu City</div>
                <div style="font-size:9.5px; color:#1E293B; margin-top:1px;">Please feel free to call us at (032) 255-3113, (032) 238-9417 &middot; Globe 0917-6519555, 0917-1051528</div>
                <div style="font-size:9.5px; font-weight:800; color:#0284C7; margin-top:1px;">Find us on Facebook: Jayraldine's Catering Services</div>
            </div>
        </div>
        """

    def _build_page_bodies(self) -> list[str]:
        """One entry per PHYSICAL A4 sheet.
        When _current_mode == "agreement", builds 1 full A4 page per booking with
        the up-and-down Booking Agreement matching the client's manual form.
        When _current_mode == "kitchen", pairs orders two per sheet for dispatch."""
        if self._current_mode == "agreement":
            return [self._build_booking_agreement_page(b) for b in self._bookings]

        n = len(self._bookings)
        if n <= 1:
            booking = self._bookings[0] if self._bookings else {}
            return [self._build_order_container(booking)]

        pages = []
        i = 0
        while i < n:
            pair = self._bookings[i:i + 2]
            if len(pair) == 2:
                half_a = self._build_order_container(pair[0])
                half_b = self._build_order_container(pair[1])
                pages.append(f"""
                {half_a}
                <div style="text-align:center; color:#000000; font-size:10px; margin:2px 0; border-top:1px dashed #000000;">✂ — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — ✂</div>
                {half_b}
                """)
            else:
                pages.append(self._build_order_container(pair[0]))
            i += 2
        return pages

    def _generate_slip_html(self) -> str:
        """Full HTML for the on-screen scrollable preview - all pages
        concatenated with CSS page-break-after hints between them."""
        joined = '<div style="page-break-after: always;"></div>'.join(self._build_page_bodies())
        return f"<!DOCTYPE html><html><head>{self._BASE_STYLE}</head><body>{joined}</body></html>"

    def _copy_slip_text(self):
        blocks = []
        if self._current_mode == "agreement":
            for booking in self._bookings:
                order_ref = str(booking.get("id") or booking.get("booking_ref") or "ORD-SLIP")
                cust_name = str(booking.get("name") or booking.get("customer_name") or "Valued Client")
                venue = str(booking.get("venue") or booking.get("address") or "TBA")
                date_str = str(booking.get("event_date") or booking.get("date") or "TBA")
                time_str = str(booking.get("event_time") or booking.get("time") or "TBA")
                pax = str(booking.get("pax", 0))
                pkg_name = str(booking.get("package_name") or booking.get("menu_type") or "Catering Package")
                tot = float(str(booking.get("total_amount") or booking.get("total") or 0).replace("₱", "").replace(",", "").strip() or 0)
                paid = float(str(booking.get("amount_paid") or booking.get("down_payment") or 0).replace("₱", "").replace(",", "").strip() or 0)
                bal = max(0.0, tot - paid)

                dishes = booking.get("dishes") or []
                dish_lines = []
                for d in dishes:
                    d_name = d.get("name") or d.get("item_name") or str(d)
                    if d_name:
                        dish_lines.append(f"  • {d_name}")
                dishes_text = "\n".join(dish_lines) if dish_lines else "  • Standard Package Inclusions"

                charges = booking.get("additional_charges") or []
                charge_lines = [f"  • {c.get('description', 'Add-on')}: PHP {float(c.get('amount', 0)):,.2f}" for c in charges]
                charges_text = "\n".join(charge_lines) if charge_lines else "  None"

                blocks.append(f"""==================================================
JAYRALDINE'S CATERING SERVICES - BOOKING AGREEMENT
Order Ref: {order_ref}
==================================================
DATE:        {date_str}
NAME:        {cust_name}
TIME:        {time_str}
{f"SET:         {pax} Set(s)"}
VENUE:       {venue}
PACKAGE:     {pkg_name}

TOTAL:       PHP {tot:,.2f}
DOWNPAYMENT: PHP {paid:,.2f}
BALANCE:     PHP {bal:,.2f}

MENU DISHES:
{dishes_text}

ADD-ONS & EXTRAS:
{charges_text}

TERMS AND CONDITIONS:
1. 50% downpayment upon reservation, full payment 3 days before event.
2. Mode of payment: Cash, Bank Transfer, or GCash.
3. Cancellation: 15 days (20%), 7 days (30%), 3 days (50%).
4. Outside food/drinks: freedom of liability, corkage applies.
==================================================""")
            text = "\n\n".join(blocks)
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            success(self, message="Booking agreement details copied to clipboard!" if len(self._bookings) == 1 else "Booking agreements copied to clipboard!")
            return

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
{f"SET:         {pax} Set(s)"}
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
        if self._current_mode == "agreement":
            if len(self._bookings) == 1:
                order_ref = str(self._bookings[0].get("id") or self._bookings[0].get("booking_ref") or "order").replace("/", "-")
                default_name = f"Booking_Agreement_{order_ref}.pdf"
            else:
                default_name = f"Booking_Agreements_{len(self._bookings)}_orders.pdf"
            title = "Save Booking Agreement PDF"
        else:
            if len(self._bookings) == 1:
                order_ref = str(self._bookings[0].get("id") or self._bookings[0].get("booking_ref") or "order").replace("/", "-")
                default_name = f"Kitchen_Slip_{order_ref}.pdf"
            else:
                default_name = f"Kitchen_Slips_{len(self._bookings)}_orders.pdf"
            title = "Save Kitchen Slip PDF"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            title,
            default_name,
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        if self._current_mode == "agreement" and len(self._bookings) == 1 and exporter.REPORTLAB_OK:
            b = self._bookings[0]
            try:
                if exporter.export_receipt_pdf(file_path, b, business=self._business, additional_charges=b.get("additional_charges", [])):
                    success(self, message=f"Booking Agreement PDF exported successfully:\n{os.path.basename(file_path)}")
                    return
            except Exception as e:
                print(f"[OrderPrintDialog] exporter fallback: {e}")

        printer = QPrinter(QPrinter.HighResolution)
        self._configure_a4(printer)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)
        self._print_document(printer)
        success(self, message=f"PDF exported successfully:\n{os.path.basename(file_path)}")

    def _print_order(self):
        if not PRINTER_SUPPORT:
            QMessageBox.warning(self, "Printing Unsupported", "Qt Print Support is not installed on this workstation.")
            return

        printer = QPrinter(QPrinter.HighResolution)
        self._configure_a4(printer)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print Banquet Order Slip" if len(self._bookings) == 1 else "Print Banquet Order Slips")
        if dialog.exec() == QPrintDialog.Accepted:
            # Booking Agreement prints must be pixel-identical to Export PDF
            # (same client complaint every time they drifted apart) — render
            # the exact same ReportLab-generated PDF onto the printer instead
            # of the separate QTextDocument/HTML layout below. That HTML path
            # only remains for Kitchen Slip mode and multi-booking prints,
            # which export_receipt_pdf doesn't support.
            if (self._current_mode == "agreement" and len(self._bookings) == 1
                    and exporter.REPORTLAB_OK and self._print_agreement_via_pdf(printer)):
                success(self, message="Order slip sent to printer successfully.")
                return
            self._print_document(printer)
            success(self, message="Order slip sent to printer successfully." if len(self._bookings) == 1 else "Order slips sent to printer successfully.")

    def _print_agreement_via_pdf(self, printer) -> bool:
        """Generate the official Booking Agreement PDF (same function Export
        PDF uses) and rasterize its pages straight onto the printer, so
        Print and Export PDF always match exactly. Returns False on any
        failure so the caller can fall back to the HTML print path."""
        import tempfile
        tmp_path = None
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtGui import QPainter
            from PySide6.QtCore import QSize, QRectF

            b = self._bookings[0]
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            if not exporter.export_receipt_pdf(
                tmp_path, b, business=self._business,
                additional_charges=b.get("additional_charges", [])
            ):
                return False

            pdf_doc = QPdfDocument(self)
            if pdf_doc.load(tmp_path) != QPdfDocument.Error.None_:
                return False
            if pdf_doc.pageCount() <= 0:
                return False

            painter = QPainter()
            if not painter.begin(printer):
                return False
            try:
                page_rect = printer.pageRect(QPrinter.DevicePixel)
                dpi_x = printer.physicalDpiX() or 300
                dpi_y = printer.physicalDpiY() or 300
                for page_idx in range(pdf_doc.pageCount()):
                    if page_idx > 0:
                        printer.newPage()
                    pt_size = pdf_doc.pagePointSize(page_idx)
                    px_w = max(1, int(pt_size.width() / 72.0 * dpi_x))
                    px_h = max(1, int(pt_size.height() / 72.0 * dpi_y))
                    image = pdf_doc.render(page_idx, QSize(px_w, px_h))
                    if image.isNull():
                        continue
                    painter.drawImage(QRectF(0, 0, page_rect.width(), page_rect.height()), image)
            finally:
                painter.end()
            return True
        except Exception as e:
            print(f"[OrderPrintDialog] PDF-based print failed, falling back to HTML print: {e}")
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _print_document(self, printer):
        # Each PHYSICAL A4 sheet is rendered from its own independent
        # scratch QTextDocument (built fresh from _build_page_bodies(),
        # NOT the live on-screen QTextBrowser's document/HTML) so page
        # boundaries are exact and deterministic - printing straight from
        # one giant concatenated document and slicing it by cumulative
        # height doesn't understand CSS page-break-after at all, so a pair
        # of orders could drift across the wrong page boundary once more
        # pages were involved. Each page is pinned to the same fixed
        # reference width used when the HTML was built (_SLIP_LAYOUT_WIDTH)
        # and painted at an explicit scale to fill the printer's actual page
        # width - this is the same core technique as before, just applied
        # per-page instead of to one combined blob.
        from PySide6.QtGui import QPainter
        from PySide6.QtCore import QRectF

        page_rect = printer.pageRect(QPrinter.DevicePixel)
        if page_rect.width() <= 0 or page_rect.height() <= 0:
            self._doc_browser.document().print_(printer)
            return

        painter = QPainter()
        if not painter.begin(printer):
            self._doc_browser.document().print_(printer)
            return
        try:
            page_bodies = self._build_page_bodies()
            for page_idx, body_html in enumerate(page_bodies):
                if page_idx > 0:
                    printer.newPage()

                scratch = QTextDocument()
                scratch.setHtml(f"<!DOCTYPE html><html><head>{self._BASE_STYLE}</head><body>{body_html}</body></html>")
                scratch.setTextWidth(_SLIP_LAYOUT_WIDTH)
                doc_size = scratch.size()
                if doc_size.width() <= 0 or doc_size.height() <= 0:
                    continue

                scale = page_rect.width() / doc_size.width()
                page_height_doc_units = page_rect.height() / scale
                total_height = doc_size.height()

                # A single physical page's content should already fit within
                # one page (it's built to a fixed half-A4 height), but if an
                # unusually long order overflows anyway, fall back to
                # slicing it across additional pages rather than clipping it.
                y_offset = 0.0
                first_slice = True
                while y_offset < total_height:
                    if not first_slice:
                        printer.newPage()
                    first_slice = False
                    painter.save()
                    painter.scale(scale, scale)
                    painter.translate(0, -y_offset)
                    slice_height = min(page_height_doc_units, total_height - y_offset)
                    scratch.drawContents(painter, QRectF(0, y_offset, doc_size.width(), slice_height))
                    painter.restore()
                    y_offset += page_height_doc_units
        finally:
            painter.end()
