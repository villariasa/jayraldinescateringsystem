"""Document / data export layer for the Jayraldine's Catering desktop app.

This module is the single place that turns in-app data (bookings, invoices,
customers, expenses, cash flow, menu/packages, calendar events) into shareable
artifacts on disk. It produces three kinds of output:

  * PDF documents via ReportLab — business reports, official receipts /
    booking agreements, kitchen order slips, daily activity/audit logs,
    printable wall-calendars + agendas, and the cash-flow ledger.
  * Excel workbooks and CSV files via openpyxl — analytics reports and
    entity data dumps (one worksheet per data set).
  * A standalone SQLite "master data" file — the PC -> Tablet transfer that
    seeds the tablet app with catalog/customer/address reference data only.

Design notes / responsibilities:
  * ReportLab and openpyxl are optional dependencies. Their imports are
    guarded (REPORTLAB_OK / OPENPYXL_OK); every public export function
    returns False (a soft failure) instead of raising when the backing
    library is missing or the build errors out, so the UI never crashes on
    an export.
  * A shared brand style/colour palette (_C_* colours and _styles()) keeps
    all PDFs visually consistent.
  * Data is pulled lazily from utils.repository / utils.db inside functions
    (not at import time) to avoid import cycles and to keep this module
    importable even when the DB layer is unavailable.
  * Currency is Philippine Peso; amounts are formatted with "PHP"/"₱".
"""

import os
from datetime import datetime, date as _dt_date
from typing import Optional, List, Dict, Any

# Module-level alias so helpers can reference the datetime class even where the
# name `datetime` is shadowed by a local re-import (see calendar/agenda helpers).
_dt_datetime = datetime


def _format_time_ampm(t_raw) -> str:
    """Format any time representation into 12-hour AM/PM format (e.g. '6:00 PM', '11:30 AM').

    Params:
        t_raw: a time/datetime object (anything exposing .strftime) or a
            string in one of several common stored formats.
    Returns:
        The time as a 12-hour AM/PM string with no leading zero on the hour.
        Falsy input yields "". Unparseable strings are returned unchanged so
        no data is silently lost.
    """
    if not t_raw:
        return ""
    # Native time/datetime objects can format themselves directly.
    if hasattr(t_raw, "strftime"):
        return t_raw.strftime("%I:%M %p").lstrip("0")  # lstrip drops the "0" in "06:00 PM"
    s = str(t_raw).strip()
    # Otherwise try each known stored string layout until one parses.
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            parsed = datetime.strptime(s, fmt).time()
            return parsed.strftime("%I:%M %p").lstrip("0")
        except ValueError:
            continue
    # Unknown format: hand the raw string back rather than raising.
    return s

# ReportLab is an optional dependency. Guard the import so the module still
# loads (and PDF functions degrade to returning False) when it is not present.
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image, KeepTogether, Flowable
    )
    REPORTLAB_OK = True

    class FillBottomSpacer(Flowable):
        """Invisible flowable that consumes the remaining vertical space on a page.

        Used to pin the receipt's footer banner to the bottom margin: it grows
        to fill whatever height is left above a reserved `footer_height`, so the
        flowables that follow it are pushed down to the page bottom.

        Params:
            footer_height: height (points) to reserve below this spacer for the
                content that should sit at the bottom of the page.
        """
        def __init__(self, footer_height):
            super().__init__()
            self.footer_height = footer_height

        def wrap(self, availWidth, availHeight):
            # Claim all remaining height minus the reserved footer band; keep a
            # tiny minimum so the layout never collapses to zero/negative.
            space = max(0.15 * cm, availHeight - self.footer_height)
            self.height = space
            return availWidth, space

        def draw(self):
            # Purely a spacer — nothing is rendered.
            pass
except ImportError:
    REPORTLAB_OK = False
    FillBottomSpacer = None  # sentinel so callers can test `if FillBottomSpacer`

# openpyxl is likewise optional; Excel/CSV-Excel paths check OPENPYXL_OK.
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False


# Shared brand palette used across every PDF. Defined only when ReportLab is
# available (colors.HexColor needs the library); otherwise all names are None
# so module import still succeeds.
if REPORTLAB_OK:
    _C_RED    = colors.HexColor("#E11D48")  # brand primary (headers, accents)
    _C_DARK   = colors.HexColor("#0B1220")  # near-black body/heading text
    _C_GRAY   = colors.HexColor("#374151")  # secondary label text
    _C_LIGHT  = colors.HexColor("#F9FAFB")  # zebra/row background
    _C_WHITE  = colors.white
    _C_MUTED  = colors.HexColor("#6B7280")  # muted captions/metadata
    _C_BORDER = colors.HexColor("#E5E7EB")  # table gridlines/borders
    _C_GREEN  = colors.HexColor("#22C55E")  # paid / confirmed status
    _C_AMBER  = colors.HexColor("#F59E0B")  # partial / pending status
    _C_BLUE   = colors.HexColor("#3B82F6")
else:
    _C_RED = _C_DARK = _C_GRAY = _C_LIGHT = _C_WHITE = _C_MUTED = _C_BORDER = _C_GREEN = _C_AMBER = _C_BLUE = None

from utils.paths import resource_path


def _logo_path() -> str:
    """Resolve the business logo path, preferring PNG and falling back to JPG.

    Returns the JPG candidate path even if neither exists; callers guard with
    os.path.exists() before using it.
    """
    p = resource_path("assets", "logo.png")
    if not os.path.exists(p):
        p = resource_path("assets", "logo.jpg")
    return p

# Page geometry constants for portrait A4 layouts. Fall back to raw point
# values when ReportLab (and thus A4/cm) is unavailable.
_PAGE_W = A4[0] if REPORTLAB_OK else 595
_MARGIN = 1.5 * cm if REPORTLAB_OK else 0
_CONTENT_W = _PAGE_W - 2 * _MARGIN  # usable width between left/right margins


def _styles():
    """Build and return the shared ReportLab stylesheet for all PDF exports.

    Extends the default sample stylesheet with the app's branded paragraph
    styles (brand headers, KPI tiles, table cells, status labels, calendar
    chips, etc.). Returns a fresh StyleSheet1 on each call so per-document
    mutation can never leak between exports.
    """
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
    """Map a payment status label to its coloured paragraph style.

    Params:
        status: one of "Paid" / "Partial" / "Unpaid" (case-sensitive).
        styles: the stylesheet from _styles().
    Returns:
        The matching status style, or the plain TableCell style as a fallback.
    """
    mapping = {
        "Paid":    styles["StatusPaid"],
        "Partial": styles["StatusPartial"],
        "Unpaid":  styles["StatusUnpaid"],
    }
    return mapping.get(status, styles["TableCell"])


def _header_block(story, styles, biz_name: str, title: str, period: str = "All Time"):
    """Append the standard branded report header to a Platypus story.

    Renders a three-column band (logo / business name / report metadata)
    followed by a red divider rule. The logo falls back to the first letter
    of the business name if the image is missing or fails to load.

    Params:
        story: the Platypus flowable list being built (mutated in place).
        styles: stylesheet from _styles().
        biz_name: business display name.
        title: report title shown top-right.
        period: reporting period label shown top-right.
    Side effects: appends flowables to `story`.
    """
    header_left = []
    _lp = _logo_path()
    # Prefer the logo image; degrade to a single-letter monogram on any failure.
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

    now_str = datetime.now().strftime("%b %d, %Y  %I:%M %p")  # generation timestamp
    header_right = [
        Paragraph(f"<b>{title}</b>", styles["BrandSubRight"]),
        Paragraph(f"Period: {period}", styles["BrandSubRight"]),
        Paragraph(f"Generated: {now_str}", styles["BrandSubRight"]),
    ]

    # Single-row 3-column table lays out the header band; fixed widths keep the
    # metadata block flush-right regardless of logo/name length.
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
    """Append a four-tile KPI summary strip (label row over value row).

    Params:
        story: Platypus story list (mutated in place).
        styles: stylesheet from _styles().
        kpis: dict with total_bookings / total_pax / total_revenue /
            unpaid_amount (all optional; missing keys default to 0).
    Side effects: appends a table + spacer to `story`.
    """
    # Label/value pairs; numeric values are pre-formatted with thousands
    # separators and a PHP currency prefix here.
    items = [
        ("Total Bookings",  str(kpis.get("total_bookings", 0))),
        ("Total Pax",       f"{int(kpis.get('total_pax', 0)):,}"),
        ("Total Revenue",   f"PHP {float(kpis.get('total_revenue', 0)):,.0f}"),
        ("Unpaid Amount",   f"PHP {float(kpis.get('unpaid_amount', 0)):,.0f}"),
    ]
    ncols = len(items)
    col_w = [_CONTENT_W / ncols] * ncols  # equal-width columns spanning content area

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
    """Append the "Booking Statistics" table listing each booking as a row.

    Params:
        story: Platypus story list (mutated in place).
        styles: stylesheet from _styles().
        bookings: list of booking dicts with keys id/name/date/pax/total/status.
    Side effects: appends a section heading and table to `story`.
    """
    story.append(Paragraph("Booking Statistics", styles["SectionHead"]))

    headers = ["Booking Ref", "Client", "Event Date", "Pax", "Total Amount", "Status"]
    col_w   = [2.8*cm, 5.5*cm, 2.8*cm, 1.5*cm, 3.2*cm, 2.4*cm]

    header_row = [Paragraph(h, styles["TableHead"]) for h in headers]
    rows = [header_row]

    # Booking status -> coloured style (reuses the payment-status palette).
    status_styles = {
        "CONFIRMED": styles["StatusPaid"],
        "PENDING":   styles["StatusPartial"],
        "CANCELLED": styles["StatusUnpaid"],
    }

    for b in bookings:
        st_key = b.get("status", "").upper()  # normalise for case-insensitive lookup
        st_style = status_styles.get(st_key, styles["TableCell"])
        rows.append([
            Paragraph(b.get("id", ""), styles["TableCell"]),
            Paragraph(b.get("name", ""), styles["TableCell"]),
            Paragraph(b.get("date", ""), styles["TableCellCenter"]),
            Paragraph(str(b.get("pax", "")), styles["TableCellCenter"]),
            Paragraph(b.get("total", ""), styles["TableCellRight"]),
            Paragraph(b.get("status", "").capitalize(), st_style),
        ])

    # repeatRows=1 repeats the red header row when the table spans pages.
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  _C_RED),                 # header band
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_C_WHITE, _C_LIGHT]),   # zebra striping
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
    """Append the standard confidential-report footer (rule + caption).

    Side effects: appends spacer/divider/caption flowables to `story`.
    """
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_C_BORDER))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"{biz_name}  •  This report is system-generated and confidential.",
        styles["Footer"]
    ))


def build_analytics_sections() -> list:
    """Analytics data tables for exports: (title, headers, rows).
    Mirrors what the Reports page charts show.

    Pulls each analytics dataset from the repository and shapes it into the
    (title, headers, rows) tuple that _section_table / export_excel consume.
    Every source query is wrapped so a single failing/absent dataset simply
    drops its section instead of aborting the whole export.

    Returns:
        list of (title:str, headers:list[str], rows:list[list]) tuples; only
        non-empty datasets are included.
    """
    import utils.repository as repo  # local import avoids an import cycle at module load
    sections = []

    def _safe(fn):
        # Run a repository call defensively: never raise, always return a list.
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
        # Location/count keys vary by repo implementation, so accept either
        # spelling ("location"/"name", "count"/"total") and fall back to "?"/0.
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
    """Append a generic titled analytics table (dark header + zebra rows).

    Params:
        story: Platypus story list (mutated in place).
        styles: stylesheet from _styles().
        title: section heading.
        headers: column header strings.
        rows: list of row sequences; each cell is stringified.
    Side effects: appends heading, table and spacer to `story`.
    """
    story.append(Paragraph(title, styles["SectionHead"]))
    data = [[Paragraph(h, styles["TableHead"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), styles["TableCell"]) for c in r])
    # Columns share the content width evenly; header repeats across page breaks.
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
    """Build the main multi-section Business Report PDF.

    Layout: branded header, KPI strip, optional chart images, the bookings
    table, then any extra analytics sections, then the footer.

    Params:
        path: output PDF file path.
        kpis: KPI dict for _kpi_row.
        bookings: booking rows for _bookings_table.
        title / period / biz_name: header metadata.
        sections: [(title, headers, rows)] — analytics tables (optional).
        chart_images: [(title, png_path)] — chart screenshots from the live page (optional).
    Returns:
        True on success; False if ReportLab is unavailable or the build raises.
    Side effects: writes `path` to disk.
    """
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
                # Scale image to full content width, preserving aspect ratio,
                # then cap the height at 9cm (re-deriving width) so a tall chart
                # can't overflow the page.
                w = _CONTENT_W
                h = ih * (w / iw)
                if h > 9 * cm:
                    h = 9 * cm
                    w = iw * (h / ih)
                # KeepTogether prevents the title splitting from its chart.
                story.append(KeepTogether([
                    Paragraph(chart_title, styles["SectionHead"]),
                    Image(png, width=w, height=h),
                    Spacer(1, 8),
                ]))
            except Exception as exc:
                # One bad screenshot shouldn't kill the whole report.
                print(f"[exporter] chart image skipped ({chart_title}): {exc}")

        _bookings_table(story, styles, bookings)

        # Append any extra analytics tables after the bookings table.
        for sec_title, headers, rows in (sections or []):
            _section_table(story, styles, sec_title, headers, rows)

        _footer(story, styles, biz_name)
        doc.build(story)  # render the assembled story to the PDF file
        return True
    except Exception as exc:
        # Soft-fail: report failure to the caller without raising to the UI.
        print(f"[exporter] PDF failed: {exc}")
        return False


