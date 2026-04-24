"""
Repository layer — the ONLY place that touches utils.db.
All UI pages import from here, never from utils.db directly.

Each function either:
  - returns data the GUI already expects (list-of-dicts with the same keys)
  - falls back to in-memory defaults when DB is unavailable
    so the app continues to work without a database.
"""
from __future__ import annotations
from datetime import date, time
from typing import Optional
import utils.db as db
import utils.menu_store as menu_store


# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------

def get_all_customers() -> list[dict]:
    rows = db.fetchall(
        "SELECT id, name, contact, email, total_events, status::TEXT FROM customers ORDER BY name"
    )
    if rows is None:
        return []
    return [
        {
            "id":      r["id"],
            "name":    r["name"],
            "contact": r["contact"],
            "email":   r["email"] or "",
            "events":  r["total_events"],
            "status":  r["status"],
        }
        for r in rows
    ]


def add_customer(data: dict) -> Optional[int]:
    """data keys: name, contact, email, status"""
    row = db.fetchone(
        """
        INSERT INTO customers (name, contact, email, status)
        VALUES (%s, %s, %s, %s::customer_status)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (data["name"], data["contact"], data.get("email", ""), data.get("status", "Active")),
    )
    return row["id"] if row else None


def delete_customer(customer_id: int) -> None:
    db.execute("DELETE FROM customers WHERE id = %s", (customer_id,))


def get_customer_names() -> list[str]:
    rows = db.fetchall("SELECT name FROM customers WHERE status != 'Inactive' ORDER BY name")
    return [r["name"] for r in rows] if rows else []


# ---------------------------------------------------------------------------
# MENU ITEMS  (synced with utils/menu_store.py in-memory list)
# ---------------------------------------------------------------------------

def get_all_menu_items() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, name, category::TEXT, package_tier::TEXT AS package,
               price, status::TEXT
        FROM menu_items ORDER BY category, name
        """
    )
    if not rows:
        return menu_store.all_items()
    return [
        {
            "id":       r["id"],
            "item":     r["name"],
            "category": r["category"],
            "package":  r["package"],
            "price":    float(r["price"]),
            "status":   r["status"],
        }
        for r in rows
    ]


def get_available_menu_items() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, name, category::TEXT, package_tier::TEXT AS package,
               price, status::TEXT
        FROM menu_items WHERE status IN ('Available','Seasonal') ORDER BY category, name
        """
    )
    if not rows:
        return menu_store.get_available_items()
    return [
        {
            "id":       r["id"],
            "item":     r["name"],
            "category": r["category"],
            "package":  r["package"],
            "price":    float(r["price"]),
            "status":   r["status"],
        }
        for r in rows
    ]


def add_menu_item(data: dict) -> Optional[int]:
    """data keys: item, category, package, price, status"""
    rows = db.callproc(
        "add_menu_item",
        (data["item"], data["category"], data["package"],
         data["price"], data["status"]),
    )
    if rows:
        new_id = list(rows[0].values())[0]
        menu_store.add_item(data)
        return new_id
    menu_store.add_item(data)
    return None


def delete_menu_item(index: int, item_name: str) -> None:
    db.execute("DELETE FROM menu_items WHERE name = %s", (item_name,))
    menu_store.remove_item(index)


# ---------------------------------------------------------------------------
# PACKAGES
# ---------------------------------------------------------------------------

def get_all_packages() -> list[dict]:
    rows = db.fetchall(
        "SELECT id, name, price_per_pax, description FROM packages ORDER BY price_per_pax"
    )
    if not rows:
        return [
            {"id": 1, "name": "Standard Package", "price_per_pax": 1500.0, "description": "Buffet setup, 5 dishes, dessert"},
            {"id": 2, "name": "Premium Package",  "price_per_pax": 2500.0, "description": "Plated service, 8 dishes, dessert + drinks"},
            {"id": 3, "name": "VIP Package",       "price_per_pax": 3500.0, "description": "Full service, 12 dishes, open bar, décor"},
        ]
    return [
        {
            "id":            r["id"],
            "name":          r["name"],
            "price_per_pax": float(r["price_per_pax"]),
            "description":   r["description"] or "",
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# BOOKINGS
# ---------------------------------------------------------------------------

def get_all_bookings() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, booking_ref, customer_name, event_date, pax,
               total_amount, status::TEXT
        FROM bookings ORDER BY event_date DESC
        """
    )
    if not rows:
        return []
    return [
        {
            "db_id":  r["id"],
            "id":     r["booking_ref"],
            "date":   r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
            "name":   r["customer_name"],
            "pax":    str(r["pax"]),
            "total":  f"₱ {int(r['total_amount']):,}",
            "status": r["status"],
        }
        for r in rows
    ]


