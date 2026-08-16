"""
Jayraldine's Catering - Modern Executive Email Templates.
Crafted with high-end responsive styling, luxury typography, and dark-mode friendly CSS.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os


def _smtp_send(smtp_config: dict, to_email: str, msg) -> tuple[bool, str]:
    try:
        context = ssl.create_default_context()
        port = int(smtp_config.get("smtp_port", 587))
        if port == 465:
            with smtplib.SMTP_SSL(smtp_config["smtp_host"], port, context=context) as server:
                server.login(smtp_config["smtp_user"], smtp_config["smtp_pass"])
                server.sendmail(smtp_config["smtp_user"], to_email, msg.as_string())
        else:
            with smtplib.SMTP(smtp_config["smtp_host"], port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(smtp_config["smtp_user"], smtp_config["smtp_pass"])
                server.sendmail(smtp_config["smtp_user"], to_email, msg.as_string())
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _base_html(content: str, biz_name: str = "Jayraldine's Catering", contact: str = "", address: str = "") -> str:
    biz_contact = contact or "+63 900 000 0000"
    biz_address = address or "Cebu City, Philippines"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{biz_name}</title>
<style>
  @media only screen and (max-width: 600px) {{
    .email-container {{ width: 100% !important; margin: 0 !important; border-radius: 0 !important; }}
    .email-header {{ padding: 24px 20px !important; }}
    .email-body {{ padding: 24px 20px !important; }}
    .email-footer {{ padding: 20px !important; }}
    .btn-table {{ width: 100% !important; }}
    .btn-cell {{ display: block !important; width: 100% !important; padding: 6px 0 !important; }}
    .btn-link {{ display: block !important; width: 100% !important; box-sizing: border-box !important; text-align: center !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#0B0F19;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;-webkit-font-smoothing:antialiased;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0B0F19;padding:32px 12px;">
<tr><td align="center">

<table class="email-container" width="620" cellpadding="0" cellspacing="0" style="width:620px;background-color:#FFFFFF;border-radius:16px;overflow:hidden;box-shadow:0 20px 40px rgba(0,0,0,0.3);border:1px solid #1E293B;">

  <!-- ACCENT BAR -->
  <tr>
    <td height="4" style="background:linear-gradient(90deg,#E11D48 0%,#FB7185 50%,#E11D48 100%);"></td>
  </tr>

  <!-- HEADER -->
  <tr>
    <td class="email-header" style="background-color:#0F172A;padding:32px 36px 26px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <table cellpadding="0" cellspacing="0">
              <tr>
                <td style="vertical-align:middle;">
                  <div style="width:40px;height:40px;background:linear-gradient(135deg,#E11D48,#BE123C);border-radius:10px;text-align:center;line-height:40px;box-shadow:0 4px 12px rgba(225,29,72,0.4);">
                    <span style="color:#FFFFFF;font-size:20px;font-weight:900;font-family:'Segoe UI',sans-serif;">J</span>
                  </div>
                </td>
                <td style="padding-left:14px;vertical-align:middle;">
                  <div style="font-size:20px;font-weight:800;color:#FFFFFF;letter-spacing:-0.3px;line-height:1.2;">
                    Jayraldine's
                  </div>
                  <div style="font-size:10px;font-weight:700;color:#94A3B8;letter-spacing:1.5px;text-transform:uppercase;margin-top:2px;">
                    CATERING & EVENT SERVICES
                  </div>
                </td>
              </tr>
            </table>
          </td>
          <td align="right" style="vertical-align:middle;">
            <div style="display:inline-block;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);padding:6px 12px;border-radius:20px;">
              <span style="color:#38BDF8;font-size:11px;font-weight:600;letter-spacing:0.3px;">Official Notification</span>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- BODY -->
  <tr>
    <td class="email-body" style="background-color:#FFFFFF;padding:36px 36px 32px;color:#1E293B;">
      {content}
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td class="email-footer" style="background-color:#F8FAFC;border-top:1px solid #E2E8F0;padding:24px 36px;text-align:center;">
      <p style="margin:0 0 8px;font-size:12px;font-weight:600;color:#475569;">
        {biz_name} &bull; Professional Event Management
      </p>
      <p style="margin:0 0 12px;font-size:11px;color:#94A3B8;line-height:1.5;">
        {biz_address} &bull; Hotline: {biz_contact}
      </p>
      <div style="height:1px;background-color:#E2E8F0;margin:12px auto;width:80%;"></div>
      <p style="margin:0;font-size:10px;color:#94A3B8;line-height:1.4;">
        This is an automated system dispatch regarding your catering reservation.<br>
        &copy; 2026 {biz_name}. All rights reserved.
      </p>
    </td>
  </tr>

</table>

</td></tr>
</table>
</body>
</html>"""


