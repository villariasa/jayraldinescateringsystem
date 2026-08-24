import os
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image, KeepTogether
    )
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False


if REPORTLAB_OK:
    _C_RED    = colors.HexColor("#E11D48")
    _C_DARK   = colors.HexColor("#0B1220")
    _C_GRAY   = colors.HexColor("#374151")
    _C_LIGHT  = colors.HexColor("#F9FAFB")
    _C_WHITE  = colors.white
    _C_MUTED  = colors.HexColor("#6B7280")
    _C_BORDER = colors.HexColor("#E5E7EB")
    _C_GREEN  = colors.HexColor("#22C55E")
    _C_AMBER  = colors.HexColor("#F59E0B")
    _C_BLUE   = colors.HexColor("#3B82F6")
else:
    _C_RED = _C_DARK = _C_GRAY = _C_LIGHT = _C_WHITE = _C_MUTED = _C_BORDER = _C_GREEN = _C_AMBER = _C_BLUE = None

from utils.paths import resource_path


def _logo_path() -> str:
    p = resource_path("assets", "logo.png")
    if not os.path.exists(p):
        p = resource_path("assets", "logo.jpg")
    return p

_PAGE_W = A4[0] if REPORTLAB_OK else 595
_MARGIN = 1.5 * cm if REPORTLAB_OK else 0
_CONTENT_W = _PAGE_W - 2 * _MARGIN


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("Brand",
        fontName="Helvetica-Bold", fontSize=22, textColor=_C_RED,
        spaceAfter=2, alignment=TA_LEFT, leading=26))
    s.add(ParagraphStyle("BrandSub",
        fontName="Helvetica", fontSize=9.5, textColor=_C_MUTED,
        spaceAfter=0, alignment=TA_LEFT, leading=13))
    s.add(ParagraphStyle("BrandSubRight",
        fontName="Helvetica", fontSize=9.5, textColor=_C_MUTED,
        spaceAfter=0, alignment=TA_RIGHT, leading=13))
    s.add(ParagraphStyle("SectionHead",
        fontName="Helvetica-Bold", fontSize=12, textColor=_C_DARK,
        spaceBefore=16, spaceAfter=8, alignment=TA_LEFT, leading=16))
    s.add(ParagraphStyle("KpiLabel",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_MUTED,
        spaceAfter=2, alignment=TA_CENTER, leading=11))
    s.add(ParagraphStyle("KpiValue",
        fontName="Helvetica-Bold", fontSize=16, textColor=_C_DARK,
        spaceAfter=0, alignment=TA_CENTER, leading=19))
    s.add(ParagraphStyle("Footer",
        fontName="Helvetica", fontSize=8, textColor=_C_MUTED,
        alignment=TA_CENTER, leading=11))
    s.add(ParagraphStyle("ReceiptTitle",
        fontName="Helvetica-Bold", fontSize=18, textColor=_C_WHITE,
        alignment=TA_LEFT, leading=22, spaceAfter=4))
    s.add(ParagraphStyle("ReceiptSub",
        fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#CBD5E1"),
        alignment=TA_LEFT, leading=13))
    s.add(ParagraphStyle("DetailLabel",
        fontName="Helvetica-Bold", fontSize=9.5, textColor=_C_GRAY,
        leading=13, wordWrap="CJK"))
    s.add(ParagraphStyle("DetailValue",
        fontName="Helvetica", fontSize=9.5, textColor=_C_DARK,
        leading=13, wordWrap="CJK"))
    s.add(ParagraphStyle("DetailValueBold",
        fontName="Helvetica-Bold", fontSize=9.5, textColor=_C_DARK,
        leading=13, wordWrap="CJK"))
    s.add(ParagraphStyle("TableHead",
        fontName="Helvetica-Bold", fontSize=9, textColor=_C_WHITE,
        alignment=TA_CENTER, leading=12))
    s.add(ParagraphStyle("TableCell",
        fontName="Helvetica", fontSize=8.5, textColor=_C_DARK,
        leading=12, wordWrap="CJK"))
    s.add(ParagraphStyle("TableCellRight",
        fontName="Helvetica", fontSize=8.5, textColor=_C_DARK,
        alignment=TA_RIGHT, leading=12, wordWrap="CJK"))
    s.add(ParagraphStyle("TableCellCenter",
        fontName="Helvetica", fontSize=8.5, textColor=_C_DARK,
        alignment=TA_CENTER, leading=12, wordWrap="CJK"))
    s.add(ParagraphStyle("StatusPaid",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_GREEN,
        alignment=TA_CENTER, leading=12))
    s.add(ParagraphStyle("StatusPartial",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_AMBER,
        alignment=TA_CENTER, leading=12))
    s.add(ParagraphStyle("StatusUnpaid",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_RED,
        alignment=TA_CENTER, leading=12))
    s.add(ParagraphStyle("CalDayHead",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_WHITE,
        alignment=TA_CENTER, leading=11))
    s.add(ParagraphStyle("CalDateNum",
        fontName="Helvetica-Bold", fontSize=9, textColor=_C_DARK,
        alignment=TA_LEFT, leading=11))
    s.add(ParagraphStyle("CalEventChip",
        fontName="Helvetica", fontSize=7, textColor=_C_DARK,
        alignment=TA_LEFT, leading=9))
    return s


def _status_style(status: str, styles):
    mapping = {
        "Paid":    styles["StatusPaid"],
        "Partial": styles["StatusPartial"],
        "Unpaid":  styles["StatusUnpaid"],
    }
    return mapping.get(status, styles["TableCell"])


def _header_block(story, styles, biz_name: str, title: str, period: str = "All Time"):
    header_left = []
    _lp = _logo_path()
    if os.path.exists(_lp):
        try:
            logo = Image(_lp, width=2*cm, height=2*cm)
            header_left.append(logo)
        except Exception:
            header_left.append(Paragraph(biz_name[:1], styles["Brand"]))
    else:
        header_left.append(Paragraph(biz_name[:1], styles["Brand"]))

    header_center = [
        Paragraph(biz_name, styles["Brand"]),
        Paragraph("Professional Catering Services", styles["BrandSub"]),
    ]

    now_str = datetime.now().strftime("%b %d, %Y  %I:%M %p")
    header_right = [
        Paragraph(f"<b>{title}</b>", styles["BrandSubRight"]),
        Paragraph(f"Period: {period}", styles["BrandSubRight"]),
        Paragraph(f"Generated: {now_str}", styles["BrandSubRight"]),
    ]

    tbl = Table([[header_left, header_center, header_right]],
                colWidths=[2.2*cm, 10.5*cm, 5.5*cm])
    tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (2, 0), (2, 0),   "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(HRFlowable(width="100%", thickness=2.5, color=_C_RED, spaceAfter=12))


