"""SMS delivery via the Semaphore API.

send_sms() normalizes a Philippine phone number to the 63xxxxxxxxxx format the
gateway expects, POSTs the message, and interprets the JSON response. All
failures are returned as (False, error_message) rather than raised, and progress
is logged to stdout for debugging. send_booking_confirmation_sms() builds the
customer-facing booking confirmation text and delegates to send_sms().
"""
import urllib.request
import urllib.parse
import urllib.error
import json


# Semaphore SMS gateway endpoint (v4 messages API).
_SEMAPHORE_API_URL = "https://api.semaphore.co/api/v4/messages"


def send_sms(api_key: str, to_number: str, message: str) -> tuple[bool, str]:
    """
    Send an SMS via Semaphore API.
    Returns (success: bool, error_message: str)
    """
    if not api_key:
        err = "SMS API key is not configured."
        print(f"[SMS] ERROR: {err}")
        return False, err

    if not to_number:
        err = "No contact number provided."
        print(f"[SMS] ERROR: {err}")
        return False, err

    # Strip everything but digits so formatting (spaces, +, dashes) is ignored.
    digits_only = "".join(c for c in to_number if c.isdigit())
    if not digits_only:
        err = f"Invalid contact number: '{to_number}'"
        print(f"[SMS] ERROR: {err}")
        return False, err

    # Normalize to PH country-code form (63xxxxxxxxxx) the gateway requires:
    if digits_only.startswith("0"):
        cleaned = "63" + digits_only[1:]     # local 09xx -> 639xx
    elif digits_only.startswith("63"):
        cleaned = digits_only                # already country-coded
    else:
        cleaned = "63" + digits_only         # bare 9xx -> prepend country code

    print(f"[SMS] Sending to: {cleaned} (original: '{to_number}')")
    print(f"[SMS] API key (first 6 chars): {api_key[:6]}...")
    print(f"[SMS] Message ({len(message)} chars): {message[:80]}...")

    try:
        # Semaphore expects form-urlencoded POST body, not JSON.
        payload = urllib.parse.urlencode({
            "apikey":  api_key,
            "number":  cleaned,
            "message": message,
        }).encode("utf-8")

        print(f"[SMS] POST {_SEMAPHORE_API_URL}")

        req = urllib.request.Request(
            _SEMAPHORE_API_URL,
            data=payload,
            method="POST",
        )
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        with urllib.request.urlopen(req, timeout=15) as resp:
            http_status = resp.getcode()
            body = resp.read().decode("utf-8")
            print(f"[SMS] HTTP {http_status} — Response: {body[:300]}")
            data = json.loads(body)
            # Successful sends return a JSON array of message objects.
            if isinstance(data, list) and data:
                status = data[0].get("status", "").lower()
                msg_id = data[0].get("message_id", "")
                print(f"[SMS] Semaphore status: {status}, message_id: {msg_id}")
                # These statuses mean the gateway accepted the message.
                if status in ("pending", "queued", "sent"):
                    print(f"[SMS] SUCCESS — message queued.")
                    return True, ""
                err = f"Semaphore status: {status}"
                print(f"[SMS] FAILED — {err}")
                return False, err
            # HTTP 200 with a non-list body: treat as success (no error signaled).
            print(f"[SMS] SUCCESS — unexpected response shape but no error.")
            return True, ""

    except urllib.error.HTTPError as exc:
        # Non-2xx response: surface the status code and any error body.
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            pass
        err = f"HTTP {exc.code} {exc.reason} — {body}"
        print(f"[SMS] HTTPError: {err}")
        return False, err

    except urllib.error.URLError as exc:
        # Connection-level failure (DNS, timeout, no network, etc.).
        err = f"Network error: {exc.reason}"
        print(f"[SMS] URLError: {err}")
        return False, err

    except Exception as exc:
        # Catch-all so SMS failures never crash the caller.
        err = str(exc)
        print(f"[SMS] Unexpected error: {err}")
        return False, err


def send_booking_confirmation_sms(api_key: str, booking: dict) -> tuple[bool, str]:
    """Send a booking confirmation SMS to the customer."""
    contact = booking.get("contact", "")
    print(f"[SMS] Preparing booking confirmation for: {booking.get('customer_name')} | contact: {contact}")
    msg = (
        f"Hi {booking.get('customer_name', 'Customer')}! "
        f"Your booking ({booking.get('booking_ref', '')}) for "
        f"{booking.get('occasion', 'your event')} on "
        f"{booking.get('event_date', '')} has been CONFIRMED. "
        f"Venue: {booking.get('venue', 'TBD')}. "
        f"Thank you - Jayraldine's Catering"
    )
    return send_sms(api_key, contact, msg)