def _info_row(label: str, value: str, is_last: bool = False) -> str:
    border = "" if is_last else "border-bottom: 1px solid #F1F5F9;"
    return f"""<tr>
  <td style="padding:12px 18px;font-size:13px;font-weight:600;color:#64748B;width:150px;{border}">{label}</td>
  <td style="padding:12px 18px;font-size:13px;font-weight:700;color:#0F172A;{border}">{value}</td>
</tr>"""


def _details_table(rows: list[tuple[str, str]]) -> str:
    html = '<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;margin:20px 0;">'
    for i, (label, value) in enumerate(rows):
        html += _info_row(label, value, is_last=(i == len(rows) - 1))
    html += "</table>"
    return html


def send_receipt_email(smtp_config: dict, to_email: str, invoice: dict, pdf_path: str) -> tuple[bool, str]:
    if not smtp_config.get("smtp_host") or not smtp_config.get("smtp_user"):
        return False, "SMTP is not configured. Please set SMTP credentials in Settings."
    if not to_email or "@" not in to_email:
        return False, "Invalid customer email address."

    balance = float(invoice.get("amount", 0)) - float(invoice.get("paid", 0))
    status  = invoice.get("status", "Unpaid")
    status_bg = "#DCFCE7" if status == "Paid" else ("#FEF3C7" if status == "Partial" else "#FEE2E2")
    status_color = "#15803D" if status == "Paid" else ("#B45309" if status == "Partial" else "#B91C1C")
    biz_name = invoice.get("business_name", "Jayraldine's Catering")
    customer = invoice.get("customer", "Valued Customer")

    rows = [
        ("Receipt Number", invoice.get("invoice", "—")),
        ("Client Name",    customer),
        ("Event Date",    str(invoice.get("event_date", "—"))),
        ("Total Package", f"&#8369; {float(invoice.get('amount', 0)):,.2f}"),
        ("Amount Paid",   f"<span style='color:#15803D;font-weight:800;'>&#8369; {float(invoice.get('paid', 0)):,.2f}</span>"),
        ("Balance Due",   f"&#8369; {balance:,.2f}"),
        ("Payment Status", f'<span style="background:{status_bg};color:{status_color};padding:3px 10px;border-radius:6px;font-size:12px;font-weight:800;">{status.upper()}</span>'),
    ]

    content = f"""
<div style="margin-bottom:24px;">
  <div style="display:inline-block;background:#DCFCE7;border:1px solid #BBF7D0;border-radius:20px;padding:4px 14px;margin-bottom:12px;">
    <span style="color:#15803D;font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;">Payment Acknowledged</span>
  </div>
  <h1 style="margin:0 0 8px;font-size:24px;font-weight:800;color:#0F172A;letter-spacing:-0.5px;">Official Payment Receipt</h1>
  <p style="margin:0;font-size:14px;color:#64748B;line-height:1.5;">
    Dear <strong>{customer}</strong>, thank you for your payment. Your receipt and reservation statement have been generated.
  </p>
</div>

{_details_table(rows)}

<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;padding:16px 20px;margin-top:16px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="vertical-align:top;width:14px;padding-top:3px;">
        <div style="width:8px;height:8px;background:#D97706;border-radius:50%;"></div>
      </td>
      <td style="padding-left:10px;">
        <div style="font-size:13px;font-weight:700;color:#92400E;">Remaining Balance: &#8369; {balance:,.2f}</div>
        <div style="font-size:12px;color:#B45309;margin-top:2px;line-height:1.4;">
          Please settle any remaining balance prior to your scheduled event date.
        </div>
      </td>
    </tr>
  </table>
</div>

<p style="font-size:13px;color:#64748B;margin-top:24px;line-height:1.5;">
  An official PDF copy of this receipt is attached to this email for your financial records.
</p>
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_config["smtp_user"]
    msg["To"]      = to_email
    msg["Subject"] = f"Official Receipt {invoice.get('invoice', '')} — {biz_name}"
    msg.attach(MIMEText(_base_html(content, biz_name), "html"))

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
            msg.attach(attach)

    return _smtp_send(smtp_config, to_email, msg)


def send_booking_confirmation_email(smtp_config: dict, to_email: str, booking: dict) -> tuple[bool, str]:
    if not smtp_config.get("smtp_host") or not smtp_config.get("smtp_user"):
        return False, "SMTP is not configured."
    if not to_email or "@" not in to_email:
        return False, "Invalid customer email address."

    biz_name = booking.get("business_name", "Jayraldine's Catering")
    customer = booking.get("customer_name", "Valued Customer")
    bkg_ref  = booking.get("booking_ref", "—")

    rows = [
        ("Booking Reference", bkg_ref),
        ("Occasion Type",     booking.get("occasion", "—")),
        ("Event Date",        str(booking.get("event_date", "—"))),
        ("Event Time",        str(booking.get("event_time", "—"))),
        ("Event Venue",       booking.get("venue", "—")),
        ("Guest Count (Pax)", str(booking.get("pax", "—"))),
        ("Total Package",     f"&#8369; {float(booking.get('total_amount', 0)):,.2f}"),
        ("Amount Paid",       f"&#8369; {float(booking.get('amount_paid', 0)):,.2f}"),
    ]

    content = f"""
