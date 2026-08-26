"""
Tablet business logic layer — Customer, Package/Menu, Order, Billing, Terms.

The order is built up in-memory through the wizard (Customer -> Package ->
Menu -> Charges -> Billing -> Preview) and only written to the local SQLite
database in one shot at create_order(), once Terms & Conditions have been
acknowledged and the staff/customer taps Confirm. This avoids abandoned
partial-order rows for orders that were started but never finished.
"""
from __future__ import annotations
from datetime import date as _date, datetime
from typing import Optional

import utils.db as db

_BOOKING_REF_PREFIX = "TB"  # Tablet-originated booking ref, distinct from
                            # the PC's "BK-" prefix so it's obvious on the
                            # PC side which orders came from a tablet.


# ─────────────────────────────────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────────────────────────────────

def search_customers(query: str) -> list[dict]:
    query = (query or "").strip()
    if not query:
        rows = db.fetchall("""
            SELECT cus_id, cus_name, cus_contact, cus_email, cus_address
            FROM customers
            GROUP BY LOWER(cus_name), cus_contact
            ORDER BY cus_name LIMIT 100
        """)
    else:
        like = f"%{query}%"
        rows = db.fetchall("""
            SELECT cus_id, cus_name, cus_contact, cus_email, cus_address
            FROM customers
            WHERE cus_name LIKE ? OR cus_contact LIKE ?
            GROUP BY LOWER(cus_name), cus_contact
            ORDER BY cus_name LIMIT 100
        """, (like, like))
    return [
        {
            "id": r["cus_id"], "name": r["cus_name"], "contact": r["cus_contact"] or "",
            "email": r["cus_email"] or "", "address": r["cus_address"] or "",
        }
        for r in rows
    ]


def find_possible_duplicate_customer(contact: str, name: str) -> Optional[dict]:
    """Duplicate-protection check before creating a new customer (Tablet-mode.md #21)."""
    contact = (contact or "").strip()
    if contact:
        row = db.fetchone("SELECT * FROM customers WHERE cus_contact = ? AND cus_contact != '' LIMIT 1", (contact,))
        if row:
            return {"id": row["cus_id"], "name": row["cus_name"], "contact": row["cus_contact"] or ""}
    name = (name or "").strip()
    if name:
        row = db.fetchone("SELECT * FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1", (name,))
        if row:
            return {"id": row["cus_id"], "name": row["cus_name"], "contact": row["cus_contact"] or ""}
    return None


def add_customer(name: str, contact: str = "", email: str = "", address: str = "") -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Customer name is required.")
    contact_clean = contact.strip()
    if contact_clean:
        existing = db.fetchone("SELECT cus_id FROM customers WHERE cus_contact = ? AND cus_contact != '' LIMIT 1", (contact_clean,))
        if existing:
            return existing["cus_id"]
    existing_name = db.fetchone("SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1", (name,))
    if existing_name:
        return existing_name["cus_id"]

    cust_id = db.execute(
        "INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status) VALUES (?, ?, ?, ?, 'Active')",
        (name, contact_clean, email.strip(), address.strip()),
    )
    return cust_id


def update_customer(customer_id: int, name: str, contact: str = "", email: str = "", address: str = "") -> bool:
    name = (name or "").strip()
    if not name or not customer_id:
        return False
    db.execute(
        "UPDATE customers SET cus_name = ?, cus_contact = ?, cus_email = ?, cus_address = ? WHERE cus_id = ?",
        (name, contact.strip(), email.strip(), address.strip(), customer_id),
    )
    return True


def delete_customer(customer_id: int) -> bool:
    if not customer_id:
        return False
    db.execute("DELETE FROM customers WHERE cus_id = ?", (customer_id,))
    return True


# ─────────────────────────────────────────────────────────────────────────
# MASTER DATA — packages / menu management
# ─────────────────────────────────────────────────────────────────────────

def get_packages() -> list[dict]:
    rows = db.fetchall("SELECT * FROM packages ORDER BY pkg_price_per_pax ASC")
    return [
        {
            "id": r["pkg_id"], "name": r["pkg_name"], "description": r["pkg_description"] or "",
            "price_per_pax": float(r["pkg_price_per_pax"]), "min_pax": int(r["pkg_min_pax"] or 30),
        }
        for r in rows
    ]


def add_package(name: str, description: str = "", price_per_pax: float = 350.0, min_pax: int = 30) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Package name is required.")
    return db.execute(
        "INSERT INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax) VALUES (?, ?, ?, ?)",
        (name, (description or "").strip(), float(price_per_pax or 0.0), int(min_pax or 30)),
    )


