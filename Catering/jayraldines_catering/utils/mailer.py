import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os


def send_receipt_email(smtp_config: dict, to_email: str, invoice: dict, pdf_path: str) -> tuple[bool, str]:
    """
    Send a receipt PDF to the customer via email.
    smtp_config: {smtp_host, smtp_port, smtp_user, smtp_pass}
    Returns (success: bool, error_message: str)
    """
    if not smtp_config.get("smtp_host") or not smtp_config.get("smtp_user"):
        return False, "SMTP is not configured. Please set SMTP credentials in Settings."
    if not to_email or "@" not in to_email:
        return False, "Invalid customer email address."
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_config["smtp_user"]
        msg["To"] = to_email
        msg["Subject"] = f"Receipt — {invoice.get('invoice', 'Invoice')} | Jayraldine's Catering"

        body = f"""
<html><body style="font-family:Arial,sans-serif;color:#1F2937;">
<h2 style="color:#E11D48;">Jayraldine's Catering</h2>
<p>Dear {invoice.get('customer', 'Valued Customer')},</p>
<p>Please find attached your official receipt for your event on <strong>{invoice.get('event_date', '—')}</strong>.</p>
<table style="border-collapse:collapse;width:400px;margin:16px 0;">
  <tr><td style="padding:6px 12px;font-weight:bold;color:#374151;">Receipt #</td><td style="padding:6px 12px;">{invoice.get('invoice', '—')}</td></tr>
  <tr style="background:#F9FAFB;"><td style="padding:6px 12px;font-weight:bold;color:#374151;">Total Amount</td><td style="padding:6px 12px;">₱ {invoice.get('amount', 0.0):,.2f}</td></tr>
  <tr><td style="padding:6px 12px;font-weight:bold;color:#374151;">Amount Paid</td><td style="padding:6px 12px;">₱ {invoice.get('paid', 0.0):,.2f}</td></tr>
  <tr style="background:#F9FAFB;"><td style="padding:6px 12px;font-weight:bold;color:#374151;">Balance</td><td style="padding:6px 12px;">₱ {invoice.get('amount', 0.0) - invoice.get('paid', 0.0):,.2f}</td></tr>
  <tr><td style="padding:6px 12px;font-weight:bold;color:#374151;">Status</td><td style="padding:6px 12px;">{invoice.get('status', '—')}</td></tr>
</table>
<p>Thank you for choosing Jayraldine's Catering!</p>
</body></html>
"""
        msg.attach(MIMEText(body, "html"))

        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header(
                    "Content-Disposition", "attachment",
                    filename=os.path.basename(pdf_path),
                )
                msg.attach(attach)

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


def send_booking_confirmation_email(smtp_config: dict, to_email: str, booking: dict) -> tuple[bool, str]:
    """
    Send a booking confirmation email to the customer.
    booking: {booking_ref, customer_name, occasion, venue, event_date, pax, contact}
    Returns (success: bool, error_message: str)
    """
    if not smtp_config.get("smtp_host") or not smtp_config.get("smtp_user"):
        return False, "SMTP is not configured. Please set SMTP credentials in Settings."
    if not to_email or "@" not in to_email:
        return False, "Invalid customer email address."
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_config["smtp_user"]
        msg["To"] = to_email
        msg["Subject"] = f"Booking Confirmed — {booking.get('booking_ref', '')} | Jayraldine's Catering"

        body = f"""
<html><body style="font-family:Arial,sans-serif;color:#1F2937;">
<h2 style="color:#E11D48;">Jayraldine's Catering</h2>
<h3 style="color:#22C55E;">✓ Your Booking is Confirmed!</h3>
<p>Dear {booking.get('customer_name', 'Valued Customer')},</p>
<p>We are pleased to confirm your booking. Here are your event details:</p>
<table style="border-collapse:collapse;width:400px;margin:16px 0;">
  <tr><td style="padding:6px 12px;font-weight:bold;color:#374151;">Booking Ref</td><td style="padding:6px 12px;">{booking.get('booking_ref', '—')}</td></tr>
  <tr style="background:#F9FAFB;"><td style="padding:6px 12px;font-weight:bold;color:#374151;">Occasion</td><td style="padding:6px 12px;">{booking.get('occasion', '—')}</td></tr>
  <tr><td style="padding:6px 12px;font-weight:bold;color:#374151;">Event Date</td><td style="padding:6px 12px;">{booking.get('event_date', '—')}</td></tr>
  <tr style="background:#F9FAFB;"><td style="padding:6px 12px;font-weight:bold;color:#374151;">Venue</td><td style="padding:6px 12px;">{booking.get('venue', '—')}</td></tr>
  <tr><td style="padding:6px 12px;font-weight:bold;color:#374151;">Pax</td><td style="padding:6px 12px;">{booking.get('pax', '—')}</td></tr>
</table>
<p>If you have any questions, please contact us at {booking.get('business_contact', '')}.</p>
<p>Thank you for choosing Jayraldine's Catering!</p>
</body></html>
"""
        msg.attach(MIMEText(body, "html"))

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
