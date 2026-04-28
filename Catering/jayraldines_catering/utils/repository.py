"""
Repository layer — the ONLY place that touches utils.db.
All UI pages import from here, never from utils.db directly.

Each function either:
  - calls a stored procedure via db.callproc_out / db.callproc_void
  - returns data the GUI already expects (list-of-dicts with the same keys)
  - falls back to in-memory defaults when DB is unavailable
"""
from __future__ import annotations
from datetime import date, time, datetime
from typing import Optional
import utils.db as db
import utils.menu_store as menu_store


# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------

def get_all_customers() -> list[dict]:
    rows = db.fetchall(
        "SELECT id, name, contact, email, address, total_events, status::TEXT FROM customers ORDER BY name"
    )
    if rows is None:
        return []
    return [
        {
            "id":      r["id"],
            "name":    r["name"],
            "contact": r["contact"],
            "email":   r["email"] or "",
            "address": r["address"] or "",
            "events":  r["total_events"],
            "status":  r["status"],
        }
        for r in rows
    ]


def add_customer(data: dict) -> Optional[int]:
    """data keys: name, contact, email, address, status"""
    result = db.callproc_out(
        "sp_add_customer",
        in_params=(
            data["name"],
            data.get("contact", ""),
            data.get("email", ""),
            data.get("address", ""),
            data.get("status", "Active"),
        ),
        out_names=["p_customer_id"],
    )
    return result["p_customer_id"] if result else None


def update_customer(customer_id: int, data: dict) -> None:
    """data keys: name, contact, email, address, status"""
    db.callproc_void(
        "sp_update_customer",
        in_params=(
            customer_id,
            data["name"],
            data.get("contact", ""),
            data.get("email", ""),
            data.get("address", ""),
            data.get("status", "Active"),
        ),
    )


def delete_customer(customer_id: int) -> None:
    db.callproc_void("sp_delete_customer", in_params=(customer_id,))


def get_customer_names() -> list[str]:
    rows = db.fetchall("SELECT name FROM customers WHERE status != 'Inactive' ORDER BY name")
    return [r["name"] for r in rows] if rows else []


def get_customer_email_by_name(name: str) -> str:
    row = db.fetchone("SELECT email FROM customers WHERE name = %s LIMIT 1", (name,))
    return (row["email"] or "") if row else ""


def get_customer_event_dates(name: str) -> list[dict]:
    """Return list of dicts {'date': '...', 'id': ...} for a customer's valid bookings."""
    rows = db.fetchall(
        """
        SELECT id, event_date
        FROM bookings
        WHERE customer_name = %s AND status NOT IN ('CANCELLED')
        ORDER BY event_date DESC
        """,
        (name,),
    )
    if not rows:
        return []
    from datetime import date as _d
    return [
        {
            "id": r["id"],
            "date": r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], _d) else str(r["event_date"])
        }
        for r in rows
    ]

# ---------------------------------------------------------------------------
# MENU ITEMS
# ---------------------------------------------------------------------------

def get_all_menu_items() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, name, description, category::TEXT, package_tier::TEXT AS package,
               price, status::TEXT
        FROM menu_items ORDER BY category, name
        """
    )
    if not rows:
        return menu_store.all_items()
    return [
        {
            "id":          r["id"],
            "item":        r["name"],
            "description": r["description"] or "",
            "category":    r["category"],
            "package":     r["package"],
            "price":       float(r["price"]),
            "status":      r["status"],
        }
        for r in rows
    ]


def get_available_menu_items() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, name, description, category::TEXT, package_tier::TEXT AS package,
               price, status::TEXT
        FROM menu_items WHERE status IN ('Available','Seasonal') ORDER BY category, name
        """
    )
    if not rows:
        return menu_store.get_available_items()
    return [
        {
            "id":          r["id"],
            "item":        r["name"],
            "description": r["description"] or "",
            "category":    r["category"],
            "package":     r["package"],
            "price":       float(r["price"]),
            "status":      r["status"],
        }
        for r in rows
    ]


def add_menu_item(data: dict) -> Optional[int]:
    """data keys: item, description, category, package, price, status"""
    result = db.callproc_out(
        "sp_add_menu_item",
        in_params=(
            data["item"],
            data.get("description", ""),
            data["category"],
            data["package"],
            data["price"],
            data["status"],
        ),
        out_names=["p_item_id"],
    )
    menu_store.add_item(data)
    return result["p_item_id"] if result else None


def update_menu_item(item_id: int, data: dict) -> None:
    """data keys: item, description, category, package, price, status"""
    db.callproc_void(
        "sp_update_menu_item",
        in_params=(
            item_id,
            data["item"],
            data.get("description", ""),
            data["category"],
            data["package"],
            data["price"],
            data["status"],
        ),
    )


def delete_menu_item(index: int, item_id: int) -> None:
    db.callproc_void("sp_delete_menu_item", in_params=(item_id,))
    menu_store.remove_item(index)


# ---------------------------------------------------------------------------
# PACKAGES
# ---------------------------------------------------------------------------