def _kpi_row(story, styles, kpis: dict):
    items = [
        ("Total Bookings",  str(kpis.get("total_bookings", 0))),
        ("Total Pax",       f"{int(kpis.get('total_pax', 0)):,}"),
        ("Total Revenue",   f"PHP {float(kpis.get('total_revenue', 0)):,.0f}"),
        ("Unpaid Amount",   f"PHP {float(kpis.get('unpaid_amount', 0)):,.0f}"),
    ]
    ncols = len(items)
    col_w = [_CONTENT_W / ncols] * ncols

    labels_row = [Paragraph(lbl, styles["KpiLabel"]) for lbl, _ in items]
    values_row = [Paragraph(val, styles["KpiValue"]) for _, val in items]

    t = Table([labels_row, values_row], colWidths=col_w)
    t.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 0.5, _C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, _C_BORDER),
        ("BACKGROUND",    (0, 0), (-1, 0),  _C_LIGHT),
        ("BACKGROUND",    (0, 1), (-1, 1),  _C_WHITE),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))


def _bookings_table(story, styles, bookings: list):
    story.append(Paragraph("Booking Statistics", styles["SectionHead"]))

    headers = ["Booking Ref", "Client", "Event Date", "Pax", "Total Amount", "Status"]
    col_w   = [2.8*cm, 5.5*cm, 2.8*cm, 1.5*cm, 3.2*cm, 2.4*cm]

    header_row = [Paragraph(h, styles["TableHead"]) for h in headers]
    rows = [header_row]

    status_styles = {
        "CONFIRMED": styles["StatusPaid"],
        "PENDING":   styles["StatusPartial"],
        "CANCELLED": styles["StatusUnpaid"],
    }

    for b in bookings:
        st_key = b.get("status", "").upper()
        st_style = status_styles.get(st_key, styles["TableCell"])
        rows.append([
            Paragraph(b.get("id", ""), styles["TableCell"]),
            Paragraph(b.get("name", ""), styles["TableCell"]),
            Paragraph(b.get("date", ""), styles["TableCellCenter"]),
            Paragraph(str(b.get("pax", "")), styles["TableCellCenter"]),
            Paragraph(b.get("total", ""), styles["TableCellRight"]),
            Paragraph(b.get("status", "").capitalize(), st_style),
        ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  _C_RED),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_C_WHITE, _C_LIGHT]),
        ("BOX",           (0, 0), (-1, -1), 0.4, _C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, _C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl)


def _footer(story, styles, biz_name: str = "Jayraldine's Catering"):
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_C_BORDER))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"{biz_name}  •  This report is system-generated and confidential.",
        styles["Footer"]
    ))


def build_analytics_sections() -> list:
    """Analytics data tables for exports: (title, headers, rows).
    Mirrors what the Reports page charts show."""
    import utils.repository as repo
    sections = []

    def _safe(fn):
        try:
            return fn() or []
        except Exception:
            return []

    rows = _safe(repo.get_profit_summary)
    if rows:
        sections.append((
            "Monthly Revenue, Expenses & Profit (This Year)",
            ["Month", "Revenue", "Expenses", "Net Profit"],
            [[r["month"], f"PHP {r['revenue']:,.0f}", f"PHP {r['expense']:,.0f}",
              f"PHP {r['profit']:,.0f}"] for r in rows]))

    rows = _safe(repo.get_payment_methods)
    if rows:
        sections.append(("Payment Methods", ["Method", "Bookings"],
                         [[r["method"], str(r["total"])] for r in rows]))

    rows = _safe(repo.get_top_menu_items)
    if rows:
        sections.append(("Top Menu Items", ["Item", "Orders"],
                         [[r["item"], str(r["count"])] for r in rows]))

    rows = _safe(lambda: repo.get_top_locations(limit=10))
    if rows:
        sections.append((
            "Top Event Locations", ["Location", "Bookings"],
            [[str(r.get("location") or r.get("name") or "?"),
              str(r.get("count") or r.get("total") or 0)] for r in rows]))

    rows = _safe(lambda: repo.get_top_occasions(limit=10))
    if rows:
        sections.append((
            "Bookings by Occasion", ["Occasion", "Bookings"],
            [[str(r.get("occasion") or r.get("name") or "?"),
              str(r.get("count") or r.get("total") or 0)] for r in rows]))

    rows = _safe(repo.get_customer_order_frequency)
    if rows:
        sections.append(("Customer Order Frequency", ["Customer", "Bookings"],
                         [[r["name"], str(r["count"])] for r in rows]))

    rows = _safe(lambda: repo.get_expense_breakdown(datetime.now().year))
    if rows:
        sections.append(("Expenses by Category (This Year)", ["Category", "Amount"],
                         [[r["category"], f"PHP {r['total']:,.0f}"] for r in rows]))

    rows = _safe(repo.get_yearly_summary)
    if rows:
        sections.append((
            "Year-over-Year Summary", ["Year", "Revenue", "Expenses", "Net Profit"],
            [[str(r["year"]), f"PHP {r['revenue']:,.0f}", f"PHP {r['expense']:,.0f}",
              f"PHP {r['profit']:,.0f}"] for r in rows]))

    return sections


def _section_table(story, styles, title: str, headers: list, rows: list):
    story.append(Paragraph(title, styles["SectionHead"]))
    data = [[Paragraph(h, styles["TableHead"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), styles["TableCell"]) for c in r])
    tbl = Table(data, colWidths=[_CONTENT_W / len(headers)] * len(headers),
                repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _C_DARK),
        ("GRID", (0, 0), (-1, -1), 0.4, _C_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_C_WHITE, _C_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 10))