def update_package(pkg_id: int, name: str, description: str = "", price_per_pax: float = 350.0, min_pax: int = 30) -> bool:
    name = (name or "").strip()
    if not name or not pkg_id:
        return False
    db.execute(
        "UPDATE packages SET pkg_name = ?, pkg_description = ?, pkg_price_per_pax = ?, pkg_min_pax = ? WHERE pkg_id = ?",
        (name, (description or "").strip(), float(price_per_pax or 0.0), int(min_pax or 30), pkg_id),
    )
    return True


def delete_package(pkg_id: int) -> bool:
    if not pkg_id:
        return False
    db.execute("DELETE FROM package_items WHERE pi_package_id = ?", (pkg_id,))
    db.execute("DELETE FROM packages WHERE pkg_id = ?", (pkg_id,))
    return True


def get_all_menu_items() -> list[dict]:
    rows = db.fetchall("SELECT * FROM menu_items ORDER BY mi_category, mi_name")
    return [
        {
            "id": r["mi_id"], "name": r["mi_name"], "category": r["mi_category"] or "Other",
            "price": float(r["mi_price"] or 0.0), "status": r.get("mi_status") or "Available",
            "description": r.get("mi_description") or "",
        }
        for r in rows
    ]


def add_menu_item(name: str, category: str = "Main Dish", price: float = 0.0, status: str = "Available", description: str = "") -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Item name is required.")
    return db.execute(
        "INSERT INTO menu_items (mi_name, mi_category, mi_price, mi_status, mi_description) VALUES (?, ?, ?, ?, ?)",
        (name, (category or "Other").strip(), float(price or 0.0), status, (description or "").strip()),
    )


def update_menu_item(mi_id: int, name: str, category: str = "Main Dish", price: float = 0.0, status: str = "Available", description: str = "") -> bool:
    name = (name or "").strip()
    if not name or not mi_id:
        return False
    db.execute(
        "UPDATE menu_items SET mi_name = ?, mi_category = ?, mi_price = ?, mi_status = ?, mi_description = ? WHERE mi_id = ?",
        (name, (category or "Other").strip(), float(price or 0.0), status, (description or "").strip(), mi_id),
    )
    return True


def delete_menu_item(mi_id: int) -> bool:
    if not mi_id:
        return False
    db.execute("DELETE FROM menu_items WHERE mi_id = ?", (mi_id,))
    return True


def get_menu_categories() -> list[str]:
    rows = db.fetchall("SELECT DISTINCT mi_category FROM menu_items WHERE mi_category IS NOT NULL AND mi_category != '' ORDER BY mi_category")
    cats = [r["mi_category"] for r in rows]
    defaults = ["Beef", "Pork", "Chicken", "Fish & Seafood", "Pasta & Noodles", "Vegetables", "Dessert", "Beverage", "Add-on"]
    for d in defaults:
        if d not in cats:
            cats.append(d)
    return cats


def get_package_menu_choices(package_id: int = None) -> dict[str, list[dict]]:
    """Menu choices grouped by category for selection. If package items exist, includes them;
    otherwise lists all available menu items grouped by category."""
    grouped: dict[str, list[dict]] = {}

    # First check all available menu items
    all_items = db.fetchall("SELECT * FROM menu_items WHERE mi_status = 'Available' ORDER BY mi_category, mi_name")
    for r in all_items:
        cat = r["mi_category"] or "Main Dish"
        grouped.setdefault(cat, []).append({
            "menu_item_id": r["mi_id"],
            "name": r["mi_name"],
            "category": cat,
            "price": float(r["mi_price"] or 0.0),
            "description": r.get("mi_description") or "",
        })
    return grouped


# ─────────────────────────────────────────────────────────────────────────
# ORDER CREATION (single-shot, atomic write at Confirm)
# ─────────────────────────────────────────────────────────────────────────

def _gen_booking_ref() -> str:
    row = db.fetchone("SELECT COUNT(*) AS c FROM bookings")
    n = (row["c"] if row else 0) + 1
    return f"{_BOOKING_REF_PREFIX}-{n:05d}-{int(datetime.now().timestamp()) % 100000}"