<div style="margin-bottom:24px;">
  <div style="display:inline-block;background:#DCFCE7;border:1px solid #BBF7D0;border-radius:20px;padding:4px 14px;margin-bottom:12px;">
    <span style="color:#15803D;font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;">Reservation Confirmed</span>
  </div>
  <h1 style="margin:0 0 8px;font-size:24px;font-weight:800;color:#0F172A;letter-spacing:-0.5px;">Your Event is Officially Confirmed!</h1>
  <p style="margin:0;font-size:14px;color:#64748B;line-height:1.5;">
    Dear <strong>{customer}</strong>, we are thrilled to partner with you for your upcoming catering event. Our executive kitchen and coordination team are actively preparing for your reservation.
  </p>
</div>

{_details_table(rows)}

<div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:12px;padding:16px 20px;margin-top:16px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="vertical-align:top;width:14px;padding-top:3px;">
        <div style="width:8px;height:8px;background:#0284C7;border-radius:50%;"></div>
      </td>
      <td style="padding-left:10px;">
        <div style="font-size:13px;font-weight:700;color:#0369A1;">Need to Adjust Menu or Schedule?</div>
        <div style="font-size:12px;color:#0284C7;margin-top:2px;line-height:1.4;">
          Please reach out to our catering coordinator at <strong>{booking.get('business_contact', '')}</strong>.
        </div>
      </td>
    </tr>
  </table>
</div>

<p style="font-size:13px;color:#64748B;margin-top:24px;line-height:1.5;">
  We look forward to delivering an unforgettable culinary experience for you and your guests!
</p>
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_config["smtp_user"]
    msg["To"]      = to_email
    msg["Subject"] = f"Reservation Confirmed — {bkg_ref} | {biz_name}"
    msg.attach(MIMEText(_base_html(content, biz_name, contact=booking.get("business_contact", "")), "html"))

    return _smtp_send(smtp_config, to_email, msg)