def get_all_packages() -> list[dict]:
    rows = db.fetchall(
        "SELECT id, name, price_per_pax, min_pax, description FROM packages ORDER BY price_per_pax"
    )
    if not rows:
        return []
    return [
        {
            "id":            r["id"],
            "name":          r["name"],
            "price_per_pax": float(r["price_per_pax"]),
            "min_pax":       int(r["min_pax"]),
            "description":   r["description"] or "",
        }
        for r in rows
    ]

def get_package_items(package_id: int) -> list[dict]:
    """Return menu items linked to a package with their custom prices."""
    rows = db.fetchall(
        """
        SELECT pi.id, pi.menu_item_id, mi.name AS item_name,
               mi.category::TEXT AS category, pi.custom_price
        FROM package_items pi
        JOIN menu_items mi ON mi.id = pi.menu_item_id
        WHERE pi.package_id = %s
        ORDER BY mi.category, mi.name
        """,
        (package_id,),
    )
    if not rows:
        return []
    return [
        {
            "id":           r["id"],
            "menu_item_id": r["menu_item_id"],
            "item_name":    r["item_name"],
            "category":     r["category"],
            "custom_price": float(r["custom_price"]),
        }
        for r in rows
    ]

def set_package_items(package_id: int, items: list[dict]) -> bool:
    """Replace all package items. items: list of {menu_item_id, custom_price}."""
    try:
        if not items:
            db.callproc_void(
                "sp_set_package_items",
                in_params=(package_id, None, None),
            )
        else:
            ids    = [i["menu_item_id"] for i in items]
            prices = [i["custom_price"]  for i in items]
            db.callproc_void(
                "sp_set_package_items",
                in_params=(package_id, ids, prices),
            )
        return True
    except Exception as exc:
        print(f"[repository] set_package_items failed: {exc}")
        return False

def add_package(data: dict) -> Optional[int]:
    """data keys: name, price_per_pax, min_pax, description. Returns new package id."""
    try:
        result = db.callproc_out(
            "sp_add_package",
            in_params=(
                data["name"],
                data["price_per_pax"],
                data.get("min_pax", 1),
                data.get("description", ""),
            ),
            out_names=["p_package_id"],
        )
        return result["p_package_id"] if result else None
    except Exception as exc:
        print(f"[repository] add_package failed: {exc}")
        return None

def update_package(db_id: int, data: dict) -> bool:
    """data keys: name, price_per_pax, min_pax, description. Returns True on success."""
    try:
        db.callproc_void(
            "sp_update_package",
            in_params=(
                db_id,
                data["name"],
                data["price_per_pax"],
                data.get("min_pax", 1),
                data.get("description", ""),
            ),
        )
        return True
    except Exception as exc:
        print(f"[repository] update_package failed: {exc}")
        return False

def delete_package(db_id: int) -> bool:
    """Returns True on success, False if linked to bookings."""
    try:
        db.callproc_void("sp_delete_package", in_params=(db_id,))
        return True
    except Exception as exc:
        print(f"[repository] delete_package failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# BOOKINGS
# ---------------------------------------------------------------------------

def get_all_bookings(period_filter: str = "") -> list[dict]:
    rows = db.fetchall(
        f"""
        SELECT id, booking_ref, customer_name, event_date, pax,
               total_amount, status::TEXT, cancellation_reason
        FROM bookings
        WHERE 1=1 {period_filter}
        ORDER BY event_date DESC
        """
    )
    if not rows:
        return []
    return [
        {
            "db_id":               r["id"],
            "id":                  r["booking_ref"],
            "date":                r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
            "name":                r["customer_name"],
            "pax":                 str(r["pax"]),
            "total":               f"₱ {int(r['total_amount']):,}",
            "status":              r["status"],
            "cancellation_reason": r["cancellation_reason"] or "",
        }
        for r in rows
    ]


def create_booking(data: dict) -> Optional[dict]:
    """
    data keys: name, contact, email, address, occasion, venue,
      date (str), time (str), pax (int), notes, menu_type, menu_value,
      payment_mode, amount_paid, total (int)
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

        result = db.callproc_out(
            "sp_create_booking",
            in_params=(
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
            ),
            out_names=["p_booking_id", "p_booking_ref"],
        )
        if result:
            return {"booking_id": result["p_booking_id"], "booking_ref": result["p_booking_ref"]}
    except Exception as exc:
        print(f"[repository] create_booking failed: {exc}")
    return None


def update_booking(db_id: int, data: dict) -> None:
    """data keys: name, contact, email, address, occasion, venue,
       date (str), time (str), pax (int), notes, menu_type, menu_value,
       payment_mode, amount_paid, total"""
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

        db.callproc_void(
            "sp_update_booking",
            in_params=(
                db_id,
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
            ),
        )
    except Exception as exc:
        print(f"[repository] update_booking failed: {exc}")


def update_booking_status(db_id: int, new_status: str, cancellation_reason: str = None) -> None:
    db.callproc_void("sp_update_booking_status", in_params=(db_id, new_status, cancellation_reason))


def check_date_capacity(event_date, exclude_id: int = 0) -> dict:
    """Returns {booked_pax, max_pax, is_over}."""
    result = db.callproc_out(
        "sp_check_date_capacity",
        in_params=(event_date, exclude_id or 0),
        out_names=["p_booked_pax", "p_max_pax", "p_is_over"],
    )
    if not result:
        return {"booked_pax": 0, "max_pax": 600, "is_over": False}
    return {
        "booked_pax": int(result["p_booked_pax"]),
        "max_pax":    int(result["p_max_pax"]),
        "is_over":    bool(result["p_is_over"]),
    }


def delete_booking(db_id: int) -> None:
    db.callproc_void("sp_delete_booking", in_params=(db_id,))


def complete_booking(db_id: int) -> bool:
    """Mark a CONFIRMED booking as COMPLETED. Returns True on success."""
    try:
        db.callproc_void("sp_complete_booking", in_params=(db_id,))
        return True
    except Exception as exc:
        print(f"[repository] complete_booking failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# INVOICES
# ---------------------------------------------------------------------------

def get_all_invoices() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT i.id, i.invoice_ref, i.customer_name, i.event_date,
               i.total_amount, i.amount_paid, i.status::TEXT,
               COALESCE(c.email, '') AS customer_email
        FROM invoices i
        LEFT JOIN customers c ON c.name = i.customer_name
        ORDER BY i.created_at DESC
        """
    )
    if not rows:
        return []
    return [
        {
            "db_id":          r["id"],
            "invoice":        r["invoice_ref"],
            "customer":       r["customer_name"],
            "customer_email": r["customer_email"],
            "event_date":     r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
            "amount":         float(r["total_amount"]),
            "paid":           float(r["amount_paid"]),
            "status":         r["status"],
        }
        for r in rows
    ]


