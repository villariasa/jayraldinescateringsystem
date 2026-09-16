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

    def _build_dishes_html(self, booking: dict, compact: bool = False, pad_scale: float = 1.0) -> str:
        dishes = booking.get("dishes") or []
        if not dishes and booking.get("menu_value"):
            raw_dishes = [d.strip() for d in str(booking["menu_value"]).split(",") if d.strip()]
            dishes = [{"name": rd, "category": "Selected Menu"} for rd in raw_dishes]

        by_cat = {}
        seen_per_cat = {}
        for d in dishes:
            cat = d.get("category") or "Menu Dishes"
            # Never fall back to str(d) - a dish record with a missing name
            # (e.g. a legacy/unresolved item_id) used to print the raw
            # Python dict repr ("{'item_id': 32, 'name': None, ...}")
            # straight onto the order slip.
            d_name = d.get("name") or d.get("item_name") or (f"Item #{d['item_id']}" if d.get("item_id") else None)
            if d_name:
                # Skip if this dish name is already listed under this
                # category (case-insensitive) - a booking can end up with
                # the same dish stored as more than one booking_menu_items
                # row (e.g. added twice during editing, or a duplicate
                # synced from another device), which used to print e.g.
                # "Chicken Pandan" twice in a row instead of once.
                seen = seen_per_cat.setdefault(cat, set())
                key = d_name.strip().lower()
                if key not in seen:
                    seen.add(key)
                    by_cat.setdefault(cat, []).append(d_name)

        # Moderate, legible sizing budgeted for a half-A4-page slip. Row
        # padding (NOT font size) scales with pad_scale so a short dish list
        # can be spread out to help fill a half-page box.
        ps = pad_scale if not compact else 1.0
        item_font = "13px" if not compact else "12px"
        cat_font = "11.5px" if not compact else "11px"
        cell_pad = f"{round(8 * ps)}px 10px" if not compact else "8px 12px"

        if by_cat:
            # Black borders/text throughout (only the business name stays
            # brand-colored) - the header row keeps a light gray fill per
            # the approved reference layout, since it's minimal ink and
            # helps the header row stand out for kitchen staff at a glance.
            html = '<table width="100%" style="width:100%; border-collapse:collapse; margin-top:6px; border:2px solid #000000;">'
            html += '<tr style="border-bottom:2px solid #000000; background-color:#EEEEEE; color:#000000;">'
            html += f'<th style="padding:{cell_pad}; text-align:left; font-size:{cat_font}; width:28%;">Course / Category</th>'
            html += f'<th style="padding:{cell_pad}; text-align:left; font-size:{cat_font}; width:72%;">Selected Food &amp; Menu</th>'
            html += '</tr>'
            for cat, items in by_cat.items():
                items_str = "<br/>".join([f"● <b>{it}</b>" for it in items])
                html += f"""
                <tr style="border-bottom:1px solid #000000;">
                    <td style="padding:{cell_pad}; vertical-align:top; font-size:{cat_font}; font-weight:bold; color:#000000;">{cat}</td>
                    <td style="padding:{cell_pad}; vertical-align:top; font-size:{item_font}; font-weight:700; color:#000000; line-height:1.6;">{items_str}</td>
                </tr>
                """
            html += '</table>'
        else:
            html = '<p style="font-size:12px; font-style:italic; color:#000000;">Standard catering package inclusions apply.</p>'
        return html

    def _build_addons_html(self, booking: dict, compact: bool = False) -> str:
        add_ons = self._get_clean_addons(booking)
        font_sz = "12px" if compact else "13px"
        if add_ons:
            # Bulleted list — no table, no price columns, no logistics column.
            # Matches reference layout: just a plain list of add-on names.
            items_html = "".join(
                f'<div style="font-size:{font_sz}; color:#000000; margin-bottom:2px;">&#8226; {a}</div>'
                for a in add_ons
            )
            html = f'<div style="margin-top:4px;">{items_html}</div>'
        else:
            html = '<p style="font-size:12px; font-style:italic; color:#000000; margin:2px 0 0 0;">No additional add-on items specified.</p>'
        return html

    def _build_slip_body(self, booking: dict, compact: bool = False, pad_scale: float = 1.0) -> str:
        """One order's content: Date | Name | Time | Pax summary strip, then
        package/menu (highlighted) and add-ons. `compact` shrinks fonts/
        spacing for the two-per-page half-page layout. `pad_scale` grows the
        WHITESPACE between sections (never font size) - used by
        _build_order_container() to spread a short order's content out to
        fill a half-A4 box instead of leaving it a small block with a big
        empty gap underneath."""
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

        dishes_html = self._build_dishes_html(booking, compact=compact, pad_scale=pad_scale)
        addons_html = self._build_addons_html(booking, compact=compact)

        # Font sizes scaled to match reference screenshot exactly.
        h_title   = "22px" if not compact else "14px"   # Business name
        strip_lbl = "9px"  if not compact else "8px"    # DATE / NAME / TIME / PAX labels
        strip_val = "16px" if not compact else "12px"   # Values in the strip row
        section_font = "12px" if not compact else "10.5px"
        venue_font   = "16px" if not compact else "12px"

        # Special Instructions — plain bold-uppercase label + italic text,
        # NO border box.  Matches the reference screenshot exactly.
        remarks_html = ""
        if clean_notes and not compact:
            remarks_html = f"""
            <div style="margin-top:10px;">
                <div style="font-size:{section_font}; font-weight:800; color:#000000; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:2px;">Special Instructions &amp; Remarks:</div>
                <div style="font-size:{section_font}; font-style:italic; color:#000000; line-height:1.4;">{clean_notes}</div>
            </div>
            """

        # pad_scale only stretches whitespace for the non-compact (single/
        # paired half-page) layout - the tiny compact metrics are untouched.
        ps = pad_scale if not compact else 1.0
        strip_pad_v = round(10 * ps) if not compact else 7
        strip_pad = f"{strip_pad_v}px 12px" if not compact else "7px 8px"
        gap_lg = f"{round(12 * ps)}px" if not compact else "8px"
        gap_md = f"{round(8 * ps)}px"  if not compact else "5px"
        gap_sm = f"{round(4 * ps)}px"  if not compact else "2px"

        # Bottom separator line — a single thin horizontal rule at the very
        # end of the slip (visible in the reference screenshot).
        bottom_sep = (
            '<hr style="border:none; border-top:1.5px solid #000000; margin-top:14px; margin-bottom:0;"/>'
            if not compact else ""
        )

        addons_section = ""
        if not compact:
            addons_section = f"""
            <div style="margin-top:{gap_lg};">
                <div style="font-size:{section_font}; font-weight:800; color:#000000; text-transform:uppercase; letter-spacing:0.3px;">Additional Items &amp; Add-ons (No Rates Shown)</div>
                {addons_html}
            </div>
            """

        return f"""
        <!-- Business header — only name in brand red, rest plain black. -->
        <div style="font-size:{h_title}; font-weight:900; color:#E11D48; line-height:1.1;">{biz.get('name', "Jayraldine's Catering")}</div>
        <div style="font-size:10px; color:#000000; margin-top:1px;">{biz.get('address', 'Cebu City')} &middot; Tel: {biz.get('contact', '')}</div>
        <div style="font-size:10px; font-weight:800; color:#000000; letter-spacing:0.5px; margin-top:3px;">BANQUET EVENT ORDER &ndash; {order_ref}</div>

        <!-- Date | Name | Time | Pax strip -->
        <table width="100%" style="width:100%; border-collapse:collapse; margin-top:{gap_md}; border:1.5px solid #000000;">
            <tr>
                <td style="padding:{strip_pad}; text-align:center; color:#000000; font-size:{strip_lbl}; font-weight:700; text-transform:uppercase; border-right:1px solid #000000;">
                    Date<br/><span style="font-size:{strip_val}; font-weight:800;">{date_str}</span>
                </td>
                <td style="padding:{strip_pad}; text-align:center; color:#000000; font-size:{strip_lbl}; font-weight:700; text-transform:uppercase; border-right:1px solid #000000;">
                    Name<br/><span style="font-size:{strip_val}; font-weight:800; text-transform:uppercase;">{cust_name}</span>
                </td>
                <td style="padding:{strip_pad}; text-align:center; color:#000000; font-size:{strip_lbl}; font-weight:700; text-transform:uppercase; border-right:1px solid #000000;">
                    Time<br/><span style="font-size:{strip_val}; font-weight:800;">{time_str}</span>
                </td>
                <td style="padding:{strip_pad}; text-align:center; color:#000000; font-size:{strip_lbl}; font-weight:700; text-transform:uppercase;">
                    Pax<br/><span style="font-size:{strip_val}; font-weight:800;">{pax}</span>
                </td>
            </tr>
        </table>

        <!-- Venue / Location -->
        <div style="margin-top:{gap_md}; font-size:{strip_lbl}; font-weight:700; color:#000000; text-transform:uppercase;">Venue / Location</div>
        <div style="font-size:{venue_font}; font-weight:800; color:#000000; margin-top:{gap_sm};">{venue}</div>

        <!-- Occasion + Contact -->
        <div style="margin-top:{gap_sm}; font-size:{section_font}; color:#000000;">
            <b>Occasion:</b> {occasion}{f' &nbsp;&nbsp; <b>Contact:</b> {contact}' if contact and not compact else ''}
        </div>

        <!-- Package name -->
        <div style="margin-top:{gap_lg}; font-size:{section_font}; font-weight:800; color:#000000; text-transform:uppercase; letter-spacing:0.4px;">Package: {pkg_name}</div>
        {dishes_html}

        {addons_section}
        {remarks_html}
        {bottom_sep}
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

    def _build_page_bodies(self) -> list[str]:
        """One entry per PHYSICAL A4 sheet - a single order's box (half-page
        if short, unconstrained/growing toward a full page if long), or two
        short orders' half-page boxes plus a cut line. Kept separate
        (rather than one giant concatenated HTML blob) so printing can
        measure/scale/draw each physical page independently and precisely,
        instead of guessing page boundaries from cumulative content height
        (which doesn't understand CSS page-break-after at all and would let
        one page's content drift into the next as more pages are added)."""
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
