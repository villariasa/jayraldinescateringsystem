import os
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image
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


_BRAND_RED   = colors.HexColor("#E11D48")
_BRAND_DARK  = colors.HexColor("#0B1220")
_BRAND_GRAY  = colors.HexColor("#374151")
_BRAND_LIGHT = colors.HexColor("#F9FAFB")
_ACCENT      = colors.HexColor("#1F2937")
_MUTED       = colors.HexColor("#6B7280")

_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "logo.png"
)
if not os.path.exists(_LOGO_PATH):
    _LOGO_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", "logo.jpg"
    )


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("BrandTitle",
        fontName="Helvetica-Bold", fontSize=22, textColor=_BRAND_RED,
        spaceAfter=2, alignment=TA_LEFT))
    s.add(ParagraphStyle("BrandSub",
        fontName="Helvetica", fontSize=9, textColor=_MUTED,
        spaceAfter=0, alignment=TA_LEFT))
    s.add(ParagraphStyle("SectionHead",
        fontName="Helvetica-Bold", fontSize=11, textColor=_BRAND_DARK,
        spaceBefore=14, spaceAfter=6, alignment=TA_LEFT))
    s.add(ParagraphStyle("KpiLabel",
        fontName="Helvetica", fontSize=8, textColor=_MUTED,
        spaceAfter=1, alignment=TA_CENTER))
    s.add(ParagraphStyle("KpiValue",
        fontName="Helvetica-Bold", fontSize=16, textColor=_BRAND_DARK,
        spaceAfter=0, alignment=TA_CENTER))
    s.add(ParagraphStyle("Footer",
        fontName="Helvetica", fontSize=7, textColor=_MUTED,
        alignment=TA_CENTER))
    return s


def _header_block(story, styles, title: str, period: str = "All Time"):
    header_data = [[]]
    if os.path.exists(_LOGO_PATH):
        try:
            logo = Image(_LOGO_PATH, width=2.2*cm, height=2.2*cm)
            header_data[0].append(logo)
        except Exception:
            header_data[0].append("")
    else:
        header_data[0].append("")

    title_cell = [
        Paragraph("Jayraldine's Catering", styles["BrandTitle"]),
        Paragraph("Professional Catering Services", styles["BrandSub"]),
    ]
    header_data[0].append(title_cell)

    meta_cell = [
        Paragraph(f"<b>{title}</b>", styles["BrandSub"]),
        Paragraph(f"Period: {period}", styles["BrandSub"]),
        Paragraph(f"Generated: {datetime.now().strftime('%b %d, %Y  %I:%M %p')}", styles["BrandSub"]),
    ]
    header_data[0].append(meta_cell)

    header_tbl = Table(header_data, colWidths=[2.5*cm, 10*cm, 6*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",       (2, 0), (2, 0),  "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
    ]))
    story.append(header_tbl)
    story.append(HRFlowable(width="100%", thickness=2, color=_BRAND_RED, spaceAfter=10))


def _kpi_row(story, styles, kpis: dict):
    items = [
        ("Total Bookings",  str(kpis.get("total_bookings", 0))),
        ("Total Pax",       f"{int(kpis.get('total_pax', 0)):,}"),
        ("Total Revenue",   f"PHP {float(kpis.get('total_revenue', 0)):,.0f}"),
        ("Unpaid Amount",   f"PHP {float(kpis.get('unpaid_amount', 0)):,.0f}"),
    ]
    row_labels = [[Paragraph(lbl, styles["KpiLabel"]) for lbl, _ in items]]
    row_values = [[Paragraph(val, styles["KpiValue"]) for _, val in items]]

    t = Table([row_labels[0], row_values[0]], colWidths=[4.7*cm]*4)
    t.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("INNERGRID",   (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#F9FAFB")),
        ("BACKGROUND",  (0, 1), (-1, 1),  colors.white),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F9FAFB"), colors.white]),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))


def _bookings_table(story, styles, bookings: list):
    story.append(Paragraph("Booking Statistics", styles["SectionHead"]))

    headers = ["Booking Ref", "Client", "Event Date", "Pax", "Total Amount", "Status"]
    col_w   = [3*cm, 5*cm, 3*cm, 1.8*cm, 3.5*cm, 2.5*cm]

    header_row = [Paragraph(f"<b>{h}</b>", ParagraphStyle(
        "TH", fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.white, alignment=TA_CENTER)) for h in headers]

    rows = [header_row]
    status_colors = {
        "CONFIRMED": colors.HexColor("#22C55E"),
        "PENDING":   colors.HexColor("#F59E0B"),
        "CANCELLED": colors.HexColor("#EF4444"),
    }
    for b in bookings:
        sc = status_colors.get(b.get("status", "").upper(), _MUTED)
        rows.append([
            Paragraph(b.get("id", ""), ParagraphStyle("td", fontName="Helvetica", fontSize=8, alignment=TA_LEFT)),
            Paragraph(b.get("name", ""), ParagraphStyle("td", fontName="Helvetica", fontSize=8, alignment=TA_LEFT)),
            Paragraph(b.get("date", ""), ParagraphStyle("td", fontName="Helvetica", fontSize=8, alignment=TA_CENTER)),
            Paragraph(str(b.get("pax", "")), ParagraphStyle("td", fontName="Helvetica", fontSize=8, alignment=TA_CENTER)),
            Paragraph(b.get("total", ""), ParagraphStyle("td", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph(b.get("status", "").capitalize(), ParagraphStyle(
                "tdst", fontName="Helvetica-Bold", fontSize=8,
                textColor=sc, alignment=TA_CENTER)),
        ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl_style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  _BRAND_RED),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    tbl.setStyle(TableStyle(tbl_style))
    story.append(tbl)


def _footer(story, styles):
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Jayraldine's Catering  •  This report is system-generated and confidential.",
        styles["Footer"]
    ))


def export_pdf(path: str, kpis: dict, bookings: list,
               title: str = "Business Report", period: str = "All Time") -> bool:
    if not REPORTLAB_OK:
        return False
    try:
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=1.5*cm, rightMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm,
            title=f"Jayraldine's Catering — {title}",
            author="Jayraldine's Catering System",
        )
        styles = _styles()
        story = []
        _header_block(story, styles, title, period)
        story.append(Paragraph("Key Performance Indicators", styles["SectionHead"]))
        _kpi_row(story, styles, kpis)
        _bookings_table(story, styles, bookings)
        _footer(story, styles)
        doc.build(story)
        return True
    except Exception as exc:
        print(f"[exporter] PDF failed: {exc}")
        return False


def export_excel(path: str, kpis: dict, bookings: list,
                 title: str = "Business Report", period: str = "All Time") -> bool:
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
        c.value = "JAYRALDINE'S CATERING"
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
        c.value = "Jayraldine's Catering  •  System-generated report  •  Confidential"
        c.font = Font(name="Calibri", size=8, italic=True, color=GRAY)
        c.alignment = Alignment(horizontal="center")

        wb.save(path)
        return True
    except Exception as exc:
        print(f"[exporter] Excel failed: {exc}")
        return False
