import urllib.request
import urllib.parse
import json


_SEMAPHORE_API_URL = "https://api.semaphore.co/api/v4/messages"


def send_sms(api_key: str, to_number: str, message: str) -> tuple[bool, str]:
    """
    Send an SMS via Semaphore API.
    Returns (success: bool, error_message: str)
    """
    if not api_key:
        return False, "SMS API key is not configured. Please set the Semaphore API key in Settings."
    if not to_number:
        return False, "No contact number provided."

    digits_only = "".join(c for c in to_number if c.isdigit())
    if not digits_only:
        return False, "Invalid contact number."
    if digits_only.startswith("0"):
        cleaned = "63" + digits_only[1:]
    elif digits_only.startswith("63"):
        cleaned = digits_only
    else:
        cleaned = "63" + digits_only

    try:
        payload = urllib.parse.urlencode({
            "apikey":   api_key,
            "number":   cleaned,
            "message":  message,
        }).encode("utf-8")
        req = urllib.request.Request(
            _SEMAPHORE_API_URL,
            data=payload,
            method="POST",
        )
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            if isinstance(data, list) and data:
                status = data[0].get("status", "").lower()
                if status in ("pending", "queued", "sent"):
                    return True, ""
                return False, f"Semaphore status: {status}"
            return True, ""
    except Exception as exc:
        return False, str(exc)


def send_booking_confirmation_sms(api_key: str, booking: dict) -> tuple[bool, str]:
    """Send a booking confirmation SMS to the customer."""
    contact = booking.get("contact", "")
    msg = (
        f"Hi {booking.get('customer_name', 'Customer')}! "
        f"Your booking ({booking.get('booking_ref', '')}) for "
        f"{booking.get('occasion', 'your event')} on "
        f"{booking.get('event_date', '')} has been CONFIRMED. "
        f"Venue: {booking.get('venue', 'TBD')}. "
        f"Thank you — Jayraldine's Catering"
    )
    return send_sms(api_key, contact, msg)