def send_booking_approval_request_email(smtp_config: dict, to_email: str, booking: dict) -> tuple[bool, str]:
    if not smtp_config.get("smtp_host") or not smtp_config.get("smtp_user"):
        return False, "SMTP is not configured."
    if not to_email or "@" not in to_email:
        return False, "Invalid email address."

    biz_name    = booking.get("business_name", "Jayraldine's Catering")
    biz_contact = booking.get("business_contact", "")
    biz_email   = smtp_config.get("smtp_user", "")
    customer    = booking.get("name", booking.get("customer_name", "Valued Client"))
    bkg_ref     = booking.get("booking_ref", "—")
    event_date  = str(booking.get("event_date", "—"))
    occasion    = booking.get("occasion", "Catering Event")
    pax         = str(booking.get("pax", "—"))
    venue       = booking.get("venue", "—")
    total_val   = float(booking.get("total", booking.get("total_amount", 0)))

    rows = [
        ("Booking Reference", f"<strong style='color:#E11D48;'>{bkg_ref}</strong>"),
        ("Occasion Type",     occasion),
        ("Event Date",        event_date),
        ("Event Venue",       venue),
        ("Guest Count",       f"{pax} Pax"),
        ("Menu Selection",    booking.get("package", booking.get("menu_value", booking.get("menu_type", "Selected Package")))),
        ("Total Investment",  f"<span style='color:#0F172A;font-size:15px;font-weight:800;'>&#8369; {total_val:,.2f}</span>"),
    ]

    approve_subject = f"APPROVE - Reservation {bkg_ref}"
    approve_body = f"Hello Jayraldine's Catering,\n\nI confirm and approve my catering reservation {bkg_ref} for {occasion} on {event_date}.\n\nThank you,\n{customer}"

    decline_subject = f"DECLINE - Reservation {bkg_ref}"
    decline_body = f"Hello Jayraldine's Catering,\n\nI would like to request changes or decline reservation {bkg_ref} for {occasion} on {event_date}.\n\nNotes/Reason: "

    import urllib.parse
    approve_href = f"mailto:{biz_email}?subject={urllib.parse.quote(approve_subject)}&body={urllib.parse.quote(approve_body)}"
    decline_href = f"mailto:{biz_email}?subject={urllib.parse.quote(decline_subject)}&body={urllib.parse.quote(decline_body)}"

    content = f"""
<!-- HERO SECTION -->
<div style="margin-bottom:24px;">
  <div style="display:inline-block;background:#FFF7ED;border:1px solid #FED7AA;border-radius:20px;padding:4px 14px;margin-bottom:12px;">
    <span style="color:#C2410C;font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;">Action Required &bull; Client Review</span>
  </div>
  <h1 style="margin:0 0 8px;font-size:24px;font-weight:800;color:#0F172A;letter-spacing:-0.5px;">Catering Reservation Summary</h1>
  <p style="margin:0;font-size:14px;color:#64748B;line-height:1.5;">
    Dear <strong>{customer}</strong>, we have prepared your event quotation and reservation proposal. Please review the details below to confirm your schedule.
  </p>
</div>

<!-- KEY METRICS BANNER -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
  <tr>
    <td width="32%" style="background-color:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:14px 16px;text-align:center;">
      <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;">BOOKING ID</div>
      <div style="font-size:15px;font-weight:800;color:#E11D48;margin-top:4px;">{bkg_ref}</div>
    </td>
    <td width="2%"></td>
    <td width="32%" style="background-color:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:14px 16px;text-align:center;">
      <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;">EVENT DATE</div>
      <div style="font-size:14px;font-weight:800;color:#0F172A;margin-top:4px;">{event_date}</div>
    </td>
    <td width="2%"></td>
    <td width="32%" style="background-color:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:14px 16px;text-align:center;">
      <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;">ESTIMATED TOTAL</div>
      <div style="font-size:15px;font-weight:800;color:#059669;margin-top:4px;">&#8369; {total_val:,.2f}</div>
    </td>
  </tr>
</table>

<!-- DETAILED BREAKDOWN -->
<div style="font-size:12px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">
  Event Specifications
</div>
{_details_table(rows)}

<!-- CTA ACTION CARD -->
<div style="background-color:#0F172A;border-radius:14px;padding:24px;margin:28px 0;text-align:center;box-shadow:0 10px 25px rgba(15,23,42,0.15);">
  <h3 style="margin:0 0 6px;color:#FFFFFF;font-size:17px;font-weight:800;">Confirm Your Reservation</h3>
  <p style="margin:0 0 20px;color:#94A3B8;font-size:13px;line-height:1.4;">
    Please click an option below to submit your approval via email.
  </p>

  <table class="btn-table" cellpadding="0" cellspacing="0" style="margin:0 auto;">
    <tr>
      <td class="btn-cell" align="center" style="padding:0 8px;">
        <a class="btn-link" href="{approve_href}"
           style="display:inline-block;background:linear-gradient(135deg,#10B981,#059669);color:#FFFFFF;font-size:13px;font-weight:700;
                  padding:14px 28px;border-radius:8px;text-decoration:none;letter-spacing:0.3px;box-shadow:0 4px 14px rgba(16,185,129,0.35);">
          &#10003;&nbsp; Approve &amp; Confirm
        </a>
      </td>
      <td class="btn-cell" align="center" style="padding:0 8px;">
        <a class="btn-link" href="{decline_href}"
           style="display:inline-block;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.18);color:#FDA4AF;font-size:13px;font-weight:600;
                  padding:13px 24px;border-radius:8px;text-decoration:none;letter-spacing:0.3px;">
          &#10007;&nbsp; Request Changes / Decline
        </a>
      </td>
    </tr>
  </table>

  <p style="margin:16px 0 0;font-size:11px;color:#64748B;">
    Clicking a button opens your email client with a pre-filled confirmation note.
  </p>
</div>

<!-- NOTICE -->
<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;padding:12px 16px;margin-top:4px;">
  <p style="margin:0;font-size:12px;color:#991B1B;line-height:1.4;">
    <strong>Reservation Policy:</strong> Dates remain tentative until formal approval and required deposit are acknowledged by management.
  </p>
</div>

<p style="font-size:13px;color:#64748B;margin-top:20px;line-height:1.5;">
  Have questions regarding menu items or setup? Reply directly to this email or call our hotline at <strong>{biz_contact}</strong>.
</p>
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_config["smtp_user"]
    msg["To"]      = to_email
    msg["Subject"] = f"Reservation Proposal — {bkg_ref} | Action Required | {biz_name}"
    msg.attach(MIMEText(_base_html(content, biz_name, contact=biz_contact), "html"))

    return _smtp_send(smtp_config, to_email, msg)