def export_tablet_master_data(save_path: str) -> dict:
    """PC -> Tablet master data transfer.
    Writes a standalone SQLite file containing packages, package_items, menu_items,
    customers directory, and address lookup tables - strictly without past bookings
    or transaction records - so the Tablet App gets the complete customer list,
    menu catalog, and address dropdown data.

    Params:
        save_path: destination path for the new standalone SQLite file.
    Returns:
        A stats dict with per-table copied counts and an "errors" list. The
        transfer is best-effort: partial failures are recorded rather than
        raised, and the destination DB is always detached in `finally`.
    Side effects: creates/overwrites `save_path`; ATTACHes then DETACHes it on
        the main connection.
    """
    import utils.db as db
    stats = {"packages": 0, "menu_items": 0, "package_items": 0, "customers": 0, "addresses": 0, "errors": []}
    try:
        # Attach the export file as schema `dst`; failure here means we can't
        # even create the file, so bail out early with the error recorded.
        db.execute("ATTACH DATABASE ? AS dst", (save_path,))
    except Exception as exc:
        stats["errors"].append(f"Could not create export file: {exc}")
        return stats
    try:
        # Recreate the catalog/reference schema in the attached DB (idempotent).
        db.execute("""
            CREATE TABLE IF NOT EXISTS dst.packages (
                pkg_id INTEGER PRIMARY KEY, pkg_name TEXT NOT NULL UNIQUE, pkg_description TEXT,
                pkg_price_per_pax REAL NOT NULL, pkg_min_pax INTEGER DEFAULT 30,
                pkg_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS dst.menu_items (
                mi_id INTEGER PRIMARY KEY, mi_name TEXT NOT NULL, mi_category TEXT NOT NULL,
                mi_price REAL NOT NULL, mi_status TEXT DEFAULT 'Available', mi_description TEXT,
                mi_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS dst.package_items (
                pi_id INTEGER PRIMARY KEY, pi_package_id INTEGER, pi_menu_item_id INTEGER,
                pi_item_name TEXT, pi_category TEXT, pi_custom_price REAL DEFAULT 0.0, pi_quantity INTEGER DEFAULT 1
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS dst.customers (
                cus_id INTEGER PRIMARY KEY, cus_name TEXT NOT NULL, cus_contact TEXT,
                cus_email TEXT, cus_address TEXT, cus_address_id INTEGER,
                cus_loyalty_tier TEXT DEFAULT 'Bronze', cus_total_events INTEGER DEFAULT 0,
                cus_total_spent REAL DEFAULT 0.0, cus_status TEXT DEFAULT 'Active',
                cus_notes TEXT, cus_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS dst.address_provinces (
                ap_id INTEGER PRIMARY KEY AUTOINCREMENT, ap_name TEXT NOT NULL UNIQUE
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS dst.address_cities (
                ac_id INTEGER PRIMARY KEY AUTOINCREMENT, ac_province_id INTEGER, ac_name TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS dst.address_barangays (
                ab_id INTEGER PRIMARY KEY AUTOINCREMENT, ab_city_id INTEGER, ab_name TEXT NOT NULL
            )
        """)

        # Clear any prior contents so re-exporting to an existing file is a
        # clean overwrite. Order respects the implicit parent->child hierarchy.
        db.execute("DELETE FROM dst.packages")
        db.execute("DELETE FROM dst.menu_items")
        db.execute("DELETE FROM dst.package_items")
        db.execute("DELETE FROM dst.customers")
        db.execute("DELETE FROM dst.address_barangays")
        db.execute("DELETE FROM dst.address_cities")
        db.execute("DELETE FROM dst.address_provinces")

        # Copy catalog data (packages, menu items, package line items) verbatim.
        db.execute("INSERT INTO dst.packages SELECT pkg_id, pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax, pkg_created_at FROM main.packages")
        db.execute("INSERT INTO dst.menu_items (mi_id, mi_name, mi_category, mi_price, mi_status, mi_description, mi_created_at) "
                   "SELECT mi_id, mi_name, mi_category, mi_price, mi_status, mi_description, mi_created_at FROM main.menu_items")
        db.execute("INSERT INTO dst.package_items SELECT pi_id, pi_package_id, pi_menu_item_id, pi_item_name, pi_category, pi_custom_price, pi_quantity FROM main.package_items")

        # Copy customer profiles without orders — only Active (or unset-status)
        # customers make it onto the tablet directory.
        db.execute("""
            INSERT INTO dst.customers (cus_id, cus_name, cus_contact, cus_email, cus_address, cus_address_id, cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, cus_notes, cus_created_at)
            SELECT cus_id, cus_name, cus_contact, cus_email, cus_address, cus_address_id, cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, cus_notes, cus_created_at
            FROM main.customers WHERE cus_status = 'Active' OR cus_status IS NULL
        """)

        # Copy address lookup hierarchy
        db.execute("INSERT INTO dst.address_provinces SELECT ap_id, ap_name FROM main.address_provinces")
        db.execute("INSERT INTO dst.address_cities SELECT ac_id, ac_province_id, ac_name FROM main.address_cities")
        db.execute("INSERT INTO dst.address_barangays SELECT ab_id, ab_city_id, ab_name FROM main.address_barangays")

        # Read back row counts so the caller/UI can confirm what was copied.
        stats["packages"] = db.fetchone("SELECT COUNT(*) AS c FROM dst.packages")["c"]
        stats["menu_items"] = db.fetchone("SELECT COUNT(*) AS c FROM dst.menu_items")["c"]
        stats["package_items"] = db.fetchone("SELECT COUNT(*) AS c FROM dst.package_items")["c"]
        stats["customers"] = db.fetchone("SELECT COUNT(*) AS c FROM dst.customers")["c"]
        stats["addresses"] = db.fetchone("SELECT COUNT(*) AS c FROM dst.address_barangays")["c"]
    except Exception as exc:
        stats["errors"].append(str(exc))
    finally:
        # Always detach so the main connection isn't left holding the export
        # file open (which would lock it on Windows).
        try:
            db.execute("DETACH DATABASE dst")
        except Exception:
            pass
    return stats


def export_daily_activity_report_pdf(path: str, entries: list, business: dict,
                                     period_label: str = "Today") -> bool:
    """PDF version of the Daily Activity / Audit Report: who did what, to
    which customer/order, for how much, and when - so the owner can review
    every action taken during the covered period.

    Params:
        path: output PDF path.
        entries: list of activity dicts (date/time/actor/action/description).
        business: business profile dict (uses "name").
        period_label: human label for the covered window (e.g. "Today").
    Returns:
        True on success; False if ReportLab is missing or the build raises.
    Side effects: writes `path` to disk.
    """
    if not REPORTLAB_OK:
        return False
    try:
        biz_name = business.get("name", "Jayraldine's Catering")
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=_MARGIN, rightMargin=_MARGIN,
            topMargin=_MARGIN, bottomMargin=_MARGIN,
            title=f"{biz_name} — Daily Activity Report",
            author=biz_name,
        )
        styles = _styles()
        story = []
        _header_block(story, styles, biz_name, "Daily Activity Report", period_label)

        if entries:
            headers = ["Date", "Time", "User", "Action", "Details"]
            rows = []
            for e in entries:
                rows.append([
                    e.get("date", ""), e.get("time", ""), e.get("actor", ""),
                    e.get("action", ""), e.get("description", ""),
                ])
            # Heading includes the count with correct singular/plural of "action".
            _section_table(story, styles, f"Activity Log ({len(entries)} action{'s' if len(entries) != 1 else ''})", headers, rows)
        else:
            # Empty-state message when nothing happened in the period.
            story.append(Paragraph("No activity recorded for this period.", styles["TableCell"]))

        _footer(story, styles, biz_name)
        doc.build(story)
        return True
    except Exception as exc:
        print(f"[exporter] Daily Activity Report PDF failed: {exc}")
        return False