def create_invoice(data: dict) -> Optional[dict]:
    """data keys: booking_id (int|None), customer, event_date (str), amount, paid, status"""
    try:
        event_date = _parse_date(data["event_date"])
        result = db.callproc_out(
            "sp_create_invoice",
            in_params=(
                data.get("booking_id"), # FIX: Now correctly passing the ID to the DB
                data["customer"],
                event_date,
                data["amount"],
                data["paid"],
                data["status"],
            ),
            out_names=["p_invoice_id", "p_invoice_ref"],
        )
        if result:
            return {"invoice_id": result["p_invoice_id"], "invoice_ref": result["p_invoice_ref"]}
    except Exception as exc:
        print(f"[repository] create_invoice failed: {exc}")
    return None

def update_invoice(db_id: int, data: dict) -> None:
    """data keys: customer, event_date (str), amount (float), paid (float), status (str)"""
    try:
        event_date = _parse_date(data["event_date"])
        db.callproc_void(
            "sp_update_invoice",
            in_params=(
                db_id,
                data["customer"],
                event_date,
                data["amount"],
                data["paid"],
                data["status"],
            ),
        )
    except Exception as exc:
        print(f"[repository] update_invoice failed: {exc}")


def record_payment(invoice_id: int, amount: float) -> Optional[str]:
    """Returns new status string or None on failure."""
    result = db.callproc_out(
        "sp_record_payment",
        in_params=(invoice_id, amount),
        out_names=["p_new_status"],
    )
    return result["p_new_status"] if result else None


def delete_invoice(db_id: int) -> None:
    db.callproc_void("sp_delete_invoice", in_params=(db_id,))


def add_payment_record(invoice_id: int, amount: float,
                       payment_date, method: str = "Cash", note: str = "") -> Optional[dict]:
    """Returns {record_id, new_status, new_paid} or None on failure."""
    try:
        from datetime import date as _d
        if payment_date is None:
            payment_date = _d.today()
        elif isinstance(payment_date, str):
            payment_date = _parse_date(payment_date)
        result = db.callproc_out(
            "sp_add_payment_record",
            in_params=(invoice_id, amount, payment_date, method, note or None),
            out_names=["p_record_id", "p_new_status", "p_new_paid"],
        )
        if result:
            return {
                "record_id":  result["p_record_id"],
                "new_status": result["p_new_status"],
                "new_paid":   float(result["p_new_paid"]),
            }
    except Exception as exc:
        print(f"[repository] add_payment_record failed: {exc}")
        raise
    return None


