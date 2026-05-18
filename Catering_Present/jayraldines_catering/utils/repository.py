"""
Repository layer — the ONLY place that touches utils.db.
All UI pages import from here, never from utils.db directly.

Column-name convention: the DB uses prefixed columns (bk_id, cus_name, etc.).
Every SELECT here uses AS aliases to map them back to the short names the GUI
expects, so no UI code needs to change.
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
    rows = db.fetchall("""
        SELECT cus_id       AS id,
               cus_name     AS name,
               cus_contact  AS contact,
               cus_email    AS email,
               cus_address  AS address,
               cus_total_events AS total_events,
               cus_status::TEXT AS status
        FROM customers ORDER BY cus_name
    """)
    if not rows:
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
    rows = db.fetchall(
        "SELECT cus_name AS name FROM customers WHERE cus_status != 'Inactive' ORDER BY cus_name"
    )
    return [r["name"] for r in rows] if rows else []


def get_customer_email_by_name(name: str) -> str:
    row = db.fetchone(
        "SELECT cus_email AS email FROM customers WHERE cus_name = %s LIMIT 1", (name,)
    )
    return (row["email"] or "") if row else ""


def get_customer_event_dates(name: str) -> list[dict]:
    rows = db.fetchall(
        """
        SELECT bk_id        AS id,
               bk_event_date AS event_date
        FROM bookings
        WHERE bk_customer_name = %s AND bk_status NOT IN ('CANCELLED')
        ORDER BY bk_event_date DESC
        """,
        (name,),
    )
    if not rows:
        return []
    return [
        {
            "id":   r["id"],
            "date": r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# MENU ITEMS
# ---------------------------------------------------------------------------

def get_all_menu_items() -> list[dict]:
    rows = db.fetchall("""
        SELECT mi_id                       AS id,
               mi_name                    AS name,
               mi_description             AS description,
               mi_category::TEXT          AS category,
               mi_package_tier::TEXT      AS package,
               mi_price                   AS price,
               mi_status::TEXT            AS status
        FROM menu_items ORDER BY mi_category, mi_name
    """)
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
    rows = db.fetchall("""
        SELECT mi_id                  AS id,
               mi_name               AS name,
               mi_description        AS description,
               mi_category::TEXT     AS category,
               mi_package_tier::TEXT AS package,
               mi_price              AS price,
               mi_status::TEXT       AS status
        FROM menu_items
        WHERE mi_status IN ('Available','Seasonal')
        ORDER BY mi_category, mi_name
    """)
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
# OCCASIONS
# ---------------------------------------------------------------------------

def get_top_occasions(limit: int = 10) -> list[dict]:
    rows = db.fetchall(
        """
        SELECT bk_occasion AS occasion, COUNT(*) AS count
        FROM bookings
        WHERE bk_occasion IS NOT NULL AND bk_occasion <> ''
          AND bk_status IN ('CONFIRMED', 'COMPLETED')
        GROUP BY bk_occasion
        ORDER BY count DESC
        LIMIT %s
        """,
        (limit,),
    )
    if not rows:
        return []
    return [{"occasion": r["occasion"], "count": int(r["count"])} for r in rows]


def get_all_occasions() -> list[str]:
    rows = db.fetchall(
        "SELECT occ_name AS name FROM occasions ORDER BY occ_id"
    )
    if not rows:
        return ["Wedding", "Birthday", "Anniversary", "Debut", "Graduation",
                "Christening / Baptism", "Corporate Event", "Family Reunion",
                "Holiday Party", "Other"]
    return [r["name"] for r in rows]


def add_occasion(name: str) -> None:
    db.execute(
        "INSERT INTO occasions (occ_name) VALUES (%s) ON CONFLICT (occ_name) DO NOTHING",
        (name.strip(),),
    )


def update_occasion(old_name: str, new_name: str) -> None:
    db.execute(
        "UPDATE occasions SET occ_name = %s WHERE occ_name = %s",
        (new_name.strip(), old_name),
    )


def delete_occasion(name: str) -> None:
    db.execute("DELETE FROM occasions WHERE occ_name = %s", (name,))


# ---------------------------------------------------------------------------
# PACKAGES
# ---------------------------------------------------------------------------

def get_all_packages() -> list[dict]:
    rows = db.fetchall("""
        SELECT pkg_id            AS id,
               pkg_name         AS name,
               pkg_price_per_pax AS price_per_pax,
               pkg_min_pax      AS min_pax,
               pkg_description  AS description
        FROM packages ORDER BY pkg_price_per_pax
    """)
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
    rows = db.fetchall(
        """
        SELECT pi.pi_id              AS id,
               pi.pi_menu_item_id   AS menu_item_id,
               mi.mi_name           AS item_name,
               mi.mi_category::TEXT AS category,
               pi.pi_custom_price   AS custom_price
        FROM package_items pi
        JOIN menu_items mi ON mi.mi_id = pi.pi_menu_item_id
        WHERE pi.pi_package_id = %s
        ORDER BY mi.mi_category, mi.mi_name
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
    try:
        db.execute("DELETE FROM package_items WHERE pi_package_id = %s", (package_id,))
        for item in items:
            db.execute(
                "INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price) VALUES (%s, %s, %s)",
                (package_id, item["menu_item_id"], item["custom_price"]),
            )
        return True
    except Exception as exc:
        print(f"[repository] set_package_items failed: {exc}")
        return False