def create_booking(data: dict) -> Optional[dict]:
    """
    data keys match BookingModal._save() output:
      name, contact, email, address, occasion, venue,
      date (str "MMM dd, yyyy"), time (str "hh:mm AP"),
      pax (int), notes, menu_type, menu_value,
      payment_mode, amount_paid (str), total (int)
    Returns dict with booking_id and booking_ref, or None on failure.
    """
    try:
        event_date = _parse_date(data["date"])
        event_time = _parse_time(data.get("time", "6:00 PM"))
        amount_paid = _parse_amount(data.get("amount_paid", "0"))

        package_id = None
        if data.get("menu_type") == "package":
            pkg_row = db.fetchone(
                "SELECT id FROM packages WHERE name = %s", (data.get("menu_value"),)
            )
            if pkg_row:
                package_id = pkg_row["id"]

        rows = db.callproc("create_booking", (
            data["name"],
            data.get("contact", ""),
            data.get("email", ""),
            data.get("address", ""),
            data.get("occasion", ""),
            data.get("venue", ""),
            event_date,
            event_time,
            data["pax"],
            data.get("notes", ""),
            data.get("menu_type", "package"),
            package_id,
            data.get("menu_value", "") if data.get("menu_type") == "custom" else None,
            data["total"],
            data.get("payment_mode", "Cash"),
            amount_paid,
        ))
        if rows:
            return {"booking_id": rows[0]["booking_id"], "booking_ref": rows[0]["booking_ref"]}
    except Exception as exc:
        print(f"[repository] create_booking failed: {exc}")
    return None


def update_booking_status(db_id: int, new_status: str) -> None:
    try:
        db.execute("SELECT update_booking_status(%s, %s)", (db_id, new_status))
    except Exception as exc:
        print(f"[repository] update_booking_status failed: {exc}")


def delete_booking(db_id: int) -> None:
    db.execute("DELETE FROM bookings WHERE id = %s", (db_id,))


# ---------------------------------------------------------------------------
# INVOICES
# ---------------------------------------------------------------------------

def get_all_invoices() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, invoice_ref, customer_name, event_date,
               total_amount, amount_paid, status::TEXT
        FROM invoices ORDER BY created_at DESC
        """
    )
    if not rows:
        return []
    return [
        {
            "db_id":      r["id"],
            "invoice":    r["invoice_ref"],
            "customer":   r["customer_name"],
            "event_date": r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
            "amount":     float(r["total_amount"]),
            "paid":       float(r["amount_paid"]),
            "status":     r["status"],
        }
        for r in rows
    ]


def create_invoice(data: dict) -> Optional[dict]:
    """
    data keys: customer, event_date (str), amount (float), paid (float), status (str)
    Returns dict with invoice_id and invoice_ref.
    """
    try:
        event_date = _parse_date(data["event_date"])
        rows = db.callproc("generate_invoice", (
            None,
            data["customer"],
            event_date,
            data["amount"],
            data["paid"],
            data["status"],
        ))
        if rows:
            return {"invoice_id": rows[0]["invoice_id"], "invoice_ref": rows[0]["invoice_ref"]}
    except Exception as exc:
        print(f"[repository] create_invoice failed: {exc}")
    return None


def delete_invoice(db_id: int) -> None:
    db.execute("DELETE FROM invoices WHERE id = %s", (db_id,))


# ---------------------------------------------------------------------------
# KITCHEN ORDERS
# ---------------------------------------------------------------------------

def get_all_orders() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, order_ref, client_name, event_name, pax, items_desc, status::TEXT
        FROM kitchen_orders WHERE status != 'Done' ORDER BY created_at
        """
    )
    if not rows:
        return []
    return [
        {
            "db_id":  r["id"],
            "id":     r["order_ref"],
            "client": r["client_name"],
            "event":  r["event_name"],
            "pax":    r["pax"],
            "items":  r["items_desc"],
            "status": r["status"],
        }
        for r in rows
    ]