def get_payment_records(invoice_id: int) -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, amount, payment_date, method, note, created_at
        FROM payment_records
        WHERE invoice_id = %s
        ORDER BY payment_date DESC, created_at DESC
        """,
        (invoice_id,),
    )
    if not rows:
        return []
    return [
        {
            "id":           r["id"],
            "amount":       float(r["amount"]),
            "payment_date": r["payment_date"].strftime("%b %d, %Y") if hasattr(r["payment_date"], "strftime") else str(r["payment_date"]),
            "method":       r["method"],
            "note":         r["note"] or "",
        }
        for r in rows
    ]


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


def create_kitchen_order(data: dict) -> Optional[dict]:
    """data keys: booking_id (int or None), client, event, pax, items"""
    result = db.callproc_out(
        "sp_create_kitchen_order",
        in_params=(
            data.get("booking_id"),
            data["client"],
            data["event"],
            data["pax"],
            data["items"],
        ),
        out_names=["p_order_id", "p_order_ref"],
    )
    if result:
        return {"order_id": result["p_order_id"], "order_ref": result["p_order_ref"]}
    return None


def update_order_status(db_id: int, new_status: str) -> None:
    db.callproc_void("sp_update_kitchen_order_status", in_params=(db_id, new_status))


def mark_order_done(db_id: int) -> None:
    update_order_status(db_id, "Done")


def delete_kitchen_order(db_id: int) -> None:
    db.callproc_void("sp_delete_kitchen_order", in_params=(db_id,))


def _auto_generate_kitchen_tasks(order_id: int, items_desc: str) -> None:
    """Split items_desc by comma and create one kitchen task per item."""
    try:
        existing = db.fetchone(
            "SELECT COUNT(*) AS cnt FROM kitchen_tasks WHERE order_id = %s", (order_id,)
        )
        if existing and existing["cnt"] > 0:
            return
        items = [item.strip() for item in items_desc.split(",") if item.strip()]
        for idx, item in enumerate(items):
            add_kitchen_task(order_id, f"Prepare: {item}", sort_order=idx)
    except Exception as exc:
        print(f"[repo] _auto_generate_kitchen_tasks: {exc}")


def sync_kitchen_from_bookings() -> int:
    """Auto-add CONFIRMED bookings that have no kitchen_order yet. Returns count added."""
    try:
        rows = db.fetchall(
            """
            SELECT b.id, b.booking_ref, b.customer_name, b.occasion, b.pax, b.event_date
            FROM bookings b
            WHERE b.status = 'CONFIRMED'
              AND NOT EXISTS (
                  SELECT 1 FROM kitchen_orders ko WHERE ko.booking_id = b.id
              )
            ORDER BY b.event_date
            """
        )
        if not rows:
            return 0
        count = 0
        for r in rows:
            occasion = r["occasion"] or "Catering Event"
            # Fetch menu items for this booking to use as task labels
            booking_detail = db.fetchone(
                "SELECT menu_type, custom_items, package_id FROM bookings WHERE id = %s",
                (r["id"],),
            )
            if booking_detail and booking_detail["menu_type"] == "custom" and booking_detail["custom_items"]:
                items_desc = booking_detail["custom_items"]
            elif booking_detail and booking_detail["package_id"]:
                pkg = db.fetchone("SELECT name FROM packages WHERE id = %s", (booking_detail["package_id"],))
                items_desc = pkg["name"] if pkg else f"Package for {int(r['pax'])} pax"
            else:
                items_desc = f"Event on {r['event_date']} — {int(r['pax'])} pax"
            result = create_kitchen_order({
                "booking_id": r["id"],
                "client":     r["customer_name"],
                "event":      occasion,
                "pax":        int(r["pax"]),
                "items":      items_desc,
            })
            if result and result.get("order_id"):
                _auto_generate_kitchen_tasks(result["order_id"], items_desc)
            count += 1
        return count
    except Exception as exc:
        print(f"[repo] sync_kitchen_from_bookings: {exc}")
        return 0


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
            "id":         r["id"],
            "ingredient": r["ingredient"],
            "unit":       r["unit"],
            "stock":      float(r["stock"]),
            "min_stock":  float(r["min_stock"]),
            "status":     "Low Stock" if r["stock"] < r["min_stock"] else "OK",
        }
        for r in rows
    ]


def add_inventory_item(data: dict) -> Optional[int]:
    """data keys: ingredient, unit, stock, min_stock, expiry_date (optional)"""
    result = db.callproc_out(
        "sp_add_inventory_item",
        in_params=(
            data["ingredient"],
            data["unit"],
            data.get("stock", 0),
            data.get("min_stock", 0),
            data.get("expiry_date", None),
        ),
        out_names=["p_item_id"],
    )
    return result["p_item_id"] if result else None


def update_inventory_item(item_id: int, data: dict) -> None:
    """data keys: ingredient, unit, min_stock, expiry_date (optional)"""
    db.callproc_void(
        "sp_update_inventory_item",
        in_params=(
            item_id,
            data["ingredient"],
            data["unit"],
            data.get("min_stock", 0),
            data.get("expiry_date", None),
        ),
    )


def adjust_inventory_stock(item_id: int, delta: float) -> Optional[float]:
    """Returns new stock level or None on failure."""
    result = db.callproc_out(
        "sp_adjust_inventory_stock",
        in_params=(item_id, delta),
        out_names=["p_new_stock"],
    )
    return float(result["p_new_stock"]) if result and result.get("p_new_stock") is not None else None


def delete_inventory_item(item_id: int) -> None:
    db.callproc_void("sp_delete_inventory_item", in_params=(item_id,))


def get_low_stock_items() -> list[dict]:
    rows = db.fetchall("SELECT * FROM v_inventory_alerts")
    return rows if rows else []


# ---------------------------------------------------------------------------
# NOTIFICATIONS
# ---------------------------------------------------------------------------

def push_notification(type_: str, title: str, message: str, color: str = "#3B82F6") -> None:
    db.callproc_out(
        "sp_push_notification",
        in_params=(type_, title, message, color),
        out_names=["p_id"],
    )


def get_event_alert_candidates() -> list[dict]:
    return db.callproc_cursor("sp_get_event_alert_candidates", "event_alert_cursor")


def get_upcoming_bookings_for_alerts() -> list[dict]:
    from datetime import datetime, date as date_type, time as time_type
    rows = db.fetchall(
        """
        SELECT booking_ref, customer_name, event_date, event_time
        FROM bookings
        WHERE status = 'CONFIRMED'
          AND event_date >= CURRENT_DATE - INTERVAL '1 day'
          AND event_date <= CURRENT_DATE + INTERVAL '2 days'
        ORDER BY event_date, event_time
        """
    )
    result = []
    for r in rows:
        try:
            ed = r["event_date"]
            et = r["event_time"]
            if isinstance(ed, date_type) and isinstance(et, time_type):
                event_dt = datetime.combine(ed, et.replace(tzinfo=None) if hasattr(et, 'tzinfo') else et)
            else:
                continue
            result.append({
                "booking_ref":   r["booking_ref"],
                "customer_name": r["customer_name"],
                "event_dt":      event_dt,
            })
        except Exception as e:
            print(f"[alerts] skip row: {e}")
            continue
    return result


def get_unread_notifications() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT id, type, title, message, color, created_at
        FROM notifications WHERE is_read = FALSE ORDER BY created_at DESC
        """
    )
    if not rows:
        return []
    return [dict(r) for r in rows]


