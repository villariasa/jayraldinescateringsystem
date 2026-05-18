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


def _base_html(content: str, biz_name: str = "Jayraldine's Catering") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{biz_name}</title>
</head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:32px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#0B1220 0%,#1F2937 100%);padding:36px 40px 28px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <div style="font-size:26px;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;">{biz_name}</div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:4px;letter-spacing:0.5px;">PROFESSIONAL CATERING SERVICES</div>
          </td>
          <td align="right">
            <div style="width:48px;height:48px;background:#E11D48;border-radius:12px;display:inline-block;text-align:center;line-height:48px;">
              <span style="color:#fff;font-size:22px;font-weight:900;">J</span>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- BODY -->
  <tr><td style="padding:36px 40px 28px;">{content}</td></tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:20px 40px;text-align:center;">
      <p style="margin:0;font-size:12px;color:#9CA3AF;">
        &copy; {biz_name} &nbsp;&bull;&nbsp; This is an automated email, please do not reply directly.
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _info_row(label: str, value: str, alt: bool = False) -> str:
    bg = "#F8FAFC" if alt else "#FFFFFF"
    return f"""<tr style="background:{bg};">
  <td style="padding:10px 16px;font-size:13px;font-weight:600;color:#374151;width:160px;border-bottom:1px solid #F1F5F9;">{label}</td>
  <td style="padding:10px 16px;font-size:13px;color:#0F172A;border-bottom:1px solid #F1F5F9;">{value}</td>
</tr>"""


def _details_table(rows: list[tuple[str, str]]) -> str:
    html = '<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;margin:20px 0;">'
    for i, (label, value) in enumerate(rows):
        html += _info_row(label, value, alt=(i % 2 == 0))
    html += "</table>"
    return html


def send_receipt_email(smtp_config: dict, to_email: str, invoice: dict, pdf_path: str) -> tuple[bool, str]:
    if not smtp_config.get("smtp_host") or not smtp_config.get("smtp_user"):
        return False, "SMTP is not configured. Please set SMTP credentials in Settings."
    if not to_email or "@" not in to_email:
        return False, "Invalid customer email address."

    balance = float(invoice.get("amount", 0)) - float(invoice.get("paid", 0))
    status  = invoice.get("status", "Unpaid")
    status_color = {"Paid": "#22C55E", "Partial": "#F59E0B", "Unpaid": "#EF4444"}.get(status, "#6B7280")
    biz_name = invoice.get("business_name", "Jayraldine's Catering")

    rows = [
        ("Receipt #",     invoice.get("invoice", "—")),
        ("Customer",      invoice.get("customer", "—")),
        ("Event Date",    str(invoice.get("event_date", "—"))),
        ("Total Amount",  f"&#8369; {float(invoice.get('amount', 0)):,.2f}"),
        ("Amount Paid",   f"&#8369; {float(invoice.get('paid', 0)):,.2f}"),
        ("Balance Due",   f"&#8369; {balance:,.2f}"),
        ("Status",        f'<span style="color:{status_color};font-weight:700;">{status}</span>'),
    ]

    content = f"""
<div style="text-align:center;margin-bottom:28px;">
  <div style="display:inline-block;background:#F0FDF4;border:1px solid #BBF7D0;border-radius:50px;padding:8px 20px;">
    <span style="color:#16A34A;font-size:13px;font-weight:600;">&#10003; Payment Receipt</span>
  </div>
  <h2 style="margin:16px 0 6px;font-size:22px;font-weight:800;color:#0F172A;">Your Receipt is Ready</h2>
  <p style="margin:0;font-size:14px;color:#6B7280;">Thank you for your payment, <strong>{invoice.get('customer', 'Valued Customer')}</strong>.</p>
</div>

{_details_table(rows)}

<div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;padding:16px 20px;margin-top:8px;">
  <p style="margin:0;font-size:13px;color:#92400E;">
    <strong>Balance Due:</strong> &#8369; {balance:,.2f} &nbsp;&mdash;&nbsp;
    Please settle your remaining balance before your event date.
  </p>
</div>

<p style="font-size:13px;color:#6B7280;margin-top:24px;">
  Your official receipt PDF is attached. Please keep it for your records.
</p>
<p style="font-size:13px;color:#6B7280;">
  For inquiries, please don't hesitate to contact us.
</p>
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_config["smtp_user"]
    msg["To"]      = to_email
    msg["Subject"] = f"Receipt {invoice.get('invoice', '')} — {biz_name}"
    msg.attach(MIMEText(_base_html(content, biz_name), "html"))

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
            msg.attach(attach)

    return _smtp_send(smtp_config, to_email, msg)


def send_booking_confirmation_email(smtp_config: dict, to_email: str, booking: dict) -> tuple[bool, str]:
    if not smtp_config.get("smtp_host") or not smtp_config.get("smtp_user"):
        return False, "SMTP is not configured. Please set SMTP credentials in Settings."
    if not to_email or "@" not in to_email:
        return False, "Invalid customer email address."

    biz_name = booking.get("business_name", "Jayraldine's Catering")
    rows = [
        ("Booking Ref",  booking.get("booking_ref", "—")),
        ("Occasion",     booking.get("occasion", "—")),
        ("Event Date",   str(booking.get("event_date", "—"))),
        ("Event Time",   str(booking.get("event_time", "—"))),
        ("Venue",        booking.get("venue", "—")),
        ("Pax",          str(booking.get("pax", "—"))),
        ("Total Amount", f"&#8369; {float(booking.get('total_amount', 0)):,.2f}"),
        ("Amount Paid",  f"&#8369; {float(booking.get('amount_paid', 0)):,.2f}"),
    ]

    content = f"""
