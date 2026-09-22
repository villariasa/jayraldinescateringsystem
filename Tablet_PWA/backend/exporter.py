"""
Receipt PDF + orders Excel archive export. Ported from the original Tablet
app's utils/exporter.py (reportlab receipt, openpyxl multi-sheet archive).
"""
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


def export_order_receipt_pdf(path: str, order: dict, business_name: str = "Jayraldine's CATERING SERVICES") -> bool:
    """Generate the official A4 Booking Agreement & Order Receipt matching the client's manual form:
    - Upper ~60%: The Order (Customer, Event, Financials, Signatures on Left; Package, Menu, Add-ons on Right)
    - Lower ~40%: Terms and Conditions (4 core points) + Invitation & Contact Footer
    """
    if not REPORTLAB_OK:
        return False
    try:
        from reportlab.lib.units import cm
        doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=1.0 * cm, rightMargin=1.0 * cm,
                                 topMargin=0.8 * cm, bottomMargin=0.8 * cm,
                                 title=f"Booking Agreement — {order.get('booking_ref', order.get('id', ''))}")
        story = []
        content_w = A4[0] - 2.0 * cm  # ~19.0 cm
        half_w = (content_w - 0.4 * cm) / 2  # ~9.3 cm

        # ── 1. HEADER (Top) ────────────────────────────────────────────────
        story.append(Paragraph(f"<b><font color='{_C_RED.hexval()}'>{business_name.upper()}</font></b>",
                               ParagraphStyle("h_biz", fontName="Helvetica-Bold", fontSize=15, alignment=TA_CENTER, leading=17)))
        story.append(Spacer(1, 2))
        story.append(Paragraph("<u><b>BOOKING AGREEMENT</b></u>",
                               ParagraphStyle("h_agree", fontName="Helvetica-Bold", fontSize=11, textColor=_C_DARK, alignment=TA_CENTER, leading=13)))
        story.append(Spacer(1, 3))
        ref_str = order.get("booking_ref") or order.get("id") or "—"
        issue_str = order.get("created_at") or datetime.now().strftime("%Y-%m-%d")
        story.append(Paragraph(f"<font color='{_C_GRAY.hexval()}'>Booking Ref: {ref_str}   ·   Date Issued: {issue_str}</font>",
                               ParagraphStyle("h_sub", fontName="Helvetica", fontSize=8, alignment=TA_CENTER, leading=10)))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=0.8, color=_C_BORDER))
        story.append(Spacer(1, 6))

        # ── 2. UPPER SECTION (THE ORDER / 2 COLUMNS) ───────────────────────
        def _lbl(txt):
            return Paragraph(f"<b>{txt}</b>", ParagraphStyle("flbl", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#475569"), leading=10))

        def _val(txt, bold=False):
            fn = "Helvetica-Bold" if bold else "Helvetica"
            return Paragraph(str(txt or "—"), ParagraphStyle("fval", fontName=fn, fontSize=8, textColor=_C_DARK, leading=10))

        cust_name = order.get("customer_name") or order.get("customer") or order.get("name") or "—"
        address = order.get("customer_address") or order.get("address") or order.get("venue") or "—"
        contact = order.get("contact") or order.get("phone") or "—"
        event_date = order.get("event_date") or "—"
        event_time = order.get("event_time") or "—"
        venue = order.get("venue") or "—"
        occasion = order.get("occasion") or "—"
        motif = order.get("motif") or order.get("color_theme") or "Standard Motif"
        pax = order.get("pax", 0)
        pkg_name = order.get("package_name") or "Catering Package"

        client_rows = [
            [_lbl("Name:"), _val(cust_name, True)],
            [_lbl("Address:"), _val(address)],
            [_lbl("Contact #:"), _val(contact)],
            [_lbl("Function Date:"), _val(f"{event_date}  ({event_time})", True)],
            [_lbl("Venue:"), _val(venue)],
            [_lbl("Occasion:"), _val(f"{occasion}  ·  Motif: {motif}")],
            [_lbl("No. of Sets:"), _val(f"{pax} Set(s)  @ {pkg_name}", True)],
        ]
        notes = order.get("notes") or order.get("special_instructions") or ""
        if notes:
            client_rows.append([_lbl("Special Instr:"), _val(notes)])

        client_tbl = Table(client_rows, colWidths=[2.2 * cm, half_w - 2.2 * cm])
        client_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))

        # Financial card (Left)
        total = float(order.get("total", 0))
        paid = float(order.get("paid", order.get("downpayment", 0)))
        balance = float(order.get("balance", max(0.0, total - paid)))
        status = str(order.get("status") or ("PAID" if balance == 0 else "PARTIAL" if paid > 0 else "PENDING")).upper()

        fin_rows = [
            [_lbl("Total Amount:"), Paragraph(f"<b>PHP {total:,.2f}</b>", ParagraphStyle("ftot", fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_DARK, alignment=TA_RIGHT))],
            [_lbl("Downpayment:"), Paragraph(f"<b>PHP {paid:,.2f}</b>", ParagraphStyle("fpaid", fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_GREEN, alignment=TA_RIGHT))],
            [_lbl("Balance Due:"), Paragraph(f"<b>PHP {balance:,.2f}</b>", ParagraphStyle("fbal", fontName="Helvetica-Bold", fontSize=9, textColor=_C_RED if balance > 0 else _C_GREEN, alignment=TA_RIGHT))],
            [Paragraph(f"<font color='{_C_GRAY.hexval()}'>Status: {status}</font>", ParagraphStyle("fst", fontName="Helvetica", fontSize=7, leading=8)),
             Paragraph(f"<font color='{_C_GRAY.hexval()}'>Mode: {order.get('payment_method', 'Cash')}</font>", ParagraphStyle("fmd", fontName="Helvetica", fontSize=7, alignment=TA_RIGHT, leading=8))],
        ]
        fin_tbl = Table(fin_rows, colWidths=[half_w * 0.48, half_w * 0.52])
        fin_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, _C_BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

        sig_rows = [
            [Paragraph("<b>CONFORME:</b>", ParagraphStyle("sc", fontName="Helvetica-Bold", fontSize=7.5, textColor=_C_DARK)),
             HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#64748B")),
             Paragraph("<b>Date:</b>", ParagraphStyle("sd", fontName="Helvetica-Bold", fontSize=7.5, textColor=_C_DARK)),
             HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#64748B"))],
            ["", Paragraph("<font color='#64748B'>Client Signature over Printed Name</font>", ParagraphStyle("scs", fontName="Helvetica", fontSize=6, alignment=TA_CENTER)), "", ""],
            [Paragraph("<b>NOTED BY:</b>", ParagraphStyle("sn", fontName="Helvetica-Bold", fontSize=7.5, textColor=_C_DARK)),
             HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#64748B")),
             Paragraph("<b>Date:</b>", ParagraphStyle("sd2", fontName="Helvetica-Bold", fontSize=7.5, textColor=_C_DARK)),
             HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#64748B"))],
            ["", Paragraph("<font color='#64748B'>Jayraldine's Catering Representative</font>", ParagraphStyle("sns", fontName="Helvetica", fontSize=6, alignment=TA_CENTER)), "", ""],
        ]
        sig_tbl = Table(sig_rows, colWidths=[1.8 * cm, 4.4 * cm, 0.9 * cm, 2.2 * cm])
        sig_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 1),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ]))

        left_story = [client_tbl, Spacer(1, 4), fin_tbl, Spacer(1, 4), sig_tbl]

        # Right Sub-Column: Package, Inclusions, Menu, Add-ons
        pkg_box = Table([[
            Paragraph(f"<b><font color='{_C_RED.hexval()}'>{pkg_name.upper()}</font></b>", ParagraphStyle("pkn", fontName="Helvetica-Bold", fontSize=8.5, leading=10)),
            Paragraph(f"<font color='{_C_DARK.hexval()}'>Good for {pax} Guests</font>", ParagraphStyle("pkp", fontName="Helvetica", fontSize=7.5, alignment=TA_RIGHT, leading=10)),
        ]], colWidths=[half_w * 0.65, half_w * 0.35])
        pkg_box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#FECDD3")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF1F2")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

        menu_items = order.get("menu_selections") or []
        menu_rows = []
        if menu_items:
            for idx, item in enumerate(menu_items[:10], 1):
                iname = item.get("item_name") or item.get("name") or str(item)
                menu_rows.append([
                    Paragraph(f"<b><font color='{_C_RED.hexval()}'>{idx}.</font></b>", ParagraphStyle("mnum", fontName="Helvetica-Bold", fontSize=7.5, leading=9)),
                    Paragraph(str(iname), ParagraphStyle("mitem", fontName="Helvetica", fontSize=7.5, textColor=_C_DARK, leading=9)),
                ])
        else:
            menu_rows.append([Paragraph("•", ParagraphStyle("mb", fontName="Helvetica-Bold", fontSize=7.5)),
                              Paragraph("Standard Package Inclusions", ParagraphStyle("ms", fontName="Helvetica-Oblique", fontSize=7.5, textColor=_C_GRAY))])

        menu_tbl = Table(menu_rows, colWidths=[0.6 * cm, half_w - 0.6 * cm])
        menu_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        right_story = [
            pkg_box, Spacer(1, 4),
            Paragraph("<u><b>MENU:</b></u>", ParagraphStyle("mh", fontName="Helvetica-Bold", fontSize=8.5, textColor=_C_DARK, leading=10)),
            Spacer(1, 2),
            menu_tbl
        ]

        charges = order.get("additional_charges") or []
        if charges:
            chg_rows = []
            for c in charges[:4]:
                amt = float(c.get("amount", 0))
                amt_str = f"- PHP {abs(amt):,.2f}" if amt < 0 else f"PHP {amt:,.2f}"
                chg_rows.append([
                    Paragraph(f"• {c.get('description', 'Add-on')}", ParagraphStyle("cd", fontName="Helvetica", fontSize=7, textColor=_C_DARK, leading=8.5)),
                    Paragraph(f"<b>{amt_str}</b>", ParagraphStyle("ca", fontName="Helvetica-Bold", fontSize=7, textColor=_C_GREEN if amt < 0 else _C_RED, alignment=TA_RIGHT, leading=8.5)),
                ])
            chg_tbl = Table(chg_rows, colWidths=[half_w * 0.68, half_w * 0.32])
            chg_tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
            right_story.extend([
                Spacer(1, 3),
                Paragraph("<u><b>ADD-ONS &amp; EXTRAS:</b></u>", ParagraphStyle("aoh", fontName="Helvetica-Bold", fontSize=8, textColor=_C_DARK, leading=9.5)),
                Spacer(1, 2),
                chg_tbl
            ])

        upper_tbl = Table([[left_story, right_story]], colWidths=[half_w, half_w])
        upper_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, -1), 6),
            ("LEFTPADDING", (1, 0), (1, -1), 6),
            ("RIGHTPADDING", (1, 0), (1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(upper_tbl)
        story.append(Spacer(1, 6))

        # ── 3. LOWER SECTION (TERMS AND CONDITIONS & FOOTER) ───────────────
        story.append(HRFlowable(width="100%", thickness=1.5, color=_C_RED))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Terms and Conditions</b>", ParagraphStyle("tc_title", fontName="Helvetica-Bold", fontSize=9, textColor=_C_DARK, leading=11)))
        story.append(Spacer(1, 2))

        terms_data = [
            ("•", "The client shall pay 50% downpayment upon reservation of booking and shall pay the full amount 3 days before the date of the event."),
            ("•", "Mode of payment. The client shall personally pay in Cash for the downpayment and full payment. If cash is not available, the client shall also pay through Bank Transfer or Gcash."),
            ("•", "Failure to pay. A failure to make payment according to the terms of the payment will be considered a cancellation of the event and the provisions for cancellation will apply: (15) days before the event - 20% charge, (7) days - 30%, (3) days - 50%."),
            ("•", "Any Food and Drinks or any consumables that is NOT prepared by JAY-RALDINE SERVICES brought by the client will FREE US ON ANY LIABILITIES due to food poisoning and spoilage. We charged Corkage Fee for bringing outside Food and Drinks. Precise time should be place in the BOOKING AGREEMENT and shall be strictly follow to avoid poisoning and spoilage."),
        ]
        t_rows = [[
            Paragraph(f"<b><font color='{_C_RED.hexval()}'>{b}</font></b>", ParagraphStyle("tb", fontName="Helvetica-Bold", fontSize=7, leading=8.5)),
            Paragraph(t, ParagraphStyle("tt", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#334155"), leading=8.5)),
        ] for b, t in terms_data]

        terms_tbl = Table(t_rows, colWidths=[0.4 * cm, content_w - 0.4 * cm])
        terms_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(terms_tbl)
        story.append(Spacer(1, 5))

        # Bottom invitation callout box
        callout_content = [
            Paragraph("<b><font color='#BE123C'>WE INVITE YOU TO SEE HOW WE CAN HELP YOUR EVENT THE BEST IT CAN POSSIBLY BE!!!</font></b>",
                      ParagraphStyle("co_top", fontName="Helvetica-Bold", fontSize=7.5, alignment=TA_CENTER, leading=9.5)),
            Spacer(1, 1.5),
            Paragraph("Located at 121 Katipunan St. Brgy Calamba Cebu City",
                      ParagraphStyle("co_addr", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#1E293B"), alignment=TA_CENTER, leading=8.5)),
            Paragraph("Please feel free to call us at (032) 255-3113, (032) 238-9417 · Globe 0917-6519555, 0917-1051528",
                      ParagraphStyle("co_tel", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#1E293B"), alignment=TA_CENTER, leading=8.5)),
            Spacer(1, 1),
            Paragraph("<b>Find us on Facebook: Jayraldine's Catering Services</b>",
                      ParagraphStyle("co_fb", fontName="Helvetica-Bold", fontSize=7, textColor=colors.HexColor("#0284C7"), alignment=TA_CENTER, leading=8.5)),
        ]
        callout_tbl = Table([[callout_content]], colWidths=[content_w])
        callout_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(callout_tbl)

        doc.build(story)
        return True
    except Exception as exc:
        print(f"[pwa exporter] Receipt PDF failed: {exc}")
        return False


def export_all_orders_to_excel(save_path: str) -> dict:
    import db
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return {"success": False, "orders_count": 0, "path": "", "error": "openpyxl is required for Excel export."}

    try:
        bookings = db.fetchall("""
            SELECT b.*, i.inv_id, i.inv_invoice_number, i.inv_total_amount, i.inv_amount_paid, i.inv_balance, i.inv_status
            FROM bookings b
            LEFT JOIN invoices i ON i.inv_booking_id = b.bk_id
            ORDER BY b.bk_created_at DESC
        """)

        wb = openpyxl.Workbook()
        ws_orders = wb.active
        ws_orders.title = "Orders Summary"

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        sub_font = Font(name="Calibri", size=10, italic=True, color="64748B")

        ws_orders.append(["JAYRALDINE'S CATERING — KIOSK ORDERS ARCHIVE"])
        ws_orders.append([f"Export Date & Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        ws_orders.append([])
        ws_orders.cell(1, 1).font = title_font
        ws_orders.cell(2, 1).font = sub_font

        order_headers = [
            "Booking Ref", "Customer Name", "Contact Number", "Email Address", "Delivery / Billing Address",
            "Event Date", "Event Time", "Venue", "Occasion", "Pax", "Package",
            "Base Total (PHP)", "Total Amount (PHP)", "Amount Paid (PHP)", "Balance Due (PHP)",
            "Status", "Payment Mode", "Date Created", "Notes",
        ]
        ws_orders.append(order_headers)
        for col_num in range(1, len(order_headers) + 1):
            c = ws_orders.cell(row=4, column=col_num)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for b in bookings:
            ws_orders.append([
                b.get("bk_booking_ref") or f"TB-{b['bk_id']:05d}",
                b.get("bk_customer_name", ""),
                b.get("bk_contact", ""),
                b.get("bk_email", ""),
                b.get("bk_address", ""),
                b.get("bk_event_date", ""),
                b.get("bk_event_time", ""),
                b.get("bk_venue", ""),
                b.get("bk_occasion", ""),
                b.get("bk_pax", 0),
                b.get("bk_package_name") or "Custom Package",
                float(b.get("bk_base_total") or 0.0),
                float(b.get("bk_total_amount") or 0.0),
                float(b.get("inv_amount_paid") or b.get("bk_amount_paid") or 0.0),
                float(b.get("inv_balance") or 0.0),
                b.get("inv_status") or b.get("bk_status") or "PENDING",
                b.get("bk_payment_mode", "Cash"),
                b.get("bk_created_at", ""),
                b.get("bk_notes", ""),
            ])

        ws_menu = wb.create_sheet(title="Menu Selections")
        ws_menu.append(["Booking Ref", "Customer Name", "Dish Name", "Category", "Quantity", "Extra Price (PHP)"])
        for col_num in range(1, 7):
            c = ws_menu.cell(row=1, column=col_num)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
        menu_items = db.fetchall("""
            SELECT bmi.*, b.bk_booking_ref, b.bk_customer_name
            FROM booking_menu_items bmi
            JOIN bookings b ON b.bk_id = bmi.bmi_booking_id
            ORDER BY b.bk_id, bmi.bmi_category
        """)
        for m in menu_items:
            ws_menu.append([
                m.get("bk_booking_ref", ""), m.get("bk_customer_name", ""),
                m.get("bmi_item_name", ""), m.get("bmi_category", ""),
                m.get("bmi_quantity", 1), float(m.get("bmi_price") or 0.0),
            ])

        ws_charges = wb.create_sheet(title="Additional Charges")
        ws_charges.append(["Booking Ref", "Customer Name", "Charge Description", "Amount (PHP)", "Date Added", "Added By"])
        for col_num in range(1, 7):
            c = ws_charges.cell(row=1, column=col_num)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
        charges = db.fetchall("""
            SELECT ac.*, b.bk_booking_ref, b.bk_customer_name
            FROM booking_additional_charges ac
            JOIN bookings b ON b.bk_id = ac.ac_booking_id
            ORDER BY b.bk_id, ac.ac_date_added
        """)
        for ch in charges:
            ws_charges.append([
                ch.get("bk_booking_ref", ""), ch.get("bk_customer_name", ""),
                ch.get("ac_description", ""), float(ch.get("ac_amount") or 0.0),
                ch.get("ac_date_added", ""), ch.get("ac_added_by", "Staff"),
            ])

        ws_payments = wb.create_sheet(title="Payment Records")
        ws_payments.append(["Booking Ref", "Customer Name", "Invoice Ref", "Payment Amount (PHP)", "Payment Date", "Payment Method", "Is Downpayment", "Notes"])
        for col_num in range(1, 9):
            c = ws_payments.cell(row=1, column=col_num)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
        payments = db.fetchall("""
            SELECT pr.*, i.inv_invoice_number, b.bk_booking_ref, b.bk_customer_name
            FROM payment_records pr
            JOIN invoices i ON i.inv_id = pr.pr_invoice_id
            JOIN bookings b ON b.bk_id = i.inv_booking_id
            ORDER BY pr.pr_payment_date DESC
        """)
        for p in payments:
            ws_payments.append([
                p.get("bk_booking_ref", ""), p.get("bk_customer_name", ""),
                p.get("inv_invoice_number", ""), float(p.get("pr_amount") or 0.0),
                p.get("pr_payment_date", ""), p.get("pr_payment_method") or p.get("pr_method") or "Cash",
                "Yes" if p.get("pr_is_downpayment") else "No",
                p.get("pr_notes") or p.get("pr_note") or "",
            ])

        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(save_path)
        return {"success": True, "orders_count": len(bookings), "path": save_path, "error": None}
    except Exception as exc:
        print(f"[pwa exporter] Excel export failed: {exc}")
        return {"success": False, "orders_count": 0, "path": "", "error": str(exc)}