def dismiss_notification(notif_id: int) -> None:
    db.callproc_void("sp_dismiss_notification", in_params=(notif_id,))


def mark_all_notifications_read() -> None:
    db.callproc_void("sp_mark_all_notifications_read")


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
    rows = db.fetchall("SELECT * FROM v_upcoming_events LIMIT %s", (limit,))
    return [dict(r) for r in rows] if rows else []


def get_report_kpis(period_filter: str = "") -> dict:
    if period_filter:
        row = db.fetchone(
            f"""
            SELECT
                COUNT(*)::INT                               AS total_bookings,
                COALESCE(SUM(pax),0)::INT                   AS total_pax,
                COALESCE(SUM(total_amount),0)::FLOAT        AS total_revenue,
                0::FLOAT                                    AS unpaid_amount,
                COALESCE((SELECT COUNT(*) FROM bookings WHERE DATE(event_date)=CURRENT_DATE),0)::INT AS today_bookings,
                COALESCE((SELECT COUNT(*) FROM bookings WHERE event_date BETWEEN date_trunc('week',CURRENT_DATE) AND date_trunc('week',CURRENT_DATE)+INTERVAL '6 days'),0)::INT AS week_bookings
            FROM bookings WHERE 1=1 {period_filter}
            """
        )
    else:
        row = db.fetchone("SELECT * FROM v_report_kpis")
    if not row:
        return {"total_bookings": 0, "total_pax": 0, "total_revenue": 0.0,
                "unpaid_amount": 0.0, "today_bookings": 0, "week_bookings": 0}
    return {
        "total_bookings":  int(row["total_bookings"]),
        "total_pax":       int(row["total_pax"]),
        "total_revenue":   float(row["total_revenue"]),
        "unpaid_amount":   float(row["unpaid_amount"]),
        "today_bookings":  int(row["today_bookings"]),
        "week_bookings":   int(row["week_bookings"]),
    }


def get_monthly_income() -> list[dict]:
    rows = db.fetchall("SELECT month_label, month_num, total_revenue, total_paid FROM v_monthly_income")
    if not rows:
        return []
    return [{"month": r["month_label"], "month_num": r["month_num"],
             "revenue": float(r["total_revenue"]), "paid": float(r["total_paid"])} for r in rows]


def get_payment_methods() -> list[dict]:
    rows = db.fetchall("SELECT method, total FROM v_payment_methods")
    if not rows:
        return []
    return [{"method": r["method"], "total": int(r["total"])} for r in rows]


def get_top_menu_items() -> list[dict]:
    rows = db.fetchall("SELECT item, order_count FROM v_top_menu_items")
    if not rows:
        return []
    return [{"item": r["item"], "count": int(r["order_count"])} for r in rows]


def get_customer_order_frequency() -> list[dict]:
    rows = db.fetchall("SELECT name, booking_count FROM v_customer_order_frequency")
    if not rows:
        return []
    return [{"name": r["name"], "count": int(r["booking_count"])} for r in rows]


def get_recent_activity(limit: int = 5) -> list[dict]:
    rows = db.fetchall(
        "SELECT title, description, color, created_at FROM v_recent_activity LIMIT %s",
        (limit,)
    )
    if not rows:
        return []
    from datetime import timezone
    now = datetime.now(timezone.utc)
    result = []
    for r in rows:
        ts = r["created_at"]
        if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
            delta = now - ts
        else:
            delta = datetime.utcnow() - ts.replace(tzinfo=None)
        secs = int(delta.total_seconds())
        if secs < 60:
            time_str = "just now"
        elif secs < 3600:
            time_str = f"{secs // 60} min ago"
        elif secs < 86400:
            time_str = f"{secs // 3600} hr ago"
        else:
            time_str = f"{secs // 86400}d ago"
        result.append({
            "title":       r["title"],
            "description": r["description"],
            "color":       r["color"],
            "time":        time_str,
        })
    return result


def get_menu_alerts() -> list[dict]:
    rows = db.fetchall("SELECT item, issue, badge_type FROM v_menu_alerts")
    if not rows:
        return []
    return [{"item": r["item"], "issue": r["issue"], "badge_type": r["badge_type"]} for r in rows]


def get_calendar_summary() -> list[dict]:
    rows = db.fetchall("SELECT * FROM v_calendar_day_summary")
    return [dict(r) for r in rows] if rows else []