<div style="text-align:center;margin-bottom:28px;">
  <div style="display:inline-block;background:#F0FDF4;border:1px solid #BBF7D0;border-radius:50px;padding:8px 20px;">
    <span style="color:#16A34A;font-size:13px;font-weight:600;">&#10003; Booking Confirmed</span>
  </div>
  <h2 style="margin:16px 0 6px;font-size:22px;font-weight:800;color:#0F172A;">Your Booking is Confirmed!</h2>
  <p style="margin:0;font-size:14px;color:#6B7280;">
    Dear <strong>{booking.get('customer_name', 'Valued Customer')}</strong>, we are thrilled to confirm your upcoming event.
  </p>
</div>

{_details_table(rows)}

<div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:10px;padding:16px 20px;margin-top:8px;">
  <p style="margin:0;font-size:13px;color:#0369A1;">
    <strong>Need to make changes?</strong> Please contact us as soon as possible at
    <strong>{booking.get('business_contact', '')}</strong>.
  </p>
</div>

<p style="font-size:13px;color:#6B7280;margin-top:24px;">
  We look forward to serving you and making your event truly memorable!
</p>
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_config["smtp_user"]
    msg["To"]      = to_email
    msg["Subject"] = f"Booking Confirmed — {booking.get('booking_ref', '')} | {biz_name}"
    msg.attach(MIMEText(_base_html(content, biz_name), "html"))

    return _smtp_send(smtp_config, to_email, msg)


def send_booking_approval_request_email(smtp_config: dict, to_email: str, booking: dict) -> tuple[bool, str]:
    if not smtp_config.get("smtp_host") or not smtp_config.get("smtp_user"):
        return False, "SMTP is not configured."
    if not to_email or "@" not in to_email:
        return False, "Invalid email address."

    biz_name    = booking.get("business_name", "Jayraldine's Catering")
    biz_contact = booking.get("business_contact", "")
    biz_email   = smtp_config.get("smtp_user", "")

    rows = [
        ("Booking Ref",  booking.get("booking_ref", "—")),
        ("Occasion",     booking.get("occasion", "—")),
        ("Event Date",   str(booking.get("event_date", "—"))),
        ("Venue",        booking.get("venue", "—")),
        ("Pax",          str(booking.get("pax", "—"))),
        ("Package",      booking.get("package", booking.get("menu_type", "—"))),
        ("Total Amount", f"&#8369; {float(booking.get('total', booking.get('total_amount', 0))):,.2f}"),
    ]

    content = f"""
<div style="text-align:center;margin-bottom:28px;">
  <div style="display:inline-block;background:#FFF7ED;border:1px solid #FED7AA;border-radius:50px;padding:8px 20px;">
    <span style="color:#C2410C;font-size:13px;font-weight:600;">&#9888; Action Required</span>
  </div>
  <h2 style="margin:16px 0 6px;font-size:22px;font-weight:800;color:#0F172A;">Booking Request Received</h2>
  <p style="margin:0;font-size:14px;color:#6B7280;">
    Dear <strong>{booking.get('name', booking.get('customer_name', 'Valued Customer'))}</strong>,
    we have received your booking request and it is currently <strong>pending your approval</strong>.
  </p>
</div>

{_details_table(rows)}

<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:20px;margin:24px 0;">
  <p style="margin:0 0 16px;font-size:14px;font-weight:700;color:#0F172A;">Please confirm your booking:</p>
  <table cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td align="center" style="padding:0 8px;">
        <a href="mailto:{biz_email}?subject=APPROVE - Booking {booking.get('booking_ref', '')}&body=I approve my booking {booking.get('booking_ref', '')} for {booking.get('occasion', '')} on {booking.get('event_date', '')}."
           style="display:inline-block;background:#16A34A;color:#FFFFFF;font-size:14px;font-weight:700;
                  padding:14px 32px;border-radius:8px;text-decoration:none;letter-spacing:0.3px;">
          &#10003;&nbsp; Approve Booking
        </a>
      </td>
      <td align="center" style="padding:0 8px;">
        <a href="mailto:{biz_email}?subject=DECLINE - Booking {booking.get('booking_ref', '')}&body=I would like to decline my booking {booking.get('booking_ref', '')} for {booking.get('occasion', '')} on {booking.get('event_date', '')}. Reason: "
           style="display:inline-block;background:#EF4444;color:#FFFFFF;font-size:14px;font-weight:700;
                  padding:14px 32px;border-radius:8px;text-decoration:none;letter-spacing:0.3px;">
          &#10007;&nbsp; Decline Booking
        </a>
      </td>
    </tr>
  </table>
  <p style="margin:16px 0 0;font-size:12px;color:#9CA3AF;text-align:center;">
    Clicking a button will open your email client with a pre-filled message. Simply send it to confirm your choice.
  </p>
</div>

<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;padding:14px 18px;margin-top:4px;">
  <p style="margin:0;font-size:13px;color:#B91C1C;">
    <strong>Important:</strong> Your booking will remain <em>pending</em> until the owner reviews and officially approves it.
    You will receive a separate confirmation email once approved.
  </p>
</div>

<p style="font-size:13px;color:#6B7280;margin-top:24px;">
  For questions or changes, contact us at <strong>{biz_contact}</strong> or reply to this email.
</p>
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_config["smtp_user"]
    msg["To"]      = to_email
    msg["Subject"] = f"Booking Request — {booking.get('booking_ref', '')} | Please Approve | {biz_name}"
    msg.attach(MIMEText(_base_html(content, biz_name), "html"))

    return _smtp_send(smtp_config, to_email, msg)