def export_pdf(path: str, kpis: dict, bookings: list,
               title: str = "Business Report", period: str = "All Time",
               biz_name: str = "Jayraldine's Catering",
               sections: list = None, chart_images: list = None) -> bool:
    """sections: [(title, headers, rows)] — analytics tables.
    chart_images: [(title, png_path)] — chart screenshots from the live page."""
    if not REPORTLAB_OK:
        return False
    try:
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=_MARGIN, rightMargin=_MARGIN,
            topMargin=_MARGIN, bottomMargin=_MARGIN,
            title=f"{biz_name} — {title}",
            author=biz_name,
        )
        styles = _styles()
        story = []
        _header_block(story, styles, biz_name, title, period)
        story.append(Paragraph("Key Performance Indicators", styles["SectionHead"]))
        _kpi_row(story, styles, kpis)

        # Charts, as images grabbed from the live Reports page
        for chart_title, png in (chart_images or []):
            try:
                from reportlab.lib.utils import ImageReader
                iw, ih = ImageReader(png).getSize()
                w = _CONTENT_W
                h = ih * (w / iw)
                if h > 9 * cm:
                    h = 9 * cm
                    w = iw * (h / ih)
                story.append(KeepTogether([
                    Paragraph(chart_title, styles["SectionHead"]),
                    Image(png, width=w, height=h),
                    Spacer(1, 8),
                ]))
            except Exception as exc:
                print(f"[exporter] chart image skipped ({chart_title}): {exc}")

        _bookings_table(story, styles, bookings)

        for sec_title, headers, rows in (sections or []):
            _section_table(story, styles, sec_title, headers, rows)

        _footer(story, styles, biz_name)
        doc.build(story)
        return True
    except Exception as exc:
        print(f"[exporter] PDF failed: {exc}")
        return False