# ---------------------------------------------------------------------------
# BUSINESS INFO (Settings page)
# ---------------------------------------------------------------------------

def get_business_policy() -> dict:
    row = db.fetchone(
        "SELECT min_downpayment_pct, allow_zero_downpayment, max_daily_pax FROM business_info LIMIT 1"
    )
    if not row:
        return {"min_downpayment_pct": 30.0, "allow_zero_downpayment": False, "max_daily_pax": 600}
    return {
        "min_downpayment_pct":    float(row["min_downpayment_pct"]),
        "allow_zero_downpayment": bool(row["allow_zero_downpayment"]),
        "max_daily_pax":          int(row["max_daily_pax"]),
    }


def save_booking_policy(min_pct: float, allow_zero: bool) -> None:
    db.callproc_void("sp_save_booking_policy", in_params=(min_pct, allow_zero))


def save_capacity_policy(max_pax: int) -> None:
    db.callproc_void("sp_save_capacity_policy", in_params=(max_pax,))


# ---------------------------------------------------------------------------
# EXPENSES
# ---------------------------------------------------------------------------

def get_all_expenses() -> list[dict]:
    rows = db.fetchall(
        "SELECT id, category::TEXT, description, amount, expense_date FROM expenses ORDER BY expense_date DESC"
    )
    if not rows:
        return []
    return [
        {
            "id":          r["id"],
            "category":    r["category"],
            "description": r["description"],
            "amount":      float(r["amount"]),
            "date":        r["expense_date"].strftime("%b %d, %Y") if hasattr(r["expense_date"], "strftime") else str(r["expense_date"]),
        }
        for r in rows
    ]


def add_expense(data: dict) -> Optional[int]:
    result = db.callproc_out(
        "sp_add_expense",
        in_params=(data["category"], data["description"], data["amount"], _parse_date(data["date"])),
        out_names=["p_expense_id"],
    )
    return result["p_expense_id"] if result else None


def update_expense(expense_id: int, data: dict) -> None:
    db.callproc_void(
        "sp_update_expense",
        in_params=(expense_id, data["category"], data["description"], data["amount"], _parse_date(data["date"])),
    )


def delete_expense(expense_id: int) -> None:
    db.callproc_void("sp_delete_expense", in_params=(expense_id,))


