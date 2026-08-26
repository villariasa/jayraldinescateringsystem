"""Receipt PDF export for the Tablet App (Tablet-mode.md section 4)."""
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

_C_RED = colors.HexColor("#E11D48") if REPORTLAB_OK else None
_C_DARK = colors.HexColor("#0B1220") if REPORTLAB_OK else None
_C_GRAY = colors.HexColor("#6B7280") if REPORTLAB_OK else None
_C_GREEN = colors.HexColor("#22C55E") if REPORTLAB_OK else None
_C_BORDER = colors.HexColor("#E5E7EB") if REPORTLAB_OK else None
_MARGIN = 1.5 * cm if REPORTLAB_OK else 0
_PAGE_W = A4[0] if REPORTLAB_OK else 0
_CONTENT_W = _PAGE_W - 2 * _MARGIN if REPORTLAB_OK else 0


def export_order_receipt_pdf(path: str, order: dict, business_name: str = "Jayraldine's Catering") -> bool:
    """order: return value of repository.get_order_detail() / create_order()."""
    if not REPORTLAB_OK:
        return False
    try:
        doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=_MARGIN, rightMargin=_MARGIN,
                                topMargin=_MARGIN, bottomMargin=_MARGIN, title=f"Receipt — {order.get('booking_ref', '')}")
        story = []

        title_style = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18, textColor=_C_RED, leading=22)
        sub_style = ParagraphStyle("sub", fontName="Helvetica", fontSize=9, textColor=_C_GRAY, leading=12)
        label_style = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=9.5, textColor=_C_GRAY, leading=13)
        value_style = ParagraphStyle("value", fontName="Helvetica", fontSize=9.5, textColor=_C_DARK, leading=13)
        right_style = ParagraphStyle("right", fontName="Helvetica", fontSize=9.5, textColor=_C_DARK, alignment=TA_RIGHT, leading=13)

        story.append(Paragraph(business_name, title_style))
        story.append(Paragraph("Order Receipt (Tablet)", sub_style))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=2, color=_C_RED))
        story.append(Spacer(1, 10))

        info_rows = [
            [Paragraph("Order Ref", label_style), Paragraph(str(order.get("booking_ref", "—")), value_style)],
            [Paragraph("Customer", label_style), Paragraph(str(order.get("customer_name", "—")), value_style)],
            [Paragraph("Event Date", label_style), Paragraph(str(order.get("event_date", "—")), value_style)],
            [Paragraph("Venue / Occasion", label_style), Paragraph(f"{order.get('venue', '—')} / {order.get('occasion', '—')}", value_style)],
            [Paragraph("Guests", label_style), Paragraph(str(order.get("pax", "—")), value_style)],
        ]
        info_tbl = Table(info_rows, colWidths=[4 * cm, _CONTENT_W - 4 * cm])
        info_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.4, _C_BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.3, _C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(info_tbl)
        story.append(Spacer(1, 10))

        menu_selections = order.get("menu_selections") or []
        if menu_selections:
            story.append(Paragraph("Selected Menu", label_style))
            story.append(Spacer(1, 4))
            rows = [[Paragraph("Category", label_style), Paragraph("Item", label_style)]]
            for m in menu_selections:
                rows.append([Paragraph(m.get("category", ""), value_style), Paragraph(m.get("item_name", ""), value_style)])
            tbl = Table(rows, colWidths=[4 * cm, _CONTENT_W - 4 * cm])
            tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.4, _C_BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.3, _C_BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), _C_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 10))

        charges = order.get("additional_charges") or []
        if charges:
            story.append(Paragraph("Additional Charges / Discounts", label_style))
            story.append(Spacer(1, 4))
            rows = [[Paragraph("Description", label_style), Paragraph("Amount", label_style)]]
            for c in charges:
                amt = float(c["amount"])
                amt_text = f"- PHP {abs(amt):,.2f}" if amt < 0 else f"PHP {amt:,.2f}"
                rows.append([Paragraph(c["description"], value_style), Paragraph(amt_text, right_style)])
            tbl = Table(rows, colWidths=[_CONTENT_W * 0.7, _CONTENT_W * 0.3])
            tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.4, _C_BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.3, _C_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 10))

        total = float(order.get("total", 0))
        paid = float(order.get("paid", 0))
        balance = float(order.get("balance", max(0.0, total - paid)))
        status = order.get("status", "Unpaid")
        status_color = {"Paid": _C_GREEN, "Partial": colors.HexColor("#F59E0B")}.get(status, colors.HexColor("#EF4444"))

        amount_rows = [
            [Paragraph("Total Amount", label_style), Paragraph(f"PHP {total:,.2f}", right_style)],
            [Paragraph("Amount Paid", label_style), Paragraph(f"PHP {paid:,.2f}", ParagraphStyle("p", parent=right_style, textColor=_C_GREEN))],
            [Paragraph("Remaining Balance", ParagraphStyle("bl", fontName="Helvetica-Bold", fontSize=10, textColor=_C_DARK)),
             Paragraph(f"PHP {balance:,.2f}", ParagraphStyle("bv", fontName="Helvetica-Bold", fontSize=12, textColor=colors.HexColor("#EF4444") if balance > 0 else _C_GREEN, alignment=TA_RIGHT))],
            [Paragraph("Payment Status", label_style), Paragraph(status.upper(), ParagraphStyle("st", fontName="Helvetica-Bold", fontSize=10, textColor=status_color, alignment=TA_RIGHT))],
        ]
        amt_tbl = Table(amount_rows, colWidths=[_CONTENT_W * 0.55, _CONTENT_W * 0.45])
        amt_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.4, _C_BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.3, _C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(amt_tbl)
        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="100%", thickness=0.5, color=_C_BORDER))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"Printed: {datetime.now().strftime('%B %d, %Y at %I:%M %p')} · Thank you for choosing {business_name}!",
            ParagraphStyle("footer", fontName="Helvetica", fontSize=7.5, textColor=_C_GRAY, alignment=TA_CENTER),
        ))

        doc.build(story)
        return True
    except Exception as exc:
        print(f"[tablet exporter] Receipt PDF failed: {exc}")
        return False