def export_receipt_pdf(path: str, inv: dict, business: dict) -> bool:
    """Generate a professional PDF receipt for a single invoice."""
    if not REPORTLAB_OK:
        return False
    try:
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=_MARGIN, rightMargin=_MARGIN,
            topMargin=_MARGIN, bottomMargin=_MARGIN,
            title=f"Receipt — {inv.get('invoice', '')}",
        )
        styles = _styles()
        story = []

        biz_name    = business.get("name", "Jayraldine's Catering")
        biz_address = business.get("address", "")
        biz_contact = business.get("contact", "")
        biz_email   = business.get("email", "")

        total   = float(inv.get("amount", 0))
        paid    = float(inv.get("paid", 0))
        balance = total - paid
        status  = inv.get("status", "Unpaid")

        status_color = {"Paid": _C_GREEN, "Partial": _C_AMBER, "Unpaid": _C_RED}.get(status, _C_MUTED)

        header_w = _CONTENT_W

        logo_cell = ""
        _lp = _logo_path()
        if os.path.exists(_lp):
            try:
                logo_cell = Image(_lp, width=2.0*cm, height=2.0*cm)
            except Exception:
                logo_cell = ""

        biz_cell = [
            Paragraph(biz_name, styles["Brand"]),
            Paragraph("Professional Catering Services", styles["BrandSub"]),
            Spacer(1, 2),
            Paragraph(biz_address, styles["BrandSub"]),
            Paragraph(f"Tel: {biz_contact}  ·  {biz_email}", styles["BrandSub"]),
        ]

        receipt_cell = [
            Paragraph("OFFICIAL RECEIPT", ParagraphStyle(
                "rcpt_lbl", fontName="Helvetica-Bold", fontSize=8.5,
                textColor=_C_MUTED, alignment=TA_RIGHT, leading=11,
                spaceAfter=4)),
            Paragraph(inv.get("invoice", "—"), ParagraphStyle(
                "rcpt_no", fontName="Helvetica-Bold", fontSize=18,
                textColor=_C_RED, alignment=TA_RIGHT, leading=22)),
        ]

        hdr_cols = [2.2*cm, 10*cm, 6*cm] if logo_cell else [12.2*cm, 6*cm]
        hdr_data = [[logo_cell, biz_cell, receipt_cell]] if logo_cell else [[biz_cell, receipt_cell]]

        hdr_tbl = Table(hdr_data, colWidths=hdr_cols)
        hdr_tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("ALIGN",         (-1, 0), (-1, 0), "RIGHT"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(hdr_tbl)
        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(width="100%", thickness=2.5, color=_C_RED, spaceAfter=0.4*cm))

        def _det_row(label, value, alt=False, value_style=None):
            bg = colors.HexColor("#F8FAFC") if alt else _C_WHITE
            vs = value_style or styles["DetailValue"]
            return [
                Paragraph(label, styles["DetailLabel"]),
                Paragraph(str(value), vs),
            ], bg

        detail_rows_data = [
            ("Receipt #",    inv.get("invoice", "—"),                   False, None),
            ("Customer",     inv.get("customer", "—"),                   True,  None),
            ("Event Date",   inv.get("event_date", "—"),                 False, None),
        ]

        detail_rows = []
        tbl_style_cmds = [
            ("BOX",          (0, 0), (-1, -1), 0.4, _C_BORDER),
            ("INNERGRID",    (0, 0), (-1, -1), 0.3, _C_BORDER),
            ("TOPPADDING",   (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ]

        for i, (lbl, val, alt, vstyle) in enumerate(detail_rows_data):
            row_data, bg = _det_row(lbl, val, alt, vstyle)
            detail_rows.append(row_data)
            if alt:
                tbl_style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8FAFC")))

        det_tbl = Table(detail_rows, colWidths=[4.5*cm, _CONTENT_W - 4.5*cm])
        det_tbl.setStyle(TableStyle(tbl_style_cmds))
        story.append(det_tbl)
        story.append(Spacer(1, 0.3*cm))

        amount_rows = [
            [Paragraph("Total Amount", styles["DetailLabel"]),
             Paragraph(f"PHP {total:,.2f}", ParagraphStyle(
                 "amt", fontName="Helvetica", fontSize=10,
                 textColor=_C_DARK, alignment=TA_RIGHT, leading=13))],
            [Paragraph("Amount Paid", styles["DetailLabel"]),
             Paragraph(f"PHP {paid:,.2f}", ParagraphStyle(
                 "paid", fontName="Helvetica", fontSize=10,
                 textColor=_C_GREEN, alignment=TA_RIGHT, leading=13))],
            [Paragraph("Balance Due", ParagraphStyle(
                 "bal_lbl", fontName="Helvetica-Bold", fontSize=10,
                 textColor=_C_DARK, leading=13)),
             Paragraph(f"PHP {balance:,.2f}", ParagraphStyle(
                 "bal_val", fontName="Helvetica-Bold", fontSize=12,
                 textColor=_C_RED if balance > 0 else _C_GREEN,
                 alignment=TA_RIGHT, leading=15))],
        ]

        amt_style = [
            ("BOX",          (0, 0), (-1, -1), 0.4, _C_BORDER),
            ("INNERGRID",    (0, 0), (-1, -1), 0.3, _C_BORDER),
            ("BACKGROUND",   (0, 0), (-1, 0),  _C_LIGHT),
            ("BACKGROUND",   (0, 1), (-1, 1),  _C_WHITE),
            ("BACKGROUND",   (0, 2), (-1, 2),  colors.HexColor("#FFF1F2") if balance > 0 else colors.HexColor("#F0FDF4")),
            ("TOPPADDING",   (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 9),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ]

        amt_tbl = Table(amount_rows, colWidths=[_CONTENT_W * 0.55, _CONTENT_W * 0.45])
        amt_tbl.setStyle(TableStyle(amt_style))
        story.append(amt_tbl)
        story.append(Spacer(1, 0.3*cm))

        status_row = Table(
            [[Paragraph("Payment Status:", ParagraphStyle(
                "st_lbl", fontName="Helvetica-Bold", fontSize=9,
                textColor=_C_GRAY, leading=12)),
              Paragraph(status.upper(), ParagraphStyle(
                "st_val", fontName="Helvetica-Bold", fontSize=11,
                textColor=status_color, alignment=TA_RIGHT, leading=14))]],
            colWidths=[_CONTENT_W * 0.5, _CONTENT_W * 0.5],
        )
        status_row.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("BOX",           (0, 0), (-1, -1), 0.4, _C_BORDER),
            ("BACKGROUND",    (0, 0), (-1, 0),  _C_LIGHT),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(status_row)

        story.append(Spacer(1, 0.6*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=_C_BORDER))
        story.append(Spacer(1, 0.3*cm))

        from datetime import datetime as _dt
        printed_str = _dt.now().strftime("%B %d, %Y at %I:%M %p")
        story.append(Paragraph(
            f"Printed: {printed_str}  ·  Thank you for choosing <b>{biz_name}</b>!",
            styles["Footer"],
        ))
        if balance > 0:
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f"Please settle the remaining balance of PHP {balance:,.2f} before your event date.",
                ParagraphStyle("bal_note", fontName="Helvetica", fontSize=7.5,
                    textColor=_C_RED, alignment=TA_CENTER, leading=10)
            ))

        doc.build(story)
        return True
    except Exception as exc:
        print(f"[exporter] Receipt PDF failed: {exc}")
        return False


def export_excel(path: str, kpis: dict, bookings: list,
                 title: str = "Business Report", period: str = "All Time",
                 biz_name: str = "Jayraldine's Catering",
                 sections: list = None) -> bool:
    if not OPENPYXL_OK:
        return False
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Report"

        RED   = "E11D48"
        DARK  = "0B1220"
        GRAY  = "374151"
        LIGHT = "F9FAFB"
        WHITE = "FFFFFF"

        def _fill(hex_color):
            return PatternFill("solid", fgColor=hex_color)

        def _border():
            s = Side(style="thin", color="E5E7EB")
            return Border(left=s, right=s, top=s, bottom=s)

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 10
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 14

        row = 1
        ws.merge_cells(f"A{row}:F{row}")
        c = ws[f"A{row}"]
        c.value = biz_name.upper()
        c.font = Font(name="Calibri", bold=True, size=18, color=RED)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 30
        row += 1

        ws.merge_cells(f"A{row}:F{row}")
        c = ws[f"A{row}"]
        c.value = f"{title}  |  Period: {period}  |  Generated: {datetime.now().strftime('%b %d, %Y %I:%M %p')}"
        c.font = Font(name="Calibri", size=9, color=GRAY)
        c.alignment = Alignment(horizontal="center")
        ws.row_dimensions[row].height = 16
        row += 2

        ws.merge_cells(f"A{row}:F{row}")
        c = ws[f"A{row}"]
        c.value = "KEY PERFORMANCE INDICATORS"
        c.font = Font(name="Calibri", bold=True, size=10, color=WHITE)
        c.fill = _fill(DARK)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 20
        row += 1

        kpi_pairs = [
            ("Total Bookings",  kpis.get("total_bookings", 0)),
            ("Total Pax",       kpis.get("total_pax", 0)),
            ("Total Revenue",   f"PHP {float(kpis.get('total_revenue', 0)):,.0f}"),
            ("Unpaid Amount",   f"PHP {float(kpis.get('unpaid_amount', 0)):,.0f}"),
            ("Today's Bookings", kpis.get("today_bookings", 0)),
            ("This Week's Bookings", kpis.get("week_bookings", 0)),
        ]
        for label, value in kpi_pairs:
            lc = ws.cell(row=row, column=1, value=label)
            lc.font = Font(name="Calibri", bold=True, size=10, color=DARK)
            lc.fill = _fill(LIGHT)
            lc.border = _border()
            lc.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            vc = ws.cell(row=row, column=2, value=value)
            vc.font = Font(name="Calibri", size=10, color=DARK)
            vc.fill = _fill(WHITE)
            vc.border = _border()
            vc.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            ws.row_dimensions[row].height = 18
            row += 1

        row += 1
        ws.merge_cells(f"A{row}:F{row}")
        c = ws[f"A{row}"]
        c.value = "BOOKING STATISTICS"
        c.font = Font(name="Calibri", bold=True, size=10, color=WHITE)
        c.fill = _fill(RED)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 20
        row += 1

        headers = ["Booking Ref", "Client", "Event Date", "Pax", "Total Amount", "Status"]
        for col, hdr in enumerate(headers, 1):
            c = ws.cell(row=row, column=col, value=hdr)
            c.font = Font(name="Calibri", bold=True, size=9, color=WHITE)
            c.fill = _fill(GRAY)
            c.border = _border()
            c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 18
        row += 1

        for i, b in enumerate(bookings):
            bg = LIGHT if i % 2 == 0 else WHITE
            vals = [
                b.get("id", ""), b.get("name", ""), b.get("date", ""),
                b.get("pax", ""), b.get("total", ""), b.get("status", "").capitalize()
            ]
            aligns = ["left","left","center","center","right","center"]
            for col, (val, aln) in enumerate(zip(vals, aligns), 1):
                c = ws.cell(row=row, column=col, value=val)
                c.font = Font(name="Calibri", size=9)
                c.fill = _fill(bg)
                c.border = _border()
                c.alignment = Alignment(horizontal=aln, vertical="center", indent=1 if aln=="left" else 0)
            ws.row_dimensions[row].height = 16
            row += 1

        row += 1
        ws.merge_cells(f"A{row}:F{row}")
        c = ws[f"A{row}"]
        c.value = f"{biz_name}  •  System-generated report  •  Confidential"
        c.font = Font(name="Calibri", size=8, italic=True, color=GRAY)
        c.alignment = Alignment(horizontal="center")

        # Analytics sections — one worksheet per section
        for sec_title, sec_headers, sec_rows in (sections or []):
            sheet_name = sec_title[:28].replace("/", "-")
            ws2 = wb.create_sheet(sheet_name)
            for col in range(1, len(sec_headers) + 1):
                ws2.column_dimensions[get_column_letter(col)].width = 24
            r2 = 1
            ws2.merge_cells(start_row=r2, start_column=1,
                            end_row=r2, end_column=len(sec_headers))
            tc = ws2.cell(row=r2, column=1, value=sec_title.upper())
            tc.font = Font(name="Calibri", bold=True, size=11, color=WHITE)
            tc.fill = _fill(DARK)
            tc.alignment = Alignment(horizontal="center", vertical="center")
            ws2.row_dimensions[r2].height = 20
            r2 += 1
            for col, hdr in enumerate(sec_headers, 1):
                hc = ws2.cell(row=r2, column=col, value=hdr)
                hc.font = Font(name="Calibri", bold=True, size=9, color=WHITE)
                hc.fill = _fill(GRAY)
                hc.border = _border()
                hc.alignment = Alignment(horizontal="center", vertical="center")
            r2 += 1
            for i, sec_row in enumerate(sec_rows):
                bg = LIGHT if i % 2 == 0 else WHITE
                for col, val in enumerate(sec_row, 1):
                    cc = ws2.cell(row=r2, column=col, value=val)
                    cc.font = Font(name="Calibri", size=9)
                    cc.fill = _fill(bg)
                    cc.border = _border()
                    cc.alignment = Alignment(
                        horizontal="left" if col == 1 else "right",
                        vertical="center", indent=1)
                r2 += 1

        wb.save(path)
        return True
    except Exception as exc:
        print(f"[exporter] Excel failed: {exc}")
        return False


def _parse_amount(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("₱", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def export_custom_entity_data(entity_name: str, is_excel: bool, save_path: str) -> bool:
    """Export Bookings, Customers, Expenses, Menu, Billings, or Master Data to Excel or CSV."""
    import utils.repository as repo
    import csv

    headers = []
    rows = []
    sheets = {}

    if "Bookings" in entity_name:
        headers = ["Booking Ref", "Customer Name", "Contact Number", "Event Date", "Event Time", "Venue / Location", "Occasion", "Guest Count (Pax)", "Total Amount (₱)", "Status"]
        b_list = repo.get_all_bookings() or []
        for b in b_list:
            rows.append([
                b.get("id", ""), b.get("name", ""), b.get("contact", ""),
                b.get("date", ""), b.get("time", ""), b.get("venue", ""),
                b.get("occasion", ""), b.get("pax", ""), f"₱{_parse_amount(b.get('total', 0)):,.2f}",
                b.get("status", "")
            ])
        sheets["Bookings"] = (headers, rows)

    elif "Customers" in entity_name:
        headers = ["Customer ID", "Customer Name", "Contact Number", "Email Address", "System Address ID", "Imported Address Text", "Notes / History"]
        c_list = repo.get_all_customers() or []
        for c in c_list:
            rows.append([
                c.get("id", ""), c.get("name", ""), c.get("contact", ""),
                c.get("email", ""), c.get("address_id", ""), c.get("address", ""),
                c.get("notes", "")
            ])
        sheets["Customers"] = (headers, rows)

    elif "Expenses" in entity_name:
        headers = ["Expense ID", "Expense Date", "Category", "Description", "Amount (₱)"]
        e_list = repo.get_all_expenses() or []
        for e in e_list:
            rows.append([
                e.get("id", ""), e.get("date", ""), e.get("category", ""),
                e.get("description", ""), f"₱{_parse_amount(e.get('amount', 0)):,.2f}"
            ])
        sheets["Expenses"] = (headers, rows)

    elif "Menu" in entity_name:
        headers = ["Item ID", "Item / Package Name", "Category", "Price / Rate (₱)", "Description / Inclusions"]
        m_list = repo.get_all_menu_items() or []
        for m in m_list:
            rows.append([
                m.get("id", ""), m.get("name", ""), m.get("category", ""),
                f"₱{_parse_amount(m.get('price', 0)):,.2f}", m.get("description", "")
            ])
        sheets["Menu Items"] = (headers, rows)

    elif "Billing" in entity_name:
        headers = ["Invoice Ref", "Booking Ref", "Customer Name", "Event Date", "Total Amount (₱)", "Paid Amount (₱)", "Balance Due (₱)", "Payment Status"]
        i_list = repo.get_all_invoices() or []
        for inv in i_list:
            rows.append([
                inv.get("invoice", ""), inv.get("booking_ref", ""), inv.get("customer", ""),
                inv.get("event_date", ""), f"₱{_parse_amount(inv.get('amount', 0)):,.2f}",
                f"₱{_parse_amount(inv.get('paid', 0)):,.2f}", f"₱{_parse_amount(inv.get('balance', 0)):,.2f}",
                inv.get("status", "")
            ])
        sheets["Invoices"] = (headers, rows)

    elif "Cash" in entity_name or "Flow" in entity_name:
        headers = ["Date", "Check #", "Particulars (Account / Detail)", "Deposit (₱)", "Withdrawal (₱)", "Running Balance (₱)", "Actual Sales (₱)", "Variance / Difference (₱)", "Remarks / Notes"]
        tx_list = repo.get_cash_flow_transactions() or []
        for tx in tx_list:
            dep = float(tx.get("deposit") or 0.0)
            withd = float(tx.get("withdrawal") or 0.0)
            bal = float(tx.get("balance") or 0.0)
            act_sales = float(tx.get("actual_sales") or 0.0)
            diff = bal - act_sales
            diff_str = f"₱{diff:,.2f}" if diff >= 0 else f"(₱{abs(diff):,.2f})"
            rows.append([
                str(tx.get("date", "")),
                str(tx.get("check_no", "")),
                str(tx.get("particulars", "")),
                f"₱{dep:,.2f}" if dep > 0 else "—",
                f"₱{withd:,.2f}" if withd > 0 else "—",
                f"₱{bal:,.2f}" if bal >= 0 else f"(₱{abs(bal):,.2f})",
                f"₱{act_sales:,.2f}" if act_sales > 0 else "—",
                diff_str if act_sales > 0 else "—",
                str(tx.get("notes", ""))
            ])
        sheets["Cash Flow Ledger"] = (headers, rows)

    else: # Master Export
        b_hdrs = ["Booking Ref", "Customer Name", "Contact Number", "Event Date", "Event Time", "Venue", "Occasion", "Pax", "Total Amount (₱)", "Status"]
        b_rows = [[b.get("id", ""), b.get("name", ""), b.get("contact", ""), b.get("date", ""), b.get("time", ""), b.get("venue", ""), b.get("occasion", ""), b.get("pax", ""), f"₱{_parse_amount(b.get('total', 0)):,.2f}", b.get("status", "")] for b in (repo.get_all_bookings() or [])]
        sheets["Bookings"] = (b_hdrs, b_rows)

        c_hdrs = ["Customer ID", "Customer Name", "Contact Number", "Email Address", "System Address ID", "Imported Address Text", "Notes / History"]
        c_rows = [[c.get("id", ""), c.get("name", ""), c.get("contact", ""), c.get("email", ""), c.get("address_id", ""), c.get("address", ""), c.get("notes", "")] for c in (repo.get_all_customers() or [])]
        sheets["Customers"] = (c_hdrs, c_rows)

        e_hdrs = ["Expense ID", "Expense Date", "Category", "Description", "Amount (₱)"]
        e_rows = [[e.get("id", ""), e.get("date", ""), e.get("category", ""), e.get("description", ""), f"₱{_parse_amount(e.get('amount', 0)):,.2f}"] for e in (repo.get_all_expenses() or [])]
        sheets["Expenses"] = (e_hdrs, e_rows)

        m_hdrs = ["Item ID", "Item / Package Name", "Category", "Price / Rate (₱)", "Description / Inclusions"]
        m_rows = [[m.get("id", ""), m.get("name", ""), m.get("category", ""), f"₱{_parse_amount(m.get('price', 0)):,.2f}", m.get("description", "")] for m in (repo.get_all_menu_items() or [])]
        sheets["Menu Items"] = (m_hdrs, m_rows)

        cf_hdrs = ["Date", "Check #", "Particulars (Account / Detail)", "Deposit (₱)", "Withdrawal (₱)", "Running Balance (₱)", "Actual Sales (₱)", "Variance / Difference (₱)", "Remarks / Notes"]
        cf_rows = [[
            str(tx.get("date", "")),
            str(tx.get("check_no", "")),
            str(tx.get("particulars", "")),
            f"₱{float(tx.get('deposit') or 0.0):,.2f}" if float(tx.get('deposit') or 0.0) > 0 else "—",
            f"₱{float(tx.get('withdrawal') or 0.0):,.2f}" if float(tx.get('withdrawal') or 0.0) > 0 else "—",
            f"₱{float(tx.get('balance') or 0.0):,.2f}" if float(tx.get('balance') or 0.0) >= 0 else f"(₱{abs(float(tx.get('balance') or 0.0)):,.2f})",
            f"₱{float(tx.get('actual_sales') or 0.0):,.2f}" if float(tx.get('actual_sales') or 0.0) > 0 else "—",
            f"₱{(float(tx.get('balance') or 0.0) - float(tx.get('actual_sales') or 0.0)):,.2f}" if float(tx.get('actual_sales') or 0.0) > 0 and (float(tx.get('balance') or 0.0) - float(tx.get('actual_sales') or 0.0)) >= 0 else (f"(₱{abs(float(tx.get('balance') or 0.0) - float(tx.get('actual_sales') or 0.0)):,.2f})" if float(tx.get('actual_sales') or 0.0) > 0 else "—"),
            str(tx.get("notes", ""))
        ] for tx in (repo.get_cash_flow_transactions() or [])]
        sheets["Cash Flow Ledger"] = (cf_hdrs, cf_rows)

        i_hdrs = ["Invoice Ref", "Booking Ref", "Customer Name", "Event Date", "Total Amount (₱)", "Paid Amount (₱)", "Balance Due (₱)", "Payment Status"]
        i_rows = [[inv.get("invoice", ""), inv.get("booking_ref", ""), inv.get("customer", ""), inv.get("event_date", ""), f"₱{_parse_amount(inv.get('amount', 0)):,.2f}", f"₱{_parse_amount(inv.get('paid', 0)):,.2f}", f"₱{_parse_amount(inv.get('balance', 0)):,.2f}", inv.get("status", "")] for inv in (repo.get_all_invoices() or [])]
        sheets["Invoices & Payments"] = (i_hdrs, i_rows)

    if not is_excel:
        try:
            with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                first_sheet = next(iter(sheets.values()))
                writer.writerow(first_sheet[0])
                writer.writerows(first_sheet[1])
            return True
        except Exception as exc:
            print(f"[exporter] CSV export failed: {exc}")
            return False

    if not OPENPYXL_OK:
        return False

    try:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        RED   = "E11D48"
        DARK  = "0B1220"
        LIGHT = "F8FAFC"
        WHITE = "FFFFFF"

        for sheet_title, (hdrs, data_rows) in sheets.items():
            ws = wb.create_sheet(title=sheet_title)

            ws.row_dimensions[1].height = 24
            for col_idx, h_text in enumerate(hdrs, 1):
                cell = ws.cell(row=1, column=col_idx, value=h_text)
                cell.font = Font(name="Calibri", bold=True, size=10, color=WHITE)
                cell.fill = PatternFill("solid", fgColor=RED if "Booking" in sheet_title or "Invoice" in sheet_title else DARK)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                s = Side(style="thin", color="E5E7EB")
                cell.border = Border(left=s, right=s, top=s, bottom=s)

            for row_idx, r_data in enumerate(data_rows, 2):
                ws.row_dimensions[row_idx].height = 18
                bg = LIGHT if row_idx % 2 == 0 else WHITE
                for col_idx, val in enumerate(r_data, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=val)
                    cell.font = Font(name="Calibri", size=9)
                    cell.fill = PatternFill("solid", fgColor=bg)
                    s = Side(style="thin", color="E5E7EB")
                    cell.border = Border(left=s, right=s, top=s, bottom=s)
                    align_right = ("₱" in str(val) or "Amount" in hdrs[col_idx-1] or "Paid" in hdrs[col_idx-1])
                    cell.alignment = Alignment(horizontal="right" if align_right else "left", vertical="center")

            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        wb.save(save_path)
        return True
    except Exception as exc:
        print(f"[exporter] Excel export failed: {exc}")
        return False


def export_calendar_pdf(save_path: str, year: int, month: int, month_events: dict,
                        biz_name: str = "Jayraldine's Catering") -> bool:
    """Generate a high-quality A4 PDF of the catering schedule and calendar agenda for a given month."""
    if not REPORTLAB_OK:
        return False
    try:
        import calendar as _cal
        doc = SimpleDocTemplate(
            save_path, pagesize=A4,
            leftMargin=_MARGIN, rightMargin=_MARGIN,
            topMargin=_MARGIN, bottomMargin=_MARGIN,
            title=f"{biz_name} — Catering Schedule {year}-{month:02d}",
            author=biz_name,
        )
        styles = _styles()
        story = []

        month_name = _cal.month_name[month]
        title = f"Catering Schedule — {month_name} {year}"
        _header_block(story, styles, biz_name, title, period=f"{month_name} {year}")

        # Compute calendar month stats
        all_events = []
        total_pax = 0
        busiest_day_pax = 0
        busiest_day = "None"
        for day, ev_list in (month_events or {}).items():
            day_pax = 0
            for ev in (ev_list or []):
                p = int(ev.get("pax", 0) or 0)
                total_pax += p
                day_pax += p
                all_events.append((day, ev))
            if day_pax > busiest_day_pax:
                busiest_day_pax = day_pax
                busiest_day = f"{month_name[:3]} {day} ({day_pax} pax)"

        # KPI Summary Row
        cal_kpis = [
            ("Total Events", str(len(all_events))),
            ("Total Guests (Pax)", f"{total_pax:,}"),
            ("Peak Day Pax", f"{busiest_day_pax} pax" if busiest_day_pax else "—"),
            ("Active Days", f"{len(month_events or {})} days"),
        ]
        ncols = len(cal_kpis)
        col_w = [_CONTENT_W / ncols] * ncols
        labels_row = [Paragraph(lbl, styles["KpiLabel"]) for lbl, _ in cal_kpis]
        values_row = [Paragraph(val, styles["KpiValue"]) for _, val in cal_kpis]
        t = Table([labels_row, values_row], colWidths=col_w)
        t.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.5, _C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, _C_BORDER),
            ("BACKGROUND",    (0, 0), (-1, 0),  _C_LIGHT),
            ("BACKGROUND",    (0, 1), (-1, 1),  _C_WHITE),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("ROUNDEDCORNERS", [4]),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

        # Calendar Grid
        story.append(Paragraph("Monthly Calendar Grid", styles["SectionHead"]))
        days_head = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        grid_data = [[Paragraph(d, styles["CalDayHead"]) for d in days_head]]

        cal_matrix = _cal.monthcalendar(year, month)
        cell_w = _CONTENT_W / 7.0
        for week in cal_matrix:
            week_row = []
            for day in week:
                if day == 0:
                    week_row.append("")
                else:
                    day_evs = (month_events or {}).get(day, [])
                    cell_content = [Paragraph(f"<b>{day}</b>", styles["CalDateNum"])]
                    if day_evs:
                        d_pax = sum(int(e.get("pax", 0) or 0) for e in day_evs)
                        badge_color = "#E11D48" if d_pax >= 600 else ("#F59E0B" if d_pax >= 400 else "#22C55E")
                        cell_content.append(Paragraph(
                            f"<font color='{badge_color}'><b>{len(day_evs)} bkg ({d_pax}p)</b></font>",
                            styles["CalEventChip"]
                        ))
                    week_row.append(cell_content)
            grid_data.append(week_row)

        grid_table = Table(grid_data, colWidths=[cell_w] * 7)
        grid_style = [
            ("BACKGROUND",    (0, 0), (-1, 0),  _C_RED),
            ("GRID",          (0, 0), (-1, -1), 0.4, _C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]
        for r_idx in range(1, len(grid_data)):
            bg = _C_LIGHT if r_idx % 2 == 0 else _C_WHITE
            grid_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), bg))

        grid_table.setStyle(TableStyle(grid_style))
        story.append(grid_table)
        story.append(Spacer(1, 14))

        # Itemized Schedule Table
        story.append(Paragraph("Itemized Event Agenda", styles["SectionHead"]))
        agenda_hdrs = ["Date & Time", "Ref #", "Event / Customer", "Venue", "Pax", "Status"]
        agenda_w = [3.2*cm, 2.4*cm, 5.0*cm, 3.8*cm, 1.6*cm, 2.0*cm]
        agenda_rows = [[Paragraph(h, styles["TableHead"]) for h in agenda_hdrs]]

        all_events_sorted = sorted(all_events, key=lambda x: x[0])
        status_styles = {
            "CONFIRMED": styles["StatusPaid"],
            "COMPLETED": styles["StatusPaid"],
            "PENDING":   styles["StatusPartial"],
            "CANCELLED": styles["StatusUnpaid"],
        }

        if not all_events_sorted:
            agenda_rows.append([Paragraph("No events scheduled for this month.", styles["TableCellCenter"]), "", "", "", "", ""])
        else:
            for day, ev in all_events_sorted:
                time_str = ev.get("time") or "6:00 PM"
                st_key = str(ev.get("status") or "CONFIRMED").upper()
                st_style = status_styles.get(st_key, styles["TableCellCenter"])
                agenda_rows.append([
                    Paragraph(f"{month_name[:3]} {day}, {year}<br/><font color='#6B7280' size=7>{time_str}</font>", styles["TableCell"]),
                    Paragraph(str(ev.get("ref") or "—"), styles["TableCell"]),
                    Paragraph(f"<b>{ev.get('event_name', '')}</b>", styles["TableCell"]),
                    Paragraph(str(ev.get("location") or "—"), styles["TableCell"]),
                    Paragraph(f"{ev.get('pax', 0)}", styles["TableCellCenter"]),
                    Paragraph(st_key.capitalize(), st_style),
                ])

        agenda_table = Table(agenda_rows, colWidths=agenda_w, repeatRows=1)
        agenda_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  _C_DARK),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_C_WHITE, _C_LIGHT]),
            ("BOX",           (0, 0), (-1, -1), 0.4, _C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, _C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(agenda_table)

        _footer(story, styles, biz_name)
        doc.build(story)
        return True
    except Exception as exc:
        print(f"[exporter] export_calendar_pdf failed: {exc}")
        return False


def export_cash_flow_pdf(save_path: str, transactions: Optional[list] = None,
                         summary: Optional[dict] = None,
                         biz_name: str = "Jayraldine's Catering") -> bool:
    """Generate a clean, high-quality A4 PDF of the Cash Flow Ledger with KPI summary and itemized entries."""
    if not REPORTLAB_OK:
        return False
    try:
        import utils.repository as repo
        tx_list = transactions if transactions is not None else (repo.get_cash_flow_transactions() or [])
        smry = summary if summary is not None else repo.get_cash_flow_summary()

        doc = SimpleDocTemplate(
            save_path, pagesize=A4,
            leftMargin=_MARGIN, rightMargin=_MARGIN,
            topMargin=_MARGIN, bottomMargin=_MARGIN,
            title=f"{biz_name} — Cash Flow Statement",
            author=biz_name,
        )
        styles = _styles()
        story = []

        now_str = datetime.now().strftime("%B %d, %Y")
        _header_block(story, styles, biz_name, "Cash Flow Statement & Ledger", period=now_str)

        # Top KPI Summary Card
        tot_dep = float(smry.get("total_deposits", 0.0))
        tot_with = float(smry.get("total_withdrawals", 0.0))
        cur_bal = float(smry.get("current_balance", 0.0))
        tot_sales = float(smry.get("total_actual_sales", 0.0))
        tot_diff = cur_bal - tot_sales

        cf_kpis = [
            ("Total Deposits (In)", f"₱{tot_dep:,.2f}"),
            ("Total Withdrawals (Out)", f"₱{tot_with:,.2f}"),
            ("Running Balance", f"₱{cur_bal:,.2f}"),
            ("Total Actual Sales", f"₱{tot_sales:,.2f}"),
        ]
        ncols = len(cf_kpis)
        col_w = [_CONTENT_W / ncols] * ncols
        labels_row = [Paragraph(lbl, styles["KpiLabel"]) for lbl, _ in cf_kpis]
        values_row = [Paragraph(val, styles["KpiValue"]) for _, val in cf_kpis]
        t = Table([labels_row, values_row], colWidths=col_w)
        t.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.5, _C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, _C_BORDER),
            ("BACKGROUND",    (0, 0), (-1, 0),  _C_LIGHT),
            ("BACKGROUND",    (0, 1), (-1, 1),  _C_WHITE),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))

        # Ledger Table
        story.append(Paragraph("Transaction Journal & Running Balances", styles["SectionHead"]))
        table_hdrs = ["Date", "Check #", "Particulars (Account / Detail)", "Deposit", "Withdrawal", "Balance", "Actual Sales", "Variance"]
        table_w = [2.0*cm, 1.8*cm, 4.4*cm, 2.1*cm, 2.1*cm, 2.2*cm, 2.1*cm, 2.1*cm]
        table_rows = [[Paragraph(h, styles["TableHead"]) for h in table_hdrs]]

        if not tx_list:
            table_rows.append([Paragraph("No cash flow transactions recorded.", styles["TableCellCenter"]), "", "", "", "", "", "", ""])
        else:
            for tx in tx_list:
                d_str = str(tx.get("date") or "")
                chk_str = str(tx.get("check_no") or "—")
                part_str = str(tx.get("particulars") or "")
                dep_val = float(tx.get("deposit") or 0.0)
                with_val = float(tx.get("withdrawal") or 0.0)
                bal_val = float(tx.get("balance") or 0.0)
                sales_val = float(tx.get("actual_sales") or 0.0)
                diff_val = bal_val - sales_val

                dep_txt = f"<font color='#16A34A'>₱{dep_val:,.2f}</font>" if dep_val > 0 else "—"
                with_txt = f"<font color='#DC2626'>₱{with_val:,.2f}</font>" if with_val > 0 else "—"
                bal_txt = f"<b>₱{bal_val:,.2f}</b>" if bal_val >= 0 else f"<font color='#DC2626'><b>(₱{abs(bal_val):,.2f})</b></font>"
                sales_txt = f"₱{sales_val:,.2f}" if sales_val > 0 else "—"
                diff_txt = f"₱{diff_val:,.2f}" if diff_val >= 0 else f"<font color='#DC2626'>(₱{abs(diff_val):,.2f})</font>"
                if sales_val <= 0:
                    diff_txt = "—"

                table_rows.append([
                    Paragraph(d_str, styles["TableCellCenter"]),
                    Paragraph(chk_str, styles["TableCellCenter"]),
                    Paragraph(part_str, styles["TableCell"]),
                    Paragraph(dep_txt, styles["TableCellRight"]),
                    Paragraph(with_txt, styles["TableCellRight"]),
                    Paragraph(bal_txt, styles["TableCellRight"]),
                    Paragraph(sales_txt, styles["TableCellRight"]),
                    Paragraph(diff_txt, styles["TableCellRight"]),
                ])

        tbl = Table(table_rows, colWidths=table_w, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  _C_DARK),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_C_WHITE, _C_LIGHT]),
            ("BOX",           (0, 0), (-1, -1), 0.4, _C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, _C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tbl)

        _footer(story, styles, biz_name)
        doc.build(story)
        return True
    except Exception as exc:
        print(f"[exporter] export_cash_flow_pdf failed: {exc}")
        return False