def get_profit_summary() -> list[dict]:
    rows = db.fetchall("SELECT month_num, month_label, revenue, total_expense, net_profit FROM v_profit_summary")
    if not rows:
        return []
    return [
        {
            "month":    r["month_label"],
            "month_num": int(r["month_num"]),
            "revenue":  float(r["revenue"]),
            "expense":  float(r["total_expense"]),
            "profit":   float(r["net_profit"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# CUSTOMER LOYALTY & FOLLOW-UPS
# ---------------------------------------------------------------------------

def get_all_customers_with_loyalty() -> list[dict]:
    rows = db.fetchall(
        "SELECT id, name, contact, email, address, total_events, status::TEXT, loyalty_tier::TEXT FROM customers ORDER BY name"
    )
    if rows is None:
        return []
    return [
        {
            "id":           r["id"],
            "name":         r["name"],
            "contact":      r["contact"],
            "email":        r["email"] or "",
            "address":      r["address"] or "",
            "events":       r["total_events"],
            "status":       r["status"],
            "loyalty_tier": r["loyalty_tier"],
        }
        for r in rows
    ]


def recalculate_loyalty(customer_id: int) -> None:
    db.callproc_void("sp_recalculate_loyalty", in_params=(customer_id,))


def get_follow_ups(customer_id: int) -> list[dict]:
    rows = db.fetchall(
        "SELECT id, follow_up_date, note, is_done FROM customer_follow_ups WHERE customer_id = %s ORDER BY follow_up_date",
        (customer_id,),
    )
    if not rows:
        return []
    return [
        {
            "id":      r["id"],
            "date":    r["follow_up_date"].strftime("%b %d, %Y") if hasattr(r["follow_up_date"], "strftime") else str(r["follow_up_date"]),
            "note":    r["note"],
            "is_done": bool(r["is_done"]),
        }
        for r in rows
    ]


def get_todays_follow_ups() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT cf.id, c.name AS customer_name, cf.note, cf.follow_up_date
        FROM customer_follow_ups cf
        JOIN customers c ON c.id = cf.customer_id
        WHERE cf.follow_up_date = CURRENT_DATE AND cf.is_done = FALSE
        ORDER BY c.name
        """
    )
    return [dict(r) for r in rows] if rows else []


def add_follow_up(customer_id: int, date_str: str, note: str) -> Optional[int]:
    result = db.callproc_out(
        "sp_add_follow_up",
        in_params=(customer_id, _parse_date(date_str), note),
        out_names=["p_follow_up_id"],
    )
    return result["p_follow_up_id"] if result else None


def complete_follow_up(follow_up_id: int) -> None:
    db.callproc_void("sp_complete_follow_up", in_params=(follow_up_id,))


def delete_follow_up(follow_up_id: int) -> None:
    db.callproc_void("sp_delete_follow_up", in_params=(follow_up_id,))


# ---------------------------------------------------------------------------
# AUDIT LOG
# ---------------------------------------------------------------------------

def write_audit_log(actor: str, action: str, table_name: str, record_id: int,
                    old_value: dict = None, new_value: dict = None) -> None:
    import json
    old_json = json.dumps(old_value) if old_value else None
    new_json = json.dumps(new_value) if new_value else None
    try:
        db.callproc_out(
            "sp_write_audit_log",
            in_params=(actor, action, table_name, record_id, old_json, new_json),
            out_names=["p_log_id"],
        )
    except Exception as exc:
        print(f"[audit] write failed: {exc}")


def get_audit_log(limit: int = 50) -> list[dict]:
    rows = db.fetchall(
        "SELECT id, actor, action, table_name, record_id, description, created_at FROM v_audit_log_recent LIMIT %s",
        (limit,),
    )
    if not rows:
        return []
    return [
        {
            "id":          r["id"],
            "actor":       r["actor"],
            "action":      r["action"],
            "table":       r["table_name"],
            "record_id":   r["record_id"],
            "description": r["description"],
            "created_at":  r["created_at"].strftime("%b %d, %Y %I:%M %p") if hasattr(r["created_at"], "strftime") else str(r["created_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# KITCHEN TASKS
# ---------------------------------------------------------------------------

def get_kitchen_tasks(order_id: int) -> list[dict]:
    rows = db.fetchall(
        "SELECT id, task_label, is_done, sort_order FROM kitchen_tasks WHERE order_id = %s ORDER BY sort_order, id",
        (order_id,),
    )
    if not rows:
        return []
    return [{"id": r["id"], "label": r["task_label"], "is_done": bool(r["is_done"])} for r in rows]


def add_kitchen_task(order_id: int, label: str, sort_order: int = 0) -> Optional[int]:
    result = db.callproc_out(
        "sp_add_kitchen_task",
        in_params=(order_id, label, sort_order),
        out_names=["p_task_id"],
    )
    return result["p_task_id"] if result else None


def toggle_kitchen_task(task_id: int) -> Optional[bool]:
    result = db.callproc_out(
        "sp_toggle_kitchen_task",
        in_params=(task_id,),
        out_names=["p_new_state"],
    )
    return bool(result["p_new_state"]) if result else None


def delete_kitchen_task(task_id: int) -> None:
    db.callproc_void("sp_delete_kitchen_task", in_params=(task_id,))


def get_calendar_events_for_date(event_date: date) -> list[dict]:
    result = []

    booking_rows = db.fetchall(
        """
        SELECT booking_ref, customer_name, pax, event_time, venue, occasion, status::TEXT
        FROM bookings
        WHERE event_date = %s AND status NOT IN ('CANCELLED')
        ORDER BY event_time
        """,
        (event_date,)
    )
    if booking_rows:
        for r in booking_rows:
            t = r["event_time"]
            time_str = t.strftime("%I:%M %p").lstrip("0") if hasattr(t, "strftime") else str(t)
            label = r["customer_name"]
            if r["occasion"]:
                label = f"{r['customer_name']} — {r['occasion']}"
            result.append({
                "id":     None,
                "name":   label,
                "pax":    int(r["pax"]),
                "time":   time_str,
                "loc":    r["venue"] or "TBD",
                "source": "booking",
                "ref":    r["booking_ref"],
                "status": r["status"],
            })

    cal_rows = db.fetchall(
        "SELECT id, name, pax, event_time, location FROM calendar_events WHERE event_date = %s ORDER BY id",
        (event_date,)
    )
    if cal_rows:
        for r in cal_rows:
            result.append({
                "id":     r["id"],
                "name":   r["name"],
                "pax":    int(r["pax"]),
                "time":   r["event_time"],
                "loc":    r["location"],
                "source": "manual",
            })

    return result


def save_calendar_day(event_date: date, events: list[dict]) -> None:
    db.callproc_void("sp_delete_calendar_events_for_date", in_params=(event_date,))
    for ev in events:
        db.callproc_out(
            "sp_save_calendar_event",
            in_params=(event_date, ev["name"], int(ev.get("pax", 0)), str(ev.get("time", "06:00 PM")), str(ev.get("loc", "TBD"))),
            out_names=["p_id"],
        )


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
    db.callproc_void(
        "sp_save_business_info",
        in_params=(data["name"], data["contact"], data["email"], data["address"]),
    )




def log_confirmation_sent(booking_id: int, method: str) -> None:
    try:
        db.execute(
            """
            INSERT INTO confirmation_log (booking_id, method, sent_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT DO NOTHING
            """,
            (booking_id, method),
        )
    except Exception:
        pass


def get_customer_ledger(customer_id: int) -> list[dict]:
    """Return unified timeline of bookings, invoices, payments for a customer."""
    rows = db.fetchall(
        """
        SELECT entry_type, recorded_date, event_date, reference,
               description, debit, credit, entry_status
        FROM v_customer_ledger
        WHERE customer_id = %s
        ORDER BY recorded_date DESC, entry_type
        """,
        (customer_id,),
    )
    if not rows:
        return []
    from datetime import date as _d
    result = []
    for r in rows:
        result.append({
            "entry_type":   r["entry_type"],
            "recorded_date": r["recorded_date"].strftime("%b %d, %Y") if isinstance(r["recorded_date"], _d) else str(r["recorded_date"]),
            "event_date":   r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], _d) else str(r["event_date"]),
            "reference":    r["reference"] or "",
            "description":  r["description"] or "",
            "debit":        float(r["debit"]) if r["debit"] else 0.0,
            "credit":       float(r["credit"]) if r["credit"] else 0.0,
            "status":       r["entry_status"] or "",
        })
    return result

def get_booking_balance(booking_id: int) -> Optional[dict]:
    """Return total_amount, total paid (from payment_records), balance for a booking."""
    row = db.fetchone(
        "SELECT total_amount FROM bookings WHERE id = %s",
        (booking_id,),
    )
    if not row:
        return None
    total = float(row["total_amount"])
    paid_row = db.fetchone(
        """
        SELECT COALESCE(SUM(pr.amount), 0) AS total_paid
        FROM invoices i
        JOIN payment_records pr ON pr.invoice_id = i.id
        WHERE i.booking_id = %s
        """,
        (booking_id,),
    )
    paid = float(paid_row["total_paid"]) if paid_row else 0.0
    return {"total": total, "paid": paid, "balance": total - paid}


def create_downpayment_invoice(booking_id: int, customer_name: str,
                               event_date, total_amount: float,
                               amount_paid: float, payment_mode: str) -> Optional[dict]:
    """Auto-create a downpayment invoice + payment record when a booking is saved."""
    try:
        from datetime import date as _d
        if isinstance(event_date, str):
            event_date = _parse_date(event_date)
        paid_status = "Paid" if abs(amount_paid - total_amount) < 0.01 else "Partial"
        inv_result = db.callproc_out(
            "sp_create_invoice",
            in_params=(booking_id, customer_name, event_date, total_amount, amount_paid, paid_status),
            out_names=["p_invoice_id", "p_invoice_ref"],
        )
        if not inv_result:
            return None
        invoice_id  = inv_result["p_invoice_id"]
        invoice_ref = inv_result["p_invoice_ref"]
        pay_result = db.callproc_out(
            "sp_add_payment_record",
            in_params=(invoice_id, amount_paid, _d.today(), payment_mode or "Cash",
                       "Initial downpayment recorded on booking"),
            out_names=["p_record_id", "p_new_status", "p_new_paid"],
        )
        return {
            "invoice_id":  invoice_id,
            "invoice_ref": invoice_ref,
            "record_id":   pay_result["p_record_id"] if pay_result else None,
        }
    except Exception as exc:
        print(f"[repository] create_downpayment_invoice failed: {exc}")
    return None

def get_booking_detail(db_id: int) -> Optional[dict]:
    row = db.fetchone(
        """
        SELECT id, customer_id, booking_ref, customer_name, contact, email, occasion,
               venue, event_date, pax, status::TEXT
        FROM bookings WHERE id = %s
        """,
        (db_id,),
    )
    if not row:
        return None
    from datetime import date as _d
    return {
        "db_id":         row["id"],
        "customer_id":   row["customer_id"],
        "booking_ref":   row["booking_ref"],
        "customer_name": row["customer_name"],
        "contact":       row["contact"] or "",
        "email":         row["email"] or "",
        "occasion":      row["occasion"],
        "venue":         row["venue"],
        "event_date":    row["event_date"].strftime("%b %d, %Y") if isinstance(row["event_date"], _d) else str(row["event_date"]),
        "pax":           row["pax"],
        "status":        row["status"],
    }


def get_smtp_config() -> dict:
    row = db.fetchone("SELECT smtp_host, smtp_port, smtp_user, smtp_pass FROM business_info LIMIT 1")
    if not row:
        return {"smtp_host": "", "smtp_port": 587, "smtp_user": "", "smtp_pass": ""}
    return {
        "smtp_host": row["smtp_host"] or "",
        "smtp_port": int(row["smtp_port"] or 587),
        "smtp_user": row["smtp_user"] or "",
        "smtp_pass": row["smtp_pass"] or "",
    }


def save_smtp_config(host: str, port: int, user: str, password: str) -> None:
    db.execute(
        "UPDATE business_info SET smtp_host=%s, smtp_port=%s, smtp_user=%s, smtp_pass=%s",
        (host, port, user, password),
    )


def log_receipt_sent(invoice_id: int, method: str) -> None:
    try:
        db.execute(
            """
            INSERT INTO receipt_log (invoice_id, method, sent_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT DO NOTHING
            """,
            (invoice_id, method),
        )
    except Exception:
        pass


def get_invoice_by_ref(invoice_ref: str) -> Optional[dict]:
    row = db.fetchone(
        """
        SELECT id, invoice_ref, customer_name, event_date,
               total_amount, amount_paid, status::TEXT
        FROM invoices WHERE invoice_ref = %s
        """,
        (invoice_ref,),
    )
    if not row:
        return None
    return {
        "db_id":      row["id"],
        "invoice":    row["invoice_ref"],
        "customer":   row["customer_name"],
        "event_date": row["event_date"].strftime("%b %d, %Y") if isinstance(row["event_date"], date) else str(row["event_date"]),
        "amount":     float(row["total_amount"]),
        "paid":       float(row["amount_paid"]),
        "status":     row["status"],
    }


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