def export_receipt_pdf(path: str, inv: dict, business: dict = None,
                       additional_charges: list = None,
                       payment_records: list = None,
                       down_payment: float = None) -> bool:
    """Generate the official A4 Booking Agreement & Order Receipt matching the client's manual form:
    - UPPER SECTION (THE ORDER):
        * Header with Business Name / Unstretched Logo and centered 'BOOKING AGREEMENT'
        * Left Sub-Column: Client Information, Event Details, and Payment Details
        * Right Sub-Column: Package Inclusions, Itemized MENU, and Additional Charges / Add-ons
    - Signatures row (CONFORME, NOTED BY with Date)
    - LOWER SECTION:
        * Terms and Conditions card with 4 exact core terms
        * Business invitation with megaphone icon, address, phone, and Facebook footer strip
    """
    if not REPORTLAB_OK:
        return False
    try:
        import utils.repository as _repo  # local import; DB access is lazy
        additional_charges = additional_charges or []
        payment_records = payment_records or []

        # Backfill the business profile from the DB when the caller didn't pass one.
        if business is None:
            try:
                business = _repo.get_business_profile() or {}
            except Exception:
                business = {}

        # Fetch linked booking details if available. The booking id may be
        # stored under any of several keys depending on where `inv` came from.
        booking_id = inv.get("booking_id") or inv.get("inv_booking_id") or inv.get("db_id")
        booking_detail = {}
        if booking_id:
            try:
                booking_detail = _repo.get_booking_detail(booking_id) or {}
            except Exception:
                booking_detail = {}
            # Only fetch charges from the DB when the caller didn't supply them.
            if not additional_charges:
                try:
                    additional_charges = _repo.get_additional_charges(booking_id) or []
                except Exception:
                    additional_charges = []
        elif "dishes" in inv or "package_name" in inv:
            # No booking id, but the invoice already carries booking-like fields:
            # treat the invoice dict itself as the booking detail.
            booking_detail = dict(inv)

        # Split signed charge amounts: positive => add-on/extra, negative => discount.
        charges = [c for c in additional_charges if float(c.get("amount", 0)) > 0]
        discounts = [c for c in additional_charges if float(c.get("amount", 0)) < 0]

        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=1.0 * cm, rightMargin=1.0 * cm,
            topMargin=0.7 * cm, bottomMargin=0.7 * cm,
            title=f"Booking Agreement & Receipt — {inv.get('invoice', inv.get('id', ''))}",
        )
        # This receipt uses tighter 1cm margins than the standard reports.
        content_w = A4[0] - 2.0 * cm  # ~19.0 cm
        half_w = (content_w - 0.4 * cm) / 2  # ~9.3 cm per column (two-column body)

        styles = _styles()
        story = []

        biz_name    = business.get("name", "JAYRALDINE'S CATERING")
        biz_address = business.get("address", "518 Y Rama Ave., Cebu City")
        biz_contact = business.get("contact", "+63 912 345 6789")

        def _val(x):
            # Coerce any money-ish value (number, or "₱1,234.50" string) to float;
            # returns 0.0 for None/unparseable input so arithmetic never fails.
            if x is None: return 0.0
            if isinstance(x, (int, float)): return float(x)
            try: return float(str(x).replace("₱", "").replace(",", "").strip())
            except Exception: return 0.0

        # Resolve monetary fields, tolerating the many key spellings across sources.
        total   = _val(inv.get("total_amount") or inv.get("amount") or inv.get("total"))
        paid    = _val(inv.get("amount_paid") or inv.get("paid"))
        if down_payment is None:
            # Fall back to invoice/booking down payment, else treat paid as the DP.
            down_payment = _val(inv.get("down_payment") or booking_detail.get("down_payment") or paid)
        # Balance uses the larger of paid vs down_payment so neither under-counts.
        balance = max(0.0, total - max(paid, down_payment))
        # Derive a status when none is stored: fully paid -> Confirmed, some paid
        # -> Partial, otherwise Unpaid.
        status  = inv.get("status", "Confirmed" if paid >= total and total > 0 else ("Partial" if paid > 0 else "Unpaid"))

        # Optional decorative icons live alongside the app assets.
        icons_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "receipt_icons")

        def _card_header(icon_name: str, title: str):
            # Build a bold card-title Paragraph, prefixing a small inline icon
            # image only when that icon file actually exists on disk.
            icon_file = os.path.join(icons_dir, f"icon_{icon_name}.png")
            img_tag = f"<img src='{icon_file}' width='10' height='10' valign='bottom'/>  " if os.path.exists(icon_file) else ""
            return Paragraph(f"<b>{img_tag}<font color='#0F172A'>{title}</font></b>", ParagraphStyle(
                f"h_{icon_name}", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=_C_DARK))

        # ── 1. HEADER (UPPER SECTION) ─────────────────────────────────────
        logo_cell = ""  # empty string cell => header falls back to text-only layout
        _lp = _logo_path()
        if os.path.exists(_lp):
            try:
                # 1:1 strict square aspect ratio — logo will NEVER stretch!
                logo_cell = Image(_lp, width=1.6 * cm, height=1.6 * cm)
            except Exception:
                logo_cell = ""

        hdr_biz_p = [
            Paragraph("<b><font color='#DC2626'>JAYRALDINE'S CATERING SERVICES</font></b>", ParagraphStyle(
                "h_biz", fontName="Helvetica-Bold", fontSize=14, alignment=TA_LEFT, leading=18)),
            Paragraph("<b><font color='#0F172A'>BOOKING AGREEMENT</font></b>", ParagraphStyle(
                "h_agree", fontName="Helvetica-Bold", fontSize=11.5, textColor=_C_DARK, alignment=TA_LEFT, leading=14)),
        ]

        # Order reference: first available of several id keys, else a placeholder.
        rcpt_no = inv.get("invoice") or inv.get("invoice_ref") or booking_detail.get("ref") or booking_detail.get("booking_ref") or "TB-00001-69215"
        today_str = _dt_datetime.now().strftime("%B %d, %Y")  # issue date = today
        hdr_meta_p = [
            Paragraph(f"ORDER REF:  <b>{rcpt_no}</b>", ParagraphStyle(
                "h_meta1", fontName="Helvetica", fontSize=8.5, textColor=_C_DARK, alignment=TA_RIGHT, leading=12)),
            Paragraph(f"DATE ISSUED:  {today_str}", ParagraphStyle(
                "h_meta2", fontName="Helvetica", fontSize=8, textColor=_C_DARK, alignment=TA_RIGHT, leading=12)),
        ]

        # Two header variants: with-logo uses a 4-column band and a red rule
        # separating logo from the business block; without-logo is 2 columns.
        if logo_cell:
            hdr_table = Table([[logo_cell, "", hdr_biz_p, hdr_meta_p]], colWidths=[1.8 * cm, 0.15 * cm, content_w - 6.75 * cm, 4.8 * cm])
            hdr_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBEFORE", (2, 0), (2, 0), 1.5, colors.HexColor("#DC2626")),
                ("LEFTPADDING", (2, 0), (2, 0), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (-1, -1), (-1, -1), 0),
            ]))
            story.append(hdr_table)
        else:
            hdr_table = Table([[hdr_biz_p, hdr_meta_p]], colWidths=[content_w - 5.0 * cm, 5.0 * cm])
            hdr_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(hdr_table)

        story.append(Spacer(1, 0.12 * cm))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#DC2626"), spaceAfter=0.22 * cm))

        # ── 2. UPPER ORDER DETAILS (2 SUB-COLUMNS) ────────────────────────
        # Gather every display field, each falling back across invoice ->
        # booking_detail -> sensible default. left_sub accumulates the left column.
        left_sub = []
        cust_name = inv.get("customer") or booking_detail.get("name") or "aasdfasdf"  # NOTE: placeholder default is test data
        contact_no = booking_detail.get("contact") or inv.get("contact") or "—"
        address = booking_detail.get("address") or inv.get("address") or "—"
        event_dt = inv.get("event_date") or booking_detail.get("date") or "—"
        raw_t = booking_detail.get("time") or booking_detail.get("event_time") or ""
        # Format start time (and end time when present) into a display range.
        time_disp = _repo.format_time_ampm(raw_t, default="To be followed") if raw_t else "To be followed"
        if booking_detail.get("event_end_time"):
            time_disp += f" - {_repo.format_time_ampm(booking_detail['event_end_time'])}"
        venue = booking_detail.get("venue") or address or "To be followed"
        occasion = booking_detail.get("occasion") or "General Event"
        motif = booking_detail.get("color_theme") or booking_detail.get("motif") or "Standard"
        pax = str(booking_detail.get("pax") or "—")
        notes = booking_detail.get("notes") or booking_detail.get("special_notes") or "Standard arrangement."
        pay_mode = inv.get("payment_method") or booking_detail.get("payment_mode") or "Cash"

        # Card 1: CLIENT INFORMATION — bordered mini-table; first row is the
        # card header spanning both columns (SPAN in the style below).
        c1_head = _card_header("user", "CLIENT INFORMATION")
        c1_rows = [
            [c1_head, ""],
            [Paragraph("<b>Name:</b>", styles["DetailLabel"]), Paragraph(str(cust_name), styles["DetailValue"])],
            [Paragraph("<b>Address:</b>", styles["DetailLabel"]), Paragraph(str(address), styles["DetailValue"])],
            [Paragraph("<b>Contact #:</b>", styles["DetailLabel"]), Paragraph(str(contact_no), styles["DetailValue"])],
        ]
        c1_tbl = Table(c1_rows, colWidths=[2.2 * cm, half_w - 2.2 * cm])
        c1_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ("SPAN", (0, 0), (1, 0)),
            ("LINEBELOW", (0, 0), (1, 0), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        left_sub.append(c1_tbl)
        left_sub.append(Spacer(1, 0.22 * cm))

        # Card 2: EVENT DETAILS
        c2_head = _card_header("calendar", "EVENT DETAILS")
        c2_rows = [
            [c2_head, ""],
            [Paragraph("<b>Function Date:</b>", styles["DetailLabel"]), Paragraph(str(event_dt), styles["DetailValue"])],
            [Paragraph("<b>Time:</b>", styles["DetailLabel"]), Paragraph(str(time_disp), styles["DetailValue"])],
            [Paragraph("<b>Venue:</b>", styles["DetailLabel"]), Paragraph(str(venue), styles["DetailValue"])],
            [Paragraph("<b>Occasion:</b>", styles["DetailLabel"]), Paragraph(str(occasion), styles["DetailValue"])],
            [Paragraph("<b>Motif:</b>", styles["DetailLabel"]), Paragraph(str(motif), styles["DetailValue"])],
            # NOTE: pax_lbl / pax_val_str are not defined in this scope; if this
            # branch is reached it raises NameError, which the outer try/except
            # turns into a soft (False) failure. Left as-is per comments-only edit.
            [Paragraph(f"<b>{pax_lbl}</b>", styles["DetailLabel"]), Paragraph(pax_val_str, styles["DetailValue"])],
            [Paragraph("<b>Special Instructions:</b>", styles["DetailLabel"]), Paragraph(str(notes), styles["DetailValue"])],
        ]
        c2_tbl = Table(c2_rows, colWidths=[3.7 * cm, half_w - 3.7 * cm])
        c2_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ("SPAN", (0, 0), (1, 0)),
            ("LINEBELOW", (0, 0), (1, 0), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        left_sub.append(c2_tbl)
        left_sub.append(Spacer(1, 0.22 * cm))

        # Card 3: PAYMENT DETAILS — total, downpayment (with mode/status) and
        # balance due, each right-aligned with its own inline paragraph style.
        c3_head = _card_header("coins", "PAYMENT DETAILS")
        c3_rows = [
            [c3_head, ""],
            [Paragraph("<b>Total Amount:</b>", styles["DetailLabel"]), Paragraph(f"<b>PHP {total:,.2f}</b>", ParagraphStyle("ft", fontName="Helvetica-Bold", fontSize=9, textColor=_C_DARK, alignment=TA_RIGHT, leading=11))],
            [Paragraph("<b>Downpayment:</b>", styles["DetailLabel"]), Paragraph(f"PHP {down_payment:,.2f} ({pay_mode} - {status})", ParagraphStyle("fd", fontName="Helvetica", fontSize=8.5, textColor=_C_DARK, alignment=TA_RIGHT, leading=11))],
            [Paragraph("<b>Balance Due:</b>", styles["DetailLabel"]), Paragraph(f"<b>PHP {balance:,.2f}</b>", ParagraphStyle("fb", fontName="Helvetica-Bold", fontSize=9.5, textColor=_C_DARK, alignment=TA_RIGHT, leading=11))],
        ]
        c3_tbl = Table(c3_rows, colWidths=[2.6 * cm, half_w - 2.6 * cm])
        c3_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ("SPAN", (0, 0), (1, 0)),
            ("LINEBELOW", (0, 0), (1, 0), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        left_sub.append(c3_tbl)

        # Right Sub-Column: Card 4 (PACKAGE & MENU)
        right_sub = []
        pkg_name = booking_detail.get("package_name") or booking_detail.get("package") or "CUSTOM PACKAGE"
        base_tot = _val(booking_detail.get("base_total") or total)  # pre-add-on package total

        c4_head = _card_header("cloche", "PACKAGE &amp; MENU")
        # Package inclusions text: prefer whatever the booking already carries,
        # else fetch the package description from the DB (by id, else by name).
        pkg_inclusions = (
            booking_detail.get("package_inclusions")
            or booking_detail.get("pkg_description")
            or booking_detail.get("package_description")
            or ""
        )
        if not pkg_inclusions:
            try:
                pkg_id = booking_detail.get("package_id") or inv.get("package_id")
                if pkg_id:
                    _pr = _repo.db.fetchone("SELECT pkg_description FROM packages WHERE pkg_id = ?", (pkg_id,))
                else:
                    _pr = _repo.db.fetchone(
                        "SELECT pkg_description FROM packages WHERE LOWER(TRIM(pkg_name)) = LOWER(TRIM(?)) LIMIT 1",
                        (pkg_name,)
                    )
                if _pr and _pr.get("pkg_description"):
                    pkg_inclusions = _pr["pkg_description"]
            except Exception:
                pass

        c4_content = [
            c4_head,
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=0.12 * cm),
            Paragraph(f"<b>PACKAGE: {str(pkg_name).upper()}</b>", ParagraphStyle(
                "r_pkg", fontName="Helvetica-Bold", fontSize=10, textColor=_C_DARK, leading=12)),
            # NOTE: `is_food_set` is not defined in this scope (a food-set flag
            # is computed only in export_order_slip_pdf). Reaching this line
            # raises NameError -> soft failure. Left unchanged (comments only).
            Paragraph(f"{'Quantity: ' + str(pax) + ' Set(s)' if is_food_set else 'Good for ' + str(pax) + ' person(s)'}  ·  Base: PHP {base_tot:,.2f}", ParagraphStyle(
                "r_pkg_sub", fontName="Helvetica", fontSize=8.5, textColor=_C_DARK, leading=11, spaceAfter=3)),
        ]

        # INCLUSIONS section (from package description) — only when present.
        if pkg_inclusions and str(pkg_inclusions).strip():
            c4_content.append(Paragraph("<b>INCLUSIONS:</b>", ParagraphStyle(
                "r_inc_h", fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_DARK, leading=11, spaceAfter=1)))
            inc_lines = str(pkg_inclusions).strip().splitlines()
            shown = "\n".join(inc_lines[:5])  # cap at 5 lines to fit the card
            # Convert newlines to <br/> for ReportLab's mini-HTML paragraph markup.
            c4_content.append(Paragraph(shown.replace("\n", "<br/>"), ParagraphStyle(
                "r_inc_v", fontName="Helvetica", fontSize=7.8, textColor=colors.HexColor("#334155"), leading=10.5, spaceAfter=3)))

        c4_content.append(Paragraph("<b>MENU:</b>", ParagraphStyle(
            "r_menu_h", fontName="Helvetica-Bold", fontSize=9.5, textColor=_C_DARK, leading=12, spaceAfter=2)))

        # MENU list: each dish may be a dict {name, category} or a bare string.
        dishes = booking_detail.get("selected_dishes") or booking_detail.get("dishes") or []
        if dishes:
            d_lines = []
            for i, d in enumerate(dishes, 1):
                d_nm = d.get("name") if isinstance(d, dict) else str(d)
                # Show the category in muted grey only when the dish carries one.
                d_cat = f" <font color='#64748B'>({d.get('category', '')})</font>" if isinstance(d, dict) and d.get("category") else ""
                d_lines.append(f"<b>{i}.</b> {d_nm}{d_cat}")
            c4_content.append(Paragraph("<br/>".join(d_lines), ParagraphStyle(
                "r_menu_l", fontName="Helvetica", fontSize=9, textColor=_C_DARK, leading=12.5)))
        else:
            c4_content.append(Paragraph("<i>Standard package inclusions.</i>", ParagraphStyle(
                "r_menu_none", fontName="Helvetica-Oblique", fontSize=8.5, textColor=_C_MUTED, leading=11)))

        # Add-ons & Inclusions. The leading spacer shrinks as the dish list
        # grows so the add-ons block sits at a roughly consistent height in the
        # card regardless of how many menu lines precede it.
        num_dishes = len(dishes) if dishes else 0
        if charges:
            addon_spacer = max(0.15 * cm, 2.5 * cm - (num_dishes * 0.22 * cm))
            c4_content.append(Spacer(1, addon_spacer))
            c4_content.append(Paragraph("<b>ADD-ONS &amp; EXTRAS:</b>", ParagraphStyle(
                "r_chg_h", fontName="Helvetica-Bold", fontSize=9.5, textColor=_C_DARK, leading=12, spaceAfter=2)))
            addon_rows = []
            for c in charges:
                desc = c.get('description', 'Extra')
                amt = float(c.get('amount', 0))
                # Signed display: "+PHP" for extras, "-PHP" for negatives.
                amt_str = f"+PHP {amt:,.2f}" if amt >= 0 else f"-PHP {abs(amt):,.2f}"
                addon_rows.append([
                    Paragraph(f"• {desc}:", ParagraphStyle("ad_lbl", fontName="Helvetica", fontSize=8.8, textColor=_C_DARK, leading=11)),
                    Paragraph(f"<b>{amt_str}</b>", ParagraphStyle("ad_val", fontName="Helvetica-Bold", fontSize=8.8, textColor=_C_DARK, alignment=TA_RIGHT, leading=11))
                ])
            addon_tbl = Table(addon_rows, colWidths=[half_w - 3.2 * cm, 2.8 * cm])
            addon_tbl.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            c4_content.append(addon_tbl)
        else:
            # No add-ons: still pad the card so its height matches the left column.
            addon_spacer = max(0.3 * cm, 3.0 * cm - (num_dishes * 0.22 * cm))
            c4_content.append(Spacer(1, addon_spacer))

        # Wrap the whole right-column content list in a single bordered cell.
        c4_tbl = Table([[c4_content]], colWidths=[half_w])
        c4_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        right_sub.append(c4_tbl)

        # Assemble Upper Two-Column Table: left cards (client/event/payment)
        # beside the right package&menu card.
        upper_table = Table([[left_sub, right_sub]], colWidths=[half_w, half_w])
        upper_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(upper_table)
        story.append(Spacer(1, 0.45 * cm))

        # Signatures: two signing lines (CONFORME / NOTED BY) each with a Date.
        sig_col1_w = content_w * 0.65
        sig_col2_w = content_w * 0.35
        sig_data = [
            [Paragraph("<b>CONFORME:</b>  ___________________________________________", styles["DetailLabel"]),
             Paragraph("<b>Date:</b>  ____________________", styles["DetailLabel"])],
            [Paragraph("<b>NOTED BY:</b>   ___________________________________________", styles["DetailLabel"]),
             Paragraph("<b>Date:</b>  ____________________", styles["DetailLabel"])],
        ]
        sig_tbl = Table(sig_data, colWidths=[sig_col1_w, sig_col2_w])
        sig_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("TOPPADDING", (0, 0), (-1, 0), 2),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 1), (-1, 1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(sig_tbl)
        story.append(Spacer(1, 0.35 * cm))

        # ── 3. LOWER SECTION: TERMS AND CONDITIONS CARD ───────────────────
        tc_head = _card_header("doc", "TERMS AND CONDITIONS")
        tc_terms = [
            "<b>The client shall pay 50% downpayment upon reservation of booking</b> and shall pay the full amount 3 days before the date of the event.",
            "<b>Mode of payment.</b> The client shall personally pay in Cash for the downpayment and full payment. If cash is not available, the client can also pay through Bank Transfer or Gcash.",
            "<b>Failure to pay.</b> A failure to make payment according to the terms of the payment will be considered a cancellation of the event and the provisions for cancellation will apply. (15) days before the event - 20% charge, (7) days - 30%, (3) days - 50%.",
            "<b>Consider Food and Liabilities.</b> Any Food and Drinks or any consumables that is NOT prepared by JAYRALDINE SERVICES brought by the client will FREE US ON ANY LIABILITIES due to food poisoning and spoilage. We charge Corkage Fee for bringing outside Food and Drinks. Precise time should be placed in the BOOKING AGREEMENT and shall be strictly follow to avoid poisoning and spoilage."
        ]
        tc_items = [tc_head, HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=0.22 * cm)]
        for term in tc_terms:
            tc_items.append(Paragraph(f"• {term}", ParagraphStyle(
                "tc_item", fontName="Helvetica", fontSize=9.2, textColor=colors.HexColor("#0F172A"), leading=13.0, spaceAfter=9)))

        tc_tbl = Table([[tc_items]], colWidths=[content_w])
        tc_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(tc_tbl)

        # ── 4. FOOTER BANNER (Pinned to bottom of A4 page) ────────────────
        # FillBottomSpacer pushes this banner to the page bottom; without
        # ReportLab's Flowable it degrades to a fixed small spacer.
        story.append(FillBottomSpacer(footer_height=2.8 * cm) if FillBottomSpacer else Spacer(1, 0.12 * cm))
        story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#DC2626"), spaceAfter=0.12 * cm))

        # Megaphone line (Centered) — icon prefixed only if the asset exists.
        mg_file = os.path.join(icons_dir, "icon_megaphone.png")
        mg_tag = f"<img src='{mg_file}' width='11' height='11' valign='middle'/>  " if os.path.exists(mg_file) else ""
        story.append(Paragraph(f"<b>{mg_tag}<font color='#DC2626'>WE INVITE YOU TO SEE HOW WE CAN HELP YOUR EVENT; THE BEST IT CAN POSSIBLY BE!!!</font></b>", ParagraphStyle(
            "f_inv", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#DC2626"), alignment=TA_CENTER, leading=10.5)))

        story.append(Paragraph(f"Located at {biz_address}", ParagraphStyle(
            "f_loc", fontName="Helvetica", fontSize=7.2, textColor=_C_DARK, alignment=TA_CENTER, leading=9)))
        story.append(Paragraph(f"Please feel free to call us at {biz_contact}", ParagraphStyle(
            "f_tel", fontName="Helvetica", fontSize=7.2, textColor=_C_DARK, alignment=TA_CENTER, leading=9)))
        story.append(Paragraph("Find us on Facebook: <b>Jayraldine's Catering Services</b>", ParagraphStyle(
            "f_fb", fontName="Helvetica", fontSize=7.2, textColor=_C_DARK, alignment=TA_CENTER, leading=9)))

        # 3-part bottom strip with icons (location | phone | Facebook), each a
        # third of the width and divided by red vertical rules.
        strip_w = content_w / 3.0
        pin_file = os.path.join(icons_dir, "icon_pin.png")
        phone_file = os.path.join(icons_dir, "icon_phone.png")
        fb_file = os.path.join(icons_dir, "icon_fb.png")

        pin_tag = f"<img src='{pin_file}' width='9' height='9' valign='middle'/>  " if os.path.exists(pin_file) else ""
        phone_tag = f"<img src='{phone_file}' width='9' height='9' valign='middle'/>  " if os.path.exists(phone_file) else ""
        fb_tag = f"<img src='{fb_file}' width='9' height='9' valign='middle'/>  " if os.path.exists(fb_file) else ""

        p_loc = Paragraph(f"{pin_tag}Located at {biz_address}", ParagraphStyle("st1", fontName="Helvetica", fontSize=6.5, textColor=_C_DARK, alignment=TA_CENTER, leading=8.5))
        p_tel = Paragraph(f"{phone_tag}Please feel free to call us at {biz_contact}", ParagraphStyle("st2", fontName="Helvetica", fontSize=6.5, textColor=_C_DARK, alignment=TA_CENTER, leading=8.5))
        p_fb = Paragraph(f"{fb_tag}Find us on Facebook: <b>Jayraldine's Catering Services</b>", ParagraphStyle("st3", fontName="Helvetica", fontSize=6.5, textColor=_C_DARK, alignment=TA_CENTER, leading=8.5))

        strip_tbl = Table([[p_loc, p_tel, p_fb]], colWidths=[strip_w, strip_w, strip_w])
        strip_tbl.setStyle(TableStyle([
            ("LINEBEFORE", (1, 0), (1, 0), 1.0, colors.HexColor("#DC2626")),
            ("LINEBEFORE", (2, 0), (2, 0), 1.0, colors.HexColor("#DC2626")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(Spacer(1, 0.08 * cm))
        story.append(strip_tbl)

        doc.build(story)
        return True
    except Exception as exc:
        # NOTE: `logger` is not imported/defined in this module; if the build
        # raises, this handler itself raises NameError. The function still fails
        # to produce a PDF either way. Left unchanged per comments-only scope.
        logger.error(f"[exporter] export_receipt_pdf failed: {exc}", exc_info=True)
        return False


def export_order_slip_pdf(path: str, booking: dict, business: dict) -> bool:
    """Generate a clean Banquet Event Order (BEO) / Kitchen Order Slip PDF.
    
    Contains:
    - Customer Name
    - Event Location / Venue
    - Event Date & Time
    - Pax (Guest Count)
    - Package Name & Categorized Dishes / Menu
    - Additional Items / Add-ons strictly WITHOUT price amounts ("walay price amount")
    - Event Notes / Operations Remarks

    Params:
        path: output PDF path.
        booking: booking dict (id/name/venue/date/time/pax/package/dishes/
            additional_charges/notes/...).
        business: business profile dict (name/address/contact/email).
    Returns:
        True on success; False if ReportLab is missing or the build raises.
    Side effects: writes `path`. Prices are deliberately stripped from add-ons.
    """
    if not REPORTLAB_OK:
        return False
    try:
        import re  # used to strip price fragments out of add-on descriptions
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=_MARGIN, rightMargin=_MARGIN,
            topMargin=_MARGIN, bottomMargin=_MARGIN,
            title=f"Order Slip — {booking.get('id') or booking.get('booking_ref', 'Order')}",
        )
        styles = _styles()
        story = []

        biz_name    = business.get("name", "Jayraldine's Catering Services")
        biz_address = business.get("address", "")
        biz_contact = business.get("contact", "")
        biz_email   = business.get("email", "")

        order_ref = str(booking.get("id") or booking.get("booking_ref") or "ORD-SLIP")
        cust_name = str(booking.get("name") or booking.get("customer_name") or "Valued Client")
        venue     = str(booking.get("venue") or booking.get("address") or "To be specified")
        date_str  = str(booking.get("event_date") or booking.get("date") or "TBA")
        raw_t     = booking.get("event_time") or booking.get("time") or ""
        time_str  = _format_time_ampm(raw_t) if raw_t else "TBA"
        pax       = str(booking.get("pax", "100"))
        pkg_name_inv = str(booking.get("package_name") or booking.get("pkg_name") or "")
        # Detect "food set/pack" style packages by name — these are counted in
        # sets/quantity rather than as a per-head guest count.
        is_food_set_inv = any(k in pkg_name_inv.lower() for k in ["food set", "food pack", "foodset", "foodpack", "set of dish"]) or pkg_name_inv.lower().startswith("set ") or " set" in pkg_name_inv.lower()
        guest_lbl = "Quantity:" if is_food_set_inv else "Guest Count:"
        pax_disp = f"<b>{pax} Set(s)</b>" if is_food_set_inv else f"<b>{pax} Pax</b>"
        pkg_name  = str(booking.get("package_name") or booking.get("menu_value") or "Standard Package")
        motif     = str(booking.get("color_theme") or booking.get("color") or "")
        occasion  = str(booking.get("occasion") or "Catering Event")

        # Top Header Table
        logo_cell = ""
        _lp = _logo_path()
        if os.path.exists(_lp):
            try:
                logo_cell = Image(_lp, width=2.0*cm, height=2.0*cm)
            except Exception:
                logo_cell = ""

        biz_cell = [
            Paragraph(biz_name, styles["Brand"]),
            Paragraph("Catering & Banquet Event Services", styles["BrandSub"]),
            Spacer(1, 2),
            Paragraph(biz_address, styles["BrandSub"]),
            Paragraph(f"Contact: {biz_contact}  ·  {biz_email}", styles["BrandSub"]),
        ]

        title_cell = [
            Paragraph("ORDER & EVENT SLIP", ParagraphStyle(
                "slip_lbl", fontName="Helvetica-Bold", fontSize=8.5,
                textColor=_C_MUTED, alignment=TA_RIGHT, leading=11, spaceAfter=4)),
            Paragraph(order_ref, ParagraphStyle(
                "slip_no", fontName="Helvetica-Bold", fontSize=17,
                textColor=_C_RED, alignment=TA_RIGHT, leading=21)),
            Paragraph("Kitchen & Operations Dispatch", ParagraphStyle(
                "slip_tag", fontName="Helvetica", fontSize=8,
                textColor=_C_MUTED, alignment=TA_RIGHT, leading=10, spaceBefore=2)),
        ]

        hdr_cols = [2.2*cm, 9.8*cm, 6.0*cm] if logo_cell else [12.0*cm, 6.0*cm]
        hdr_data = [[logo_cell, biz_cell, title_cell]] if logo_cell else [[biz_cell, title_cell]]
        hdr_tbl = Table(hdr_data, colWidths=hdr_cols)
        hdr_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(hdr_tbl)
        story.append(HRFlowable(width="100%", thickness=1.5, color=_C_RED))
        story.append(Spacer(1, 0.4*cm))

        # Event & Client Information Grid
        story.append(Paragraph("EVENT SPECIFICATIONS", styles["SectionHead"]))
        event_info = [
            [
                Paragraph("<b>Client Name:</b>", styles["DetailLabel"]),
                Paragraph(f"<b>{cust_name}</b>", styles["DetailValueBold"]),
                Paragraph("<b>Event Date:</b>", styles["DetailLabel"]),
                Paragraph(f"<b>{date_str}</b>", styles["DetailValueBold"]),
            ],
            [
                Paragraph("<b>Location / Venue:</b>", styles["DetailLabel"]),
                Paragraph(venue, styles["DetailValue"]),
                Paragraph("<b>Event Time:</b>", styles["DetailLabel"]),
                Paragraph(f"<b>{time_str}</b>", styles["DetailValue"]),
            ],
            [
                Paragraph("<b>Occasion:</b>", styles["DetailLabel"]),
                Paragraph(occasion, styles["DetailValue"]),
                Paragraph(f"<b>{guest_lbl}</b>", styles["DetailLabel"]),
                Paragraph(pax_disp, styles["DetailValueBold"]),
            ],
        ]
        if motif:
            event_info.append([
                Paragraph("<b>Color Motif:</b>", styles["DetailLabel"]),
                Paragraph(motif, styles["DetailValue"]),
                Paragraph("<b>Service Style:</b>", styles["DetailLabel"]),
                Paragraph("Buffet / Catered Setup", styles["DetailValue"]),
            ])

        col_w = [_CONTENT_W * 0.22, _CONTENT_W * 0.38, _CONTENT_W * 0.18, _CONTENT_W * 0.22]
        info_tbl = Table(event_info, colWidths=col_w)
        info_tbl.setStyle(TableStyle([
            ("BOX",          (0, 0), (-1, -1), 0.4, _C_BORDER),
            ("INNERGRID",    (0, 0), (-1, -1), 0.3, _C_BORDER),
            ("BACKGROUND",   (0, 0), (0, -1),  colors.HexColor("#F8FAFC")),
            ("BACKGROUND",   (2, 0), (2, -1),  colors.HexColor("#F8FAFC")),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(info_tbl)
        story.append(Spacer(1, 0.4*cm))

        # Package & Dishes Section
        story.append(Paragraph(f"MENU & DISHES — <font color='{_C_RED.hexval()}'>{pkg_name.upper()}</font>", styles["SectionHead"]))

        dishes = booking.get("dishes") or []
        # Fallback: derive dishes from a comma-separated "menu_value" string.
        if not dishes and booking.get("menu_value"):
            raw_dishes = [d.strip() for d in str(booking["menu_value"]).split(",") if d.strip()]
            dishes = [{"name": rd, "category": "Selected Dishes"} for rd in raw_dishes]

        if dishes:
            # Group dish names by course/category for the kitchen table.
            by_cat = {}
            for d in dishes:
                cat = d.get("category") or "Menu Items"
                d_name = d.get("name") or d.get("item_name") or str(d)
                if d_name:
                    by_cat.setdefault(cat, []).append(d_name)

            dish_table_data = [[
                Paragraph("Category / Course", styles["TableHead"]),
                Paragraph("Dishes & Prepared Items", styles["TableHead"]),
            ]]
            for cat, items_list in by_cat.items():
                items_p = "<br/>".join([f"• <b>{itm}</b>" for itm in items_list])
                dish_table_data.append([
                    Paragraph(f"<b>{cat}</b>", styles["DetailLabel"]),
                    Paragraph(items_p, styles["DetailValue"]),
                ])

            dish_tbl = Table(dish_table_data, colWidths=[_CONTENT_W * 0.30, _CONTENT_W * 0.70])
            dish_tbl.setStyle(TableStyle([
                ("BOX",          (0, 0), (-1, -1), 0.4, _C_BORDER),
                ("INNERGRID",    (0, 0), (-1, -1), 0.3, _C_BORDER),
                ("BACKGROUND",   (0, 0), (-1, 0),  _C_RED),
                ("TOPPADDING",   (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(dish_tbl)
        else:
            story.append(Paragraph("<i>Standard catering package inclusions apply.</i>", styles["BrandSub"]))
        story.append(Spacer(1, 0.4*cm))

        # Additional Inclusions / Add-ons (WALAY PRICE AMOUNT - STRICT REQUIREMENT)
        story.append(Paragraph("ADDITIONAL ITEMS & ADD-ONS (NO CHARGE/RATE DISPLAY)", styles["SectionHead"]))

        # Extract add-on descriptions strictly without price amounts. Two regex
        # passes remove (a) a trailing "(... 123 ...)" price parenthetical and
        # (b) any inline "₱/P 123" fragment; de-duplicated into add_ons.
        add_ons = []
        raw_charges = booking.get("additional_charges") or []
        for chg in raw_charges:
            desc = str(chg.get("description") or "").strip()
            if desc:
                clean_desc = re.sub(r"\s*\([+-]?[^\)]*[\d,.]+[^\)]*\)\s*$", "", desc).strip()
                clean_desc = re.sub(r"[+-]?[₱P]\s*[\d,.]+", "", clean_desc).strip()
                if clean_desc and clean_desc not in add_ons:
                    add_ons.append(clean_desc)

        # Also mine add-ons from a "[Add-ons: ...]" marker embedded in notes.
        notes_str = str(booking.get("notes") or "").strip()
        m_addons = re.search(r"\[Add-ons:\s*(.*?)\]", notes_str, re.IGNORECASE)
        if m_addons:
            # Split on commas that follow a ")" so a price parenthetical isn't
            # split mid-item; then strip prices the same way as above.
            raw_addons = re.split(r"(?<=\))\s*,\s*", m_addons.group(1))
            for a in raw_addons:
                clean_a = re.sub(r"\s*\([+-]?[^\)]*[\d,.]+[^\)]*\)\s*$", "", a).strip()
                clean_a = re.sub(r"[+-]?[₱P]\s*[\d,.]+", "", clean_a).strip()
                if clean_a and clean_a not in add_ons:
                    add_ons.append(clean_a)

        # Remove the whole "[Add-ons: ...]" marker from the notes we display.
        clean_notes = re.sub(r"\n?\[Add-ons:\s*.*?\]", "", notes_str, flags=re.IGNORECASE).strip()

        if add_ons:
            addon_rows = [[
                Paragraph("#", styles["TableHead"]),
                Paragraph("Item / Add-on Description", styles["TableHead"]),
                Paragraph("Status / Fulfillment", styles["TableHead"]),
            ]]
            for idx, a_text in enumerate(add_ons, 1):
                addon_rows.append([
                    Paragraph(str(idx), ParagraphStyle("idx_p", fontName="Helvetica", fontSize=9, alignment=TA_CENTER)),
                    Paragraph(f"<b>{a_text}</b>", styles["DetailValue"]),
                    Paragraph("[  ] Prepared / In Vehicle", ParagraphStyle("stat_p", fontName="Helvetica", fontSize=8.5, textColor=_C_MUTED)),
                ])
            addon_tbl = Table(addon_rows, colWidths=[_CONTENT_W * 0.08, _CONTENT_W * 0.62, _CONTENT_W * 0.30])
            addon_tbl.setStyle(TableStyle([
                ("BOX",          (0, 0), (-1, -1), 0.4, _C_BORDER),
                ("INNERGRID",    (0, 0), (-1, -1), 0.3, _C_BORDER),
                ("BACKGROUND",   (0, 0), (-1, 0),  _C_GRAY),
                ("TOPPADDING",   (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(addon_tbl)
        else:
            story.append(Paragraph("<i>No additional add-on items specified for this event.</i>", styles["BrandSub"]))
        story.append(Spacer(1, 0.4*cm))

        # Special Notes / Operations Remarks
        if clean_notes:
            story.append(Paragraph("OPERATIONS NOTES & SPECIAL REQUESTS", styles["SectionHead"]))
            notes_tbl = Table([[Paragraph(clean_notes, styles["DetailValue"])]], colWidths=[_CONTENT_W])
            notes_tbl.setStyle(TableStyle([
                ("BOX",          (0, 0), (-1, -1), 0.4, _C_BORDER),
                ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                ("TOPPADDING",   (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
                ("LEFTPADDING",  (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(notes_tbl)
            story.append(Spacer(1, 0.4*cm))
        from datetime import datetime as _dt
        printed_str = _dt.now().strftime("%B %d, %Y at %I:%M %p")
        story.append(Paragraph(
            f"Generated: {printed_str}  ·  Kitchen & Event Operations Order Slip  ·  <b>{biz_name}</b>",
            styles["Footer"],
        ))

        doc.build(story)
        return True
    except Exception as exc:
        print(f"[exporter] Order Slip PDF failed: {exc}")
        return False


def export_excel(path: str, kpis: dict, bookings: list,
                 title: str = "Business Report", period: str = "All Time",
                 biz_name: str = "Jayraldine's Catering",
                 sections: list = None) -> bool:
    """Excel counterpart of export_pdf: KPIs + bookings on the main sheet,
    then one extra worksheet per analytics section.

    Params:
        path: output .xlsx path.
        kpis: KPI dict (adds today/week counts beyond the PDF set).
        bookings: booking rows.
        title / period / biz_name: header metadata.
        sections: [(title, headers, rows)] extra analytics tables (optional).
    Returns:
        True on success; False if openpyxl is missing or saving raises.
    Side effects: writes `path` to disk.
    """
    if not OPENPYXL_OK:
        return False
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Report"

        # Brand colours as ARGB-less hex for openpyxl fills/fonts.
        RED   = "E11D48"
        DARK  = "0B1220"
        GRAY  = "374151"
        LIGHT = "F9FAFB"
        WHITE = "FFFFFF"

        def _fill(hex_color):
            # Solid cell fill shorthand.
            return PatternFill("solid", fgColor=hex_color)

        def _border():
            # Thin uniform border on all four sides.
            s = Side(style="thin", color="E5E7EB")
            return Border(left=s, right=s, top=s, bottom=s)

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 10
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 14

        # `row` is a running write cursor advanced as each block is written.
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
            # Excel sheet names max out at 31 chars and cannot contain "/".
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
    """Coerce a money value (number or "₱1,234.50" string) to float, defaulting
    to 0.0 for None or unparseable input. Module-level twin of the nested `_val`
    used in export_receipt_pdf."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("₱", "").replace(",", "").strip()  # drop currency/grouping
    try:
        return float(s)
    except ValueError:
        return 0.0


def _record_in_month(rec: dict, date_key: str, year: int, month: int) -> bool:
    """True if rec[date_key] falls within the given (year, month). Handles
    date/datetime objects and common string formats used across the app.

    Params:
        rec: a record dict.
        date_key: which field holds the date.
        year, month: the target month.
    Returns:
        True if the record's date is in that month; False if missing or if it
        cannot be interpreted at all.
    """
    raw = rec.get(date_key)
    if not raw:
        return False
    # Native date/datetime: compare components directly.
    if isinstance(raw, (_dt_date, _dt_datetime)):
        return raw.year == year and raw.month == month
    s = str(raw).strip()
    # Try each known stored date layout.
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"):
        try:
            d = _dt_datetime.strptime(s, fmt)
            return d.year == year and d.month == month
        except ValueError:
            continue
    # Last resort: ISO "YYYY-MM" prefix match for otherwise-unparsed strings.
    return s.startswith(f"{year:04d}-{month:02d}")


def _filter_by_month(records: list, date_key: str, year: int, month: int) -> list:
    """Filter records to a single (year, month) by their `date_key` column.

    When year or month is falsy, no filtering is applied (returns records
    unchanged) — this is how "all time" / date-less entities pass through.
    """
    if not year or not month:
        return records
    return [r for r in records if _record_in_month(r, date_key, year, month)]


def export_custom_entity_data(entity_name: str, is_excel: bool, save_path: str,
                              year: int = None, month: int = None) -> bool:
    """Export Bookings, Customers, Expenses, Menu, Billings, or Master Data to Excel or CSV.

    When year and month are given, only records whose relevant date column falls
    in that month are included (bookings/invoices by event date, expenses/cash
    flow by their own date). Customers and Menu Items have no date to filter by
    and are always exported in full.

    Params:
        entity_name: free-text entity selector ("bookings", "customers",
            "expenses", "menu", "packages", "billing", "cash flow", or anything
            else -> full master export).
        is_excel: True -> multi-sheet .xlsx; False -> single-sheet CSV.
        save_path: output file path.
        year, month: optional month filter (see _filter_by_month).
    Returns:
        True on success; False on write failure or missing openpyxl (Excel).
    Side effects: writes `save_path`.
    """
    import utils.repository as repo  # local import avoids import cycle
    import csv

    headers = []
    rows = []
    sheets = {}  # {sheet_title: (headers, rows)} — CSV uses only the first entry
    ent_lower = str(entity_name or "").lower().strip()  # normalised selector

    # Dispatch on keywords in the entity name. Each branch populates `sheets`
    # (and, for single-entity exports, `headers`/`rows`) from the repository.
    if "booking" in ent_lower or "order" in ent_lower:
        headers = ["Booking Ref", "Customer Name", "Contact Number", "Email Address", "Address", "Occasion", "Venue / Location", "Event Date", "Event Time", "Guest Count (Pax)", "Total Amount (₱)", "Down Paid (₱)", "Balance (₱)", "Status", "Payment Mode", "Special Notes / Theme"]
        b_list = _filter_by_month(repo.get_all_bookings_for_export() or [], "event_date", year, month)
        for b in b_list:
            try:
                # Compute balance = total - paid (floored at 0) per booking.
                tot = _parse_amount(b.get('total') or b.get('total_amount') or 0)
                paid = _parse_amount(b.get('amount_paid') or b.get('down_payment') or 0)
                bal = max(0.0, tot - paid)
                rows.append([
                    b.get("id") or b.get("booking_ref") or "",
                    b.get("name") or b.get("customer_name") or "",
                    b.get("contact") or b.get("phone") or "",
                    b.get("email") or "",
                    b.get("address") or b.get("imported_address") or "",
                    b.get("occasion") or "",
                    b.get("venue") or "",
                    b.get("date") or b.get("event_date") or "",
                    _format_time_ampm(b.get("time") or b.get("event_time") or ""),
                    str(b.get("pax") or 0),
                    f"₱{tot:,.2f}",
                    f"₱{paid:,.2f}",
                    f"₱{bal:,.2f}",
                    str(b.get("status") or "PENDING").upper(),
                    b.get("payment_mode") or "Cash",
                    b.get("notes") or ""
                ])
            except Exception as row_exc:
                # A single malformed booking is skipped, not fatal to the export.
                print(f"[exporter] Bookings row error (skipping): {row_exc}")
        sheets["Bookings"] = (headers, rows)

    elif "customer" in ent_lower or "client" in ent_lower:
        headers = ["Customer ID", "Customer Name", "Contact Number", "Email Address", "Address", "Status", "Notes / History"]
        c_list = repo.get_all_customers() or []
        for c in c_list:
            rows.append([
                c.get("id", ""), c.get("name", ""), c.get("contact", ""),
                c.get("email", ""), c.get("address", "") or c.get("imported_address", ""),
                c.get("status", "Active"),
                c.get("notes", "")
            ])
        sheets["Customers"] = (headers, rows)

    elif "expense" in ent_lower or "cost" in ent_lower:
        headers = ["Expense ID", "Expense Date", "Category", "Description", "Amount (₱)", "Notes / Remarks"]
        e_list = _filter_by_month(repo.get_all_expenses() or [], "date", year, month)
        for e in e_list:
            rows.append([
                e.get("id", ""), e.get("date", ""), e.get("category", ""),
                e.get("description", ""), f"₱{_parse_amount(e.get('amount', 0)):,.2f}",
                e.get("notes", "")
            ])
        sheets["Expenses"] = (headers, rows)

    # Order matters below: the "package-only" and "menu-only" branches are
    # checked before the combined "menu or package" branch so a request naming
    # just one entity doesn't accidentally pull both.
    elif "package" in ent_lower and "menu" not in ent_lower:
        p_hdrs = ["Package ID", "Package Name", "Price Per Pax (₱)", "Minimum Pax", "Description / Inclusions"]
        p_rows = []
        for p in (repo.get_all_packages() or []):
            p_rows.append([
                p.get("id", ""), p.get("name", ""),
                f"₱{_parse_amount(p.get('price_per_pax', 0)):,.2f}",
                str(p.get("min_pax", 1)),
                p.get("description", "")
            ])
        sheets["Catering Packages"] = (p_hdrs, p_rows)
        headers = p_hdrs
        rows = p_rows

    elif "menu" in ent_lower and "package" not in ent_lower:
        m_hdrs = ["Item ID", "Item Name", "Category", "Package Tier", "Price / Rate (₱)", "Status", "Description / Inclusions"]
        m_rows = []
        for m in (repo.get_all_menu_items() or []):
            m_rows.append([
                m.get("id", ""), m.get("name", "") or m.get("item", ""), m.get("category", ""),
                m.get("package", "Standard"),
                f"₱{_parse_amount(m.get('price', 0)):,.2f}",
                m.get("status", "Available"),
                m.get("description", "")
            ])
        sheets["Menu Items"] = (m_hdrs, m_rows)
        headers = m_hdrs
        rows = m_rows

    elif "menu" in ent_lower or "package" in ent_lower:
        m_hdrs = ["Item ID", "Item Name", "Category", "Package Tier", "Price / Rate (₱)", "Status", "Description / Inclusions"]
        m_rows = []
        for m in (repo.get_all_menu_items() or []):
            m_rows.append([
                m.get("id", ""), m.get("name", "") or m.get("item", ""), m.get("category", ""),
                m.get("package", "Standard"),
                f"₱{_parse_amount(m.get('price', 0)):,.2f}",
                m.get("status", "Available"),
                m.get("description", "")
            ])
        sheets["Menu Items"] = (m_hdrs, m_rows)

        p_hdrs = ["Package ID", "Package Name", "Price Per Pax (₱)", "Minimum Pax", "Description / Inclusions"]
        p_rows = []
        for p in (repo.get_all_packages() or []):
            p_rows.append([
                p.get("id", ""), p.get("name", ""),
                f"₱{_parse_amount(p.get('price_per_pax', 0)):,.2f}",
                str(p.get("min_pax", 1)),
                p.get("description", "")
            ])
        sheets["Catering Packages"] = (p_hdrs, p_rows)
        headers = m_hdrs
        rows = m_rows

    elif "billing" in ent_lower or "invoice" in ent_lower:
        headers = ["Invoice Ref", "Booking Ref", "Customer Name", "Contact Number", "Email Address", "Event Date", "Total Amount (₱)", "Paid Amount (₱)", "Balance Due (₱)", "Payment Status", "Payment Mode", "Notes / Remarks"]
        i_list = _filter_by_month(repo.get_all_invoices() or [], "event_date", year, month)
        for inv in i_list:
            rows.append([
                inv.get("invoice", ""), inv.get("booking_ref", ""), inv.get("customer", ""),
                inv.get("contact", "") or inv.get("phone", ""),
                inv.get("email", "") or inv.get("customer_email", ""),
                inv.get("event_date", ""),
                f"₱{_parse_amount(inv.get('amount', 0)):,.2f}",
                f"₱{_parse_amount(inv.get('paid', 0)):,.2f}",
                f"₱{_parse_amount(inv.get('balance', 0)):,.2f}",
                inv.get("status", ""),
                inv.get("payment_mode", "Cash"),
                inv.get("notes", "")
            ])
        sheets["Billing & Invoices"] = (headers, rows)

    elif "cash" in ent_lower or "flow" in ent_lower:
        headers = ["Transaction ID", "Date", "Check #", "Particulars (Account / Detail)", "Deposit (₱)", "Withdrawal (₱)", "Running Balance (₱)", "Actual Sales (₱)", "Variance / Difference (₱)", "Remarks / Notes"]
        tx_list = _filter_by_month(repo.get_cash_flow_transactions() or [], "date", year, month)
        for tx in tx_list:
            dep = float(tx.get("deposit") or 0.0)
            withd = float(tx.get("withdrawal") or 0.0)
            bal = float(tx.get("balance") or 0.0)
            act_sales = float(tx.get("actual_sales") or 0.0)
            # Variance = running balance minus actual sales; negatives shown in
            # accounting parentheses.
            diff = bal - act_sales
            diff_str = f"₱{diff:,.2f}" if diff >= 0 else f"(₱{abs(diff):,.2f})"
            rows.append([
                str(tx.get("id", "") or tx.get("cft_id", "")),
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

    else: # Master Export (All System Data) — builds every sheet at once.
        b_hdrs = ["Booking Ref", "Customer Name", "Contact Number", "Email Address", "Address", "Occasion", "Venue / Location", "Event Date", "Event Time", "Guest Count (Pax)", "Total Amount (₱)", "Down Paid (₱)", "Balance (₱)", "Status", "Payment Mode", "Special Notes / Theme"]
        b_rows = []
        for b in _filter_by_month(repo.get_all_bookings_for_export() or [], "event_date", year, month):
            try:
                tot = _parse_amount(b.get('total') or b.get('total_amount') or 0)
                paid = _parse_amount(b.get('amount_paid') or b.get('down_payment') or 0)
                bal = max(0.0, tot - paid)
                b_rows.append([
                    b.get("id") or b.get("booking_ref") or "",
                    b.get("name") or b.get("customer_name") or "",
                    b.get("contact") or b.get("phone") or "",
                    b.get("email") or "",
                    b.get("address") or b.get("imported_address") or "",
                    b.get("occasion") or "",
                    b.get("venue") or "",
                    b.get("date") or b.get("event_date") or "",
                    _format_time_ampm(b.get("time") or b.get("event_time") or ""),
                    str(b.get("pax") or 0),
                    f"₱{tot:,.2f}",
                    f"₱{paid:,.2f}",
                    f"₱{bal:,.2f}",
                    str(b.get("status") or "PENDING").upper(),
                    b.get("payment_mode") or "Cash",
                    b.get("notes") or ""
                ])
            except Exception as row_exc:
                print(f"[exporter] Master Bookings row error (skipping): {row_exc}")
        sheets["Bookings"] = (b_hdrs, b_rows)

        c_hdrs = ["Customer ID", "Customer Name", "Contact Number", "Email Address", "Address", "Status", "Notes / History"]
        c_rows = [[c.get("id", ""), c.get("name", ""), c.get("contact", ""), c.get("email", ""), c.get("address", "") or c.get("imported_address", ""), c.get("status", "Active"), c.get("notes", "")] for c in (repo.get_all_customers() or [])]
        sheets["Customers"] = (c_hdrs, c_rows)

        e_hdrs = ["Expense ID", "Expense Date", "Category", "Description", "Amount (₱)", "Notes / Remarks"]
        e_rows = [[e.get("id", ""), e.get("date", ""), e.get("category", ""), e.get("description", ""), f"₱{_parse_amount(e.get('amount', 0)):,.2f}", e.get("notes", "")] for e in _filter_by_month(repo.get_all_expenses() or [], "date", year, month)]
        sheets["Expenses"] = (e_hdrs, e_rows)

        m_hdrs = ["Item ID", "Item Name", "Category", "Package Tier", "Price / Rate (₱)", "Status", "Description / Inclusions"]
        m_rows = [[m.get("id", ""), m.get("name", "") or m.get("item", ""), m.get("category", ""), m.get("package", "Standard"), f"₱{_parse_amount(m.get('price', 0)):,.2f}", m.get("status", "Available"), m.get("description", "")] for m in (repo.get_all_menu_items() or [])]
        sheets["Menu Items"] = (m_hdrs, m_rows)

        p_hdrs = ["Package ID", "Package Name", "Price Per Pax (₱)", "Minimum Pax", "Description / Inclusions"]
        p_rows = [[p.get("id", ""), p.get("name", ""), f"₱{_parse_amount(p.get('price_per_pax', 0)):,.2f}", str(p.get("min_pax", 1)), p.get("description", "")] for p in (repo.get_all_packages() or [])]
        sheets["Catering Packages"] = (p_hdrs, p_rows)

        cf_hdrs = ["Transaction ID", "Date", "Check #", "Particulars (Account / Detail)", "Deposit (₱)", "Withdrawal (₱)", "Running Balance (₱)", "Actual Sales (₱)", "Variance / Difference (₱)", "Remarks / Notes"]
        cf_rows = [[
            str(tx.get("id", "") or tx.get("cft_id", "")),
            str(tx.get("date", "")),
            str(tx.get("check_no", "")),
            str(tx.get("particulars", "")),
            f"₱{float(tx.get('deposit') or 0.0):,.2f}" if float(tx.get('deposit') or 0.0) > 0 else "—",
            f"₱{float(tx.get('withdrawal') or 0.0):,.2f}" if float(tx.get('withdrawal') or 0.0) > 0 else "—",
            f"₱{float(tx.get('balance') or 0.0):,.2f}" if float(tx.get('balance') or 0.0) >= 0 else f"(₱{abs(float(tx.get('balance') or 0.0)):,.2f})",
            f"₱{float(tx.get('actual_sales') or 0.0):,.2f}" if float(tx.get('actual_sales') or 0.0) > 0 else "—",
            f"₱{(float(tx.get('balance') or 0.0) - float(tx.get('actual_sales') or 0.0)):,.2f}" if float(tx.get('actual_sales') or 0.0) > 0 and (float(tx.get('balance') or 0.0) - float(tx.get('actual_sales') or 0.0)) >= 0 else (f"(₱{abs(float(tx.get('balance') or 0.0) - float(tx.get('actual_sales') or 0.0)):,.2f})" if float(tx.get('actual_sales') or 0.0) > 0 else "—"),
            str(tx.get("notes", ""))
        ] for tx in _filter_by_month(repo.get_cash_flow_transactions() or [], "date", year, month)]
        sheets["Cash Flow Ledger"] = (cf_hdrs, cf_rows)

        i_hdrs = ["Invoice Ref", "Booking Ref", "Customer Name", "Contact Number", "Email Address", "Event Date", "Total Amount (₱)", "Paid Amount (₱)", "Balance Due (₱)", "Payment Status", "Payment Mode", "Notes / Remarks"]
        i_rows = [[inv.get("invoice", ""), inv.get("booking_ref", ""), inv.get("customer", ""), inv.get("contact", "") or inv.get("phone", ""), inv.get("email", "") or inv.get("customer_email", ""), inv.get("event_date", ""), f"₱{_parse_amount(inv.get('amount', 0)):,.2f}", f"₱{_parse_amount(inv.get('paid', 0)):,.2f}", f"₱{_parse_amount(inv.get('balance', 0)):,.2f}", inv.get("status", ""), inv.get("payment_mode", "Cash"), inv.get("notes", "")] for inv in _filter_by_month(repo.get_all_invoices() or [], "event_date", year, month)]
        sheets["Billing & Invoices"] = (i_hdrs, i_rows)

    # ── CSV path: flat file, single table only (the first/primary sheet). ──
    if not is_excel:
        try:
            # utf-8-sig writes a BOM so Excel opens the ₱ symbol correctly.
            with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                first_sheet = next(iter(sheets.values()))  # (headers, rows)
                writer.writerow(first_sheet[0])
                writer.writerows(first_sheet[1])
            return True
        except Exception as exc:
            print(f"[exporter] CSV export failed: {exc}")
            return False

    # ── Excel path: one styled worksheet per entry in `sheets`. ──
    if not OPENPYXL_OK:
        return False

    try:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # drop the default sheet; we create our own named ones

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
                # Booking/Invoice sheets get the red header; everything else dark.
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
                    # Right-align monetary/amount columns, left-align the rest.
                    align_right = ("₱" in str(val) or "Amount" in hdrs[col_idx-1] or "Paid" in hdrs[col_idx-1])
                    cell.alignment = Alignment(horizontal="right" if align_right else "left", vertical="center")

            # Auto-size each column to its widest cell (min width 14).
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        wb.save(save_path)
        return True
    except Exception as exc:
        print(f"[exporter] Excel export failed: {exc}")
        return False


def _format_time_short(t_raw) -> str:
    """Format time string compactly for calendar day cells: e.g. 5:00 PM -> 5PM, 11:30 AM -> 11:30AM."""
    if not t_raw:
        return ""
    from datetime import datetime as _dt
    if hasattr(t_raw, "strftime"):
        s = t_raw.strftime("%I:%M %p").lstrip("0")
    else:
        s = str(t_raw).strip()
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"):
            try:
                parsed = _dt.strptime(s, fmt).time()
                s = parsed.strftime("%I:%M %p").lstrip("0")
                break
            except ValueError:
                continue
    # Replace :00 AM/PM with AM/PM (e.g. 5:00 PM -> 5PM, but keep 5:30 PM -> 5:30PM)
    s = s.replace(":00 ", " ").replace(" ", "").upper()
    return s


def _fit_string(c, text: str, font_name: str, font_size: float, max_w: float) -> str:
    """Safely truncate string with ellipsis if it exceeds max_w in ReportLab.

    Params:
        c: the ReportLab Canvas (its stringWidth measures the font metrics).
        text: input string.
        font_name, font_size: font used for measuring.
        max_w: maximum allowed width in points.
    Returns:
        `text` unchanged if it fits, else a trimmed prefix + "…" that fits.
    """
    if not text:
        return ""
    if c.stringWidth(text, font_name, font_size) <= max_w:
        return text
    # Drop one trailing char at a time until "text…" fits (keep >3 chars).
    while len(text) > 3 and c.stringWidth(text + "…", font_name, font_size) > max_w:
        text = text[:-1]
    return text + "…"


# ─── shared helper: draw one landscape wall-calendar page onto a Canvas ──────
def _draw_calendar_page(c, LS_W, LS_H, year, month, month_events,
                        biz_name, MX, MY, colors_ns):
    """Draw a single landscape wall-calendar month page onto canvas `c`.
    `c` must already be in the correct page; caller is responsible for
    calling c.showPage() afterwards.
    `colors_ns` is the reportlab `colors` module (passed in to avoid
    re-importing inside the helper).

    Params:
        c: ReportLab Canvas positioned on a fresh landscape page.
        LS_W, LS_H: landscape page width/height in points.
        year, month: the month to render.
        month_events: {day:int -> [event_dict, ...]} for that month.
        biz_name: business name for the footer.
        MX, MY: page x/y margins in points.
        colors_ns: the reportlab colors module (dependency-injected).
    This is a low-level canvas draw — it uses absolute coordinates rather than
    the Platypus flow model used elsewhere in this file.
    """
    import calendar as _cal
    from datetime import datetime
    from reportlab.lib.units import mm
    colors = colors_ns  # alias so the rest of the body reads like module code

    month_name = _cal.month_name[month]

    # Colour palette
    _C_GR_BG  = colors.HexColor("#DCFCE7")
    _C_GR_TXT = colors.HexColor("#15803D")
    _C_AM_BG  = colors.HexColor("#FEF3C7")
    _C_AM_TXT = colors.HexColor("#B45309")
    _C_RD_BG  = colors.HexColor("#FEE2E2")
    _C_RD_TXT = colors.HexColor("#B91C1C")
    _C_NAV    = colors.HexColor("#0F172A")
    _C_DAY_H  = colors.HexColor("#1E293B")
    _C_CELL_B = colors.HexColor("#CBD5E1")
    _C_EMPTY  = colors.HexColor("#F8FAFC")
    _C_TODAY  = colors.HexColor("#EFF6FF")
    _C_MUTED  = colors.HexColor("#6B7280")

    draw_w = LS_W - 2 * MX

    # KPI pre-calc: flatten to (day, event) pairs, then tally pax/events/days.
    all_evs   = [(d, ev) for d, evl in (month_events or {}).items() for ev in (evl or [])]
    total_pax = sum(int(ev.get("pax", 0) or 0) for _, ev in all_evs)
    total_evs = len(all_evs)
    active_d  = len([d for d, evl in (month_events or {}).items() if evl])  # days with >=1 event

    # ── Title bar (clean, unshaded, printer-friendly) ──────────────────────
    TITLE_H = 50
    title_y  = LS_H - MY - TITLE_H

    c.setFillColor(colors.white)
    c.setStrokeColor(_C_CELL_B)
    c.setLineWidth(0.8)
    c.roundRect(MX, title_y, draw_w, TITLE_H, 6, fill=1, stroke=1)

    _lp = _logo_path()
    LOGO_S = 34
    if os.path.exists(_lp):
        try:
            c.drawImage(_lp, MX + 10, title_y + (TITLE_H - LOGO_S) / 2,
                        width=LOGO_S, height=LOGO_S,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(LS_W / 2, title_y + TITLE_H / 2 - 8,
                        f"{month_name.upper()}  {year}")

    kpi_items = [("EVENTS", str(total_evs)),
                 ("PAX",    f"{total_pax:,}"),
                 ("DAYS",   str(active_d))]
    BW, BH, BG = 64, 30, 6
    kx = MX + draw_w - len(kpi_items) * (BW + BG) - 8
    for lbl, val in kpi_items:
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.setLineWidth(0.6)
        c.roundRect(kx, title_y + (TITLE_H - BH) / 2, BW, BH, 4, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(kx + BW / 2, title_y + (TITLE_H + BH) / 2 - 8, lbl)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(kx + BW / 2, title_y + (TITLE_H - BH) / 2 + 5, val)
        kx += BW + BG

    # ── Weekday headers (clean light background, printer-friendly) ─────────
    WDAY_H   = 24
    wday_y   = title_y - WDAY_H
    col_w    = draw_w / 7
    DAYS_FULL = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY",
                 "THURSDAY", "FRIDAY", "SATURDAY"]
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(_C_CELL_B)
    c.setLineWidth(0.5)
    c.rect(MX, wday_y, draw_w, WDAY_H, fill=1, stroke=1)
    for i, dn in enumerate(DAYS_FULL):
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(MX + col_w * i + col_w / 2, wday_y + WDAY_H / 2 - 3.5, dn)
        if i > 0:
            c.setStrokeColor(_C_CELL_B)
            c.setLineWidth(0.5)
            c.line(MX + col_w * i, wday_y, MX + col_w * i, wday_y + WDAY_H)

    # ── Day cells ──────────────────────────────────────────────────────────
    _cal.setfirstweekday(_cal.SUNDAY)  # week starts Sunday to match the headers
    month_matrix = _cal.monthcalendar(year, month)  # weeks x 7, 0 == padding day
    n_rows  = len(month_matrix)
    avail_h = wday_y - MY - 14          # vertical space left for the grid
    cell_h  = avail_h / n_rows          # equal-height rows
    today_dt = datetime.now().date()    # to highlight "today" if in this month

    for r_idx, week in enumerate(month_matrix):
        row_bot = wday_y - (r_idx + 1) * cell_h

        for c_idx, day in enumerate(week):
            cx = MX + c_idx * col_w
            cy = row_bot

            # day == 0 marks a leading/trailing padding cell (blank grey box).
            if day == 0:
                c.setFillColor(_C_EMPTY)
                c.setStrokeColor(_C_CELL_B)
                c.setLineWidth(0.5)
                c.rect(cx, cy, col_w, cell_h, fill=1, stroke=1)
                continue

            is_today = (today_dt.year == year and
                        today_dt.month == month and
                        today_dt.day == day)

            c.setFillColor(_C_TODAY if is_today else colors.white)
            c.setStrokeColor(_C_CELL_B)
            c.setLineWidth(0.5)
            c.rect(cx, cy, col_w, cell_h, fill=1, stroke=1)

            day_fs = max(10, min(14, cell_h * 0.17))
            c.setFillColor(colors.HexColor("#1D4ED8") if is_today else _C_NAV)
            c.setFont("Helvetica-Bold", day_fs)
            c.drawString(cx + 4, cy + cell_h - day_fs - 3, str(day))
            if is_today:
                c.setFillColor(colors.HexColor("#1D4ED8"))
                c.setFont("Helvetica-Bold", 5.5)
                c.drawString(cx + 4 + day_fs + 3, cy + cell_h - 8, "TODAY")

            day_evs = (month_events or {}).get(day, [])
            if day_evs:
                d_count = len(day_evs)
                d_pax   = sum(int(e.get("pax", 0) or 0) for e in day_evs)

                top_space_y = cy + cell_h - day_fs - 5
                bot_space_y = cy + 2
                avail_h_box = top_space_y - bot_space_y
                bw = col_w - 6
                bx = cx + 3

                # Visual palette per event row (distinct colored accent borders)
                accent_colors = [
                    (colors.HexColor("#F1F5F9"), colors.HexColor("#2563EB"), colors.HexColor("#1E3A8A")),  # Slate/Blue
                    (colors.HexColor("#FFFBEB"), colors.HexColor("#D97706"), colors.HexColor("#92400E")),  # Amber
                    (colors.HexColor("#F0FDF4"), colors.HexColor("#16A34A"), colors.HexColor("#14532D")),  # Emerald
                    (colors.HexColor("#FAF5FF"), colors.HexColor("#9333EA"), colors.HexColor("#581C87")),  # Purple
                    (colors.HexColor("#FFF1F2"), colors.HexColor("#E11D48"), colors.HexColor("#881337")),  # Rose
                    (colors.HexColor("#F0FDFA"), colors.HexColor("#0D9488"), colors.HexColor("#115E59")),  # Teal
                    (colors.HexColor("#FEF2F2"), colors.HexColor("#DC2626"), colors.HexColor("#991B1B")),  # Red
                ]

                # Event-chip sizing is adaptive: the more events a day holds (N),
                # the smaller each chip's height/fonts and — past a threshold —
                # the layout collapses from two lines (title + pax) to one.
                N = d_count
                if N == 1:
                    gap = 0.0
                    bh = min(avail_h_box, 30.0)
                    fs_t, fs_p = 7.2, 6.8
                    two_lines = True
                elif N == 2:
                    gap = 2.5
                    bh = min(26.0, (avail_h_box - gap) / 2)
                    fs_t, fs_p = 6.8, 6.2
                    two_lines = True
                elif N == 3:
                    gap = 1.8
                    bh = (avail_h_box - 2 * gap) / 3
                    fs_t, fs_p = 5.8, 5.2
                    two_lines = True
                elif N == 4:
                    gap = 1.2
                    bh = (avail_h_box - 3 * gap) / 4
                    fs_t, fs_p = 5.0, 4.6
                    two_lines = True
                elif N == 5:
                    gap = 1.0
                    bh = (avail_h_box - 4 * gap) / 5
                    fs_t, fs_p = 4.8, 4.4
                    two_lines = (bh >= 13.0)
                else: # N >= 6
                    gap = 0.8
                    bh = (avail_h_box - (N - 1) * gap) / N
                    fs_t = max(4.0, min(4.8, bh * 0.55))
                    fs_p = max(3.8, fs_t * 0.9)
                    two_lines = False

                for i, ev in enumerate(day_evs):
                    by = top_space_y - (i + 1) * bh - i * gap
                    occ = str(ev.get("occasion") or ev.get("name") or ev.get("customer_name") or "EVENT").strip().upper()
                    t_short = _format_time_short(ev.get("time") or ev.get("event_time"))
                    pax = int(ev.get("pax", 0) or 0)
                    header_txt = f"{occ} {t_short}".strip()
                    pax_txt = f"{pax:,} PAX"

                    # Chip colour: use the event's own theme hex when valid,
                    # deriving a pale tint for the background; otherwise cycle
                    # through the preset accent palette by row index.
                    col_hex = str(ev.get("color_theme") or ev.get("color") or "").strip()
                    if col_hex and col_hex.startswith("#"):
                        try:
                            bar_c = colors.HexColor(col_hex)
                            c_r, c_g, c_b = bar_c.red, bar_c.green, bar_c.blue
                            # Blend heavily toward white (0.93 base) for a soft fill.
                            bg_c = colors.Color(0.93 + 0.07 * c_r, 0.93 + 0.07 * c_g, 0.93 + 0.07 * c_b)
                            txt_c = bar_c
                        except Exception:
                            bg_c, bar_c, txt_c = accent_colors[i % len(accent_colors)]
                    else:
                        bg_c, bar_c, txt_c = accent_colors[i % len(accent_colors)]

                    stripe = 2.2 if N <= 3 else 1.8

                    c.setFillColor(bg_c)
                    c.roundRect(bx, by, bw, bh, 2.0, fill=1, stroke=0)
                    c.setFillColor(bar_c)
                    c.roundRect(bx, by, stripe, bh, 1.0, fill=1, stroke=0)

                    if two_lines:
                        c.setFillColor(colors.HexColor("#0F172A"))
                        c.setFont("Helvetica-Bold", fs_t)
                        fit_h = _fit_string(c, header_txt, "Helvetica-Bold", fs_t, bw - stripe - 5)
                        c.drawString(bx + stripe + 3, by + bh - fs_t - 2.0, fit_h)

                        c.setFillColor(txt_c)
                        c.setFont("Helvetica-Bold", fs_p)
                        fit_p = _fit_string(c, pax_txt, "Helvetica-Bold", fs_p, bw - stripe - 5)
                        c.drawString(bx + stripe + 3, by + 1.8, fit_p)
                    else:
                        line_txt = f"{header_txt} · {pax}p"
                        c.setFillColor(colors.HexColor("#0F172A"))
                        c.setFont("Helvetica-Bold", fs_t)
                        fit_l = _fit_string(c, line_txt, "Helvetica-Bold", fs_t, bw - stripe - 4)
                        c.drawString(bx + stripe + 3, by + (bh - fs_t) / 2, fit_l)

    # ── Legend ─────────────────────────────────────────────────────────────
    # Capacity legend drawn along the bottom; lx advances past each swatch+label.
    leg_y = MY + 1
    leg_items = [
        (_C_GR_BG, _C_GR_TXT, "Available (< 400 pax)"),
        (_C_AM_BG, _C_AM_TXT, "Near Full (400–599 pax)"),
        (_C_RD_BG, _C_RD_TXT, "Fully Booked (600+ pax)"),
    ]
    lx = MX
    for bg_c, tc, lbl in leg_items:
        BOX = 9
        c.setFillColor(bg_c)
        c.roundRect(lx, leg_y, BOX, BOX, 2, fill=1, stroke=0)
        c.setFillColor(tc)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(lx + BOX + 3, leg_y + 2, lbl)
        lx += BOX + 3 + c.stringWidth(lbl, "Helvetica-Bold", 6.5) + 18

    now_str = datetime.now().strftime("%b %d, %Y  %I:%M %p")
    c.setFillColor(_C_MUTED)
    c.setFont("Helvetica", 6)
    c.drawRightString(MX + draw_w, leg_y + 2,
                      f"Generated: {now_str}  •  {biz_name}")


# ─── shared helper: build agenda story for one month ─────────────────────────
def _build_agenda_story(year, month, month_events, styles, biz_name):
    """Return a ReportLab Platypus story list for one month's agenda page(s).

    Platypus (flowable) version of the month agenda — an itemised, paginating
    table of every event. (The canvas version is _draw_agenda_canvas_pages.)

    Params:
        year, month: the month to render.
        month_events: {day -> [event_dict, ...]}.
        styles: stylesheet from _styles().
        biz_name: business name for header/footer.
    Returns:
        A list of flowables ready to feed to doc.build().
    """
    import calendar as _cal
    month_name = _cal.month_name[month]

    story = []
    _header_block(story, styles, biz_name,
                  f"Booking Agenda — {month_name} {year}",
                  period=f"{month_name} {year}")
    story.append(Paragraph("Itemized Event Agenda", styles["SectionHead"]))

    # Flatten to chronological (day, event) pairs (sorted by day).
    all_events = [(d, ev)
                  for d, evl in sorted((month_events or {}).items())
                  for ev in (evl or [])]

    agenda_hdrs = ["Date & Time", "Ref / Occasion", "Customer & Menu", "Venue", "Pax", "Theme / Notes", "Status"]
    agenda_w    = [2.6*cm, 2.6*cm, 4.4*cm, 3.8*cm, 1.4*cm, 3.2*cm, 2.0*cm]
    agenda_rows = [[Paragraph(h, styles["TableHead"]) for h in agenda_hdrs]]

    sstyles = {
        "CONFIRMED": styles["StatusPaid"],
        "COMPLETED": styles["StatusPaid"],
        "PENDING":   styles["StatusPartial"],
        "CANCELLED": styles["StatusUnpaid"],
    }

    if not all_events:
        agenda_rows.append([
            Paragraph("No events scheduled for this month.", styles["TableCellCenter"]),
            "", "", "", "", "", ""
        ])
    else:
        for day, ev in all_events:
            time_str = _format_time_ampm(ev.get("time") or ev.get("event_time") or "6:00 PM") or "6:00 PM"
            st_key   = str(ev.get("status") or "CONFIRMED").upper()
            c_name   = ev.get("customer_name") or ev.get("name") or "Valued Client"
            occ      = ev.get("occasion") or "Event"
            menu_txt = ev.get("menu") or ev.get("package_name") or "Standard Menu"
            theme_notes = str(ev.get("notes") or ev.get("theme") or ev.get("description_theme") or ev.get("description") or "Standard Setup").strip()
            if not theme_notes:
                theme_notes = "Standard Setup"

            agenda_rows.append([
                Paragraph(
                    f"<b>{month_name[:3]} {day}, {year}</b><br/>"
                    f"<font color='#6B7280' size=7>{time_str}</font>",
                    styles["TableCell"]),
                Paragraph(
                    f"<font color='#E11D48'><b>{ev.get('ref') or '—'}</b></font><br/>"
                    f"<font color='#4B5563' size=7>{occ}</font>",
                    styles["TableCell"]),
                Paragraph(
                    f"<b>{c_name}</b><br/>"
                    f"<font color='#6B7280' size=7>{menu_txt}</font>",
                    styles["TableCell"]),
                Paragraph(str(ev.get("venue") or ev.get("location") or "—"), styles["TableCell"]),
                Paragraph(str(ev.get("pax", 0)), styles["TableCellCenter"]),
                Paragraph(f"<font color='#374151'>{theme_notes}</font>", styles["TableCell"]),
                Paragraph(str(st_key).capitalize(),
                          sstyles.get(st_key, styles["TableCellCenter"])),
            ])

    tbl = Table(agenda_rows, colWidths=agenda_w, repeatRows=1)
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
    return story


def _draw_agenda_canvas_pages(c, year, month, month_events, biz_name, styles):
    """Draw one or more LANDSCAPE A4 agenda pages onto canvas `c` with full booking details.

    Low-level canvas equivalent of _build_agenda_story, used by the multi-month
    calendar export so calendar and agenda share a single Canvas (no PDF merge
    needed). Handles its own pagination and column truncation.

    Params:
        c: ReportLab Canvas.
        year, month: month to render.
        month_events: {day -> [event_dict, ...]}.
        biz_name: business name for header/footer.
        styles: stylesheet (accepted for signature symmetry).
    Side effects: draws pages on `c`, ending each with c.showPage().
    """
    import calendar as _cal
    from datetime import datetime
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import cm, mm

    LS = landscape(A4)
    PW, PH = LS          # 841.89 x 595.28
    MX = 16 * mm         # matches calendar page margins
    MY = 12 * mm
    CW = PW - 2 * MX     # content width

    # Colour aliases
    C_DARK   = _C_DARK
    C_MUTED  = _C_MUTED
    C_BORDER = _C_BORDER
    C_LIGHT  = _C_LIGHT
    C_GREEN  = _C_GREEN
    C_AMBER  = _C_AMBER
    C_RED    = _C_RED
    C_WHITE  = _C_WHITE

    month_name = _cal.month_name[month]
    now_str    = datetime.now().strftime("%b %d, %Y  %I:%M %p")

    all_events = [
        (d, ev)
        for d, evl in sorted((month_events or {}).items())
        for ev in (evl or [])
    ]

    # ── Column layout (landscape, 7 columns) ─────────────────────────────
    COL_X = [
        MX + 4,          # 0: Date & Time (84pt)
        MX + 92,         # 1: Ref & Occasion (100pt)
        MX + 196,        # 2: Customer & Menu (165pt)
        MX + 366,        # 3: Venue & Address (145pt)
        MX + 516,        # 4: Pax (40pt)
        MX + 560,        # 5: Description / Theme (115pt)
        MX + 680,        # 6: Status (68pt)
    ]
    COL_HDRS   = ["DATE & TIME", "REF / OCCASION", "CUSTOMER & MENU", "VENUE / ADDRESS", "PAX", "THEME / NOTES", "STATUS"]
    COL_MAXW   = [84, 98, 160, 140, 36, 110, 65]

    HEADER_H   = 50   # title bar height
    COL_HDR_H  = 22   # column-header row height
    ROW_H      = 36   # data row height (2-line layout)
    PAGE_BOT   = MY + 14

    def start_page():
        # Draw the title bar + column headers + footer for a fresh page and
        # return the y-coordinate at which the first data row should start.
        c.setPageSize(LS)

        # Clean white title bar with border
        c.setFillColor(colors.white)
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.8)
        c.roundRect(MX, PH - MY - HEADER_H, CW, HEADER_H, 6, fill=1, stroke=1)

        # Logo
        _lp = _logo_path()
        LOGO_S = 34
        if os.path.exists(_lp):
            try:
                c.drawImage(_lp, MX + 10,
                            PH - MY - HEADER_H + (HEADER_H - LOGO_S) / 2,
                            width=LOGO_S, height=LOGO_S,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                pass

        # Title
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 17)
        c.drawCentredString(PW / 2,
                            PH - MY - HEADER_H / 2 - 6,
                            f"Booking Agenda — {month_name.upper()}  {year}")

        # Biz name right-aligned in header
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawRightString(MX + CW - 10,
                          PH - MY - HEADER_H + (HEADER_H / 2) - 4, biz_name)

        # Column header row
        hdr_y = PH - MY - HEADER_H - COL_HDR_H
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.5)
        c.rect(MX, hdr_y, CW, COL_HDR_H, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica-Bold", 7.5)
        for cx, hdr in zip(COL_X, COL_HDRS):
            c.drawString(cx, hdr_y + 7, hdr)

        # Footer line
        c.setFillColor(C_MUTED)
        c.setFont("Helvetica", 6)
        c.drawCentredString(PW / 2, MY - 2,
                            f"Generated: {now_str}  •  {biz_name}")

        return hdr_y - 1

    def status_color(st):
        # Map a booking status to its text colour for this page.
        st = str(st or "").upper()
        if st in ("CONFIRMED", "COMPLETED"):
            return C_GREEN
        if st == "PENDING":
            return C_AMBER
        if st == "CANCELLED":
            return C_RED
        return C_MUTED

    def trunc(text, font, size, max_w):
        # Local ellipsis-truncation helper (canvas-scoped twin of _fit_string).
        t = str(text or "")
        if c.stringWidth(t, font, size) <= max_w:
            return t
        while t and c.stringWidth(t + "…", font, size) > max_w:
            t = t[:-1]
        return t + "…"

    y       = start_page()  # y descends as rows are drawn top-to-bottom
    row_num = 0             # for zebra striping / reset per page

    if not all_events:
        # Empty-state message centred where the first row would go.
        c.setFillColor(C_MUTED)
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(PW / 2, y - ROW_H,
                            "No events scheduled for this month.")
        c.showPage()
        return

    for day, ev in all_events:
        # Break to a new page when the next row would cross the bottom margin.
        if y - ROW_H < PAGE_BOT:
            c.showPage()
            y = start_page()
            row_num = 0

        # Row background
        c.setFillColor(C_WHITE if row_num % 2 == 0 else C_LIGHT)
        c.rect(MX, y - ROW_H, CW, ROW_H, fill=1, stroke=0)

        # Bottom border
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.3)
        c.line(MX, y - ROW_H, MX + CW, y - ROW_H)

        # ── 0: DATE & TIME ────────────────────────────────────────────────
        c.setFillColor(C_DARK)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(COL_X[0], y - 14, f"{month_name[:3]} {day}, {year}")
        c.setFont("Helvetica", 7)
        c.setFillColor(C_MUTED)
        c.drawString(COL_X[0], y - 26, str(_format_time_ampm(ev.get("time") or ev.get("event_time") or "6:00 PM") or "6:00 PM"))

        # ── 1: REF / OCCASION ─────────────────────────────────────────────
        c.setFillColor(colors.HexColor("#E11D48"))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(COL_X[1], y - 14, trunc(ev.get("ref") or "—", "Helvetica-Bold", 8.5, COL_MAXW[1]))
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#4B5563"))
        c.drawString(COL_X[1], y - 26, trunc(ev.get("occasion") or "Event", "Helvetica", 7, COL_MAXW[1]))

        # ── 2: CUSTOMER & MENU ────────────────────────────────────────────
        c.setFillColor(C_DARK)
        c.setFont("Helvetica-Bold", 8.5)
        c_name = ev.get("customer_name") or ev.get("name") or "Valued Client"
        c.drawString(COL_X[2], y - 14, trunc(c_name, "Helvetica-Bold", 8.5, COL_MAXW[2]))
        c.setFont("Helvetica", 7)
        c.setFillColor(C_MUTED)
        menu_desc = ev.get("menu") or ev.get("package_name") or "Standard Package"
        c.drawString(COL_X[2], y - 26, trunc(menu_desc, "Helvetica", 7, COL_MAXW[2]))

        # ── 3: VENUE / ADDRESS ────────────────────────────────────────────
        venue_str = ev.get("venue") or ev.get("location") or "Client Venue"
        c.setFillColor(C_DARK)
        c.setFont("Helvetica", 8)
        c.drawString(COL_X[3], y - 14, trunc(venue_str, "Helvetica", 8, COL_MAXW[3]))
        addr_str = ev.get("address") or ""
        if addr_str and addr_str != venue_str:
            c.setFont("Helvetica", 6.5)
            c.setFillColor(C_MUTED)
            c.drawString(COL_X[3], y - 26, trunc(addr_str, "Helvetica", 6.5, COL_MAXW[3]))

        # ── 4: PAX ────────────────────────────────────────────────────────
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(C_DARK)
        c.drawCentredString(COL_X[4] + 18, y - 15, str(ev.get("pax") or 0))
        c.setFont("Helvetica", 6.5)
        c.setFillColor(C_MUTED)
        c.drawCentredString(COL_X[4] + 18, y - 26, "guests")

        # ── 5: THEME / NOTES ──────────────────────────────────────────────
        theme_txt = str(ev.get("notes") or ev.get("theme") or ev.get("description_theme") or ev.get("description") or "Standard Setup").strip()
        if not theme_txt:
            theme_txt = "Standard Setup"

        c.setFillColor(C_DARK)
        # Single line if it fits; otherwise greedily wrap words into two lines.
        if c.stringWidth(theme_txt, "Helvetica", 7.5) <= COL_MAXW[5]:
            c.setFont("Helvetica", 7.5)
            c.drawString(COL_X[5], y - 18, theme_txt)
        else:
            words = theme_txt.split()
            line1, line2 = "", ""
            for word in words:
                # Fill line1 until the next word won't fit; overflow goes to line2.
                test_l1 = (line1 + " " + word).strip()
                if c.stringWidth(test_l1, "Helvetica", 7.5) <= COL_MAXW[5]:
                    line1 = test_l1
                else:
                    line2 = (line2 + " " + word).strip()
            if not line1:
                line1 = trunc(theme_txt, "Helvetica", 7.5, COL_MAXW[5])
            c.setFont("Helvetica", 7.5)
            c.drawString(COL_X[5], y - 14, line1)
            if line2:
                c.setFont("Helvetica", 7)
                c.setFillColor(C_MUTED)
                c.drawString(COL_X[5], y - 26, trunc(line2, "Helvetica", 7, COL_MAXW[5]))

        # ── 6: STATUS ─────────────────────────────────────────────────────
        st_key = str(ev.get("status") or "CONFIRMED").upper()
        st_col = status_color(st_key)

        badge_lbl = st_key.capitalize()
        badge_w   = max(56, c.stringWidth(badge_lbl, "Helvetica-Bold", 7.5) + 14)
        badge_x   = COL_X[6]
        badge_y   = y - ROW_H + 9
        badge_h   = 18

        if st_key in ("CONFIRMED", "COMPLETED"):
            pill_bg = colors.HexColor("#DCFCE7")
        elif st_key == "PENDING":
            pill_bg = colors.HexColor("#FEF3C7")
        elif st_key == "CANCELLED":
            pill_bg = colors.HexColor("#FEE2E2")
        else:
            pill_bg = colors.HexColor("#F1F5F9")

        c.setFillColor(pill_bg)
        c.roundRect(badge_x, badge_y, badge_w, badge_h, 4, fill=1, stroke=0)
        c.setFillColor(st_col)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(badge_x + badge_w / 2, badge_y + 5, badge_lbl)

        y -= ROW_H
        row_num += 1

    c.showPage()




def export_calendar_pdf_range(
    save_path: str,
    months: list,               # list of (year, month) tuples
    events_by_month: dict,      # {(year, month): {day: [event_dicts]}}
    biz_name: str = "Jayraldine's Catering",
    include_agenda: bool = True,
    include_empty: bool = False,
) -> bool:
    """Export a multi-month printable wall-calendar PDF.

    Uses a SINGLE ReportLab Canvas with setPageSize() between pages — no
    external PDF merge library (pypdf / PyPDF2) is required.

    Each month gets one landscape A4 calendar page. When *include_agenda*
    is True, landscape A4 agenda pages follow each calendar page.
    When *include_empty* is False, months with zero bookings are skipped.
    """
    if not REPORTLAB_OK:
        return False
    try:
        import calendar as _cal
        from reportlab.lib.pagesizes import landscape
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as _canvas_mod

        LS     = landscape(A4)
        LS_W, LS_H = LS
        MX, MY = 16 * mm, 12 * mm
        styles = _styles()

        # One canvas, one file — pages are appended and page size is switched
        # per page, avoiding any external PDF merge dependency.
        c = _canvas_mod.Canvas(save_path)
        c.setTitle(f"{biz_name} — Calendar Export")
        c.setAuthor(biz_name)

        wrote_any = False  # tracks whether at least one real month was drawn

        for (year, month) in months:
            month_events = events_by_month.get((year, month), {})
            has_bookings = any(bool(v) for v in month_events.values())

            # Skip months with no bookings unless the caller wants empties.
            if not has_bookings and not include_empty:
                continue

            # ── Landscape calendar page ───────────────────────────────────
            c.setPageSize(LS)
            _draw_calendar_page(c, LS_W, LS_H, year, month,
                                month_events, biz_name, MX, MY, colors)
            c.showPage()
            wrote_any = True

            # ── Landscape agenda pages ───────────────────────────────────
            if include_agenda:
                _draw_agenda_canvas_pages(c, year, month, month_events,
                                          biz_name, styles)

        if not wrote_any:
            # Nothing qualified — emit one placeholder page so the file is valid.
            c.setPageSize(LS)
            c.setFont("Helvetica-Bold", 16)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawCentredString(LS_W / 2, LS_H / 2,
                                "No bookings found for the selected date range.")
            c.showPage()

        c.save()
        return True

    except Exception as exc:
        # Full traceback here since calendar layout bugs are otherwise opaque.
        print(f"[exporter] export_calendar_pdf_range failed: {exc}")
        import traceback; traceback.print_exc()
        return False



def export_calendar_pdf(arg1, arg2, arg3, month_events: dict = None,
                        biz_name: str = "Jayraldine's Catering") -> bool:
    """Generate a printable monthly wall-calendar PDF (single month).
    Flexibly supports (save_path, year, month, events) or (year, month, save_path, events).

    Backwards-compatible shim: two historical call conventions exist, so the
    positional args are disambiguated by detecting which one looks like a path.
    Delegates to export_calendar_pdf_range for the actual rendering.
    """
    # Case A: first arg is the path.
    if isinstance(arg1, str) and (arg1.endswith(".pdf") or "/" in arg1 or "\\" in arg1):
        save_path = str(arg1)
        year = int(arg2)
        month = int(arg3)
    # Case B: third arg is the path (legacy (year, month, save_path) order).
    elif isinstance(arg3, str) and (arg3.endswith(".pdf") or "/" in arg3 or "\\" in arg3):
        year = int(arg1)
        month = int(arg2)
        save_path = str(arg3)
    else:
        # Ambiguous: assume the (save_path, year, month) order.
        save_path = str(arg1)
        year = int(arg2)
        month = int(arg3)

    return export_calendar_pdf_range(
        save_path       = save_path,
        months          = [(year, month)],
        events_by_month = {(year, month): month_events or {}},
        biz_name        = biz_name,
        include_agenda  = True,
        include_empty   = True,   # always export even if empty (single-month call)
    )



def export_cash_flow_pdf(save_path: str, transactions: Optional[list] = None,
                         summary: Optional[dict] = None,
                         biz_name: str = "Jayraldine's Catering") -> bool:
    """Generate a clean, high-quality A4 PDF of the Cash Flow Ledger with KPI summary and itemized entries.

    Params:
        save_path: output PDF path.
        transactions: ledger rows; when None they are fetched from the repo.
        summary: summary KPI dict; when None it is fetched from the repo.
        biz_name: business name for header/footer.
    Returns:
        True on success; False if ReportLab is missing or the build raises.
    Side effects: writes `save_path`; may query the repository.
    """
    if not REPORTLAB_OK:
        return False
    try:
        import utils.repository as repo
        # Accept caller-provided data, else pull the full ledger/summary from DB.
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

                # Colour-code the money columns: green deposits, red
                # withdrawals, red-parenthesised negatives. "—" for zero/absent.
                dep_txt = f"<font color='#16A34A'>₱{dep_val:,.2f}</font>" if dep_val > 0 else "—"
                with_txt = f"<font color='#DC2626'>₱{with_val:,.2f}</font>" if with_val > 0 else "—"
                bal_txt = f"<b>₱{bal_val:,.2f}</b>" if bal_val >= 0 else f"<font color='#DC2626'><b>(₱{abs(bal_val):,.2f})</b></font>"
                sales_txt = f"₱{sales_val:,.2f}" if sales_val > 0 else "—"
                diff_txt = f"₱{diff_val:,.2f}" if diff_val >= 0 else f"<font color='#DC2626'>(₱{abs(diff_val):,.2f})</font>"
                # Variance is only meaningful when actual sales were recorded.
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