def add_package(data: dict) -> Optional[int]:
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
        SELECT bk_id                  AS id,
               bk_booking_ref        AS booking_ref,
               bk_customer_name      AS customer_name,
               bk_event_date         AS event_date,
               bk_pax                AS pax,
               bk_total_amount       AS total_amount,
               bk_status::TEXT       AS status,
               bk_cancellation_reason AS cancellation_reason
        FROM bookings
        WHERE bk_status IN ('CONFIRMED', 'COMPLETED') {period_filter}
        ORDER BY bk_event_date DESC
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
    try:
        event_date  = _parse_date(data["date"])
        event_time  = _parse_time(data.get("time", "6:00 PM"))
        amount_paid = _parse_amount(data.get("amount_paid", "0"))

        package_id = None
        if data.get("menu_type") == "package":
            pkg_row = db.fetchone(
                "SELECT pkg_id AS id FROM packages WHERE pkg_name = %s",
                (data.get("menu_value"),),
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
    try:
        event_date  = _parse_date(data["date"])
        event_time  = _parse_time(data.get("time", "6:00 PM"))
        amount_paid = _parse_amount(data.get("amount_paid", "0"))

        package_id = None
        if data.get("menu_type") == "package":
            pkg_row = db.fetchone(
                "SELECT pkg_id AS id FROM packages WHERE pkg_name = %s",
                (data.get("menu_value"),),
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
    rows = db.fetchall("""
        SELECT i.inv_id              AS id,
               i.inv_invoice_ref    AS invoice_ref,
               i.inv_booking_id     AS booking_id,
               i.inv_customer_name  AS customer_name,
               i.inv_event_date     AS event_date,
               i.inv_total_amount   AS total_amount,
               i.inv_amount_paid    AS amount_paid,
               i.inv_status::TEXT   AS status,
               COALESCE(c.cus_email, '') AS customer_email
        FROM invoices i
        LEFT JOIN customers c ON c.cus_name = i.inv_customer_name
        ORDER BY i.inv_created_at DESC
    """)
    if not rows:
        return []
    return [
        {
            "db_id":          r["id"],
            "invoice":        r["invoice_ref"],
            "booking_id":     r["booking_id"],
            "customer":       r["customer_name"],
            "customer_email": r["customer_email"],
            "event_date":     r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
            "amount":         float(r["total_amount"]),
            "paid":           float(r["amount_paid"]),
            "status":         r["status"],
        }
        for r in rows
    ]


def auto_create_invoice(booking_id: int) -> Optional[dict]:
    try:
        result = db.callproc_out(
            "sp_auto_create_invoice",
            in_params=(booking_id,),
            out_names=["p_invoice_id", "p_invoice_ref"],
        )
        if result:
            return {"invoice_id": result["p_invoice_id"], "invoice_ref": result["p_invoice_ref"]}
    except Exception as exc:
        print(f"[repository] auto_create_invoice failed: {exc}")
    return None


def pay_invoice(booking_id: int, payment_amount: float, payment_date,
                method: str = "Cash", note: str = "") -> dict:
    from datetime import date as _d
    if payment_date is None:
        payment_date = _d.today()
    elif isinstance(payment_date, str):
        payment_date = _parse_date(payment_date)
    result = db.callproc_out(
        "sp_pay_invoice",
        in_params=(booking_id, payment_amount, payment_date, method, note or None),
        out_names=[
            "p_invoice_id", "p_invoice_ref",
            "p_new_invoice_status", "p_new_booking_status",
            "p_new_paid", "p_remaining",
        ],
    )
    if not result:
        raise Exception("Payment failed — no result from database.")
    return {
        "invoice_id":         result["p_invoice_id"],
        "invoice_ref":        result["p_invoice_ref"],
        "new_invoice_status": result["p_new_invoice_status"],
        "new_booking_status": result["p_new_booking_status"],
        "new_paid":           float(result["p_new_paid"]),
        "remaining":          float(result["p_remaining"]),
    }


def get_invoice_payment_info(booking_id: int) -> Optional[dict]:
    row = db.fetchone(
        """
        SELECT i.inv_id                      AS id,
               i.inv_invoice_ref            AS invoice_ref,
               i.inv_total_amount           AS total_amount,
               i.inv_amount_paid            AS amount_paid,
               i.inv_status::TEXT           AS status,
               bi.bi_min_downpayment_pct    AS min_downpayment_pct,
               bi.bi_allow_zero_downpayment AS allow_zero_downpayment
        FROM invoices i
        JOIN bookings b ON b.bk_id = i.inv_booking_id
        CROSS JOIN business_info bi
        WHERE i.inv_booking_id = %s AND bi.bi_id = 1
        LIMIT 1
        """,
        (booking_id,),
    )
    if not row:
        return None
    total      = float(row["total_amount"])
    paid       = float(row["amount_paid"])
    min_pct    = float(row["min_downpayment_pct"])
    allow_zero = bool(row["allow_zero_downpayment"])
    required_down = round(total * min_pct / 100, 2)
    remaining  = total - paid
    required_payment = 0.0 if (paid == 0 and allow_zero) else (required_down if paid == 0 else remaining)
    return {
        "invoice_id":       row["id"],
        "invoice_ref":      row["invoice_ref"],
        "total":            total,
        "paid":             paid,
        "remaining":        remaining,
        "required_down":    required_down,
        "required_payment": required_payment,
        "allow_zero":       allow_zero,
        "min_pct":          min_pct,
        "status":           row["status"],
    }


def update_invoice(db_id: int, data: dict) -> None:
    try:
        event_date = _parse_date(data["event_date"])
        db.callproc_void(
            "sp_update_invoice",
            in_params=(db_id, data["customer"], event_date, data["amount"], data["paid"], data["status"]),
        )
    except Exception as exc:
        print(f"[repository] update_invoice failed: {exc}")


def delete_invoice(db_id: int) -> None:
    db.callproc_void("sp_delete_invoice", in_params=(db_id,))


def add_payment_record(invoice_id: int, amount: float,
                       payment_date, method: str = "Cash", note: str = "") -> Optional[dict]:
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
        SELECT pr_id           AS id,
               pr_amount       AS amount,
               pr_payment_date AS payment_date,
               pr_method       AS method,
               pr_note         AS note,
               pr_created_at   AS created_at
        FROM payment_records
        WHERE pr_invoice_id = %s
        ORDER BY pr_payment_date DESC, pr_created_at DESC
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
    rows = db.fetchall("""
        SELECT ko_id           AS id,
               ko_order_ref   AS order_ref,
               ko_client_name AS client_name,
               ko_event_name  AS event_name,
               ko_pax         AS pax,
               ko_items_desc  AS items_desc,
               ko_status::TEXT AS status
        FROM kitchen_orders
        WHERE ko_status != 'Done'
        ORDER BY ko_created_at
    """)
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
    try:
        existing = db.fetchone(
            "SELECT COUNT(*) AS cnt FROM kitchen_tasks WHERE kt_order_id = %s", (order_id,)
        )
        if existing and existing["cnt"] > 0:
            return
        items = [item.strip() for item in items_desc.split(",") if item.strip()]
        for idx, item in enumerate(items):
            add_kitchen_task(order_id, f"Prepare: {item}", sort_order=idx)
    except Exception as exc:
        print(f"[repo] _auto_generate_kitchen_tasks: {exc}")


def sync_kitchen_from_bookings() -> int:
    try:
        rows = db.fetchall("""
            SELECT bk_id           AS id,
                   bk_booking_ref  AS booking_ref,
                   bk_customer_name AS customer_name,
                   bk_occasion     AS occasion,
                   bk_pax          AS pax,
                   bk_event_date   AS event_date
            FROM bookings b
            WHERE bk_status = 'CONFIRMED'
              AND NOT EXISTS (
                  SELECT 1 FROM kitchen_orders ko WHERE ko.ko_booking_id = b.bk_id
              )
            ORDER BY bk_event_date
        """)
        if not rows:
            return 0
        count = 0
        for r in rows:
            occasion = r["occasion"] or "Catering Event"
            detail = db.fetchone(
                "SELECT bk_menu_type AS menu_type, bk_custom_items AS custom_items, bk_package_id AS package_id FROM bookings WHERE bk_id = %s",
                (r["id"],),
            )
            if detail and detail["menu_type"] == "custom" and detail["custom_items"]:
                items_desc = detail["custom_items"]
            elif detail and detail["package_id"]:
                pkg = db.fetchone(
                    "SELECT pkg_name AS name FROM packages WHERE pkg_id = %s",
                    (detail["package_id"],),
                )
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
    rows = db.fetchall("""
        SELECT bk_booking_ref  AS booking_ref,
               bk_customer_name AS customer_name,
               bk_event_date   AS event_date,
               bk_event_time   AS event_time
        FROM bookings
        WHERE bk_status = 'CONFIRMED'
          AND bk_event_date >= CURRENT_DATE - INTERVAL '1 day'
          AND bk_event_date <= CURRENT_DATE + INTERVAL '2 days'
        ORDER BY bk_event_date, bk_event_time
    """)
    result = []
    for r in rows:
        try:
            ed = r["event_date"]
            et = r["event_time"]
            if isinstance(ed, date) and isinstance(et, time):
                event_dt = datetime.combine(ed, et.replace(tzinfo=None) if hasattr(et, "tzinfo") else et)
            else:
                continue
            result.append({
                "booking_ref":   r["booking_ref"],
                "customer_name": r["customer_name"],
                "event_dt":      event_dt,
            })
        except Exception as e:
            print(f"[alerts] skip row: {e}")
    return result


def get_unread_notifications() -> list[dict]:
    rows = db.fetchall("""
        SELECT notif_id         AS id,
               notif_type       AS type,
               notif_title      AS title,
               notif_message    AS message,
               notif_color      AS color,
               notif_created_at AS created_at
        FROM notifications
        WHERE notif_is_read = FALSE
        ORDER BY notif_created_at DESC
    """)
    return [dict(r) for r in rows] if rows else []


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
            "todays_events": 0, "pending_bookings": 0,
            "weekly_revenue": 0, "unpaid_invoices": 0, "todays_pax": 0,
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
                COUNT(*)::INT                        AS total_bookings,
                COALESCE(SUM(bk_pax),0)::INT         AS total_pax,
                COALESCE(SUM(bk_total_amount),0)::FLOAT AS total_revenue,
                0::FLOAT                             AS unpaid_amount,
                COALESCE((SELECT COUNT(*) FROM bookings
                          WHERE bk_created_at::DATE = CURRENT_DATE
                            AND bk_status IN ('CONFIRMED','COMPLETED')),0)::INT AS today_bookings,
                COALESCE((SELECT COUNT(*) FROM bookings
                          WHERE bk_created_at::DATE BETWEEN date_trunc('week',CURRENT_DATE)::DATE
                                AND (date_trunc('week',CURRENT_DATE)+INTERVAL '6 days')::DATE
                            AND bk_status IN ('CONFIRMED','COMPLETED')),0)::INT AS week_bookings
            FROM bookings
            WHERE bk_status IN ('CONFIRMED', 'COMPLETED') {period_filter}
            """
        )
    else:
        row = db.fetchone("SELECT * FROM v_report_kpis")
    if not row:
        return {"total_bookings": 0, "total_pax": 0, "total_revenue": 0.0,
                "unpaid_amount": 0.0, "today_bookings": 0, "week_bookings": 0}
    return {
        "total_bookings": int(row["total_bookings"]),
        "total_pax":      int(row["total_pax"]),
        "total_revenue":  float(row["total_revenue"]),
        "unpaid_amount":  float(row["unpaid_amount"]),
        "today_bookings": int(row["today_bookings"]),
        "week_bookings":  int(row["week_bookings"]),
    }


def get_monthly_income() -> list[dict]:
    rows = db.fetchall(
        "SELECT month_label, month_num, total_revenue, total_paid FROM v_monthly_income"
    )
    if not rows:
        return []
    return [{"month": r["month_label"], "month_num": r["month_num"],
             "revenue": float(r["total_revenue"]), "paid": float(r["total_paid"])} for r in rows]


def get_payment_methods() -> list[dict]:
    rows = db.fetchall("SELECT method, total FROM v_payment_methods")
    return [{"method": r["method"], "total": int(r["total"])} for r in rows] if rows else []


def get_top_menu_items() -> list[dict]:
    rows = db.fetchall("SELECT item, order_count FROM v_top_menu_items")
    return [{"item": r["item"], "count": int(r["order_count"])} for r in rows] if rows else []


def get_customer_order_frequency() -> list[dict]:
    rows = db.fetchall("SELECT name, booking_count FROM v_customer_order_frequency")
    return [{"name": r["name"], "count": int(r["booking_count"])} for r in rows] if rows else []


def get_recent_activity(limit: int = 5) -> list[dict]:
    rows = db.fetchall(
        "SELECT title, description, color, created_at FROM v_recent_activity LIMIT %s",
        (limit,),
    )
    if not rows:
        return []
    from datetime import timezone
    now = datetime.now(timezone.utc)
    result = []
    for r in rows:
        ts = r["created_at"]
        delta = (now - ts) if (hasattr(ts, "tzinfo") and ts.tzinfo) else (datetime.utcnow() - ts.replace(tzinfo=None))
        secs = int(delta.total_seconds())
        if secs < 60:        time_str = "just now"
        elif secs < 3600:    time_str = f"{secs // 60} min ago"
        elif secs < 86400:   time_str = f"{secs // 3600} hr ago"
        else:                time_str = f"{secs // 86400}d ago"
        result.append({"title": r["title"], "description": r["description"],
                        "color": r["color"], "time": time_str})
    return result


def get_menu_alerts() -> list[dict]:
    rows = db.fetchall("SELECT item, issue, badge_type FROM v_menu_alerts")
    return [{"item": r["item"], "issue": r["issue"], "badge_type": r["badge_type"]} for r in rows] if rows else []


def get_calendar_summary() -> list[dict]:
    rows = db.fetchall("SELECT * FROM v_calendar_day_summary")
    return [dict(r) for r in rows] if rows else []


# ---------------------------------------------------------------------------
# BUSINESS INFO / SETTINGS
# ---------------------------------------------------------------------------

def get_business_policy() -> dict:
    row = db.fetchone("""
        SELECT bi_min_downpayment_pct    AS min_downpayment_pct,
               bi_allow_zero_downpayment AS allow_zero_downpayment,
               bi_max_daily_pax          AS max_daily_pax
        FROM business_info LIMIT 1
    """)
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


def get_business_info() -> dict:
    row = db.fetchone("""
        SELECT bi_name    AS name,
               bi_contact AS contact,
               bi_email   AS email,
               bi_address AS address
        FROM business_info LIMIT 1
    """)
    if not row:
        return {"name": "Jayraldine's Catering", "contact": "+63 912 345 6789",
                "email": "admin@jayraldines.com", "address": "123 Rizal St., Manila"}
    return dict(row)


def save_business_info(data: dict) -> None:
    db.callproc_void(
        "sp_save_business_info",
        in_params=(data["name"], data["contact"], data["email"], data["address"]),
    )


def get_smtp_config() -> dict:
    row = db.fetchone("""
        SELECT bi_smtp_host AS smtp_host,
               bi_smtp_port AS smtp_port,
               bi_smtp_user AS smtp_user,
               bi_smtp_pass AS smtp_pass
        FROM business_info LIMIT 1
    """)
    if not row:
        return {"smtp_host": "", "smtp_port": 587, "smtp_user": "", "smtp_pass": ""}
    return {
        "smtp_host": row["smtp_host"] or "",
        "smtp_port": int(row["smtp_port"] or 587),
        "smtp_user": row["smtp_user"] or "",
        "smtp_pass": row["smtp_pass"] or "",
    }


def save_smtp_config(host: str, port: int, user: str, password: str) -> None:
    db.callproc_void("sp_save_smtp_config", in_params=(host, port, user, password))


# ---------------------------------------------------------------------------
# EXPENSES
# ---------------------------------------------------------------------------

def get_all_expenses() -> list[dict]:
    rows = db.fetchall("""
        SELECT exp_id              AS id,
               exp_category::TEXT AS category,
               exp_description    AS description,
               exp_amount         AS amount,
               exp_expense_date   AS expense_date
        FROM expenses ORDER BY exp_expense_date DESC
    """)
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


def get_top_locations(limit: int = 10) -> list[dict]:
    rows = db.fetchall(
        """
        SELECT
            TRIM(
                CASE
                    WHEN bk_address LIKE '%%,%%' THEN
                        SPLIT_PART(bk_address, ',',
                            ARRAY_LENGTH(STRING_TO_ARRAY(TRIM(bk_address), ','), 1) - 1)
                    ELSE TRIM(bk_address)
                END
            ) AS area,
            COUNT(*) AS booking_count
        FROM bookings
        WHERE bk_address IS NOT NULL AND TRIM(bk_address) != ''
          AND bk_status IN ('CONFIRMED', 'COMPLETED')
        GROUP BY 1
        HAVING TRIM(
            CASE
                WHEN bk_address LIKE '%%,%%' THEN
                    SPLIT_PART(bk_address, ',',
                        ARRAY_LENGTH(STRING_TO_ARRAY(TRIM(bk_address), ','), 1) - 1)
                ELSE TRIM(bk_address)
            END
        ) != ''
        ORDER BY booking_count DESC
        LIMIT %s
        """,
        (limit,),
    )
    return [{"venue": r["area"], "count": int(r["booking_count"])} for r in rows] if rows else []


def get_profit_summary() -> list[dict]:
    rows = db.fetchall(
        "SELECT month_num, month_label, revenue, total_expense, net_profit FROM v_profit_summary"
    )
    if not rows:
        return []
    return [
        {
            "month":     r["month_label"],
            "month_num": int(r["month_num"]),
            "revenue":   float(r["revenue"]),
            "expense":   float(r["total_expense"]),
            "profit":    float(r["net_profit"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# CUSTOMER LOYALTY & FOLLOW-UPS
# ---------------------------------------------------------------------------

def get_all_customers_with_loyalty() -> list[dict]:
    rows = db.fetchall("""
        SELECT cus_id              AS id,
               cus_name           AS name,
               cus_contact        AS contact,
               cus_email          AS email,
               cus_address        AS address,
               cus_total_events   AS total_events,
               cus_status::TEXT   AS status,
               cus_loyalty_tier::TEXT AS loyalty_tier
        FROM customers ORDER BY cus_name
    """)
    if not rows:
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
        """
        SELECT cfu_id            AS id,
               cfu_follow_up_date AS follow_up_date,
               cfu_note          AS note,
               cfu_is_done       AS is_done
        FROM customer_follow_ups
        WHERE cfu_customer_id = %s
        ORDER BY cfu_follow_up_date
        """,
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
    rows = db.fetchall("""
        SELECT cf.cfu_id          AS id,
               c.cus_name         AS customer_name,
               cf.cfu_note        AS note,
               cf.cfu_follow_up_date AS follow_up_date
        FROM customer_follow_ups cf
        JOIN customers c ON c.cus_id = cf.cfu_customer_id
        WHERE cf.cfu_follow_up_date = CURRENT_DATE AND cf.cfu_is_done = FALSE
        ORDER BY c.cus_name
    """)
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
        """
        SELECT al_id          AS id,
               al_actor       AS actor,
               al_action      AS action,
               al_table_name  AS table_name,
               al_record_id   AS record_id,
               description,
               al_created_at  AS created_at
        FROM v_audit_log_recent LIMIT %s
        """,
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
        """
        SELECT kt_id         AS id,
               kt_task_label AS task_label,
               kt_is_done    AS is_done,
               kt_sort_order AS sort_order
        FROM kitchen_tasks
        WHERE kt_order_id = %s
        ORDER BY kt_sort_order, kt_id
        """,
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


# ---------------------------------------------------------------------------
# CALENDAR
# ---------------------------------------------------------------------------

def get_calendar_events_for_date(event_date: date) -> list[dict]:
    result = []

    booking_rows = db.fetchall(
        """
        SELECT bk_booking_ref   AS booking_ref,
               bk_customer_name AS customer_name,
               bk_pax           AS pax,
               bk_event_time    AS event_time,
               bk_venue         AS venue,
               bk_occasion      AS occasion,
               bk_status::TEXT  AS status
        FROM bookings
        WHERE bk_event_date = %s AND bk_status NOT IN ('CANCELLED')
        ORDER BY bk_event_time
        """,
        (event_date,),
    )
    for r in booking_rows or []:
        t = r["event_time"]
        time_str = t.strftime("%I:%M %p").lstrip("0") if hasattr(t, "strftime") else str(t)
        label = r["customer_name"]
        if r["occasion"]:
            label = f"{r['customer_name']} — {r['occasion']}"
        result.append({
            "id": None, "name": label, "pax": int(r["pax"]),
            "time": time_str, "loc": r["venue"] or "TBD",
            "source": "booking", "ref": r["booking_ref"], "status": r["status"],
        })

    cal_rows = db.fetchall(
        """
        SELECT ce_id         AS id,
               ce_name       AS name,
               ce_pax        AS pax,
               ce_event_time AS event_time,
               ce_location   AS location
        FROM calendar_events
        WHERE ce_event_date = %s ORDER BY ce_id
        """,
        (event_date,),
    )
    for r in cal_rows or []:
        result.append({
            "id": r["id"], "name": r["name"], "pax": int(r["pax"]),
            "time": r["event_time"], "loc": r["location"], "source": "manual",
        })

    return result


def save_calendar_day(event_date: date, events: list[dict]) -> None:
    db.callproc_void("sp_delete_calendar_events_for_date", in_params=(event_date,))
    for ev in events:
        db.callproc_out(
            "sp_save_calendar_event",
            in_params=(event_date, ev["name"], int(ev.get("pax", 0)),
                       str(ev.get("time", "06:00 PM")), str(ev.get("loc", "TBD"))),
            out_names=["p_id"],
        )


# ---------------------------------------------------------------------------
# BOOKING DETAIL & BALANCE
# ---------------------------------------------------------------------------

def get_booking_detail(db_id: int) -> Optional[dict]:
    row = db.fetchone(
        """
        SELECT bk_id            AS id,
               bk_customer_id   AS customer_id,
               bk_booking_ref   AS booking_ref,
               bk_customer_name AS customer_name,
               bk_contact       AS contact,
               bk_email         AS email,
               bk_occasion      AS occasion,
               bk_venue         AS venue,
               bk_event_date    AS event_date,
               bk_pax           AS pax,
               bk_status::TEXT  AS status
        FROM bookings WHERE bk_id = %s
        """,
        (db_id,),
    )
    if not row:
        return None
    return {
        "db_id":         row["id"],
        "customer_id":   row["customer_id"],
        "booking_ref":   row["booking_ref"],
        "customer_name": row["customer_name"],
        "contact":       row["contact"] or "",
        "email":         row["email"] or "",
        "occasion":      row["occasion"],
        "venue":         row["venue"],
        "event_date":    row["event_date"].strftime("%b %d, %Y") if isinstance(row["event_date"], date) else str(row["event_date"]),
        "pax":           row["pax"],
        "status":        row["status"],
    }


def get_booking_balance(booking_id: int) -> Optional[dict]:
    row = db.fetchone(
        "SELECT bk_total_amount AS total_amount FROM bookings WHERE bk_id = %s",
        (booking_id,),
    )
    if not row:
        return None
    total = float(row["total_amount"])
    paid_row = db.fetchone(
        """
        SELECT COALESCE(SUM(pr.pr_amount), 0) AS total_paid
        FROM invoices i
        JOIN payment_records pr ON pr.pr_invoice_id = i.inv_id
        WHERE i.inv_booking_id = %s
        """,
        (booking_id,),
    )
    paid = float(paid_row["total_paid"]) if paid_row else 0.0
    return {"total": total, "paid": paid, "balance": total - paid}


def create_downpayment_invoice(booking_id: int, customer_name: str,
                               event_date, total_amount: float,
                               amount_paid: float, payment_mode: str) -> Optional[dict]:
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


def get_invoice_by_ref(invoice_ref: str) -> Optional[dict]:
    row = db.fetchone(
        """
        SELECT inv_id             AS id,
               inv_invoice_ref   AS invoice_ref,
               inv_customer_name AS customer_name,
               inv_event_date    AS event_date,
               inv_total_amount  AS total_amount,
               inv_amount_paid   AS amount_paid,
               inv_status::TEXT  AS status
        FROM invoices WHERE inv_invoice_ref = %s
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


def get_customer_ledger(customer_id: int) -> list[dict]:
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
    result = []
    for r in rows:
        result.append({
            "entry_type":    r["entry_type"],
            "recorded_date": r["recorded_date"].strftime("%b %d, %Y") if isinstance(r["recorded_date"], date) else str(r["recorded_date"]),
            "event_date":    r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
            "reference":     r["reference"] or "",
            "description":   r["description"] or "",
            "debit":         float(r["debit"]) if r["debit"] else 0.0,
            "credit":        float(r["credit"]) if r["credit"] else 0.0,
            "status":        r["entry_status"] or "",
        })
    return result


# ---------------------------------------------------------------------------
# CEBU ADDRESS SYSTEM
# ---------------------------------------------------------------------------

def search_cebu_address(query: str, limit: int = 10) -> list[dict]:
    if not query or len(query.strip()) < 2:
        return []
    rows = db.fetchall(
        "SELECT * FROM fn_search_cebu_address(%s::text, %s::int)",
        (query.strip(), limit),
    )
    return rows or []


def save_address(street: str, barangay_id: int, city_id: int,
                 province_id: int, zip_code: str = "") -> Optional[int]:
    result = db.callproc_out(
        "sp_save_address",
        in_params=(street, barangay_id, city_id, province_id, zip_code),
        out_names=["p_address_id"],
    )
    return result.get("p_address_id") if result else None


def link_customer_address(customer_id: int, address_id: int) -> None:
    db.execute(
        "UPDATE customers SET cus_address_id = %s WHERE cus_id = %s",
        (address_id, customer_id),
    )


def get_recent_addresses(limit: int = 5) -> list[dict]:
    rows = db.fetchall(
        """
        SELECT a.addr_id     AS id,
               a.addr_street AS street,
               a.addr_zip_code AS zip_code,
               b.ab_name     AS barangay,
               c.ac_name     AS city,
               pr.ap_name    AS province,
               b.ab_id       AS barangay_id,
               c.ac_id       AS city_id,
               pr.ap_id      AS province_id,
               (a.addr_street || ', ' || b.ab_name || ', ' || c.ac_name) AS display_text
        FROM addresses a
        JOIN address_barangays b  ON b.ab_id  = a.addr_barangay_id
        JOIN address_cities    c  ON c.ac_id  = a.addr_city_id
        JOIN address_provinces pr ON pr.ap_id = a.addr_province_id
        ORDER BY a.addr_created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    return rows or []


# ---------------------------------------------------------------------------
# MISC STUBS (non-fatal — tables may not exist in all deployments)
# ---------------------------------------------------------------------------

def log_confirmation_sent(booking_id: int, method: str) -> None:
    try:
        db.execute(
            "INSERT INTO confirmation_log (booking_id, method, sent_at) VALUES (%s, %s, NOW()) ON CONFLICT DO NOTHING",
            (booking_id, method),
        )
    except Exception:
        pass


def log_receipt_sent(invoice_id: int, method: str) -> None:
    try:
        db.execute(
            "INSERT INTO receipt_log (invoice_id, method, sent_at) VALUES (%s, %s, NOW()) ON CONFLICT DO NOTHING",
            (invoice_id, method),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# PRIVATE HELPERS
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s!r}")


def _parse_time(s: str) -> time:
    for fmt in ("%I:%M %p", "%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s.strip().upper(), fmt).time()
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