def create_order(order: dict) -> dict:
    """order = {
        customer_id, customer_name, contact, email, address,
        event_date, event_time, venue, occasion, pax,
        package_id, package_name, base_total,
        menu_selections: [{item_name, category, price, quantity}],
        additional_charges: [{description, amount}],
        discount_total: float,          # already folded into additional_charges as negative entries
        down_payment: float, payment_method: str,
        notes: str,
    }
    Returns {"booking_id", "booking_ref", "invoice_id", "total", "paid", "balance", "status"}.
    """
    customer_id = order.get("customer_id")
    if not customer_id:
        customer_id = add_customer(order["customer_name"], order.get("contact", ""), order.get("email", ""), order.get("address", ""))

    booking_ref = _gen_booking_ref()
    base_total = float(order.get("base_total") or 0.0)
    charges_sum = sum(float(c["amount"]) for c in order.get("additional_charges", []))
    total = base_total + charges_sum
    down_payment = float(order.get("down_payment") or 0.0)

    booking_id = db.execute("""
        INSERT INTO bookings (
            bk_booking_ref, bk_customer_id, bk_customer_name, bk_address, bk_event_date, bk_event_time,
            bk_venue, bk_occasion, bk_pax, bk_total_amount, bk_base_total, bk_payment_mode,
            bk_amount_paid, bk_down_payment, bk_menu_type, bk_package_id, bk_notes, bk_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'package', ?, ?, 'PENDING')
    """, (
        booking_ref, customer_id, order["customer_name"], order.get("address", ""),
        order["event_date"], order.get("event_time", "18:00"), order.get("venue", ""),
        order.get("occasion", ""), int(order.get("pax") or 1), total, base_total,
        order.get("payment_method", "Cash"), down_payment, down_payment,
        order.get("package_id"), order.get("notes", ""),
    ))

    for m in order.get("menu_selections", []):
        db.execute("""
            INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (booking_id, m.get("menu_item_id"), m["item_name"], m.get("category", ""), float(m.get("price") or 0.0), int(m.get("quantity") or 1)))

    for c in order.get("additional_charges", []):
        db.execute("""
            INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by)
            VALUES (?, ?, ?, ?, ?)
        """, (booking_id, c["description"], float(c["amount"]), _date.today().isoformat(), order.get("actor", "Tablet")))

    status = db.compute_invoice_status(total, down_payment)
    balance = max(0.0, total - down_payment)
    inv_num = f"INV-{booking_ref}"
    invoice_id = db.execute("""
        INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name,
            inv_event_date, inv_total_amount, inv_amount_paid, inv_balance, inv_down_payment, inv_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (booking_id, inv_num, inv_num, order["customer_name"], order["event_date"], total, down_payment, balance, down_payment, status))

    if down_payment > 0:
        db.execute("""
            INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_notes, pr_is_downpayment)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (invoice_id, down_payment, _date.today().isoformat(), order.get("payment_method", "Cash"), "Down payment recorded on tablet order"))

    return {
        "booking_id": booking_id, "booking_ref": booking_ref, "invoice_id": invoice_id,
        "total": total, "paid": down_payment, "balance": balance, "status": status,
    }


def record_terms_acknowledgement(booking_id: int, version: str, customer_name: str) -> None:
    db.execute("""
        INSERT INTO terms_acknowledgements (ta_booking_id, ta_version, ta_acknowledged, ta_acknowledged_at, ta_customer_name)
        VALUES (?, ?, 1, ?, ?)
    """, (booking_id, version, datetime.now().isoformat(timespec="seconds"), customer_name))


def get_order_detail(booking_id: int) -> Optional[dict]:
    b = db.fetchone("SELECT * FROM bookings WHERE bk_id = ?", (booking_id,))
    if not b:
        return None
    inv = db.fetchone("SELECT * FROM invoices WHERE inv_booking_id = ? LIMIT 1", (booking_id,))
    menu_items = db.fetchall("SELECT * FROM booking_menu_items WHERE bmi_booking_id = ?", (booking_id,))
    charges = db.fetchall("SELECT * FROM booking_additional_charges WHERE ac_booking_id = ?", (booking_id,))
    payments = db.fetchall("SELECT * FROM payment_records WHERE pr_invoice_id = ?", (inv["inv_id"],)) if inv else []
    terms = db.fetchone("SELECT * FROM terms_acknowledgements WHERE ta_booking_id = ? ORDER BY ta_id DESC LIMIT 1", (booking_id,))

    return {
        "booking_id": b["bk_id"], "booking_ref": b["bk_booking_ref"],
        "customer_name": b["bk_customer_name"], "address": b["bk_address"],
        "event_date": b["bk_event_date"], "event_time": b["bk_event_time"],
        "venue": b["bk_venue"], "occasion": b["bk_occasion"], "pax": b["bk_pax"],
        "base_total": float(b["bk_base_total"] or 0.0), "total": float(b["bk_total_amount"] or 0.0),
        "paid": float(inv["inv_amount_paid"]) if inv else 0.0,
        "balance": float(inv["inv_balance"]) if inv else float(b["bk_total_amount"] or 0.0),
        "status": inv["inv_status"] if inv else "Unpaid",
        "menu_selections": [{"item_name": m["bmi_item_name"], "category": m["bmi_category"], "price": float(m["bmi_price"] or 0.0), "quantity": m["bmi_quantity"]} for m in menu_items],
        "additional_charges": [{"description": c["ac_description"], "amount": float(c["ac_amount"])} for c in charges],
        "payments": [{"amount": float(p["pr_amount"]), "date": p["pr_payment_date"], "method": p["pr_payment_method"]} for p in payments],
        "terms_version": terms["ta_version"] if terms else None,
        "terms_acknowledged_at": terms["ta_acknowledged_at"] if terms else None,
        "notes": b["bk_notes"],
    }


def get_all_orders(limit: int = 100) -> list[dict]:
    rows = db.fetchall("""
        SELECT b.bk_id, b.bk_booking_ref, b.bk_customer_name, b.bk_event_date, b.bk_total_amount, b.bk_status,
               i.inv_status, i.inv_amount_paid, i.inv_balance
        FROM bookings b LEFT JOIN invoices i ON i.inv_booking_id = b.bk_id
        ORDER BY b.bk_created_at DESC LIMIT ?
    """, (limit,))
    return [
        {
            "booking_id": r["bk_id"], "booking_ref": r["bk_booking_ref"], "customer": r["bk_customer_name"],
            "event_date": r["bk_event_date"], "total": float(r["bk_total_amount"] or 0.0),
            "paid": float(r["inv_amount_paid"] or 0.0), "balance": float(r["inv_balance"] or 0.0),
            "status": r["inv_status"] or "Unpaid",
        }
        for r in rows
    ]


def clear_all_orders() -> int:
    """Clears all historical orders and transactions from the tablet
    while keeping the customer list, menu, packages, and addresses intact.
    Returns the count of bookings cleared."""
    row = db.fetchone("SELECT COUNT(*) AS c FROM bookings")
    count = row["c"] if row else 0

    try:
        db.execute("PRAGMA foreign_keys = OFF;")
        db.execute("DELETE FROM payment_records")
        db.execute("DELETE FROM invoices")
        db.execute("DELETE FROM booking_additional_charges")
        db.execute("DELETE FROM booking_menu_items")
        db.execute("DELETE FROM terms_acknowledgements")
        db.execute("DELETE FROM bookings")
    finally:
        try:
            db.execute("PRAGMA foreign_keys = ON;")
        except Exception:
            pass

    return count


# ─────────────────────────────────────────────────────────────────────────
# BUILT-IN ADDRESS SYSTEM
# ─────────────────────────────────────────────────────────────────────────

_cebu_address_cache: Optional[list[dict]] = None


def get_all_cebu_addresses() -> list[dict]:
    global _cebu_address_cache
    if _cebu_address_cache:
        return _cebu_address_cache
    try:
        rows = db.fetchall("""
            SELECT b.ab_id AS barangay_id, b.ab_name AS barangay,
                   c.ac_id AS city_id, c.ac_name AS city,
                   pr.ap_id AS province_id, pr.ap_name AS province,
                   (b.ab_name || ', ' || c.ac_name || ', ' || pr.ap_name) AS display_text
            FROM address_barangays b
            JOIN address_cities    c  ON c.ac_id  = b.ab_city_id
            JOIN address_provinces pr ON pr.ap_id = c.ac_province_id
            ORDER BY c.ac_name, b.ab_name
        """)
        if rows:
            _cebu_address_cache = [dict(r) for r in rows]
            return _cebu_address_cache
    except Exception as exc:
        print(f"[tablet repo] get_all_cebu_addresses failed: {exc}")

    _cebu_address_cache = _cebu_address_cache or []
    return _cebu_address_cache


def search_cebu_address(query: str, limit: int = 15) -> list[dict]:
    if not query or len(query.strip()) < 1:
        return []
    all_addrs = get_all_cebu_addresses()
    q_tokens = query.strip().lower().replace(",", " ").split()
    results = []
    for addr in all_addrs:
        text = addr["display_text"].lower()
        if all(token in text for token in q_tokens):
            results.append(addr)
            if len(results) >= limit:
                break
    return results