def update_order_status(db_id: int, new_status: str) -> None:
    try:
        db.execute("SELECT update_kitchen_order_status(%s, %s)", (db_id, new_status))
    except Exception as exc:
        print(f"[repository] update_order_status failed: {exc}")


def mark_order_done(db_id: int) -> None:
    update_order_status(db_id, "Done")


# ---------------------------------------------------------------------------
# INVENTORY
# ---------------------------------------------------------------------------

def get_all_inventory() -> list[dict]:
    rows = db.fetchall(
        "SELECT id, ingredient, unit::TEXT, stock, min_stock FROM inventory ORDER BY ingredient"
    )
    if not rows:
        return []
    return [
        {
            "id":        r["id"],
            "ingredient": r["ingredient"],
            "unit":      r["unit"],
            "stock":     float(r["stock"]),
            "min_stock": float(r["min_stock"]),
            "status":    "Low Stock" if r["stock"] < r["min_stock"] else "OK",
        }
        for r in rows
    ]


def get_low_stock_items() -> list[dict]:
    rows = db.fetchall(
        "SELECT * FROM v_inventory_alerts"
    )
    return rows if rows else []


# ---------------------------------------------------------------------------
# NOTIFICATIONS
# ---------------------------------------------------------------------------

def get_unread_notifications() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, type, title, message, color
        FROM notifications WHERE is_read = FALSE ORDER BY created_at DESC
        """
    )
    if not rows:
        return []
    return [dict(r) for r in rows]


def dismiss_notification(notif_id: int) -> None:
    try:
        db.execute("SELECT dismiss_notification(%s)", (notif_id,))
    except Exception as exc:
        print(f"[repository] dismiss_notification failed: {exc}")


def mark_all_notifications_read() -> None:
    try:
        db.execute("SELECT mark_all_notifications_read()")
    except Exception as exc:
        print(f"[repository] mark_all_notifications_read failed: {exc}")


# ---------------------------------------------------------------------------
# DASHBOARD KPIs
# ---------------------------------------------------------------------------

def get_dashboard_kpis() -> dict:
    row = db.fetchone("SELECT * FROM v_dashboard_kpis")
    if not row:
        return {
            "todays_events":    0,
            "pending_bookings": 0,
            "weekly_revenue":   0,
            "unpaid_invoices":  0,
            "todays_pax":       0,
        }
    return {
        "todays_events":    int(row["todays_events"]),
        "pending_bookings": int(row["pending_bookings"]),
        "weekly_revenue":   float(row["weekly_revenue"]),
        "unpaid_invoices":  float(row["unpaid_invoices"]),
        "todays_pax":       int(row["todays_pax"]),
    }


def get_upcoming_events(limit: int = 10) -> list[dict]:
    rows = db.fetchall(
        "SELECT * FROM v_upcoming_events LIMIT %s", (limit,)
    )
    return [dict(r) for r in rows] if rows else []


def get_calendar_summary() -> list[dict]:
    rows = db.fetchall("SELECT * FROM v_calendar_day_summary")
    return [dict(r) for r in rows] if rows else []


# ---------------------------------------------------------------------------
# BUSINESS INFO (Settings page)
# ---------------------------------------------------------------------------

def get_business_info() -> dict:
    row = db.fetchone("SELECT name, contact, email, address FROM business_info LIMIT 1")
    if not row:
        return {
            "name":    "Jayraldine's Catering",
            "contact": "+63 912 345 6789",
            "email":   "admin@jayraldines.com",
            "address": "123 Rizal St., Manila, Metro Manila",
        }
    return dict(row)


def save_business_info(data: dict) -> None:
    db.execute(
        """
        UPDATE business_info
        SET name = %s, contact = %s, email = %s, address = %s, updated_at = NOW()
        WHERE id = 1
        """,
        (data["name"], data["contact"], data["email"], data["address"]),
    )


# ---------------------------------------------------------------------------
# PRIVATE HELPERS
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s!r}")


def _parse_time(s: str) -> time:
    from datetime import datetime as dt
    for fmt in ("%I:%M %p", "%H:%M", "%H:%M:%S"):
        try:
            return dt.strptime(s.strip().upper(), fmt).time()
        except ValueError:
            continue
    return time(18, 0)


def _parse_amount(s) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    cleaned = str(s).replace("₱", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
