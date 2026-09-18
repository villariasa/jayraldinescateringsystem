"""
Repository layer — the ONLY place that touches utils.db.
All UI pages import from here, never from utils.db directly.

Column-name convention: the DB uses prefixed columns (bk_id, cus_name, etc.).
Every SELECT here uses AS aliases to map them back to the short names the GUI
expects, so no UI code needs to change.
"""
from __future__ import annotations
from datetime import date, time, datetime, timedelta
from typing import Optional
import utils.db as db
import utils.menu_store as menu_store


def format_time_ampm(t_raw) -> str:
    """
    Converts any time representation (e.g. '18:00', '18:00:00', '09:30', time objects)
    into standard 12-hour AM/PM format (e.g. '6:00 PM', '9:30 AM', '11:45 AM').
    Replaces all military time.
    """
    if not t_raw:
        return "6:00 PM"
    if hasattr(t_raw, "strftime"):
        return t_raw.strftime("%I:%M %p").lstrip("0")
    s = str(t_raw).strip()
    if not s or s in ("—", "-", "TBA", "None", "null"):
        return "6:00 PM"
    for fmt in ("%I:%M %p", "%I:%M%p", "%I:%M %P", "%I:%M%P", "%H:%M:%S", "%H:%M", "%H:%M:%S.%f"):
        try:
            parsed = datetime.strptime(s, fmt).time()
            return parsed.strftime("%I:%M %p").lstrip("0")
        except ValueError:
            continue
    return s


# ---------------------------------------------------------------------------
# MENU ITEMS & PACKAGES
# ---------------------------------------------------------------------------

def get_available_menu_items() -> list[dict]:
    return menu_store.get_available_items()


def get_all_customers(force_refresh: bool = False) -> list[dict]:
    from utils.data_cache import DataCache
    if not force_refresh:
        cached = DataCache.get("customers")
        if cached is not None:
            return cached

    rows = db.fetchall("""
        SELECT c.cus_id       AS id,
               c.cus_name     AS name,
               c.cus_contact  AS contact,
               c.cus_email    AS email,
               c.cus_address  AS address,
               COALESCE(b.cnt, 0) AS total_events,
               COALESCE(b.total, 0.0) AS total_spent,
               c.cus_status   AS status,
               c.cus_loyalty_tier AS loyalty_tier
        FROM customers c
        LEFT JOIN (
            SELECT bk_customer_id, COUNT(*) AS cnt, SUM(bk_total_amount) AS total
            FROM bookings
            WHERE bk_status != 'CANCELLED'
            GROUP BY bk_customer_id
        ) b ON b.bk_customer_id = c.cus_id
        ORDER BY c.cus_name
    """)
    if not rows:
        DataCache.set("customers", [], ttl_seconds=300.0)
        return []
    result = [
        {
            "id":           r["id"],
            "name":         r["name"],
            "contact":      r["contact"],
            "email":        r["email"] or "",
            "address":      r["address"] or "",
            "events":       int(r["total_events"] or 0),
            "total_spent":  float(r["total_spent"] or 0.0),
            "loyalty_tier": r.get("loyalty_tier") or ("Gold" if int(r["total_events"] or 0) >= 5 or float(r["total_spent"] or 0.0) >= 100000 else ("Silver" if int(r["total_events"] or 0) >= 3 or float(r["total_spent"] or 0.0) >= 50000 else "Bronze")),
            "status":       r["status"],
        }
        for r in rows
    ]
    DataCache.set("customers", result, ttl_seconds=300.0)
    return result



def add_customer(data: dict) -> Optional[int]:
    name = str(data.get("name", "")).strip()
    if not name:
        return None
    contact = str(data.get("contact", "")).strip()
    email = str(data.get("email", "")).strip()
    address = str(data.get("address", "")).strip()
    status = str(data.get("status", "Active")).strip()
    if status not in ("Active", "Pending", "Inactive"):
        status = "Active"

    cust_id = None
    try:
        result = db.callproc_out(
            "sp_add_customer",
            in_params=(name, contact, email, address, status),
            out_names=["p_customer_id"],
        )
        if result and result.get("p_customer_id"):
            cust_id = result["p_customer_id"]
    except Exception as exc:
        print(f"[repository] sp_add_customer procedure failed: {exc}")

    # Fallback direct insert if procedure fails or returns None
    if not cust_id:
        try:
            row = db.fetchone("""
                INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status)
                VALUES (%s, %s, %s, %s, %s::customer_status)
                ON CONFLICT (cus_name, cus_contact) DO UPDATE
                SET cus_email = EXCLUDED.cus_email,
                    cus_address = EXCLUDED.cus_address,
                    cus_status = EXCLUDED.cus_status
                RETURNING cus_id
            """, (name, contact, email, address, status))
            if row and row.get("cus_id"):
                cust_id = row["cus_id"]
        except Exception as exc:
            print(f"[repository] add_customer direct insert failed: {exc}")
            existing = db.fetchone(
                "SELECT cus_id FROM customers WHERE cus_name = %s LIMIT 1", (name,)
            )
            if existing and existing.get("cus_id"):
                cust_id = existing["cus_id"]

    if cust_id:
        from utils.data_cache import DataCache
        DataCache.invalidate("customers")
        DataCache.invalidate("customers_loyalty")
        write_audit_log(
            action="CREATE",
            table_name="customers",
            record_id=cust_id,
            new_value={"name": name, "contact": contact, "email": email, "address": address, "status": status}
        )
        return cust_id

    return None


def update_customer(customer_id: int, data: dict) -> None:
    from utils.data_cache import DataCache
    DataCache.invalidate("customers")
    DataCache.invalidate("customers_loyalty")
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
    write_audit_log(
        action="UPDATE",
        table_name="customers",
        record_id=customer_id,
        new_value={
            "name": data.get("name", ""),
            "contact": data.get("contact", ""),
            "email": data.get("email", ""),
            "address": data.get("address", ""),
            "status": data.get("status", "Active"),
        }
    )


def delete_customer(customer_id: int) -> None:
    from utils.data_cache import DataCache
    DataCache.invalidate("customers")
    DataCache.invalidate("customers_loyalty")
    c_name = ""
    try:
        row = db.fetchone("SELECT cus_name FROM customers WHERE cus_id = %s", (customer_id,))
        if row:
            c_name = row.get("cus_name", "")
    except Exception:
        pass
    db.callproc_void("sp_delete_customer", in_params=(customer_id,))
    write_audit_log(
        action="DELETE",
        table_name="customers",
        record_id=customer_id,
        old_value={"name": c_name or f"Customer #{customer_id}"}
    )



def delete_multiple_customers(customer_ids: list[int]) -> int:
    """Deletes multiple customers by their IDs in a single operation."""
    if not customer_ids:
        return 0
    count = 0
    for cid in customer_ids:
        try:
            delete_customer(int(cid))
            count += 1
        except Exception as exc:
            print(f"[repository] delete_multiple_customers failed for ID {cid}: {exc}")
    return count


def delete_multiple_bookings(booking_ids: list[int | str]) -> int:
    """Deletes multiple bookings by their IDs or references."""
    if not booking_ids:
        return 0
    count = 0
    for bid in booking_ids:
        try:
            if isinstance(bid, str) and (bid.startswith("BK-") or bid.startswith("ORD-")):
                row = db.fetchone("SELECT bk_id FROM bookings WHERE bk_booking_ref = %s", (bid,))
                if row and row.get("bk_id"):
                    delete_booking(int(row["bk_id"]))
                    count += 1
            else:
                delete_booking(int(bid))
                count += 1
        except Exception as exc:
            print(f"[repository] delete_multiple_bookings failed for ID {bid}: {exc}")
    return count


def merge_duplicate_customers() -> int:
    """Finds duplicate customers (same normalized name, with a matching or
    absent contact number) and consolidates all booking relations and event
    totals into a single master customer row.

    Deliberately does NOT match on contact number alone: two different real
    customers can share a phone number (a household landline, an office
    number), and merging on that basis silently hard-deletes one of them.
    Only rows with the same name are considered duplicates of each other;
    among those, a contact mismatch (both sides non-empty and different)
    blocks the merge since it signals two distinct people who just share a
    name."""
    import re
    all_custs = get_all_customers()
    if not all_custs:
        return 0

    merged_count = 0
    seen_groups = {}
    for c in all_custs:
        norm_name = re.sub(r"[^\w]", "", str(c.get("name", "")).lower())
        if not norm_name:
            continue
        seen_groups.setdefault(norm_name, []).append(c)

    for key, name_group in seen_groups.items():
        non_empty_contacts = {}
        no_contact = []
        for c in name_group:
            norm_contact = re.sub(r"\D", "", str(c.get("contact", "")))
            if norm_contact:
                non_empty_contacts.setdefault(norm_contact, []).append(c)
            else:
                no_contact.append(c)

        if len(non_empty_contacts) == 0:
            # No one under this name has a contact on file - nothing to
            # disambiguate by, merge them same as before.
            groups_to_merge = [name_group] if len(name_group) > 1 else []
        elif len(non_empty_contacts) == 1:
            # Only one distinct contact for this name - blank-contact rows
            # unambiguously belong with it.
            (only_group,) = non_empty_contacts.values()
            groups_to_merge = [only_group + no_contact]
        else:
            # Multiple distinct contacts under the same name: these are
            # likely different people who happen to share a name. Only
            # merge exact contact matches; leave blank-contact rows alone
            # since it's ambiguous which person they belong to.
            groups_to_merge = [g for g in non_empty_contacts.values() if len(g) > 1]

        for group in groups_to_merge:
            group.sort(key=lambda x: (int(x.get("events") or 0), -(int(x.get("id") or 0))), reverse=True)
            master = group[0]
            master_id = master["id"]

            for dup in group[1:]:
                dup_id = dup["id"]
                try:
                    db.execute("UPDATE bookings SET bk_customer_id = %s, bk_customer_name = %s WHERE bk_customer_id = %s",
                               (master_id, master["name"], dup_id))
                    db.execute("UPDATE customer_follow_ups SET cf_customer_id = %s WHERE cf_customer_id = %s",
                               (master_id, dup_id))
                    delete_customer(dup_id)
                    merged_count += 1
                except Exception as exc:
                    print(f"[repository] Failed merging duplicate customer {dup_id} -> {master_id}: {exc}")

            try:
                b_stats = db.fetchone("""
                    SELECT COUNT(*) AS cnt, COALESCE(SUM(bk_total_amount), 0.0) AS spent
                    FROM bookings WHERE bk_customer_id = %s AND bk_status != 'CANCELLED'
                """, (master_id,))
                if b_stats:
                    ev_cnt = int(b_stats.get("cnt") or 0)
                    sp_amt = float(b_stats.get("spent") or 0.0)
                    tier = "Gold" if (ev_cnt >= 5 or sp_amt >= 100000) else ("Silver" if (ev_cnt >= 3 or sp_amt >= 50000) else "Bronze")
                    db.execute("""
                        UPDATE customers
                        SET cus_total_events = %s, cus_total_spent = %s, cus_loyalty_tier = %s
                        WHERE cus_id = %s
                    """, (ev_cnt, sp_amt, tier, master_id))
            except Exception as exc:
                print(f"[repository] Error recalculating master customer stats: {exc}")

    return merged_count


def get_customer_names() -> list[str]:
    rows = db.fetchall(
        "SELECT cus_name AS name FROM customers WHERE cus_status != 'Inactive' ORDER BY cus_name"
    )
    return [r["name"] for r in rows] if rows else []


def get_customer_by_name(name: str) -> Optional[dict]:
    """Fetch customer details by name."""
    if not name:
        return None
    row = db.fetchone(
        "SELECT cus_id AS id, cus_name AS name, cus_contact AS contact, cus_email AS email, cus_address AS address, cus_status AS status FROM customers WHERE cus_name = %s LIMIT 1",
        (name,)
    )
    return dict(row) if row else None


def customer_exists(name: str) -> bool:
    """Case-insensitive duplicate check by customer name — matches the
    convention used elsewhere in this file (bookings/customers are keyed by
    name, not contact, e.g. get_customer_by_name)."""
    name = (name or "").strip()
    if not name:
        return False
    row = db.fetchone(
        "SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(%s) LIMIT 1",
        (name,),
    )
    return bool(row)


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
               mi_status::TEXT            AS status,
               COALESCE(mi_image, '')     AS image
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
            "image":       r.get("image", "") or "",
        }
        for r in rows
    ]


def get_menu_items_page(offset: int = 0, limit: int = 50) -> list[dict]:
    """Fetch one page of menu items, ordered as get_all_menu_items. Used for
    incremental/lazy loading so we never fetch/shape rows nobody's scrolled to."""
    rows = db.fetchall("""
        SELECT mi_id                       AS id,
               mi_name                    AS name,
               mi_description             AS description,
               mi_category::TEXT          AS category,
               mi_package_tier::TEXT      AS package,
               mi_price                   AS price,
               mi_status::TEXT            AS status,
               COALESCE(mi_image, '')     AS image
        FROM menu_items ORDER BY mi_category, mi_name LIMIT %s OFFSET %s
    """, (limit, offset))
    if not rows:
        return []
    return [
        {
            "id":          r["id"],
            "item":        r["name"],
            "description": r["description"] or "",
            "category":    r["category"],
            "package":     r["package"],
            "price":       float(r["price"]),
            "status":      r["status"],
            "image":       r.get("image", "") or "",
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
               mi_status::TEXT       AS status,
               COALESCE(mi_image, '') AS image
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
            "image":       r.get("image", "") or "",
        }
        for r in rows
    ]


def add_menu_item(data: dict) -> Optional[int]:
    item_name = data.get("item") or data.get("name", "")
    raw_st = str(data.get("status", "Available")).strip().lower()
    st = "Unavailable" if any(w in raw_st for w in ("unavail", "inact", "out", "disab", "no")) else "Available"
    image_val = data.get("image", "") or ""
    p_id = None
    try:
        result = db.callproc_out(
            "sp_add_menu_item",
            in_params=(
                item_name,
                data.get("description", ""),
                data.get("category", "Main Course"),
                data.get("package", "Standard"),
                data.get("price", 0.0),
                st,
                image_val,
            ),
            out_names=["p_item_id"],
        )
        if result and result.get("p_item_id"):
            p_id = result["p_item_id"]
    except Exception as exc:
        print(f"[repository] sp_add_menu_item call failed: {exc}")

    if not p_id:
        try:
            row = db.fetchone("""
                INSERT INTO menu_items (mi_name, mi_description, mi_category, mi_package_tier, mi_price, mi_status, mi_image)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (mi_name) DO UPDATE SET
                    mi_description = COALESCE(NULLIF(EXCLUDED.mi_description, ''), menu_items.mi_description),
                    mi_price = EXCLUDED.mi_price,
                    mi_category = EXCLUDED.mi_category,
                    mi_image = CASE WHEN EXCLUDED.mi_image <> '' THEN EXCLUDED.mi_image ELSE menu_items.mi_image END
                RETURNING mi_id
            """, (item_name, data.get("description", ""), data.get("category", "Main Course"), data.get("package", "Standard"), data.get("price", 0.0), st, image_val))
            if row and row.get("mi_id"):
                p_id = row["mi_id"]
        except Exception as exc:
            print(f"[repository] add_menu_item direct insert fallback failed: {exc}")

    menu_store.add_item(data)
    if p_id:
        write_audit_log(
            action="CREATE",
            table_name="menu_items",
            record_id=p_id,
            new_value={"name": item_name, "category": data.get("category"), "price": data.get("price")}
        )
    return p_id


def update_menu_item(item_id: int, data: dict) -> None:
    item_name = data.get("item") or data.get("name", "")
    raw_st = str(data.get("status", "Available")).strip().lower()
    st = "Unavailable" if any(w in raw_st for w in ("unavail", "inact", "out", "disab", "no")) else "Available"
    image_val = data.get("image", "") or ""
    try:
        db.callproc_void(
            "sp_update_menu_item",
            in_params=(
                item_id,
                item_name,
                data.get("description", ""),
                data.get("category", "Main Course"),
                data.get("package", "Standard"),
                data.get("price", 0.0),
                st,
                image_val,
            ),
        )
    except Exception as exc:
        print(f"[repository] sp_update_menu_item failed, falling back to direct UPDATE: {exc}")
        try:
            db.execute("""
                UPDATE menu_items
                SET mi_name = %s, mi_description = %s, mi_category = %s::menu_category, mi_package_tier = %s::menu_package_tier,
                    mi_price = %s, mi_status = %s::menu_status,
                    mi_image = CASE WHEN %s <> '' THEN %s ELSE mi_image END,
                    mi_updated_at = NOW()
                WHERE mi_id = %s
            """, (item_name, data.get("description", ""), data.get("category", "Main Course"), data.get("package", "Standard"), data.get("price", 0.0), st, image_val, image_val, item_id))
        except Exception as exc2:
            print(f"[repository] update_menu_item direct fallback failed: {exc2}")

    write_audit_log(
        action="UPDATE",
        table_name="menu_items",
        record_id=item_id,
        new_value={"name": data.get("item") or data.get("name"), "category": data.get("category"), "price": data.get("price")}
    )


def delete_menu_item(arg1: int, arg2: int = None) -> None:
    # Supports both delete_menu_item(item_id) and delete_menu_item(index, item_id)
    if arg2 is not None:
        item_id = int(arg2)
        idx = int(arg1)
    else:
        item_id = int(arg1)
        idx = 0
    m_name = ""
    try:
        row = db.fetchone("SELECT mi_name FROM menu_items WHERE mi_id = %s", (item_id,))
        if row:
            m_name = row.get("mi_name", "")
    except Exception:
        pass
    db.callproc_void("sp_delete_menu_item", in_params=(item_id,))
    try:
        menu_store.remove_item(idx)
    except Exception:
        pass
    write_audit_log(
        action="DELETE",
        table_name="menu_items",
        record_id=item_id,
        old_value={"name": m_name or f"Menu Item #{item_id}"}
    )


def delete_multiple_menu_items(item_ids: list[int]) -> int:
    """Deletes multiple menu items by their IDs."""
    if not item_ids:
        return 0
    count = 0
    for mid in item_ids:
        try:
            delete_menu_item(int(mid))
            count += 1
        except Exception as exc:
            print(f"[repository] delete_multiple_menu_items failed for ID {mid}: {exc}")
    return count


def delete_multiple_packages(pkg_ids: list[int]) -> int:
    """Deletes multiple packages by their IDs."""
    if not pkg_ids:
        return 0
    count = 0
    for pid in pkg_ids:
        try:
            if delete_package(int(pid)):
                count += 1
        except Exception as exc:
            print(f"[repository] delete_multiple_packages failed for ID {pid}: {exc}")
    return count


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
    try:
        rows = db.fetchall(
            "SELECT occ_name AS name FROM occasions WHERE occ_is_active = 1 OR occ_is_active IS NULL ORDER BY occ_id"
        )
        if rows:
            res = [str(r["name"]).strip() for r in rows if r.get("name") and str(r["name"]).strip()]
            if res:
                return res
    except Exception as exc:
        print(f"[repository] get_all_occasions error: {exc}")

    defaults = [
        "Wedding", "Birthday", "Debut", "Corporate Event", "Anniversary",
        "Christening", "Graduation", "Holiday Party"
    ]
    try:
        for d in defaults:
            db.execute("INSERT INTO occasions (occ_name, occ_is_active) VALUES (%s, 1) ON CONFLICT (occ_name) DO NOTHING", (d,))
    except Exception:
        pass
    return defaults


def add_occasion(name: str) -> None:
    if not name or not name.strip():
        return
    clean_name = name.strip()
    db.execute(
        "INSERT INTO occasions (occ_name, occ_is_active) VALUES (%s, 1) ON CONFLICT (occ_name) DO UPDATE SET occ_is_active = 1",
        (clean_name,),
    )
    write_audit_log(action="CREATE", table_name="occasions", record_id=0, new_value={"name": clean_name})


def update_occasion(old_name: str, new_name: str) -> None:
    if not new_name or not new_name.strip():
        return
    db.execute(
        "UPDATE occasions SET occ_name = %s WHERE occ_name = %s",
        (new_name.strip(), old_name.strip()),
    )
    write_audit_log(
        action="UPDATE",
        table_name="occasions",
        record_id=0,
        old_value={"name": old_name.strip()},
        new_value={"name": new_name.strip()}
    )


def delete_occasion(name: str) -> None:
    if not name:
        return
    db.execute("DELETE FROM occasions WHERE occ_name = %s", (name.strip(),))
    write_audit_log(
        action="DELETE",
        table_name="occasions",
        record_id=0,
        old_value={"name": name.strip()}
    )


# ---------------------------------------------------------------------------
# MENU CATEGORIES
# ---------------------------------------------------------------------------

_DEFAULT_MENU_CATEGORIES = ["Main Course", "Noodles", "Soup", "Vegetables", "Dessert", "Drinks", "Bread", "Other"]


def get_all_menu_categories() -> list[str]:
    try:
        rows = db.fetchall(
            "SELECT mc_name AS name FROM menu_categories WHERE mc_is_active = 1 OR mc_is_active IS NULL ORDER BY mc_id"
        )
        if rows:
            res = [str(r["name"]).strip() for r in rows if r.get("name") and str(r["name"]).strip()]
            if res:
                return res
    except Exception as exc:
        print(f"[repository] get_all_menu_categories error: {exc}")

    try:
        for d in _DEFAULT_MENU_CATEGORIES:
            db.execute("INSERT INTO menu_categories (mc_name, mc_is_active) VALUES (%s, 1) ON CONFLICT (mc_name) DO NOTHING", (d,))
    except Exception:
        pass
    return list(_DEFAULT_MENU_CATEGORIES)


def add_menu_category(name: str) -> None:
    if not name or not name.strip():
        return
    clean_name = name.strip()
    db.execute(
        "INSERT INTO menu_categories (mc_name, mc_is_active) VALUES (%s, 1) ON CONFLICT (mc_name) DO UPDATE SET mc_is_active = 1",
        (clean_name,),
    )
    write_audit_log(action="CREATE", table_name="menu_categories", record_id=0, new_value={"name": clean_name})


def update_menu_category(old_name: str, new_name: str) -> None:
    if not new_name or not new_name.strip():
        return
    db.execute(
        "UPDATE menu_categories SET mc_name = %s WHERE mc_name = %s",
        (new_name.strip(), old_name.strip()),
    )
    # Keep existing menu items pointing at the renamed category instead of
    # silently orphaning them under the old (now-gone) name.
    db.execute(
        "UPDATE menu_items SET mi_category = %s WHERE mi_category = %s",
        (new_name.strip(), old_name.strip()),
    )
    write_audit_log(
        action="UPDATE",
        table_name="menu_categories",
        record_id=0,
        old_value={"name": old_name.strip()},
        new_value={"name": new_name.strip()}
    )


def delete_menu_category(name: str) -> None:
    if not name:
        return
    db.execute("DELETE FROM menu_categories WHERE mc_name = %s", (name.strip(),))
    write_audit_log(
        action="DELETE",
        table_name="menu_categories",
        record_id=0,
        old_value={"name": name.strip()}
    )


# ---------------------------------------------------------------------------
# PACKAGES
# ---------------------------------------------------------------------------

def get_all_packages() -> list[dict]:
    pkg_rows = db.fetchall("""
        SELECT pkg_id                  AS id,
               pkg_name                AS name,
               pkg_price_per_pax       AS price_per_pax,
               pkg_min_pax             AS min_pax,
               pkg_description         AS description,
               COALESCE(pkg_image, '') AS image
        FROM packages
        ORDER BY pkg_price_per_pax ASC
    """)
    if not pkg_rows:
        return []

    # Batch fetch all package items
    pi_rows = db.fetchall("""
        SELECT pi.pi_id              AS id,
               pi.pi_package_id      AS package_id,
               pi.pi_menu_item_id    AS menu_item_id,
               COALESCE(mi.mi_name, '') AS item_name,
               COALESCE(mi.mi_category::TEXT, 'General') AS category,
               COALESCE(pi.pi_custom_price, 0.0) AS custom_price
        FROM package_items pi
        LEFT JOIN menu_items mi ON mi.mi_id = pi.pi_menu_item_id
        ORDER BY pi.pi_package_id, item_name
    """)
    items_by_pkg: dict[int, list[dict]] = {}
    for item in pi_rows or []:
        p_id = item.get("package_id")
        if p_id:
            items_by_pkg.setdefault(p_id, []).append({
                "id":           item["id"],
                "menu_item_id": item["menu_item_id"],
                "item_name":    item["item_name"],
                "category":     item["category"],
                "custom_price": float(item["custom_price"]),
            })

    result = []
    for r in pkg_rows:
        p_id = r["id"]
        result.append({
            "id":            p_id,
            "name":          r["name"],
            "price_per_pax": float(r["price_per_pax"]),
            "min_pax":       int(r["min_pax"]),
            "description":   r["description"] or "",
            "image":         r.get("image", "") or "",
            "items":         items_by_pkg.get(p_id, []),
        })
    return result


def get_packages_page(offset: int = 0, limit: int = 50) -> list[dict]:
    """Fetch one page of packages (with their items), ordered as get_all_packages.
    Package items are fetched only for the packages in this page, so we never
    shape rows/joins for packages nobody's scrolled to."""
    pkg_rows = db.fetchall("""
        SELECT pkg_id                  AS id,
               pkg_name                AS name,
               pkg_price_per_pax       AS price_per_pax,
               pkg_min_pax             AS min_pax,
               pkg_description         AS description,
               COALESCE(pkg_image, '') AS image
        FROM packages
        ORDER BY pkg_price_per_pax ASC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    if not pkg_rows:
        return []

    pkg_ids = [r["id"] for r in pkg_rows]
    placeholders = ",".join(["%s"] * len(pkg_ids))
    pi_rows = db.fetchall(f"""
        SELECT pi.pi_id              AS id,
               pi.pi_package_id      AS package_id,
               pi.pi_menu_item_id    AS menu_item_id,
               COALESCE(mi.mi_name, '') AS item_name,
               COALESCE(mi.mi_category::TEXT, 'General') AS category,
               COALESCE(pi.pi_custom_price, 0.0) AS custom_price
        FROM package_items pi
        LEFT JOIN menu_items mi ON mi.mi_id = pi.pi_menu_item_id
        WHERE pi.pi_package_id IN ({placeholders})
        ORDER BY pi.pi_package_id, item_name
    """, tuple(pkg_ids))
    items_by_pkg: dict[int, list[dict]] = {}
    for item in pi_rows or []:
        p_id = item.get("package_id")
        if p_id:
            items_by_pkg.setdefault(p_id, []).append({
                "id":           item["id"],
                "menu_item_id": item["menu_item_id"],
                "item_name":    item["item_name"],
                "category":     item["category"],
                "custom_price": float(item["custom_price"]),
            })

    result = []
    for r in pkg_rows:
        p_id = r["id"]
        result.append({
            "id":            p_id,
            "name":          r["name"],
            "price_per_pax": float(r["price_per_pax"]),
            "min_pax":       int(r["min_pax"]),
            "description":   r["description"] or "",
            "image":         r.get("image", "") or "",
            "items":         items_by_pkg.get(p_id, []),
        })
    return result


def get_package_items(package_id: int) -> list[dict]:
    rows = db.fetchall(
        """
        SELECT pi.pi_id              AS id,
               pi.pi_menu_item_id    AS menu_item_id,
               COALESCE(NULLIF(pi.pi_item_name, ''), mi.mi_name, '') AS item_name,
               COALESCE(NULLIF(pi.pi_category, ''), mi.mi_category, 'General') AS category,
               COALESCE(pi.pi_custom_price, 0.0) AS custom_price
        FROM package_items pi
        LEFT JOIN menu_items mi ON mi.mi_id = pi.pi_menu_item_id
        WHERE pi.pi_package_id = %s
        ORDER BY category, item_name
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
        pkg_row = db.fetchone("SELECT pkg_id FROM packages WHERE pkg_id = %s", (package_id,))
        if not pkg_row:
            return False

        db.execute("DELETE FROM package_items WHERE pi_package_id = %s", (package_id,))
        for item in items:
            m_id = item.get("menu_item_id")
            c_price = float(item.get("custom_price", 0.0))
            valid_m_id = None
            i_name = str(item.get("item_name") or item.get("item") or item.get("name") or "")
            i_cat = str(item.get("category") or "General")

            if m_id:
                mi_row = db.fetchone("SELECT mi_id, mi_name, mi_category FROM menu_items WHERE mi_id = %s", (m_id,))
                if mi_row:
                    valid_m_id = mi_row.get("mi_id")
                    i_name = mi_row.get("mi_name") or i_name
                    i_cat = mi_row.get("mi_category") or i_cat

            if not valid_m_id and i_name:
                name_row = db.fetchone("SELECT mi_id, mi_name, mi_category FROM menu_items WHERE LOWER(mi_name) = LOWER(%s) LIMIT 1", (i_name,))
                if name_row:
                    valid_m_id = name_row.get("mi_id")
                    i_cat = name_row.get("mi_category") or i_cat

            if valid_m_id:
                try:
                    db.execute(
                        "INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price, pi_item_name, pi_category) VALUES (%s, %s, %s, %s, %s)",
                        (package_id, valid_m_id, c_price, i_name, i_cat),
                    )
                except Exception:
                    db.execute(
                        "INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price) VALUES (%s, %s, %s)",
                        (package_id, valid_m_id, c_price),
                    )
            elif i_name:
                try:
                    db.execute(
                        "INSERT INTO package_items (pi_package_id, pi_custom_price, pi_item_name, pi_category) VALUES (%s, %s, %s, %s)",
                        (package_id, c_price, i_name, i_cat),
                    )
                except Exception:
                    pass
        return True
    except Exception as exc:
        print(f"[repository] set_package_items failed: {exc}")
        return False


def add_package(data: dict) -> Optional[int]:
    pkg_id = None
    pkg_name = str(data.get("name", "")).strip()
    if not pkg_name:
        return None
    image_val = data.get("image", "") or ""
    try:
        existing = db.fetchone("SELECT pkg_id FROM packages WHERE LOWER(pkg_name) = LOWER(%s) LIMIT 1", (pkg_name,))
        if existing and existing.get("pkg_id"):
            pkg_id = existing["pkg_id"]
            db.execute("""
                UPDATE packages
                SET pkg_price_per_pax = %s,
                    pkg_min_pax = %s,
                    pkg_description = COALESCE(NULLIF(%s, ''), pkg_description),
                    pkg_image = CASE WHEN %s <> '' THEN %s ELSE pkg_image END
                WHERE pkg_id = %s
            """, (data.get("price_per_pax", 0.0), data.get("min_pax", 1), data.get("description", ""), image_val, image_val, pkg_id))
            return pkg_id

        result = db.callproc_out(
            "sp_add_package",
            in_params=(
                pkg_name,
                data.get("price_per_pax", 0.0),
                data.get("min_pax", 1),
                data.get("description", ""),
                image_val,
            ),
            out_names=["p_package_id"],
        )
        if result and result.get("p_package_id"):
            pkg_id = result["p_package_id"]
    except Exception as exc:
        print(f"[repository] sp_add_package failed: {exc}")

    # Fallback to direct INSERT / UPDATE if procedure failed or returned None
    if not pkg_id:
        try:
            row = db.fetchone("""
                INSERT INTO packages (pkg_name, pkg_price_per_pax, pkg_min_pax, pkg_description, pkg_image)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (pkg_name) DO UPDATE SET
                    pkg_price_per_pax = EXCLUDED.pkg_price_per_pax,
                    pkg_min_pax = EXCLUDED.pkg_min_pax,
                    pkg_description = COALESCE(NULLIF(EXCLUDED.pkg_description, ''), packages.pkg_description),
                    pkg_image = CASE WHEN EXCLUDED.pkg_image <> '' THEN EXCLUDED.pkg_image ELSE packages.pkg_image END
                RETURNING pkg_id
            """, (pkg_name, data.get("price_per_pax", 0.0), data.get("min_pax", 1), data.get("description", ""), image_val))
            if row and row.get("pkg_id"):
                pkg_id = row["pkg_id"]
        except Exception as exc:
            print(f"[repository] add_package direct insert fallback failed: {exc}")

    if pkg_id:
        try:
            db.execute("UPDATE packages SET pkg_image = %s WHERE pkg_id = %s", (image_val, pkg_id))
        except Exception:
            pass
        write_audit_log(
            action="CREATE",
            table_name="packages",
            record_id=pkg_id,
            new_value={"name": pkg_name, "price": data.get("price_per_pax"), "image": image_val}
        )
        return pkg_id
    return None


def update_package(db_id: int, data: dict) -> bool:
    image_val = data.get("image", "") or ""
    try:
        db.callproc_void(
            "sp_update_package",
            in_params=(
                db_id,
                data["name"],
                data["price_per_pax"],
                data.get("min_pax", 1),
                data.get("description", ""),
                image_val,
            ),
        )
    except Exception as exc:
        print(f"[repository] sp_update_package note: {exc}")

    try:
        db.execute("""
            UPDATE packages
            SET pkg_name = %s, pkg_price_per_pax = %s, pkg_min_pax = %s, pkg_description = %s,
                pkg_image = %s
            WHERE pkg_id = %s
        """, (data["name"], data["price_per_pax"], data.get("min_pax", 1), data.get("description", ""), image_val, db_id))
        write_audit_log(
            action="UPDATE",
            table_name="packages",
            record_id=db_id,
            new_value={"name": data["name"], "price": data.get("price_per_pax"), "image": image_val}
        )
        return True
    except Exception as exc2:
        print(f"[repository] update_package direct fallback failed: {exc2}")
        return False


def delete_package(db_id: int) -> bool:
    pkg_name = ""
    try:
        row = db.fetchone("SELECT pkg_name FROM packages WHERE pkg_id = %s", (db_id,))
        if row:
            pkg_name = row.get("pkg_name", "")
    except Exception:
        pass
    try:
        db.callproc_void("sp_delete_package", in_params=(db_id,))
        write_audit_log(
            action="DELETE",
            table_name="packages",
            record_id=db_id,
            old_value={"name": pkg_name or f"Package #{db_id}"}
        )
        return True
    except Exception as exc:
        print(f"[repository] delete_package failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# BOOKINGS
# ---------------------------------------------------------------------------
# BOOKINGS
# ---------------------------------------------------------------------------

# Shared column projection for booking rows so the full-fetch, paginated, and
# any future booking readers all shape rows identically.
_BOOKING_ROW_SQL = """
        SELECT b.bk_id                   AS id,
               b.bk_booking_ref          AS booking_ref,
               b.bk_customer_name        AS customer_name,
               COALESCE(NULLIF(b.bk_contact, ''), NULLIF(c.cus_contact, ''), '') AS contact,
               COALESCE(NULLIF(b.bk_email, ''), NULLIF(c.cus_email, ''), '')   AS email,
               b.bk_event_date           AS event_date,
               b.bk_event_time           AS event_time,
               b.bk_venue                AS venue,
               b.bk_occasion             AS occasion,
               b.bk_pax                  AS pax,
               b.bk_total_amount         AS total_amount,
               b.bk_amount_paid          AS amount_paid,
               COALESCE(b.bk_down_payment, b.bk_amount_paid, 0.0) AS down_payment,
               b.bk_status               AS status,
               b.bk_color_theme          AS color_theme,
               COALESCE(NULLIF(b.bk_special_notes, ''), NULLIF(b.bk_notes, ''), '') AS notes,
               b.bk_menu_type            AS menu_type,
               b.bk_payment_mode         AS payment_mode,
               b.bk_cancellation_reason  AS cancellation_reason,
               p.pkg_name                AS package_name
        FROM bookings b
        LEFT JOIN customers c ON c.cus_id = b.bk_customer_id
        LEFT JOIN packages p ON p.pkg_id = b.bk_package_id
"""


def _rows_to_booking_dicts(rows) -> list[dict]:
    if not rows:
        return []
    result = []
    for r in rows:
        t_val = format_time_ampm(r.get("event_time"))
        tot_val = float(r.get("total_amount") or 0.0)
        paid_val = float(r.get("amount_paid") or 0.0)
        bal_val = max(0.0, tot_val - paid_val)
        date_str = r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"] or "")

        result.append({
            "db_id":               r["id"],
            "id":                  r["booking_ref"] or "",
            "booking_ref":         r["booking_ref"] or "",
            "ref_id":              r["booking_ref"] or "",
            "date":                date_str,
            "event_date":          date_str,
            "time":                t_val,
            "event_time":          t_val,
            "name":                r["customer_name"] or "",
            "customer_name":       r["customer_name"] or "",
            "client_name":         r["customer_name"] or "",
            "contact":             r.get("contact") or "",
            "phone":               r.get("contact") or "",
            "email":               r.get("email") or "",
            "venue":               r.get("venue") or "",
            "occasion":            r.get("occasion") or "",
            "pax":                 str(r["pax"] or "0"),
            "total":               f"\u20b1 {int(tot_val):,}",
            "total_amount":        tot_val,
            "amount_paid":         paid_val,
            "down_payment":        paid_val,
            "balance":             bal_val,
            "status":              r["status"] or "PENDING",
            "color_theme":         r.get("color_theme") or "#2563EB",
            "color":               r.get("color_theme") or "#2563EB",
            "notes":               r.get("notes") or "",
            "menu_type":           r.get("menu_type") or "package",
            "package_name":        r.get("package_name") or "",
            "payment_mode":        r.get("payment_mode") or "Cash",
            "cancellation_reason": r.get("cancellation_reason") or "",
        })
    return result


def get_all_bookings(period_filter: str = "", confirmed_only: bool = False) -> list[dict]:
    """Unpaginated fetch of every booking (optionally status/period scoped).
    Kept for callers that genuinely need the full set (e.g. login pre-load cache,
    exports). The Orders UI uses get_bookings_page() for lazy per-tab loading."""
    status_clause = "AND b.bk_status IN ('CONFIRMED', 'COMPLETED')" if confirmed_only else ""
    rows = db.fetchall(
        _BOOKING_ROW_SQL + f"""
        WHERE 1=1 {status_clause} {period_filter}
        ORDER BY b.bk_id DESC
        """
    )
    return _rows_to_booking_dicts(rows)


# Status buckets the Orders tabs page through, so pagination filters map 1:1
# to what each tab renders.
_BOOKING_TAB_STATUSES = {
    "pending":   ("PENDING",),
    "confirmed": ("CONFIRMED", "COMPLETED"),
}


def get_bookings_page(status_filter=None, offset: int = 0, limit: int = 50,
                       date_start: str = None, date_end: str = None,
                       customer: str = None, event: str = None,
                       time_start: str = None, time_end: str = None) -> list[dict]:
    """Fetch one page of bookings, newest first, optionally filtered.

    status_filter: an iterable of status strings (e.g. ["PENDING"]) to restrict
      the result to those statuses, or None for all bookings (the Orders tab).
    date_start/date_end: optional ISO date bounds on the event date (both must
      be given together to apply; None/None = unbounded).
    customer: optional case-insensitive substring match on customer name.
    event: optional case-insensitive substring match on the occasion field.
    time_start/time_end: optional "HH:MM" (24h) bounds on the event time
      (both must be given together to apply) - lets Orders narrow bookings
      down to a specific time-of-day slot, on top of the date range.
    """
    params: list = []
    where = "WHERE 1=1"
    if status_filter:
        statuses = list(status_filter)
        placeholders = ", ".join(["%s"] * len(statuses))
        where += f" AND b.bk_status IN ({placeholders})"
        params.extend(statuses)
    if date_start and date_end:
        where += " AND b.bk_event_date BETWEEN %s AND %s"
        params.extend([date_start, date_end])
    if time_start and time_end:
        # SUBSTR to compare only the HH:MM portion - bk_event_time is a real
        # TIME column on Postgres but plain TEXT ("HH:MM:SS") on SQLite, so
        # comparing full-precision strings against a minute-granularity
        # "HH:MM" filter value could miscompare (e.g. "18:00" vs "18:00:00").
        where += " AND SUBSTR(CAST(b.bk_event_time AS TEXT), 1, 5) BETWEEN %s AND %s"
        params.extend([time_start, time_end])
    if customer:
        where += " AND b.bk_customer_name ILIKE %s"
        params.append(f"%{customer}%")
    if event:
        where += " AND b.bk_occasion ILIKE %s"
        params.append(f"%{event}%")
    params.extend([limit, offset])
    rows = db.fetchall(
        _BOOKING_ROW_SQL + f" {where} ORDER BY b.bk_id DESC LIMIT %s OFFSET %s",
        tuple(params),
    )
    return _rows_to_booking_dicts(rows)


def get_default_orders_window() -> tuple[str, str]:
    """1 month back -> 2 months ahead of today, as ISO date strings. Default
    scope for the Orders list so it doesn't load the entire booking history
    on every open."""
    return get_default_billing_window()


def get_booking_counts(date_start: str = None, date_end: str = None,
                        customer: str = None, event: str = None,
                        time_start: str = None, time_end: str = None) -> dict:
    """Return per-tab booking counts independent of how many rows are loaded into
    the UI, so tab title counts stay accurate under pagination. Accepts the same
    optional date/time/customer/event filters as get_bookings_page() so the
    counts reflect whatever's currently filtered, not the whole table.

    Returns {"pending": N, "confirmed": N, "all": N} where "confirmed" covers
    both CONFIRMED and COMPLETED (matching the Confirmed tab's status bucket).
    """
    counts = {"pending": 0, "confirmed": 0, "all": 0}
    try:
        where = "WHERE 1=1"
        params: list = []
        if date_start and date_end:
            where += " AND b.bk_event_date BETWEEN %s AND %s"
            params.extend([date_start, date_end])
        if time_start and time_end:
            where += " AND SUBSTR(CAST(b.bk_event_time AS TEXT), 1, 5) BETWEEN %s AND %s"
            params.extend([time_start, time_end])
        if customer:
            where += " AND b.bk_customer_name ILIKE %s"
            params.append(f"%{customer}%")
        if event:
            where += " AND b.bk_occasion ILIKE %s"
            params.append(f"%{event}%")
        rows = db.fetchall(
            f"SELECT b.bk_status AS status, COUNT(*) AS cnt FROM bookings b {where} GROUP BY b.bk_status",
            tuple(params),
        )
        for r in rows or []:
            status = (r.get("status") or "").upper()
            cnt = int(r.get("cnt") or 0)
            counts["all"] += cnt
            if status == "PENDING":
                counts["pending"] += cnt
            elif status in ("CONFIRMED", "COMPLETED"):
                counts["confirmed"] += cnt
    except Exception as exc:
        print(f"[repository] get_booking_counts error: {exc}")
    return counts


def get_all_bookings_for_export() -> list[dict]:
    """Fetch full booking details including contact, venue, occasion, time — for exports only."""
    rows = db.fetchall("""
        SELECT b.bk_id              AS id,
               b.bk_booking_ref    AS booking_ref,
               b.bk_customer_name  AS customer_name,
               COALESCE(NULLIF(b.bk_contact, ''), NULLIF(c.cus_contact, ''), '') AS contact,
               COALESCE(NULLIF(b.bk_email, ''), NULLIF(c.cus_email, ''), '')   AS email,
               b.bk_event_date     AS event_date,
               b.bk_event_time     AS event_time,
               b.bk_venue          AS venue,
               b.bk_occasion       AS occasion,
               b.bk_pax            AS pax,
               b.bk_total_amount   AS total_amount,
               b.bk_amount_paid    AS amount_paid,
               COALESCE(b.bk_down_payment, b.bk_amount_paid, 0.0) AS down_payment,
               b.bk_status         AS status,
               b.bk_color_theme    AS color_theme,
               COALESCE(NULLIF(b.bk_special_notes, ''), NULLIF(b.bk_notes, ''), '') AS notes,
               b.bk_menu_type      AS menu_type,
               b.bk_payment_mode   AS payment_mode,
               p.pkg_name          AS package_name
        FROM bookings b
        LEFT JOIN customers c ON c.cus_id = b.bk_customer_id
        LEFT JOIN packages p ON p.pkg_id = b.bk_package_id
        ORDER BY b.bk_event_date DESC
    """)
    if not rows:
        return []
    result = []
    for r in rows:
        try:
            event_date_raw = r["event_date"]
            date_str = event_date_raw.strftime("%b %d, %Y") if isinstance(event_date_raw, date) else str(event_date_raw or "")
            time_val = format_time_ampm(r.get("event_time"))
            total_amt = float(r["total_amount"] or 0.0)
            paid_amt = float(r["amount_paid"] or 0.0)
            down_amt = float(r.get("down_payment") or paid_amt)
            balance = max(0.0, total_amt - paid_amt)
            result.append({
                "id":           r["booking_ref"] or "",
                "booking_ref":  r["booking_ref"] or "",
                "ref_id":       r["booking_ref"] or "",
                "name":         r["customer_name"] or "",
                "customer_name": r["customer_name"] or "",
                "client_name":  r["customer_name"] or "",
                "contact":      r["contact"] or "",
                "phone":        r["contact"] or "",
                "email":        r["email"] or "",
                "date":         date_str,
                "event_date":   date_str,
                "time":         str(time_val),
                "event_time":   str(time_val),
                "venue":        r["venue"] or "",
                "occasion":     r["occasion"] or "",
                "pax":          r["pax"] or 0,
                "total":        total_amt,
                "total_amount": total_amt,
                "amount_paid":  paid_amt,
                "down_payment": down_amt,
                "balance":      balance,
                "status":       r["status"] or "",
                "color_theme":  r.get("color_theme") or "#2563EB",
                "color":        r.get("color_theme") or "#2563EB",
                "notes":        r["notes"] or "",
                "menu_type":    r.get("menu_type") or "package",
                "package_name": r.get("package_name") or "",
                "payment_mode": r["payment_mode"] or "",
            })
        except Exception as exc:
            print(f"[repository] get_all_bookings_for_export row error: {exc}")
    return result


def get_booking_detail(db_id: int) -> Optional[dict]:
    """Fetch complete details for a booking order for modal editing/viewing/printing."""
    row = db.fetchone("""
        SELECT b.bk_id AS db_id,
               b.bk_booking_ref AS id,
               b.bk_booking_ref AS booking_ref,
               b.bk_customer_id AS customer_id,
               b.bk_customer_name AS name,
               b.bk_customer_name AS customer_name,
               b.bk_address AS address,
               b.bk_event_date AS event_date,
               b.bk_event_time AS event_time,
               b.bk_occasion AS occasion,
               b.bk_venue AS venue,
               b.bk_pax AS pax,
               b.bk_total_amount AS total,
               b.bk_total_amount AS total_amount,
               b.bk_payment_mode AS payment_mode,
               b.bk_amount_paid AS amount_paid,
               COALESCE(b.bk_down_payment, b.bk_amount_paid, 0.0) AS down_payment,
               b.bk_menu_type AS menu_type,
               b.bk_package_id AS package_id,
               COALESCE(NULLIF(b.bk_special_notes, ''), NULLIF(b.bk_notes, ''), '') AS notes,
               b.bk_status AS status,
               b.bk_color_theme AS color_theme,
               COALESCE(NULLIF(b.bk_contact, ''), NULLIF(c.cus_contact, ''), '') AS contact,
               COALESCE(NULLIF(b.bk_email, ''), NULLIF(c.cus_email, ''), '') AS email,
               p.pkg_name AS package_name
        FROM bookings b
        LEFT JOIN customers c ON c.cus_id = b.bk_customer_id
        LEFT JOIN packages p ON p.pkg_id = b.bk_package_id
        WHERE b.bk_id = %s
    """, (db_id,))
    if not row:
        return None
    d = dict(row)
    if isinstance(d.get("event_date"), (datetime, date)):
        d["date"] = d["event_date"].strftime("%Y-%m-%d")
        d["event_date"] = d["event_date"].strftime("%b %d, %Y")
    else:
        d["date"] = str(d.get("event_date", ""))
    d["time"] = format_time_ampm(d.get("event_time"))
    d["event_time"] = format_time_ampm(d.get("event_time"))
    d["color_theme"] = d.get("color_theme") or "#2563EB"
    d["color"] = d.get("color_theme") or "#2563EB"

    # Fetch selected dishes from booking_menu_items. COALESCE against
    # menu_items by item_id as a defensive fallback for any pre-existing
    # rows left with a NULL name/category (e.g. tablet-created bookings
    # synced before bmi_item_name/bmi_category were populated server-side),
    # OR stuck with the old generic "Selected Dishes"/"Main Course"
    # placeholder categories that used to be written for every dish
    # regardless of what it actually was - prefer the real menu_items
    # category for those existing rows too, not just genuinely-empty ones.
    # bmi_item_id is NULL for a lot of real rows (dishes were historically
    # saved as plain strings, no id at all - see create_booking) - joining
    # ONLY by id silently misses every one of those, which is exactly why
    # every dish fell back to the same generic "Menu Dishes"/"Selected
    # Dishes" bucket regardless of what it actually was. Falling back to a
    # name match MUST be a scalar subquery (LIMIT 1), not a LEFT JOIN - if
    # more than one menu_items row shares the same dish name (e.g. the same
    # dish listed under two categories), a plain JOIN fans out into
    # duplicate rows, which is exactly what happened: every dish got
    # printed 2-4x, once per matching menu_items row.
    dish_rows = db.fetchall("""
        SELECT bmi.bmi_item_id AS item_id,
               COALESCE(
                   NULLIF(bmi.bmi_item_name, ''),
                   mi.mi_name,
                   (SELECT mi2.mi_name FROM menu_items mi2 WHERE LOWER(mi2.mi_name) = LOWER(bmi.bmi_item_name) ORDER BY mi2.mi_id LIMIT 1)
               ) AS name,
               COALESCE(
                   NULLIF(CASE WHEN bmi.bmi_category IN ('Selected Dishes', 'Menu Dishes') THEN '' ELSE bmi.bmi_category END, ''),
                   mi.mi_category,
                   (SELECT mi2.mi_category FROM menu_items mi2 WHERE LOWER(mi2.mi_name) = LOWER(bmi.bmi_item_name) ORDER BY mi2.mi_id LIMIT 1)
               ) AS category
        FROM booking_menu_items bmi
        LEFT JOIN menu_items mi ON mi.mi_id = bmi.bmi_item_id
        WHERE bmi.bmi_booking_id = %s
        ORDER BY bmi.bmi_id ASC
    """, (db_id,))
    if dish_rows:
        d["dishes"] = [dict(r) for r in dish_rows]
    elif d.get("package_id"):
        pkg_items = get_package_items(d["package_id"])
        d["dishes"] = [{"name": pi["item_name"], "category": pi["category"]} for pi in pkg_items]
    else:
        d["dishes"] = []

    # Fetch itemized additional add-on charges
    d["additional_charges"] = get_additional_charges(db_id)
    return d


def update_booking_color_theme(db_id_or_ref, color_theme: str) -> bool:
    """Update the assigned color theme hex code for a booking."""
    try:
        color_hex = str(color_theme or "#2563EB").strip()
        if isinstance(db_id_or_ref, int):
            db.execute("UPDATE bookings SET bk_color_theme = %s WHERE bk_id = %s", (color_hex, db_id_or_ref))
        else:
            db.execute("UPDATE bookings SET bk_color_theme = %s WHERE bk_booking_ref = %s", (color_hex, str(db_id_or_ref)))
        return True
    except Exception as exc:
        print(f"[repository] update_booking_color_theme failed: {exc}")
        return False


def _lookup_menu_item_category(item_id=None, item_name: str = None) -> Optional[str]:
    """Real category (Main Course, Dessert, Beverage, etc.) for a menu item,
    by id or by name. Used when saving a booking's selected dishes so
    booking_menu_items.bmi_category records the ACTUAL category instead of a
    generic placeholder like "Selected Dishes"/"Main Course" - the kitchen
    needs to know what each dish actually IS, not a made-up bucket name that
    lumped every dish (mains, desserts, drinks alike) under one label on the
    printed order slip."""
    try:
        if item_id:
            row = db.fetchone("SELECT mi_category FROM menu_items WHERE mi_id = %s", (item_id,))
            if row and row.get("mi_category"):
                return row["mi_category"]
        if item_name:
            row = db.fetchone("SELECT mi_category FROM menu_items WHERE LOWER(mi_name) = LOWER(%s) LIMIT 1", (item_name,))
            if row and row.get("mi_category"):
                return row["mi_category"]
    except Exception:
        pass
    return None


def create_booking(data: dict) -> Optional[dict]:
    try:
        raw_date    = data.get("date") or data.get("event_date")
        raw_time    = data.get("time") or data.get("event_time", "6:00 PM")
        raw_total   = data.get("total") if "total" in data else data.get("total_amount", 0.0)
        raw_down    = data.get("down_payment") or data.get("amount_paid", "0")

        event_date  = _parse_date(raw_date)
        event_time  = _parse_time(raw_time)
        amount_paid = _parse_amount(raw_down)
        total_amt   = _parse_amount(raw_total)

        menu_type = str(data.get("menu_type") or "package").strip().lower()
        if menu_type not in ("package", "custom"):
            menu_type = "package"

        package_id = data.get("package_id")
        if package_id:
            try:
                chk = db.fetchone("SELECT pkg_id FROM packages WHERE pkg_id = %s", (package_id,))
                if not chk:
                    package_id = None
            except Exception:
                package_id = None
        if not package_id and menu_type == "package":
            pkg_row = db.fetchone(
                "SELECT pkg_id AS id FROM packages WHERE pkg_name = %s",
                (data.get("menu_value"),),
            )
            if pkg_row:
                package_id = pkg_row["id"]

        mode_raw = str(data.get("payment_mode") or "Cash").strip()
        if mode_raw.upper() == "GCASH":
            pm = "GCash"
        elif mode_raw.upper() == "PAYMAYA":
            pm = "PayMaya"
        elif "BANK" in mode_raw.upper() or "TRANSFER" in mode_raw.upper():
            pm = "Bank Transfer"
        else:
            pm = "Cash"

        venue_val = (data.get("venue") or "").strip()
        if not venue_val:
            venue_val = (data.get("address") or "").strip()
        if not venue_val:
            venue_val = "Main Hall / Venue TBD"

        result = db.callproc_out(
            "sp_create_booking",
            in_params=(
                data["name"],
                data.get("contact", ""),
                data.get("email", ""),
                data.get("address", ""),
                data.get("occasion", ""),
                venue_val,
                event_date,
                event_time,
                data["pax"],
                data.get("notes", ""),
                menu_type,
                package_id,
                data.get("menu_value", "") if menu_type == "custom" else None,
                total_amt,
                pm,
                amount_paid,
            ),
            out_names=["p_booking_id", "p_booking_ref"],
        )
        if result and result.get("p_booking_id"):
            b_id = result["p_booking_id"]
            if data.get("color_theme"):
                try:
                    db.execute("UPDATE bookings SET bk_color_theme = %s WHERE bk_id = %s", (str(data["color_theme"]).strip(), b_id))
                except Exception:
                    pass

            # Save selected package dishes into booking_menu_items
            selected_dishes = data.get("selected_dishes") or []
            if selected_dishes:
                try:
                    db.execute("DELETE FROM booking_menu_items WHERE bmi_booking_id = %s", (b_id,))
                    for itm in selected_dishes:
                        if isinstance(itm, dict):
                            i_id = itm.get("id") or itm.get("menu_item_id")
                            i_name = itm.get("name") or itm.get("item") or itm.get("item_name") or ""
                            i_cat = itm.get("category") or _lookup_menu_item_category(i_id, i_name) or "Main Course"
                        else:
                            i_id = None
                            i_name = str(itm).strip()
                            i_cat = _lookup_menu_item_category(None, i_name) or "Selected Dishes"
                        if i_name:
                            db.execute("""
                                INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity)
                                VALUES (%s, %s, %s, %s, 0.0, 1)
                            """, (b_id, i_id, i_name, i_cat))
                except Exception as bmie:
                    print(f"[repository] create_booking save dishes note: {bmie}")

            write_audit_log(
                action="CREATE",
                table_name="bookings",
                record_id=b_id,
                new_value={
                    "customer": data.get("name"),
                    "amount": total_amt,
                    "down_payment": amount_paid,
                    "ref": result.get("p_booking_ref"),
                }
            )
            return {"booking_id": b_id, "booking_ref": result["p_booking_ref"]}
    except Exception as exc:
        print(f"[repository] create_booking failed: {exc}")
    return None


add_booking = create_booking


def update_booking(db_id: int, data: dict) -> None:
    try:
        raw_date    = data.get("date") or data.get("event_date")
        raw_time    = data.get("time") or data.get("event_time", "6:00 PM")
        raw_total   = data.get("total") if "total" in data else data.get("total_amount", 0.0)
        raw_down    = data.get("down_payment") or data.get("amount_paid", "0")

        event_date  = _parse_date(raw_date)
        event_time  = _parse_time(raw_time)
        amount_paid = _parse_amount(raw_down)
        total_amt   = _parse_amount(raw_total)

        package_id = data.get("package_id")
        if not package_id and data.get("menu_type") == "package":
            pkg_row = db.fetchone(
                "SELECT pkg_id AS id FROM packages WHERE pkg_name = %s",
                (data.get("menu_value"),),
            )
            if pkg_row:
                package_id = pkg_row["id"]

        mode_raw = str(data.get("payment_mode") or "Cash").strip()
        if mode_raw.upper() == "GCASH":
            pm = "GCash"
        elif mode_raw.upper() == "PAYMAYA":
            pm = "PayMaya"
        elif "BANK" in mode_raw.upper() or "TRANSFER" in mode_raw.upper():
            pm = "Bank Transfer"
        else:
            pm = "Cash"

        venue_val = (data.get("venue") or "").strip()
        if not venue_val:
            venue_val = (data.get("address") or "").strip()
        if not venue_val:
            venue_val = "Main Hall / Venue TBD"

        db.callproc_void(
            "sp_update_booking",
            in_params=(
                db_id,
                data["name"],
                data.get("contact", ""),
                data.get("email", ""),
                data.get("address", ""),
                data.get("occasion", ""),
                venue_val,
                event_date,
                event_time,
                data["pax"],
                data.get("notes", ""),
                data.get("menu_type", "package"),
                package_id,
                data.get("menu_value", "") if data.get("menu_type") == "custom" else None,
                data["total"],
                pm,
                amount_paid,
            ),
        )
        if data.get("color_theme"):
            try:
                db.execute("UPDATE bookings SET bk_color_theme = %s WHERE bk_id = %s", (str(data["color_theme"]).strip(), db_id))
            except Exception:
                pass

        if "selected_dishes" in data:
            selected_dishes = data.get("selected_dishes") or []
            try:
                db.execute("DELETE FROM booking_menu_items WHERE bmi_booking_id = %s", (db_id,))
                for itm in selected_dishes:
                    if isinstance(itm, dict):
                        i_id = itm.get("id") or itm.get("menu_item_id")
                        i_name = itm.get("name") or itm.get("item") or itm.get("item_name") or ""
                        i_cat = itm.get("category") or _lookup_menu_item_category(i_id, i_name) or "Main Course"
                    else:
                        i_id = None
                        i_name = str(itm).strip()
                        i_cat = _lookup_menu_item_category(None, i_name) or "Selected Dishes"
                    if i_name:
                        db.execute("""
                            INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity)
                            VALUES (%s, %s, %s, %s, 0.0, 1)
                        """, (db_id, i_id, i_name, i_cat))
            except Exception as bmie:
                print(f"[repository] update_booking save dishes note: {bmie}")

        write_audit_log(
            action="UPDATE",
            table_name="bookings",
            record_id=db_id,
            new_value={
                "customer": data.get("name"),
                "amount": total_amt,
            }
        )
    except Exception as exc:
        print(f"[repository] update_booking failed: {exc}")


def update_booking_status(db_id: int, new_status: str, cancellation_reason: str = None, color_theme: str = None) -> None:
    db.callproc_void("sp_update_booking_status", in_params=(db_id, new_status, cancellation_reason))
    if color_theme:
        try:
            db.execute("UPDATE bookings SET bk_color_theme = %s WHERE bk_id = %s", (str(color_theme).strip(), db_id))
        except Exception:
            pass

    c_name = ""
    b_tot = None
    try:
        row = db.fetchone("SELECT bk_customer_name, bk_total_amount FROM bookings WHERE bk_id = %s", (db_id,))
        if row:
            c_name = row.get("bk_customer_name", "")
            b_tot = row.get("bk_total_amount")
    except Exception:
        pass

    act = "STATUS_CHANGE"
    st_upper = str(new_status or "").upper()
    if "CANCEL" in st_upper:
        act = "CANCEL"
    elif "CONFIRM" in st_upper:
        act = "APPROVE"

    write_audit_log(
        action=act,
        table_name="bookings",
        record_id=db_id,
        new_value={
            "customer": c_name or f"Order #{db_id}",
            "status": new_status,
            "amount": b_tot,
            "reason": cancellation_reason,
        }
    )


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


def delete_booking(db_id: int) -> bool:
    c_name = ""
    amt = None
    try:
        row = db.fetchone("SELECT bk_customer_name, bk_total_amount FROM bookings WHERE bk_id = %s", (db_id,))
        if row:
            c_name = row.get("bk_customer_name", "")
            amt = row.get("bk_total_amount")
    except Exception:
        pass
    ok = db.callproc_void("sp_delete_booking", in_params=(db_id,))
    if not ok:
        return False
    write_audit_log(
        action="DELETE",
        table_name="bookings",
        record_id=db_id,
        old_value={"customer": c_name or f"Order #{db_id}", "amount": amt}
    )
    return True


def complete_booking(db_id: int) -> bool:
    try:
        db.callproc_void("sp_complete_booking", in_params=(db_id,))
        c_name = ""
        try:
            row = db.fetchone("SELECT bk_customer_name FROM bookings WHERE bk_id = %s", (db_id,))
            if row:
                c_name = row.get("bk_customer_name", "")
        except Exception:
            pass
        write_audit_log(
            action="STATUS_CHANGE",
            table_name="bookings",
            record_id=db_id,
            new_value={"customer": c_name or f"Order #{db_id}", "status": "COMPLETED"}
        )
        return True
    except Exception as exc:
        print(f"[repository] complete_booking failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# INVOICES
# ---------------------------------------------------------------------------

_INVOICE_ROW_SQL = """
        SELECT i.inv_id              AS id,
               i.inv_invoice_ref    AS invoice_ref,
               i.inv_booking_id     AS booking_id,
               i.inv_customer_name  AS customer_name,
               i.inv_event_date     AS event_date,
               i.inv_total_amount   AS total_amount,
               i.inv_amount_paid    AS amount_paid,
               CASE WHEN i.inv_balance IS NOT NULL AND (i.inv_balance > 0 OR (i.inv_total_amount - i.inv_amount_paid) <= 0)
                    THEN i.inv_balance
                    WHEN (i.inv_total_amount - i.inv_amount_paid) > 0
                    THEN ROUND(i.inv_total_amount - i.inv_amount_paid, 2)
                    ELSE 0.0 END AS balance_due,
               i.inv_status         AS status,
               COALESCE(c.cus_email, '') AS customer_email
        FROM invoices i
        LEFT JOIN customers c ON c.cus_name = i.inv_customer_name
        WHERE CAST(i.inv_status AS TEXT) NOT IN ('CANCELLED', 'Cancelled')
"""


def _rows_to_invoice_dicts(rows) -> list[dict]:
    if not rows:
        return []
    return [
        {
            "db_id":          r["id"],
            "invoice":        r["invoice_ref"],
            "booking_id":     r["booking_id"],
            "booking_ref":    r["invoice_ref"],  # re-alias for exporter compatibility
            "customer":       r["customer_name"],
            "customer_email": r["customer_email"],
            "event_date":     r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
            "amount":         float(r["total_amount"]),
            "paid":           float(r["amount_paid"]),
            "balance":        float(r["balance_due"]),
            "status":         r["status"],
        }
        for r in rows
    ]


def get_invoices_page(offset: int = 0, limit: int = 50, date_start: str = None, date_end: str = None,
                       customer: str = None, paid_status: str = None) -> list[dict]:
    """Fetch one page of invoices. Used for incremental/lazy loading.

    date_start/date_end: optional ISO date bounds on the invoice's event_date
      (both must be given together to apply; None/None = unbounded).
    customer: optional case-insensitive substring match on customer name.
    paid_status: "unpaid" (Unpaid/Partial), "paid" (Paid only), or None/"all"
      for no paid-status filter.

    Sort: when paid_status is not explicitly set (the default/unfiltered view),
    unpaid/partial invoices sort BEFORE paid ones (so the most actionable
    invoices land on page 0), then by event_date. Any explicit paid_status
    filter already narrows to one bucket, so it just sorts by event_date.
    """
    where = ""
    params: list = []
    if date_start and date_end:
        where += " AND i.inv_event_date BETWEEN %s AND %s"
        params.extend([date_start, date_end])
    if customer:
        where += " AND i.inv_customer_name ILIKE %s"
        params.append(f"%{customer}%")
    if paid_status == "unpaid":
        where += " AND CAST(i.inv_status AS TEXT) IN ('Unpaid', 'Partial')"
    elif paid_status == "paid":
        where += " AND CAST(i.inv_status AS TEXT) = 'Paid'"

    if paid_status in (None, "", "all"):
        order = "ORDER BY (CASE WHEN CAST(i.inv_status AS TEXT) IN ('Unpaid', 'Partial') THEN 0 ELSE 1 END), i.inv_event_date ASC"
    else:
        order = "ORDER BY i.inv_event_date ASC"

    params.extend([limit, offset])
    rows = db.fetchall(
        _INVOICE_ROW_SQL + f"{where} {order} LIMIT %s OFFSET %s",
        tuple(params),
    )
    return _rows_to_invoice_dicts(rows)


def search_invoices(query: str, limit: int = 100) -> list[dict]:
    """Search invoices by customer name/invoice ref, ignoring the paid-status
    and date-window filters entirely. Used by Billing's search box - without
    this, typing a customer's name only ever searched WITHIN whatever subset
    the current filter had already loaded (e.g. "Unpaid Invoices" default),
    so an already-paid invoice for that customer would silently not be found
    even though it exists, looking like the record had vanished."""
    q = (query or "").strip()
    if not q:
        return []
    rows = db.fetchall(
        _INVOICE_ROW_SQL + """
        AND (i.inv_customer_name ILIKE %s OR i.inv_invoice_ref ILIKE %s)
        ORDER BY (CASE WHEN CAST(i.inv_status AS TEXT) IN ('Unpaid', 'Partial') THEN 0 ELSE 1 END), i.inv_event_date DESC
        LIMIT %s
        """,
        (f"%{q}%", f"%{q}%", limit),
    )
    return _rows_to_invoice_dicts(rows)


def get_default_billing_window() -> tuple[str, str]:
    """1 month back -> 2 months ahead of today, as ISO date strings. This is
    the default scope for the Billing list so it doesn't load the entire
    invoice history on every open."""
    from datetime import date as _date
    today = _date.today()
    start = (today.replace(day=1) - timedelta(days=32)).replace(day=1)
    # +2 months ahead, end of that month
    m = today.month + 2
    y = today.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    if m == 12:
        end = _date(y, 12, 31)
    else:
        end = _date(y, m + 1, 1) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def get_invoices_summary(date_start: str = None, date_end: str = None,
                          customer: str = None, paid_status: str = None) -> dict:
    """Aggregate totals across non-cancelled invoices, independent of how many
    pages have been loaded into the UI - keeps summary cards accurate under pagination.

    date_start/date_end: optional ISO date bounds on the invoice's event_date
    (both must be given together to apply; None/None = unbounded).
    customer/paid_status: same semantics as get_invoices_page() - pass the
    Billing page's CURRENT active filter state so the header KPI cards
    reflect whatever filter is applied instead of always showing an
    unrelated all-time total, which is what the client found confusing when
    changing filters never visibly changed the header numbers. Call with no
    args at all for a true all-time/unfiltered aggregate (e.g. Reports)."""
    where = "WHERE CAST(i.inv_status AS TEXT) NOT IN ('CANCELLED', 'Cancelled')"
    params: list = []
    if date_start and date_end:
        where += " AND i.inv_event_date BETWEEN %s AND %s"
        params.extend([date_start, date_end])
    if customer:
        where += " AND i.inv_customer_name ILIKE %s"
        params.append(f"%{customer}%")
    if paid_status == "unpaid":
        where += " AND CAST(i.inv_status AS TEXT) IN ('Unpaid', 'Partial')"
    elif paid_status == "paid":
        where += " AND CAST(i.inv_status AS TEXT) = 'Paid'"
    row = db.fetchone(f"""
        SELECT
            COALESCE(SUM(i.inv_amount_paid), 0.0) AS total_received,
            COALESCE(SUM(
                CASE WHEN CAST(i.inv_status AS TEXT) != 'Paid'
                     THEN MAX(
                        CASE WHEN i.inv_balance IS NOT NULL AND (i.inv_balance > 0 OR (i.inv_total_amount - i.inv_amount_paid) <= 0)
                             THEN i.inv_balance
                             ELSE ROUND(i.inv_total_amount - i.inv_amount_paid, 2) END,
                        0.0)
                     ELSE 0.0 END
            ), 0.0) AS total_pending,
            COUNT(*) AS events_count
        FROM invoices i
        {where}
    """, tuple(params))
    if not row:
        return {"total_received": 0.0, "total_pending": 0.0, "events_count": 0}
    return {
        "total_received": float(row["total_received"] or 0.0),
        "total_pending":  float(row["total_pending"] or 0.0),
        "events_count":   int(row["events_count"] or 0),
    }


def get_all_invoices() -> list[dict]:
    """Unpaginated fetch - kept for CSV export, which genuinely needs every row."""
    rows = db.fetchall(_INVOICE_ROW_SQL + " ORDER BY i.inv_created_at DESC")
    return _rows_to_invoice_dicts(rows)


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

    # Ensure invoice exists before recording payment
    try:
        inv_check = db.fetchone("SELECT inv_id FROM invoices WHERE inv_booking_id = %s", (booking_id,))
        if not inv_check:
            auto_create_invoice(booking_id)
    except Exception:
        pass
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

    c_name = ""
    try:
        b_row = db.fetchone("SELECT bk_customer_name FROM bookings WHERE bk_id = %s", (booking_id,))
        if b_row:
            c_name = b_row.get("bk_customer_name", "")
    except Exception:
        pass

    write_audit_log(
        action="PAYMENT",
        table_name="invoices",
        record_id=result.get("p_invoice_id") or booking_id,
        new_value={
            "customer": c_name or result.get("p_invoice_ref"),
            "amount": payment_amount,
            "method": method,
            "note": note,
            "invoice_ref": result.get("p_invoice_ref"),
        }
    )

    return {
        "invoice_id":         result["p_invoice_id"],
        "invoice_ref":        result["p_invoice_ref"],
        "new_invoice_status": result["p_new_invoice_status"],
        "new_booking_status": result["p_new_booking_status"],
        "new_paid":           float(result["p_new_paid"]),
        "remaining":          float(result["p_remaining"]),
    }


def update_invoice_payment(invoice_id: int, new_paid: float, new_balance: float = None) -> bool:
    """Correct manual encoding mistakes on an invoice's paid amount and balance.
    
    Updates:
    - invoices (inv_amount_paid, inv_balance, inv_status)
    - linked bookings (bk_amount_paid, bk_down_payment, bk_status)
    - payment_records (updates latest record or creates correction record)
    """
    try:
        inv = db.fetchone("SELECT * FROM invoices WHERE inv_id = %s", (invoice_id,))
        if not inv:
            return False
        
        tot = float(inv.get("inv_total_amount") or 0.0)
        paid = max(0.0, float(new_paid))
        if new_balance is not None:
            bal = max(0.0, float(new_balance))
        else:
            bal = max(0.0, tot - paid)
        
        # Determine status via the single source-of-truth helper
        new_inv_status = db.compute_invoice_status(tot, paid)
        new_bk_status = "CONFIRMED" if new_inv_status in ("Paid", "Partial") else "PENDING"
        
        # Update invoices
        db.execute("""
            UPDATE invoices
            SET inv_amount_paid = %s,
                inv_balance = %s,
                inv_status = %s
            WHERE inv_id = %s
        """, (paid, bal, new_inv_status, invoice_id))
        
        # Update linked booking if present
        bk_id = inv.get("inv_booking_id")
        if bk_id:
            db.execute("""
                UPDATE bookings
                SET bk_amount_paid = %s,
                    bk_down_payment = %s
                WHERE bk_id = %s
            """, (paid, paid, bk_id))
        
        # Update or insert payment record for audit trail
        pr = db.fetchone("SELECT pr_id FROM payment_records WHERE pr_invoice_id = %s ORDER BY pr_id DESC LIMIT 1", (invoice_id,))
        if pr:
            db.execute("""
                UPDATE payment_records
                SET pr_amount = %s, pr_note = %s
                WHERE pr_id = %s
            """, (paid, f"Adjusted via Billing Edit ({datetime.now().strftime('%Y-%m-%d %H:%M')})", pr["pr_id"]))
        elif paid > 0:
            db.execute("""
                INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_note)
                VALUES (%s, %s, %s, %s, %s)
            """, (invoice_id, paid, date.today(), "Cash", "Initial payment recorded via Billing Edit"))
        
        from utils.signals import app_events
        ev = app_events()
        ev.data_changed.emit()
        ev.invoice_saved.emit()
        ev.booking_saved.emit()
        return True
    except Exception as exc:
        print(f"[repository] update_invoice_payment failed: {exc}")
        return False


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
        write_audit_log(
            action="UPDATE",
            table_name="invoices",
            record_id=db_id,
            new_value={"customer": data.get("customer"), "amount": data.get("amount"), "status": data.get("status")}
        )
    except Exception as exc:
        print(f"[repository] update_invoice failed: {exc}")


def delete_invoice(db_id: int) -> None:
    c_name = ""
    try:
        inv_row = db.fetchone("SELECT inv_customer_name FROM invoices WHERE inv_id = %s", (db_id,))
        if inv_row:
            c_name = inv_row.get("inv_customer_name", "")
    except Exception:
        pass
    db.callproc_void("sp_delete_invoice", in_params=(db_id,))
    write_audit_log(
        action="DELETE",
        table_name="invoices",
        record_id=db_id,
        old_value={"customer": c_name or f"Invoice #{db_id}"}
    )


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
            c_name = ""
            try:
                inv_row = db.fetchone("SELECT inv_customer_name FROM invoices WHERE inv_id = %s", (invoice_id,))
                if inv_row:
                    c_name = inv_row.get("inv_customer_name", "")
            except Exception:
                pass
            write_audit_log(
                action="PAYMENT",
                table_name="invoices",
                record_id=invoice_id,
                new_value={"customer": c_name, "amount": float(amount), "method": method, "note": note}
            )
            return {
                "record_id":  result["p_record_id"],
                "new_status": result["p_new_status"],
                "new_paid":   float(result["p_new_paid"]),
            }
    except Exception as exc:
        print(f"[repository] add_payment_record failed: {exc}")
        raise
    return None


def get_payment_ledger(year: int = None, month: int = None) -> list[dict]:
    """Full cross-customer payment history for the Ledger view: Date, Customer,
    Transaction type (Down Payment vs Full/Remaining Payment), Amount, Status.

    Each payment_records row keeps its own pr_payment_date - a later payment
    never overwrites an earlier one's date, so down payment and subsequent
    payments both show their real, distinct dates here."""
    # NOTE: pr_is_downpayment only exists in the Postgres schema - the SQLite
    # schema never had that column, so selecting it directly raised "no such
    # column: pr.pr_is_downpayment" on every call, silently emptying the
    # Ledger tab regardless of how much payment data actually existed.
    # Derive the same distinction instead: the earliest payment_records row
    # per invoice IS the down payment, any later one is a remaining/full
    # payment - works identically on both engines, no schema change needed.
    sql = """
        SELECT pr.pr_id            AS id,
               pr.pr_payment_date  AS payment_date,
               i.inv_customer_name AS customer,
               CASE WHEN pr.pr_id = (
                   SELECT MIN(pr2.pr_id) FROM payment_records pr2 WHERE pr2.pr_invoice_id = pr.pr_invoice_id
               ) THEN 1 ELSE 0 END AS is_downpayment,
               pr.pr_amount        AS amount,
               i.inv_status        AS status,
               i.inv_booking_id    AS booking_id
        FROM payment_records pr
        JOIN invoices i ON i.inv_id = pr.pr_invoice_id
    """
    params: tuple = ()
    if year and month:
        sql += " WHERE strftime('%Y', pr.pr_payment_date) = %s AND strftime('%m', pr.pr_payment_date) = %s"
        params = (str(year), f"{month:02d}")
    sql += " ORDER BY pr.pr_payment_date DESC, pr.pr_created_at DESC"
    rows = db.fetchall(sql, params)
    if not rows:
        return []
    return [
        {
            "id":          r["id"],
            "date":        r["payment_date"].strftime("%b %d, %Y") if hasattr(r["payment_date"], "strftime") else str(r["payment_date"]),
            "customer":    r["customer"],
            "transaction": "Down Payment" if r["is_downpayment"] else "Full/Remaining Payment",
            "amount":      float(r["amount"]),
            "status":      r["status"],
            "booking_id":  r["booking_id"],
        }
        for r in rows
    ]


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
# ADDITIONAL CHARGES / ADDITIONAL ITEMS
# ---------------------------------------------------------------------------

def get_additional_charges(booking_id: int) -> list[dict]:
    rows = db.fetchall(
        """
        SELECT ac_id AS id, ac_description AS description, ac_amount AS amount,
               ac_date_added AS date_added, ac_added_by AS added_by
        FROM booking_additional_charges
        WHERE ac_booking_id = %s
        ORDER BY ac_created_at DESC
        """,
        (booking_id,),
    )
    if not rows:
        return []
    return [
        {
            "id":          r["id"],
            "description": r["description"],
            "amount":      float(r["amount"]),
            "date_added":  r["date_added"].strftime("%b %d, %Y") if hasattr(r["date_added"], "strftime") else str(r["date_added"]),
            "added_by":    r["added_by"] or "",
        }
        for r in rows
    ]


def _recalc_booking_totals(booking_id: int) -> None:
    """Recompute bk_total_amount / invoice totals as base + additional charges,
    then re-derive Paid/Partial/Unpaid from the single source-of-truth helper."""
    row = db.fetchone("SELECT bk_base_total, bk_total_amount FROM bookings WHERE bk_id = %s", (booking_id,))
    if not row:
        return
    base = row.get("bk_base_total")
    base = float(base) if base is not None else float(row.get("bk_total_amount") or 0.0)
    charges_row = db.fetchone("SELECT COALESCE(SUM(ac_amount), 0.0) AS s FROM booking_additional_charges WHERE ac_booking_id = %s", (booking_id,))
    charges_sum = float(charges_row["s"]) if charges_row else 0.0
    new_total = base + charges_sum

    db.execute("UPDATE bookings SET bk_total_amount = %s WHERE bk_id = %s", (new_total, booking_id))

    # Read the paid amount from invoices.inv_amount_paid - the authoritative
    # column actually shown/summed on the Billing page - instead of
    # bookings.bk_amount_paid, which some payment paths can leave stale.
    # Using the stale bookings copy here silently corrupted inv_balance/inv_status
    # whenever an additional charge was added after such a payment.
    inv_row = db.fetchone("SELECT inv_id, inv_amount_paid FROM invoices WHERE inv_booking_id = %s", (booking_id,))
    if inv_row:
        paid = float(inv_row.get("inv_amount_paid") or 0.0)
        new_status = db.compute_invoice_status(new_total, paid)
        new_balance = max(0.0, new_total - paid)
        db.execute(
            "UPDATE invoices SET inv_total_amount = %s, inv_balance = %s, inv_status = %s WHERE inv_id = %s",
            (new_total, new_balance, new_status, inv_row["inv_id"]),
        )
        db.execute("UPDATE bookings SET bk_amount_paid = %s WHERE bk_id = %s", (paid, booking_id))


def add_additional_charge(booking_id: int, description: str, amount: float, added_by: str = "") -> list[dict]:
    from datetime import date as _d
    db.execute(
        """
        INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (booking_id, description.strip(), float(amount), _d.today(), added_by or ""),
    )
    _recalc_booking_totals(booking_id)
    c_name = ""
    try:
        b_row = db.fetchone("SELECT bk_customer_name FROM bookings WHERE bk_id = %s", (booking_id,))
        if b_row:
            c_name = b_row.get("bk_customer_name", "")
    except Exception:
        pass
    write_audit_log(
        actor=added_by,
        action="ADD_CHARGE",
        table_name="bookings",
        record_id=booking_id,
        new_value={"customer": c_name, "description": description.strip(), "amount": float(amount)}
    )
    return get_additional_charges(booking_id)


def delete_additional_charge(charge_id: int) -> bool:
    row = db.fetchone("SELECT ac_booking_id, ac_description, ac_amount FROM booking_additional_charges WHERE ac_id = %s", (charge_id,))
    if not row:
        return False
    booking_id = row["ac_booking_id"]
    desc = row.get("ac_description", "")
    amt = row.get("ac_amount", 0.0)
    db.execute("DELETE FROM booking_additional_charges WHERE ac_id = %s", (charge_id,))
    _recalc_booking_totals(booking_id)
    c_name = ""
    try:
        b_row = db.fetchone("SELECT bk_customer_name FROM bookings WHERE bk_id = %s", (booking_id,))
        if b_row:
            c_name = b_row.get("bk_customer_name", "")
    except Exception:
        pass
    write_audit_log(
        action="DELETE_CHARGE",
        table_name="bookings",
        record_id=booking_id,
        old_value={"customer": c_name, "description": desc, "amount": amt}
    )
    return True


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


def get_recent_notifications(limit: int = 20) -> list[dict]:
    """Read + unread, newest first — for a full notification history view."""
    rows = db.fetchall("""
        SELECT notif_id         AS id,
               notif_type       AS type,
               notif_title      AS title,
               notif_message    AS message,
               notif_color      AS color,
               notif_is_read    AS is_read,
               notif_created_at AS created_at
        FROM notifications
        ORDER BY notif_created_at DESC
        LIMIT %s
    """, (limit,))
    return [dict(r) for r in rows] if rows else []


# ---------------------------------------------------------------------------
# DASHBOARD KPIs
# ---------------------------------------------------------------------------

def get_downpayment_received() -> float:
    """Total amount of downpayments/payments received for upcoming/active events (not yet completed or cancelled)."""
    try:
        row = db.fetchone("""
            SELECT COALESCE(SUM(
                CASE 
                    WHEN b.bk_amount_paid > 0 THEN b.bk_amount_paid
                    WHEN b.bk_down_payment > 0 THEN b.bk_down_payment
                    WHEN i.inv_amount_paid > 0 THEN i.inv_amount_paid
                    ELSE 0.0
                END
            ), 0.0) AS total_downpayment
            FROM bookings b
            LEFT JOIN invoices i ON b.bk_id = i.inv_booking_id
            WHERE b.bk_status NOT IN ('COMPLETED', 'CANCELLED')
        """)
        return float(row["total_downpayment"] if row and row.get("total_downpayment") is not None else 0.0)
    except Exception as exc:
        print(f"[repository] get_downpayment_received failed: {exc}")
        return 0.0


def get_dashboard_kpis() -> dict:
    row = db.fetchone("SELECT * FROM v_dashboard_kpis")
    dp_rec = get_downpayment_received()
    if not row:
        return {
            "todays_events": 0, "pending_bookings": 0,
            "weekly_revenue": 0, "unpaid_invoices": 0, "todays_pax": 0,
            "downpayment_received": dp_rec,
        }
    return {
        "todays_events":         int(row["todays_events"]),
        "pending_bookings":      int(row["pending_bookings"]),
        "weekly_revenue":        float(row["weekly_revenue"]),
        "unpaid_invoices":       float(row["unpaid_invoices"]),
        "todays_pax":            int(row["todays_pax"]),
        "downpayment_received":  dp_rec,
    }


def get_dashboard_kpis_filtered(target_date: str = None) -> dict:
    """Return dashboard metrics for a specific date (e.g. today or custom date), or default view."""
    if not target_date:
        return get_dashboard_kpis()
    
    d_str = _parse_date(target_date)
    dp_rec = get_downpayment_received()
    
    # 1. Events on this date
    e_row = db.fetchone("""
        SELECT COUNT(*) AS todays_events, COALESCE(SUM(bk_pax), 0) AS todays_pax,
               COALESCE(SUM(bk_total_amount), 0.0) AS daily_sales
        FROM bookings
        WHERE bk_event_date = %s AND bk_status != 'CANCELLED'
    """, (d_str,))
    todays_events = int(e_row["todays_events"] if e_row and e_row.get("todays_events") is not None else 0)
    todays_pax = int(e_row["todays_pax"] if e_row and e_row.get("todays_pax") is not None else 0)
    daily_sales = float(e_row["daily_sales"] if e_row and e_row.get("daily_sales") is not None else 0.0)
    
    # 2. Pending bookings for this date
    p_row = db.fetchone("""
        SELECT COUNT(*) AS pending_bookings
        FROM bookings
        WHERE bk_status = 'PENDING' AND bk_event_date = %s
    """, (d_str,))
    pending = int(p_row["pending_bookings"] if p_row and p_row.get("pending_bookings") is not None else 0)
    
    # 3. Payments collected on this specific date
    pay_row = db.fetchone("""
        SELECT COALESCE(SUM(pr_amount), 0.0) AS total_paid
        FROM payment_records
        WHERE pr_payment_date = %s
    """, (d_str,))
    paid_amt = float(pay_row["total_paid"] if pay_row and pay_row.get("total_paid") is not None else 0.0)

    # 4. Expenses on this date
    exp_row = db.fetchone("""
        SELECT COALESCE(SUM(exp_amount), 0.0) AS total_exp
        FROM expenses
        WHERE (exp_expense_date = %s OR exp_date = %s)
    """, (d_str, d_str))
    exp_amt = float(exp_row["total_exp"] if exp_row and exp_row.get("total_exp") is not None else 0.0)

    # 5. Unpaid balance for events on this date
    inv_row = db.fetchone("""
        SELECT COALESCE(SUM(
            CASE 
                WHEN inv_balance IS NOT NULL AND inv_balance > 0 THEN inv_balance
                WHEN (inv_total_amount - inv_amount_paid) > 0 THEN ROUND(inv_total_amount - inv_amount_paid, 2)
                ELSE 0.0 
            END
        ), 0.0) AS unpaid
        FROM invoices
        WHERE inv_event_date = %s AND CAST(inv_status AS TEXT) != 'Paid' AND CAST(inv_status AS TEXT) NOT IN ('CANCELLED', 'Cancelled')
    """, (d_str,))
    unpaid = float(inv_row["unpaid"] if inv_row and inv_row.get("unpaid") is not None else 0.0)

    return {
        "todays_events":        todays_events,
        "pending_bookings":     pending,
        "weekly_revenue":       paid_amt if paid_amt > 0 else daily_sales,
        "daily_sales":          daily_sales,
        "daily_payments":       paid_amt,
        "daily_expenses":       exp_amt,
        "unpaid_invoices":      unpaid,
        "todays_pax":           todays_pax,
        "downpayment_received": dp_rec,
        "net_income":           (paid_amt if paid_amt > 0 else daily_sales) - exp_amt,
    }


def get_upcoming_events(limit: int = 10) -> list[dict]:
    rows = db.fetchall("SELECT * FROM v_upcoming_events LIMIT %s", (limit,))
    if not rows:
        return []
    return [
        {
            "id":            r.get("bk_id") if r.get("bk_id") is not None else r.get("id"),
            "booking_ref":   r.get("bk_booking_ref") or r.get("booking_ref", ""),
            "customer_name": r.get("bk_customer_name") or r.get("customer_name", ""),
            "occasion":      r.get("bk_occasion") or r.get("occasion", ""),
            "venue":         r.get("bk_venue") or r.get("venue", ""),
            "event_date":    r.get("bk_event_date") if r.get("bk_event_date") is not None else r.get("event_date"),
            "event_time":    r.get("bk_event_time") if r.get("bk_event_time") is not None else r.get("event_time"),
            "pax":           r.get("bk_pax") if r.get("bk_pax") is not None else r.get("pax", 0),
            "status":        r.get("bk_status") or r.get("status", "PENDING"),
        }
        for r in rows
    ]


def get_report_kpis(period_filter: str = "") -> dict:
    if period_filter:
        bkg_filter = period_filter
        exp_filter = (
            period_filter
            .replace("bk_event_date", "exp_date")
            .replace("bk_created_at", "exp_created_at")
            .replace("DATE(bk_event_date)", "DATE(exp_date)")
        )
        row = db.fetchone(
            f"""
            SELECT
                COUNT(*)                           AS total_bookings,
                COALESCE(SUM(bk_pax), 0)            AS total_pax,
                COALESCE(SUM(bk_total_amount), 0)    AS total_revenue,
                0                                  AS unpaid_amount,
                (SELECT COUNT(*) FROM bookings WHERE DATE(bk_created_at) = DATE('now') AND bk_status IN ('CONFIRMED','COMPLETED')) AS today_bookings,
                (SELECT COUNT(*) FROM bookings WHERE DATE(bk_created_at) >= DATE('now', '-7 days') AND bk_status IN ('CONFIRMED','COMPLETED')) AS week_bookings
            FROM bookings
            WHERE bk_status IN ('CONFIRMED', 'COMPLETED') {bkg_filter}
            """
        )
        exp_row = db.fetchone(
            f"""
            SELECT COALESCE(SUM(exp_amount), 0) AS total_expenses
            FROM expenses
            WHERE 1=1 {exp_filter}
            """
        )
    else:
        row = db.fetchone("SELECT * FROM v_report_kpis")
        exp_row = db.fetchone("SELECT COALESCE(SUM(exp_amount), 0) AS total_expenses FROM expenses")

    total_bookings = int(row["total_bookings"]) if row and row.get("total_bookings") is not None else 0
    total_pax      = int(row["total_pax"]) if row and row.get("total_pax") is not None else 0
    total_revenue  = float(row["total_revenue"]) if row and row.get("total_revenue") is not None else 0.0
    unpaid_amount  = float(row["unpaid_amount"]) if row and row.get("unpaid_amount") is not None else 0.0
    today_bookings = int(row["today_bookings"]) if row and row.get("today_bookings") is not None else 0
    week_bookings  = int(row["week_bookings"]) if row and row.get("week_bookings") is not None else 0
    total_expenses = float(exp_row["total_expenses"]) if exp_row and exp_row.get("total_expenses") is not None else 0.0
    net_profit     = total_revenue - total_expenses

    return {
        "total_bookings": total_bookings,
        "total_pax":      total_pax,
        "total_revenue":  total_revenue,
        "total_expenses": total_expenses,
        "net_profit":     net_profit,
        "unpaid_amount":  unpaid_amount,
        "today_bookings": today_bookings,
        "week_bookings":  week_bookings,
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


def get_top_occasions(limit: int = 10) -> list[dict]:
    rows = db.fetchall("""
        SELECT bk_occasion AS occasion, COUNT(*) AS total
        FROM bookings
        WHERE bk_occasion IS NOT NULL AND TRIM(bk_occasion) != ''
          AND bk_status IN ('CONFIRMED', 'COMPLETED')
        GROUP BY bk_occasion
        ORDER BY total DESC
        LIMIT %s
    """, (limit,))
    if not rows:
        return []
    return [{"occasion": r["occasion"], "count": int(r["total"])} for r in rows]


def get_recent_activity(limit: int = 5) -> list[dict]:
    rows = db.fetchall(
        "SELECT title, description, color, created_at FROM v_recent_activity LIMIT %s",
        (limit,),
    )
    if not rows:
        return []
    now = datetime.now()
    result = []
    for r in rows:
        ts = r.get("created_at")
        dt_val = None
        if isinstance(ts, datetime):
            dt_val = ts.replace(tzinfo=None) if ts.tzinfo else ts
        elif isinstance(ts, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
                try:
                    dt_val = datetime.strptime(ts.split(".")[0], "%Y-%m-%d %H:%M:%S")
                    break
                except ValueError:
                    pass
        if dt_val:
            secs = max(0, int((now - dt_val).total_seconds()))
            if secs < 60:        time_str = "just now"
            elif secs < 3600:    time_str = f"{secs // 60} min ago"
            elif secs < 86400:   time_str = f"{secs // 3600} hr ago"
            else:                time_str = f"{secs // 86400}d ago"
        else:
            time_str = "recently"
        result.append({
            "title": r.get("title", "Activity"),
            "description": r.get("description", ""),
            "color": r.get("color", "#3B82F6"),
            "time": time_str,
        })
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
    db.execute("""
        UPDATE business_info
        SET bi_min_downpayment_pct = %s, bi_allow_zero_downpayment = %s, bi_updated_at = NOW()
        WHERE bi_id = (SELECT MIN(bi_id) FROM business_info);
    """, (min_pct, allow_zero))
    write_audit_log(
        action="UPDATE",
        table_name="business_info",
        record_id=0,
        new_value={"name": "Booking Policy", "details": f"Updated booking policy (min down payment: {min_pct}%, allow zero: {allow_zero})"}
    )


def save_capacity_policy(max_pax: int) -> None:
    db.execute("""
        UPDATE business_info
        SET bi_max_daily_pax = %s, bi_updated_at = NOW()
        WHERE bi_id = (SELECT MIN(bi_id) FROM business_info);
    """, (max_pax,))
    write_audit_log(
        action="UPDATE",
        table_name="business_info",
        record_id=0,
        new_value={"name": "Capacity Policy", "details": f"Updated daily capacity limit to {max_pax} pax"}
    )


def get_business_info() -> dict:
    row = db.fetchone("""
        SELECT bi_name    AS name,
               bi_contact AS contact,
               bi_email   AS email,
               bi_address AS address
        FROM business_info
        ORDER BY bi_id ASC LIMIT 1
    """)
    if not row:
        return {"name": "Jayraldine's Catering", "contact": "+63 912 345 6789",
                "email": "admin@jayraldines.com", "address": "123 Rizal St., Manila"}
    return dict(row)


def save_business_info(data: dict) -> None:
    db.execute("""
        UPDATE business_info
        SET bi_name = %s, bi_contact = %s, bi_email = %s, bi_address = %s, bi_updated_at = NOW()
        WHERE bi_id = (SELECT MIN(bi_id) FROM business_info);
    """, (data["name"], data["contact"], data["email"], data["address"]))
    write_audit_log(
        action="UPDATE",
        table_name="business_info",
        record_id=0,
        new_value={"name": data.get("name"), "details": f"Updated business information for '{data.get('name')}'"}
    )


def get_smtp_config() -> dict:
    row = db.fetchone("""
        SELECT bi_smtp_host AS smtp_host,
               bi_smtp_port AS smtp_port,
               bi_smtp_user AS smtp_user,
               bi_smtp_pass AS smtp_pass
        FROM business_info
        ORDER BY bi_id ASC LIMIT 1
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
    db.execute("""
        UPDATE business_info
        SET bi_smtp_host = %s, bi_smtp_port = %s, bi_smtp_user = %s, bi_smtp_pass = %s, bi_updated_at = NOW()
        WHERE bi_id = (SELECT MIN(bi_id) FROM business_info);
    """, (host, port, user, password))


# ---------------------------------------------------------------------------
# EXPENSES
# ---------------------------------------------------------------------------

_EXPENSE_ROW_SQL = """
        SELECT exp_id              AS id,
               exp_category::TEXT AS category,
               exp_description    AS description,
               exp_amount         AS amount,
               COALESCE(exp_expense_date, exp_date) AS expense_date
        FROM expenses
"""


def _rows_to_expense_dicts(rows) -> list[dict]:
    if not rows:
        return []
    res = []
    for r in rows:
        d_val = r.get("expense_date")
        if d_val and hasattr(d_val, "strftime"):
            d_str = d_val.strftime("%b %d, %Y")
        elif d_val:
            parsed_d = _parse_date(str(d_val))
            d_str = parsed_d.strftime("%b %d, %Y") if parsed_d else str(d_val)
        else:
            d_str = date.today().strftime("%b %d, %Y")
        res.append({
            "id":          r["id"],
            "category":    r["category"],
            "description": r["description"],
            "amount":      float(r["amount"]),
            "date":        d_str,
        })
    return res


def get_all_expenses() -> list[dict]:
    """Unpaginated fetch - kept for CSV export / any caller that genuinely
    needs every row. UI list rendering should use get_expenses_page()."""
    rows = db.fetchall(
        _EXPENSE_ROW_SQL + " ORDER BY COALESCE(exp_expense_date, exp_date) DESC"
    )
    return _rows_to_expense_dicts(rows)


def get_expenses_page(offset: int = 0, limit: int = 50) -> list[dict]:
    """Fetch one page of expenses, newest first. Used for incremental/lazy loading."""
    rows = db.fetchall(
        _EXPENSE_ROW_SQL
        + " ORDER BY COALESCE(exp_expense_date, exp_date) DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )
    return _rows_to_expense_dicts(rows)


def get_expenses_summary(date_start: str = None, date_end: str = None) -> dict:
    """Aggregate expense totals across ALL rows, independent of how many pages
    have been loaded into the UI - keeps the KPI cards and the category
    breakdown accurate under pagination (never sum the loaded/paginated list).

    total_all_time / total_this_year / total_this_month are always computed
    across the whole dataset regardless of date_start/date_end (they're fixed
    reference points, not meant to track the active filter). by_category is
    scoped to [date_start, date_end] when both are given - this is what the
    breakdown chart uses, so it reflects whatever period the user has
    filtered to instead of always showing all-time totals.

    Returns:
        total_all_time / total_this_year / total_this_month  (floats)
        by_category:  [{"category": str, "total": float}, ...]  (desc)
    """
    row = db.fetchone("""
        SELECT
            COALESCE(SUM(exp_amount), 0.0) AS total_all_time,
            COALESCE(SUM(CASE WHEN CAST(strftime('%Y', COALESCE(exp_expense_date, exp_date)) AS INTEGER)
                                   = CAST(strftime('%Y', 'now', 'localtime') AS INTEGER)
                              THEN exp_amount ELSE 0.0 END), 0.0) AS total_this_year,
            COALESCE(SUM(CASE WHEN strftime('%Y-%m', COALESCE(exp_expense_date, exp_date))
                                   = strftime('%Y-%m', 'now', 'localtime')
                              THEN exp_amount ELSE 0.0 END), 0.0) AS total_this_month
        FROM expenses
    """)
    if date_start and date_end:
        cat_rows = db.fetchall("""
            SELECT exp_category::TEXT AS category,
                   COALESCE(SUM(exp_amount), 0.0) AS total
            FROM expenses
            WHERE COALESCE(exp_expense_date, exp_date) BETWEEN %s AND %s
            GROUP BY exp_category
            HAVING SUM(exp_amount) > 0
            ORDER BY total DESC
        """, (date_start, date_end))
    else:
        cat_rows = db.fetchall("""
            SELECT exp_category::TEXT AS category,
                   COALESCE(SUM(exp_amount), 0.0) AS total
            FROM expenses
            GROUP BY exp_category
            HAVING SUM(exp_amount) > 0
            ORDER BY total DESC
        """)
    by_category = [
        {"category": r["category"] or "Other", "total": float(r["total"] or 0.0)}
        for r in (cat_rows or [])
    ]
    # Unlike total_all_time/total_this_year/total_this_month (fixed reference
    # points, unaffected by the filter by design - see docstring), this DOES
    # track whatever period the user has actively filtered to, so the UI can
    # show a "Filtered Total" figure next to the Period/Month filter controls
    # instead of only ever showing All Time/This Month regardless of filter.
    total_filtered = sum(c["total"] for c in by_category) if (date_start and date_end) else (float(row["total_all_time"] or 0.0) if row else 0.0)
    return {
        "total_all_time":  float(row["total_all_time"] or 0.0) if row else 0.0,
        "total_this_year": float(row["total_this_year"] or 0.0) if row else 0.0,
        "total_this_month": float(row["total_this_month"] or 0.0) if row else 0.0,
        "total_filtered":  total_filtered,
        "by_category":     by_category,
    }


def add_expense(data: dict) -> Optional[int]:
    cat = str(data.get("category", "Other")).strip() or "Other"
    desc = str(data.get("description", "—")).strip() or "—"
    try:
        amt = float(data.get("amount", 0.0))
    except (ValueError, TypeError):
        amt = 0.0
    d_val = _parse_date(data.get("date"))

    exp_id = None
    try:
        result = db.callproc_out(
            "sp_add_expense",
            in_params=(cat, desc, amt, d_val),
            out_names=["p_expense_id"],
        )
        if result and result.get("p_expense_id"):
            exp_id = result["p_expense_id"]
    except Exception as exc:
        print(f"[repository] sp_add_expense failed: {exc}")

    # Direct fallback if procedure fails
    if not exp_id:
        try:
            row = db.fetchone("""
                INSERT INTO expenses (exp_category, exp_description, exp_amount, exp_date)
                VALUES (%s, %s, %s, %s)
                RETURNING exp_id
            """, (cat, desc, amt, d_val))
            if row and row.get("exp_id"):
                exp_id = row["exp_id"]
        except Exception as exc:
            print(f"[repository] add_expense direct insert fallback failed: {exc}")

    if exp_id:
        write_audit_log(
            action="CREATE",
            table_name="expenses",
            record_id=exp_id,
            new_value={"category": cat, "description": desc, "amount": amt}
        )
        return exp_id
    return None


def update_expense(expense_id: int, data: dict) -> None:
    db.callproc_void(
        "sp_update_expense",
        in_params=(expense_id, data["category"], data["description"], data["amount"], _parse_date(data["date"])),
    )
    write_audit_log(
        action="UPDATE",
        table_name="expenses",
        record_id=expense_id,
        new_value={"category": data.get("category"), "description": data.get("description"), "amount": data.get("amount")}
    )


def delete_expense(expense_id: int) -> None:
    desc = ""
    amt = 0.0
    cat = ""
    try:
        row = db.fetchone("SELECT exp_category, exp_description, exp_amount FROM expenses WHERE exp_id = %s", (expense_id,))
        if row:
            desc = row.get("exp_description", "")
            amt = float(row.get("exp_amount") or 0.0)
            cat = row.get("exp_category", "")
    except Exception:
        pass
    db.callproc_void("sp_delete_expense", in_params=(expense_id,))
    write_audit_log(
        action="DELETE",
        table_name="expenses",
        record_id=expense_id,
        old_value={"category": cat, "description": desc, "amount": amt}
    )


def get_top_locations(limit: int = 10) -> list[dict]:
    rows = db.fetchall(
        """
        SELECT bk_address, COUNT(*) AS booking_count
        FROM bookings
        WHERE bk_address IS NOT NULL AND TRIM(bk_address) != ''
          AND bk_status IN ('CONFIRMED', 'COMPLETED')
        GROUP BY bk_address
        ORDER BY booking_count DESC
        LIMIT %s
        """,
        (limit * 2,),
    )
    if not rows:
        return []
    areas: dict[str, int] = {}
    for r in rows:
        addr = (r.get("bk_address") or "").strip()
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        area = parts[-2] if len(parts) >= 2 else (parts[0] if parts else "Cebu")
        areas[area] = areas.get(area, 0) + int(r.get("booking_count", 1))

    sorted_items = sorted(areas.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"venue": k, "count": v} for k, v in sorted_items]


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

_CUSTOMER_ACTIVITY_SUBQ = (
    "(SELECT MAX(bk_event_date) FROM bookings "
    "WHERE (bk_customer_id = c.cus_id OR LOWER(bk_customer_name) = LOWER(c.cus_name)) "
    "AND bk_status != 'CANCELLED')"
)

_CUSTOMER_LOYALTY_ROW_SQL = f"""
        SELECT c.cus_id              AS id,
               c.cus_name           AS name,
               c.cus_contact        AS contact,
               c.cus_email          AS email,
               c.cus_address        AS address,
               (SELECT COUNT(*) FROM bookings WHERE (bk_customer_id = c.cus_id OR LOWER(bk_customer_name) = LOWER(c.cus_name)) AND bk_status != 'CANCELLED') AS total_events,
               (SELECT COALESCE(SUM(bk_total_amount), 0.0) FROM bookings WHERE (bk_customer_id = c.cus_id OR LOWER(bk_customer_name) = LOWER(c.cus_name)) AND bk_status != 'CANCELLED') AS total_spent,
               c.cus_status::TEXT   AS status,
               c.cus_loyalty_tier::TEXT AS loyalty_tier,
               {_CUSTOMER_ACTIVITY_SUBQ} AS last_event_date
        FROM customers c
"""


def _rows_to_customer_loyalty_dicts(rows) -> list[dict]:
    if not rows:
        return []
    return [
        {
            "id":           r["id"],
            "name":         r["name"],
            "contact":      r["contact"],
            "email":        r["email"] or "",
            "address":      r["address"] or "",
            "events":       int(r["total_events"] or 0),
            "total_spent":  float(r["total_spent"] or 0.0),
            "status":       r["status"],
            "loyalty_tier": r["loyalty_tier"] or ("Gold" if int(r["total_events"] or 0) >= 5 or float(r["total_spent"] or 0.0) >= 100000 else ("Silver" if int(r["total_events"] or 0) >= 3 or float(r["total_spent"] or 0.0) >= 50000 else "Bronze")),
            "last_event_date": r["last_event_date"],
        }
        for r in rows
    ]


def get_all_customers_with_loyalty() -> list[dict]:
    rows = db.fetchall(_CUSTOMER_LOYALTY_ROW_SQL + " ORDER BY c.cus_name")
    return _rows_to_customer_loyalty_dicts(rows)


def get_customers_page(offset: int = 0, limit: int = 50, active_only: bool = False) -> list[dict]:
    """Fetch one page of customers (with loyalty stats), name-ordered.
    Used for incremental/lazy loading so the UI never fetches or renders rows
    nobody is looking at.

    active_only: when True, restricts to customers with at least one
    (non-cancelled) booking dated within the last 6 months - the default
    "Active Customers" view. Pass False for "Show All"."""
    where = ""
    params: list = []
    if active_only:
        cutoff = (date.today() - timedelta(days=182)).isoformat()
        where = f" WHERE {_CUSTOMER_ACTIVITY_SUBQ} >= %s"
        params.append(cutoff)
    params.extend([limit, offset])
    rows = db.fetchall(
        _CUSTOMER_LOYALTY_ROW_SQL + where + " ORDER BY c.cus_name LIMIT %s OFFSET %s",
        tuple(params),
    )
    return _rows_to_customer_loyalty_dicts(rows)


def recalculate_all_customer_stats() -> None:
    """Synchronize customer total events, total spent, and loyalty tier directly from booking records."""
    try:
        custs = db.fetchall("SELECT cus_id, cus_name FROM customers") or []
        for c in custs:
            cid = c.get("cus_id")
            cname = c.get("cus_name", "")
            stats = db.fetchone("""
                SELECT COUNT(*) AS cnt, COALESCE(SUM(bk_total_amount), 0.0) AS spent
                FROM bookings
                WHERE (bk_customer_id = %s OR LOWER(bk_customer_name) = LOWER(%s))
                  AND bk_status != 'CANCELLED'
            """, (cid, cname))
            if stats:
                cnt = int(stats.get("cnt") or 0)
                spent = float(stats.get("spent") or 0.0)
                tier = "Gold" if (cnt >= 5 or spent >= 100000) else ("Silver" if (cnt >= 3 or spent >= 50000) else "Bronze")
                db.execute("""
                    UPDATE customers
                    SET cus_total_events = %s, cus_total_spent = %s, cus_loyalty_tier = %s
                    WHERE cus_id = %s
                """, (cnt, spent, tier, cid))
    except Exception as exc:
        print(f"[repository] Error recalculating all customer stats: {exc}")


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
    fid = result["p_follow_up_id"] if result else None
    c_name = ""
    try:
        c_row = db.fetchone("SELECT cus_name FROM customers WHERE cus_id = %s", (customer_id,))
        if c_row:
            c_name = c_row.get("cus_name", "")
    except Exception:
        pass
    write_audit_log(
        action="FOLLOW_UP",
        table_name="customers",
        record_id=customer_id,
        new_value={"name": c_name, "date": date_str, "note": note}
    )
    return fid


def complete_follow_up(follow_up_id: int) -> None:
    c_name = ""
    cid = 0
    try:
        row = db.fetchone("""
            SELECT c.cus_name, c.cus_id 
            FROM customer_follow_ups cf 
            JOIN customers c ON c.cus_id = cf.cfu_customer_id 
            WHERE cf.cfu_id = %s
        """, (follow_up_id,))
        if row:
            c_name = row.get("cus_name", "")
            cid = row.get("cus_id", 0)
    except Exception:
        pass
    db.callproc_void("sp_complete_follow_up", in_params=(follow_up_id,))
    write_audit_log(
        action="COMPLETE_FOLLOW_UP",
        table_name="customers",
        record_id=cid or follow_up_id,
        new_value={"name": c_name}
    )


def delete_follow_up(follow_up_id: int) -> None:
    c_name = ""
    cid = 0
    try:
        row = db.fetchone("""
            SELECT c.cus_name, c.cus_id 
            FROM customer_follow_ups cf 
            JOIN customers c ON c.cus_id = cf.cfu_customer_id 
            WHERE cf.cfu_id = %s
        """, (follow_up_id,))
        if row:
            c_name = row.get("cus_name", "")
            cid = row.get("cus_id", 0)
    except Exception:
        pass
    db.callproc_void("sp_delete_follow_up", in_params=(follow_up_id,))
    write_audit_log(
        action="DELETE_FOLLOW_UP",
        table_name="customers",
        record_id=cid or follow_up_id,
        old_value={"name": c_name}
    )


def get_upcoming_follow_ups(days: int = 7) -> list[dict]:
    """Open follow-ups due within the next `days` days (today included)."""
    rows = db.fetchall(
        """
        SELECT cf.cfu_id             AS id,
               c.cus_id              AS customer_id,
               c.cus_name            AS customer_name,
               cf.cfu_note           AS note,
               cf.cfu_follow_up_date AS follow_up_date
        FROM customer_follow_ups cf
        JOIN customers c ON c.cus_id = cf.cfu_customer_id
        WHERE cf.cfu_is_done = FALSE
          AND cf.cfu_follow_up_date BETWEEN CURRENT_DATE
              AND CURRENT_DATE + (%s || ' days')::INTERVAL
        ORDER BY cf.cfu_follow_up_date, c.cus_name
        """,
        (days,),
    )
    if not rows:
        return []
    return [
        {
            "id":            r["id"],
            "customer_id":   r["customer_id"],
            "customer_name": r["customer_name"],
            "note":          r["note"],
            "date":          r["follow_up_date"].strftime("%b %d, %Y")
                             if hasattr(r["follow_up_date"], "strftime") else str(r["follow_up_date"]),
        }
        for r in rows
    ]


def get_overdue_follow_ups() -> list[dict]:
    """Open follow-ups whose date has already passed."""
    rows = db.fetchall("""
        SELECT cf.cfu_id             AS id,
               c.cus_id              AS customer_id,
               c.cus_name            AS customer_name,
               cf.cfu_note           AS note,
               cf.cfu_follow_up_date AS follow_up_date
        FROM customer_follow_ups cf
        JOIN customers c ON c.cus_id = cf.cfu_customer_id
        WHERE cf.cfu_is_done = FALSE
          AND cf.cfu_follow_up_date < CURRENT_DATE
        ORDER BY cf.cfu_follow_up_date, c.cus_name
    """)
    if not rows:
        return []
    return [
        {
            "id":            r["id"],
            "customer_id":   r["customer_id"],
            "customer_name": r["customer_name"],
            "note":          r["note"],
            "date":          r["follow_up_date"].strftime("%b %d, %Y")
                             if hasattr(r["follow_up_date"], "strftime") else str(r["follow_up_date"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# AUDIT LOG
# ---------------------------------------------------------------------------

_last_audit_entry = {"key": None, "time": 0.0}

def write_audit_log(actor: str = None, action: str = "LOG", table_name: str = "general",
                    record_id: int = 0, old_value: dict = None, new_value: dict = None,
                    device: str = "Desktop / Server") -> None:
    import json
    import time
    global _last_audit_entry

    if not actor or not str(actor).strip():
        try:
            from utils.session import get_actor
            actor = get_actor()
        except Exception:
            actor = "Staff"
    actor = str(actor).strip()

    action = str(action or "LOG").strip().upper()
    table_name = str(table_name or "general").strip().lower()
    record_id = int(record_id or 0)
    device = str(device or "Desktop / Server").strip()

    # 1.0s deduplication guard
    dedup_key = (actor, action, table_name, record_id, str(new_value), device)
    now = time.time()
    if dedup_key == _last_audit_entry["key"] and (now - _last_audit_entry["time"]) < 1.0:
        return
    _last_audit_entry["key"] = dedup_key
    _last_audit_entry["time"] = now

    old_json = json.dumps(old_value, default=str) if old_value else None
    new_json = json.dumps(new_value, default=str) if new_value else None
    res = None
    try:
        res = db.callproc_out(
            "sp_write_audit_log",
            in_params=(actor, action, table_name, record_id, old_json, new_json, device),
            out_names=["p_log_id"],
        )
    except Exception as exc:
        print(f"[audit] sp_write_audit_log note: {exc}")

    # Fallback direct insert if procedure failed or didn't return an ID
    if not res or not res.get("p_log_id"):
        try:
            db.execute("""
                INSERT INTO audit_logs (al_actor, al_action, al_table_name, al_record_id, al_old_value, al_new_value, al_device)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (actor, action, table_name, record_id, old_json, new_json, device))
        except Exception as exc2:
            print(f"[audit] direct insert fallback failed: {exc2}")

    try:
        from utils.signals import app_events
        app_events().data_changed.emit()
    except Exception:
        pass


add_audit_log = write_audit_log


def _format_audit_description(action: str, old_value, new_value, table_name: str = None) -> str:
    """Build a human-readable sentence from the JSON old/new value blobs
    and table context for audit_logs entries."""
    import json
    import re

    def _load(v):
        if not v or v in ("None", "null"):
            return {}
        try:
            return json.loads(v) if isinstance(v, str) else (v if isinstance(v, dict) else {})
        except Exception:
            return {}

    def _parse_amount(v):
        if v in (None, ""):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            clean = re.sub(r"[^\d.\-]", "", v)
            if not clean:
                return None
            try:
                return float(clean)
            except (TypeError, ValueError):
                return None
        return None

    data = {**_load(old_value), **_load(new_value)}
    table = str(table_name or data.get("table") or "").strip().lower()
    act = str(action or "").strip().upper()

    # If an explicit human-readable description or details was passed, prioritize it
    explicit_desc = data.get("details") or data.get("audit_desc")
    if explicit_desc and isinstance(explicit_desc, str) and explicit_desc.strip():
        return explicit_desc.strip()

    name = data.get("name") or data.get("customer") or data.get("customer_name") or data.get("client") or ""
    amount = _parse_amount(data.get("amount") or data.get("total") or data.get("total_amount") or data.get("price"))
    amount_str = f" — ₱{amount:,.2f}" if amount is not None else ""
    reason = data.get("reason") or ""
    contact = data.get("contact") or data.get("phone") or ""
    contact_str = f" ({contact})" if contact else ""
    category = data.get("category") or ""
    item_desc = data.get("description") or data.get("desc") or ""

    # CUSTOMERS
    if table in ("customers", "customer"):
        c_label = f"'{name}'" if name else "customer"
        if act in ("CREATE", "ADD"):
            return f"Added new customer {c_label}{contact_str}"
        elif act in ("UPDATE", "EDIT"):
            status_part = f" [Status: {data.get('status')}]" if data.get("status") else ""
            return f"Updated customer details for {c_label}{status_part}"
        elif act in ("DELETE", "REMOVE"):
            return f"Deleted customer {c_label}"
        elif act == "FOLLOW_UP":
            note = data.get("note", "")
            return f"Added follow-up note for {c_label}{': ' + note if note else ''}"
        elif act == "COMPLETE_FOLLOW_UP":
            return f"Marked follow-up as completed for {c_label}"
        elif act == "DELETE_FOLLOW_UP":
            return f"Deleted follow-up for {c_label}"

    # MENU ITEMS
    elif table in ("menu_items", "menu_item", "dishes", "menu"):
        m_label = f"'{name}'" if name else "menu item"
        cat_part = f" ({category})" if category else ""
        if act in ("CREATE", "ADD"):
            return f"Added menu item {m_label}{cat_part}{amount_str}"
        elif act in ("UPDATE", "EDIT"):
            return f"Updated menu item {m_label}{cat_part}{amount_str}"
        elif act in ("DELETE", "REMOVE"):
            return f"Deleted menu item {m_label}"

    # PACKAGES
    elif table in ("packages", "package", "menu_packages"):
        p_label = f"'{name}'" if name else "package"
        if act in ("CREATE", "ADD"):
            return f"Added package {p_label}{amount_str}"
        elif act in ("UPDATE", "EDIT"):
            return f"Updated package {p_label}{amount_str}"
        elif act in ("DELETE", "REMOVE"):
            return f"Deleted package {p_label}"

    # EXPENSES
    elif table in ("expenses", "expense"):
        cat_part = f" ({category})" if category else ""
        e_desc = f": {item_desc}" if item_desc else ""
        if act in ("CREATE", "ADD"):
            return f"Recorded expense{cat_part}{e_desc}{amount_str}"
        elif act in ("UPDATE", "EDIT"):
            return f"Updated expense{cat_part}{e_desc}{amount_str}"
        elif act in ("DELETE", "REMOVE"):
            return f"Deleted expense{cat_part}{e_desc}{amount_str}"

    # INVOICES & PAYMENTS
    elif table in ("invoices", "invoice", "payment_records", "payments", "payment"):
        cust_part = f" from {name}" if name else ""
        if act in ("PAYMENT", "RECORD_PAYMENT"):
            method = data.get("method") or "Cash"
            return f"Recorded payment{cust_part} via {method}{amount_str}"
        elif act == "DOWN_PAYMENT":
            return f"Recorded down payment{cust_part}{amount_str}"
        elif act in ("CREATE", "ADD"):
            return f"Created invoice for {name or 'booking'}{amount_str}"
        elif act in ("UPDATE", "EDIT"):
            return f"Updated invoice for {name or 'booking'}{amount_str}"
        elif act in ("DELETE", "VOID", "CANCEL"):
            return f"Voided/deleted invoice for {name or 'booking'}"

    # INVENTORY
    elif table in ("inventory", "inventory_items", "ingredients"):
        ingredient = data.get("ingredient") or name or "item"
        unit = data.get("unit") or ""
        stock = data.get("stock")
        if act in ("CREATE", "ADD"):
            stock_info = f" ({stock} {unit})" if stock is not None else ""
            return f"Added inventory item '{ingredient}'{stock_info}"
        elif act in ("UPDATE", "EDIT"):
            return f"Updated inventory item '{ingredient}'"
        elif act == "ADJUST_STOCK":
            delta = data.get("delta")
            delta_str = f" ({'+' if delta and delta > 0 else ''}{delta} {unit})" if delta is not None else ""
            return f"Adjusted stock for '{ingredient}'{delta_str}"
        elif act in ("DELETE", "REMOVE"):
            return f"Deleted inventory item '{ingredient}'"

    # CASH FLOW
    elif table in ("cash_flow", "cash_flow_transactions"):
        cft_type = data.get("type") or "Transaction"
        desc_part = f" ({item_desc})" if item_desc else ""
        if act in ("CREATE", "ADD"):
            return f"Recorded cash flow {cft_type}{desc_part}{amount_str}"
        elif act in ("UPDATE", "EDIT"):
            return f"Updated cash flow {cft_type}{desc_part}{amount_str}"
        elif act in ("DELETE", "REMOVE"):
            return f"Deleted cash flow {cft_type}{desc_part}"

    # OCCASIONS
    elif table in ("occasions", "occasion"):
        o_label = f"'{name}'" if name else "occasion"
        if act in ("CREATE", "ADD"):
            return f"Added occasion {o_label}"
        elif act in ("UPDATE", "EDIT"):
            return f"Updated occasion {o_label}"
        elif act in ("DELETE", "REMOVE"):
            return f"Deleted occasion {o_label}"

    # SETTINGS / BUSINESS
    elif table in ("business_info", "settings", "policy"):
        return f"Updated {name or 'business settings'}"

    # IMPORT / BACKUP
    elif act == "MERGE_IMPORT":
        imported = data.get("imported") or data.get("summary") or ""
        return f"Merged database import{' — ' + str(imported) if imported else ''}"

    # BOOKINGS / ORDERS / FALLBACK
    verbs = {
        "CREATE":        "Added a new order",
        "ADD":           "Added an order",
        "UPDATE":        "Updated an order",
        "EDIT":          "Edited an order",
        "DELETE":        "Deleted an order",
        "CANCEL":        "Cancelled an order",
        "APPROVE":       "Approved an order",
        "PAYMENT":       "Recorded a payment",
        "DOWN_PAYMENT":  "Recorded a down payment",
        "ADD_CHARGE":    "Added an additional charge",
        "DELETE_CHARGE": "Removed an additional charge",
        "STATUS_CHANGE": "Changed the order status",
        "CONFIRM":       "Confirmed an order",
    }
    verb = verbs.get(act, act.replace("_", " ").title())
    parts = [verb]
    if name:
        parts.append(f"from {name}" if act in ("PAYMENT", "DOWN_PAYMENT") else f"for {name}")
    if act in ("ADD_CHARGE", "DELETE_CHARGE") and item_desc:
        parts.append(f"({item_desc})")
    if act == "CANCEL" and reason:
        parts.append(f"— reason: {reason}")
    elif act == "STATUS_CHANGE" and data.get("status"):
        parts.append(f"to {data.get('status')}")

    return (" ".join(parts) + amount_str).strip()


def get_audit_log(limit: int = 50, start_date=None, end_date=None, table_name=None, device_filter=None) -> list[dict]:
    """Recent activity log. If start_date/end_date are given, returns every
    matching entry in that range (used by the Daily Activity Report) instead
    of only the most recent `limit` rows. Supports filtering by device (Tablet / Desktop / Server)."""
    sql = """
        SELECT al_id          AS id,
               al_actor       AS actor,
               al_action      AS action,
               al_table_name  AS table_name,
               al_record_id   AS record_id,
               al_old_value,
               al_new_value,
               COALESCE(al_device, 'Desktop / Server') AS device,
               al_created_at  AS created_at
        FROM audit_logs
    """
    params: list = []
    where_clauses = []
    if start_date and end_date:
        where_clauses.append("DATE(al_created_at) BETWEEN %s AND %s")
        params.extend([start_date, end_date])
    elif start_date:
        where_clauses.append("DATE(al_created_at) >= %s")
        params.append(start_date)
    elif end_date:
        where_clauses.append("DATE(al_created_at) <= %s")
        params.append(end_date)
    if table_name:
        where_clauses.append("LOWER(al_table_name) = LOWER(%s)")
        params.append(str(table_name).strip().lower())

    if device_filter:
        df = str(device_filter).strip().lower()
        if "tablet" in df or "kiosk" in df:
            where_clauses.append("(LOWER(al_device) LIKE '%tablet%' OR LOWER(al_device) LIKE '%kiosk%')")
        elif "desktop" in df or "server" in df:
            where_clauses.append("(LOWER(al_device) NOT LIKE '%tablet%' AND LOWER(al_device) NOT LIKE '%kiosk%')")

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += " ORDER BY al_created_at DESC, al_id DESC"
    if not (start_date or end_date):
        sql += " LIMIT %s"
        params.append(limit)

    rows = db.fetchall(sql, tuple(params))
    if not rows:
        return []
    results = []
    for r in rows:
        ts = r["created_at"]
        if isinstance(ts, str):
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    ts = datetime.strptime(ts, fmt)
                    break
                except ValueError:
                    continue
        if hasattr(ts, "strftime"):
            date_str, time_str = ts.strftime("%b %d, %Y"), ts.strftime("%I:%M %p")
        else:
            date_str, time_str = str(r["created_at"]), ""
        results.append({
            "id":          r["id"],
            "actor":       r["actor"],
            "action":      r["action"],
            "table":       r["table_name"],
            "record_id":   r["record_id"],
            "device":      r.get("device") or "Desktop / Server",
            "description": _format_audit_description(
                r["action"],
                r.get("al_old_value"),
                r.get("al_new_value"),
                table_name=r.get("table_name")
            ),
            "date":        date_str,
            "time":        time_str,
            "created_at":  f"{date_str} {time_str}".strip(),
        })
    return results


get_audit_logs = get_audit_log


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

def get_calendar_events_for_month(year: int, month: int) -> dict[tuple[int, int, int], list[dict]]:
    """Fetch all bookings and manual calendar events for the entire month with robust date parsing."""
    result_by_day: dict[tuple[int, int, int], list[dict]] = {}

    booking_rows = db.fetchall(
        """
        SELECT b.bk_id            AS db_id,
               b.bk_event_date    AS event_date,
               b.bk_booking_ref   AS booking_ref,
               b.bk_customer_name AS customer_name,
               b.bk_pax           AS pax,
               b.bk_event_time    AS event_time,
               b.bk_venue         AS venue,
               b.bk_address       AS address,
               b.bk_occasion      AS occasion,
               b.bk_menu_type     AS menu_type,
               b.bk_notes         AS notes,
               b.bk_color_theme   AS color_theme,
               p.pkg_name         AS package_name,
               p.pkg_description  AS package_description,
               b.bk_total_amount  AS total_amount,
               b.bk_amount_paid   AS amount_paid,
               i.inv_amount_paid  AS inv_amount_paid,
               i.inv_balance      AS balance,
               b.bk_status        AS status
        FROM bookings b
        LEFT JOIN packages p ON b.bk_package_id = p.pkg_id
        LEFT JOIN invoices i ON b.bk_id = i.inv_booking_id
        WHERE b.bk_status NOT IN ('CANCELLED')
        ORDER BY b.bk_event_date, b.bk_event_time
        """
    )
    for r in booking_rows or []:
        raw_ed = r.get("event_date")
        if not raw_ed:
            continue
        try:
            ed = _parse_date(raw_ed)
        except Exception:
            continue
        if not ed or ed.year != year or ed.month != month:
            continue

        key = (ed.year, ed.month, ed.day)
        t_raw = r.get("event_time") or "6:00 PM"
        if hasattr(t_raw, "strftime"):
            time_str = t_raw.strftime("%I:%M %p").lstrip("0")
        else:
            time_str = str(t_raw).strip()
            try:
                for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"):
                    try:
                        parsed_t = datetime.strptime(time_str, fmt).time()
                        time_str = parsed_t.strftime("%I:%M %p").lstrip("0")
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        label = r.get("customer_name") or "Valued Client"
        
        tot_val = float(r.get("total_amount") or 0.0)
        paid_val = float(r.get("inv_amount_paid") if r.get("inv_amount_paid") is not None else (r.get("amount_paid") or 0.0))
        bal_val = float(r.get("balance") if r.get("balance") is not None else max(0.0, tot_val - paid_val))
        
        notes_str = str(r.get("notes") or "").strip()
        pkg_desc = str(r.get("package_description") or "").strip()
        occ_str = str(r.get("occasion") or "Event").strip()
        
        theme_desc = notes_str or pkg_desc or (f"{occ_str} Theme" if occ_str else "Standard Setup")
        menu_desc = r.get("package_name") or notes_str or ("Custom Menu" if r.get("menu_type") == "custom" else "Standard Package")
        venue_str = r.get("venue") or r.get("address") or "Client Venue"
        if r.get("address") and r.get("venue") and r.get("address") not in r.get("venue"):
            venue_str = f"{r.get('venue')}, {r.get('address')}"
        
        st_val = str(r.get("status") or "CONFIRMED")
        color_theme_val = str(r.get("color_theme") or "#2563EB").strip()
        
        result_by_day.setdefault(key, []).append({
            "id":                r.get("db_id"),
            "db_id":             r.get("db_id"),
            "name":              label,
            "customer_name":     r.get("customer_name") or "Valued Client",
            "occasion":          occ_str,
            "pax":               int(r.get("pax") or 0),
            "time":              time_str,
            "loc":               venue_str,
            "venue":             venue_str,
            "address":           r.get("address") or "",
            "menu":              menu_desc,
            "package_name":      menu_desc,
            "notes":             notes_str,
            "theme":             theme_desc,
            "description":       theme_desc,
            "description_theme": theme_desc,
            "color_theme":       color_theme_val,
            "color":             color_theme_val,
            "total_amount":      tot_val,
            "amount_paid":       paid_val,
            "balance":           bal_val,
            "source":            "booking",
            "ref":               r.get("booking_ref") or "—",
            "status":            st_val,
        })

    cal_rows = db.fetchall(
        """
        SELECT ce_event_date AS event_date,
               ce_id         AS id,
               ce_name       AS name,
               ce_pax        AS pax,
               ce_event_time AS event_time,
               ce_location   AS location
        FROM calendar_events
        ORDER BY ce_id
        """
    )
    for r in cal_rows or []:
        raw_ed = r.get("event_date")
        if not raw_ed:
            continue
        try:
            ed = _parse_date(raw_ed)
        except Exception:
            continue
        if not ed or ed.year != year or ed.month != month:
            continue

        key = (ed.year, ed.month, ed.day)
        t = r["event_time"]
        time_str = t.strftime("%I:%M %p").lstrip("0") if hasattr(t, "strftime") else str(t)
        result_by_day.setdefault(key, []).append({
            "id":          r["id"],
            "db_id":       None,
            "name":        r["name"],
            "pax":         int(r["pax"]),
            "time":        time_str,
            "loc":         r["location"] or "TBD",
            "color_theme": "#2563EB",
            "color":       "#2563EB",
            "source":      "manual",
            "ref":         None,
            "status":      "CONFIRMED",
        })

    return result_by_day


def get_calendar_events_for_date(event_date: date) -> list[dict]:
    result = []

    booking_rows = db.fetchall(
        """
        SELECT bk_id            AS db_id,
               bk_event_date    AS event_date,
               bk_booking_ref   AS booking_ref,
               bk_customer_name AS customer_name,
               bk_pax           AS pax,
               bk_event_time    AS event_time,
               bk_venue         AS venue,
               bk_occasion      AS occasion,
               bk_color_theme   AS color_theme,
               bk_status        AS status
        FROM bookings
        WHERE bk_status NOT IN ('CANCELLED')
        ORDER BY bk_event_time
        """
    )
    for r in booking_rows or []:
        raw_ed = r.get("event_date")
        if not raw_ed:
            continue
        try:
            ed = _parse_date(raw_ed)
        except Exception:
            continue
        if ed != event_date:
            continue

        t = r.get("event_time") or "6:00 PM"
        time_str = t.strftime("%I:%M %p").lstrip("0") if hasattr(t, "strftime") else str(t)
        label = r.get("customer_name") or "Valued Client"
        if r.get("occasion"):
            label = f"{r['customer_name']} — {r['occasion']}"
        color_val = str(r.get("color_theme") or "#2563EB").strip()
        result.append({
            "id": r.get("db_id"), "db_id": r.get("db_id"), "name": label, "pax": int(r.get("pax") or 0),
            "time": time_str, "loc": r.get("venue") or "TBD",
            "color_theme": color_val, "color": color_val,
            "source": "booking", "ref": r.get("booking_ref"), "status": r.get("status") or "CONFIRMED",
        })

    cal_rows = db.fetchall(
        """
        SELECT ce_event_date AS event_date,
               ce_id         AS id,
               ce_name       AS name,
               ce_pax        AS pax,
               ce_event_time AS event_time,
               ce_location   AS location
        FROM calendar_events
        ORDER BY ce_id
        """
    )
    for r in cal_rows or []:
        raw_ed = r.get("event_date")
        if not raw_ed:
            continue
        try:
            ed = _parse_date(raw_ed)
        except Exception:
            continue
        if ed != event_date:
            continue

        t = r.get("event_time") or "6:00 PM"
        time_str = t.strftime("%I:%M %p").lstrip("0") if hasattr(t, "strftime") else str(t)
        result.append({
            "id": r["id"], "name": r["name"], "pax": int(r.get("pax") or 0),
            "time": time_str, "loc": r.get("location") or "TBD",
            "color_theme": "#2563EB", "color": "#2563EB",
            "source": "manual", "ref": None, "status": "CONFIRMED",
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
# BOOKING BALANCE
# ---------------------------------------------------------------------------


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
        paid_status = db.compute_invoice_status(total_amount, amount_paid)
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
    if not customer_id:
        return []
    try:
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
    except Exception as e:
        print(f"[repository] get_customer_ledger DB error for cid {customer_id}: {e}")
        rows = []

    if not rows:
        return []
    result = []
    for r in rows:
        rec_d = r.get("recorded_date")
        ev_d = r.get("event_date")
        result.append({
            "entry_type":    str(r.get("entry_type") or "Entry"),
            "recorded_date": rec_d.strftime("%b %d, %Y") if isinstance(rec_d, (date, datetime)) else str(rec_d or "—"),
            "event_date":    ev_d.strftime("%b %d, %Y") if isinstance(ev_d, (date, datetime)) else str(ev_d or "—"),
            "reference":     str(r.get("reference") or "—"),
            "description":   str(r.get("description") or "—"),
            "debit":         float(r.get("debit") or 0.0),
            "credit":        float(r.get("credit") or 0.0),
            "status":        str(r.get("entry_status") or "CONFIRMED"),
        })
    return result


# ---------------------------------------------------------------------------
# CEBU ADDRESS SYSTEM (In-Memory Cached for 0.1ms Instant Search)
# ---------------------------------------------------------------------------

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
        print(f"[repository] get_all_cebu_addresses query failed: {exc}")

    _cebu_address_cache = _cebu_address_cache or []
    return _cebu_address_cache


def search_cebu_address(query: str, limit: int = 10) -> list[dict]:
    if not query or len(query.strip()) < 2:
        return []
    all_addrs = get_all_cebu_addresses()
    if not all_addrs:
        try:
            rows = db.fetchall(
                "SELECT * FROM fn_search_cebu_address(%s::text, %s::int)",
                (query.strip(), limit),
            )
            if rows:
                return [dict(r) for r in rows]
        except Exception:
            pass

    q_raw = query.strip().lower().replace(",", " ")
    tokens = [t for t in q_raw.split() if t]
    if not tokens:
        return []

    prefix_matches = []
    phrase_matches = []
    token_matches = []

    for r in all_addrs:
        b_name = r.get("barangay", "").lower()
        c_name = r.get("city", "").lower()
        p_name = r.get("province", "").lower()
        display = r.get("display_text", f"{b_name}, {c_name}, {p_name}").lower()
        search_blob = f"{b_name} {c_name} {p_name} {display}"

        # 1. Highest priority: exact prefix on barangay or city
        if b_name.startswith(tokens[0]) or c_name.startswith(tokens[0]):
            if all(t in search_blob for t in tokens):
                prefix_matches.append(r)
                if len(prefix_matches) >= limit:
                    return prefix_matches
                continue

        # 2. Second priority: full raw search query substring in display
        if q_raw in display:
            phrase_matches.append(r)
            continue

        # 3. Third priority: all tokens present anywhere in search blob
        if all(t in search_blob for t in tokens):
            token_matches.append(r)

    combined = prefix_matches + phrase_matches + token_matches
    # Deduplicate while preserving rank order
    seen = set()
    deduped = []
    for item in combined:
        b_id = item.get("barangay_id") or item.get("display_text")
        if b_id not in seen:
            seen.add(b_id)
            deduped.append(item)
            if len(deduped) >= limit:
                break
    return deduped


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
# COMMUNICATION LOGS
# cl_log_type is one of: receipt, booking_confirm, follow_up
# cl_method   is one of: email, sms, print
# ---------------------------------------------------------------------------

def log_confirmation_sent(booking_id: int, method: str) -> None:
    try:
        row = db.fetchone("SELECT bk_email AS email FROM bookings WHERE bk_id = %s", (booking_id,))
        db.execute(
            "INSERT INTO communication_logs "
            "(cl_log_type, cl_method, cl_recipient, cl_booking_id, cl_status) "
            "VALUES ('booking_confirm', %s, %s, %s, 'sent')",
            (method, (row or {}).get("email", "") or "", booking_id),
        )
    except Exception:
        pass


def log_receipt_sent(invoice_id: int, method: str) -> None:
    try:
        row = db.fetchone(
            "SELECT COALESCE(c.cus_email, '') AS email FROM invoices i "
            "LEFT JOIN customers c ON c.cus_name = i.inv_customer_name WHERE i.inv_id = %s",
            (invoice_id,),
        )
        db.execute(
            "INSERT INTO communication_logs "
            "(cl_log_type, cl_method, cl_recipient, cl_invoice_id, cl_status) "
            "VALUES ('receipt', %s, %s, %s, 'sent')",
            (method, (row or {}).get("email", "") or "", invoice_id),
        )
    except Exception:
        pass


def log_follow_up_sent(customer_id: int, method: str, note: str = "") -> None:
    """Log a follow-up contact attempt (call/SMS/email) against a customer.
    Resolved through their most recent booking, since communication_logs
    only links to bookings/invoices, not customers directly."""
    try:
        row = db.fetchone(
            "SELECT bk_id, bk_email FROM bookings WHERE bk_customer_id = %s "
            "ORDER BY bk_created_at DESC LIMIT 1",
            (customer_id,),
        )
        booking_id = row.get("bk_id") if row else None
        recipient = (row or {}).get("bk_email", "") or ""
        db.execute(
            "INSERT INTO communication_logs "
            "(cl_log_type, cl_method, cl_recipient, cl_booking_id, cl_status, cl_note) "
            "VALUES ('follow_up', %s, %s, %s, 'sent', %s)",
            (method, recipient, booking_id, note or None),
        )
    except Exception:
        pass


def get_communication_logs(customer_id: int = None, limit: int = 20) -> list[dict]:
    """Communication history, optionally scoped to one customer (via their
    bookings/invoices — communication_logs has no direct customer FK)."""
    rows = db.fetchall(
        """
        SELECT cl.cl_id          AS id,
               cl.cl_log_type    AS log_type,
               cl.cl_method      AS method,
               cl.cl_recipient   AS recipient,
               cl.cl_status      AS status,
               cl.cl_note        AS note,
               cl.cl_created_at  AS created_at,
               COALESCE(b.bk_customer_name, b2.bk_customer_name, '') AS customer_name
        FROM communication_logs cl
        LEFT JOIN bookings b  ON b.bk_id  = cl.cl_booking_id
        LEFT JOIN invoices i  ON i.inv_id = cl.cl_invoice_id
        LEFT JOIN bookings b2 ON b2.bk_id = i.inv_booking_id
        WHERE (%(cid)s::INT IS NULL
               OR b.bk_customer_id = %(cid)s
               OR b2.bk_customer_id = %(cid)s)
        ORDER BY cl.cl_created_at DESC
        LIMIT %(lim)s
        """,
        {"cid": customer_id, "lim": limit},
    )
    if not rows:
        return []
    return [
        {
            "id":            r["id"],
            "log_type":      r["log_type"],
            "method":        r["method"],
            "recipient":     r["recipient"],
            "status":        r["status"],
            "note":          r["note"] or "",
            "customer_name": r["customer_name"],
            "created_at":    r["created_at"].strftime("%b %d, %Y %I:%M %p")
                             if hasattr(r["created_at"], "strftime") else str(r["created_at"]),
        }
        for r in rows
    ]


def get_last_contact(customer_id: int) -> Optional[dict]:
    logs = get_communication_logs(customer_id, limit=1)
    return logs[0] if logs else None


# ---------------------------------------------------------------------------
# PRIVATE HELPERS
# ---------------------------------------------------------------------------

def _parse_date(s: Any) -> date:
    from datetime import timedelta
    import re
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    if not s:
        return date.today()

    if isinstance(s, (int, float)):
        try:
            if 20000 <= s <= 80000:
                return (datetime(1899, 12, 30) + timedelta(days=float(s))).date()
        except Exception:
            pass

    s_str = str(s).strip()
    if not s_str:
        return date.today()

    clean_s = re.sub(r"[T\s]+\d{1,2}:\d{2}(:\d{2})?(\.\d+)?(\s*[AP]M)?.*$", "", s_str, flags=re.IGNORECASE).strip()

    if clean_s.replace(".", "", 1).isdigit() and len(clean_s) in (5, 6, 7):
        try:
            num = float(clean_s)
            if 20000 <= num <= 80000:
                return (datetime(1899, 12, 30) + timedelta(days=num)).date()
        except Exception:
            pass

    for fmt in (
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y",
        "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y",
        "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y",
        "%b-%d-%Y", "%B-%d-%Y",
        "%m/%d/%y", "%d/%m/%y", "%y-%m-%d"
    ):
        try:
            return datetime.strptime(clean_s, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s_str[:10]).date()
    except Exception:
        pass
    print(f"[repository] Warning: cannot parse date {s!r}, defaulting to today")
    return date.today()


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

# ---------------------------------------------------------------------------
# ANALYTICS (year-parameterized — requires analytics_functions_migration.sql)
# ---------------------------------------------------------------------------

def get_available_years() -> list[int]:
    """Every year that has booking, invoice or expense data, newest first."""
    try:
        rows = db.fetchall("""
            SELECT DISTINCT CAST(strftime('%Y', bk_event_date) AS INTEGER) AS yr FROM bookings WHERE bk_event_date IS NOT NULL
            UNION
            SELECT DISTINCT CAST(strftime('%Y', exp_date) AS INTEGER) AS yr FROM expenses WHERE exp_date IS NOT NULL
            ORDER BY yr DESC
        """)
        years = [int(r["yr"]) for r in rows if r.get("yr")]
        if years:
            return years
    except Exception:
        pass
    return [datetime.now().year]


def get_monthly_income_for_year(year: int) -> list[dict]:
    year_str = str(year)
    try:
        rows = db.fetchall(
            """
            WITH months(m_num, m_label) AS (
                VALUES
                (1, 'Jan'), (2, 'Feb'), (3, 'Mar'), (4, 'Apr'),
                (5, 'May'), (6, 'Jun'), (7, 'Jul'), (8, 'Aug'),
                (9, 'Sep'), (10, 'Oct'), (11, 'Nov'), (12, 'Dec')
            ),
            bkg AS (
                SELECT CAST(strftime('%m', bk_event_date) AS INTEGER) AS m_num,
                       SUM(bk_total_amount) AS rev,
                       SUM(bk_amount_paid) AS paid
                FROM bookings
                WHERE bk_status IN ('CONFIRMED', 'COMPLETED') AND strftime('%Y', bk_event_date) = %s
                GROUP BY m_num
            )
            SELECT
                months.m_label AS month_label,
                months.m_num AS month_num,
                COALESCE(bkg.rev, 0.0) AS total_revenue,
                COALESCE(bkg.paid, 0.0) AS total_paid
            FROM months
            LEFT JOIN bkg ON bkg.m_num = months.m_num
            ORDER BY months.m_num
            """,
            (year_str,)
        )
        if rows:
            return [{"month": r["month_label"], "month_num": int(r["month_num"]),
                     "revenue": float(r["total_revenue"]), "paid": float(r["total_paid"])}
                    for r in rows]
    except Exception:
        pass
    _MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return [{"month": _MONTH_LABELS[m-1], "month_num": m, "revenue": 0.0, "paid": 0.0} for m in range(1, 13)]


def get_profit_summary_for_year(year: int) -> list[dict]:
    year_str = str(year)
    try:
        rows = db.fetchall(
            """
            WITH months(m_num, m_label) AS (
                VALUES
                (1, 'Jan'), (2, 'Feb'), (3, 'Mar'), (4, 'Apr'),
                (5, 'May'), (6, 'Jun'), (7, 'Jul'), (8, 'Aug'),
                (9, 'Sep'), (10, 'Oct'), (11, 'Nov'), (12, 'Dec')
            ),
            rev AS (
                SELECT CAST(strftime('%m', bk_event_date) AS INTEGER) AS m_num, SUM(bk_total_amount) AS revenue
                FROM bookings
                WHERE bk_status IN ('CONFIRMED', 'COMPLETED') AND strftime('%Y', bk_event_date) = %s
                GROUP BY m_num
            ),
            exp AS (
                SELECT CAST(strftime('%m', exp_date) AS INTEGER) AS m_num, SUM(exp_amount) AS total_expense
                FROM expenses
                WHERE strftime('%Y', exp_date) = %s
                GROUP BY m_num
            )
            SELECT
                months.m_num AS month_num,
                months.m_label AS month_label,
                COALESCE(rev.revenue, 0.0) AS revenue,
                COALESCE(exp.total_expense, 0.0) AS total_expense,
                (COALESCE(rev.revenue, 0.0) - COALESCE(exp.total_expense, 0.0)) AS net_profit
            FROM months
            LEFT JOIN rev ON rev.m_num = months.m_num
            LEFT JOIN exp ON exp.m_num = months.m_num
            ORDER BY months.m_num
            """,
            (year_str, year_str)
        )
        if rows:
            return [{"month": r["month_label"], "month_num": int(r["month_num"]),
                     "revenue": float(r["revenue"]), "expense": float(r["total_expense"]),
                     "profit": float(r["net_profit"])}
                    for r in rows]
    except Exception:
        pass
    _MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return [{"month": _MONTH_LABELS[m-1], "month_num": m, "revenue": 0.0, "expense": 0.0, "profit": 0.0} for m in range(1, 13)]


def get_monthly_revenue_chart_data(year: int = None) -> list[dict]:
    """Fetch monthly revenue, expense, and profit data for charts."""
    if year:
        return get_profit_summary_for_year(year)
    return get_profit_summary()


def get_weekly_summary(year: int, month: int) -> list[dict]:
    """Revenue/expense/profit per week-of-month (Week 1 = days 1-7, ...)."""
    rows = db.fetchall(
        "SELECT week_num, week_label, revenue, total_expense, net_profit"
        " FROM fn_weekly_summary(%s, %s)", (year, month)
    )
    if not rows:
        return []
    return [{"week": r["week_label"], "week_num": int(r["week_num"]),
             "revenue": float(r["revenue"]), "expense": float(r["total_expense"]),
             "profit": float(r["net_profit"])}
            for r in rows]


def get_yearly_summary() -> list[dict]:
    """Revenue/expense/profit per year across all history."""
    try:
        rows = db.fetchall(
            """
            WITH b_years AS (
                SELECT CAST(strftime('%Y', bk_event_date) AS INTEGER) AS yr,
                       SUM(bk_total_amount) AS rev
                FROM bookings
                WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
                GROUP BY yr
            ),
            e_years AS (
                SELECT CAST(strftime('%Y', exp_date) AS INTEGER) AS yr,
                       SUM(exp_amount) AS exp
                FROM expenses
                GROUP BY yr
            ),
            all_years AS (
                SELECT yr FROM b_years UNION SELECT yr FROM e_years
            )
            SELECT
                ay.yr AS year,
                COALESCE(by.rev, 0.0) AS revenue,
                COALESCE(ey.exp, 0.0) AS total_expense,
                (COALESCE(by.rev, 0.0) - COALESCE(ey.exp, 0.0)) AS net_profit
            FROM all_years ay
            LEFT JOIN b_years by ON by.yr = ay.yr
            LEFT JOIN e_years ey ON ey.yr = ay.yr
            WHERE ay.yr IS NOT NULL
            ORDER BY ay.yr DESC
            """
        )
        if rows:
            return [{"year": int(r["year"]), "revenue": float(r["revenue"]),
                     "expense": float(r["total_expense"]), "profit": float(r["net_profit"])}
                    for r in rows]
    except Exception:
        pass
    return []


def get_expense_breakdown(year: int, month: Optional[int] = None) -> list[dict]:
    """Expense totals per category for a year (or one month of it)."""
    try:
        if month:
            rows = db.fetchall(
                """
                SELECT exp_category AS category, SUM(exp_amount) AS total
                FROM expenses
                WHERE CAST(strftime('%Y', exp_date) AS INTEGER) = %s
                  AND CAST(strftime('%m', exp_date) AS INTEGER) = %s
                GROUP BY exp_category
                ORDER BY total DESC
                """,
                (year, month),
            )
        else:
            rows = db.fetchall(
                """
                SELECT exp_category AS category, SUM(exp_amount) AS total
                FROM expenses
                WHERE CAST(strftime('%Y', exp_date) AS INTEGER) = %s
                GROUP BY exp_category
                ORDER BY total DESC
                """,
                (year,),
            )
        if rows:
            return [{"category": r["category"], "total": float(r["total"])} for r in rows]
    except Exception:
        pass
    return []


def get_bookings_any_status() -> list[dict]:
    """All bookings regardless of status — used by the AI assistant to
    resolve approve/cancel/complete targets (incl. PENDING ones)."""
    rows = db.fetchall(
        """
        SELECT bk_id             AS id,
               bk_booking_ref   AS booking_ref,
               bk_customer_name AS customer_name,
               bk_event_date    AS event_date,
               bk_pax           AS pax,
               bk_total_amount  AS total_amount,
               bk_status::TEXT  AS status
        FROM bookings
        ORDER BY bk_event_date DESC
        """
    )
    if not rows:
        return []
    return [
        {
            "db_id":  r["id"],
            "ref":    r["booking_ref"],
            "name":   r["customer_name"],
            "date":   r["event_date"].strftime("%b %d, %Y") if isinstance(r["event_date"], date) else str(r["event_date"]),
            "pax":    int(r["pax"]),
            "total":  float(r["total_amount"]),
            "status": r["status"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# DATA RESET & PURGE MANAGEMENT
# ---------------------------------------------------------------------------

def get_data_counts() -> dict:
    """Return row counts for all purgeable categories."""
    def _c(tbl):
        try:
            r = db.fetchone(f"SELECT COUNT(*) AS c FROM {tbl}")
            return int(r["c"]) if r and r.get("c") is not None else 0
        except Exception:
            return 0

    return {
        "bookings": _c("bookings"),
        "invoices": _c("invoices"),
        "payments": _c("payment_records"),
        "customers": _c("customers"),
        "expenses": _c("expenses"),
        "menu_items": _c("menu_items"),
        "packages": _c("packages"),
        "calendar_events": _c("calendar_events"),
        "notifications": _c("notifications"),
        "audit_logs": _c("audit_logs"),
    }


def purge_bookings() -> int:
    """Delete all bookings, invoices, payments, kitchen orders, and tasks."""
    cnt = db.fetchone("SELECT COUNT(*) AS c FROM bookings")
    c_val = int(cnt["c"]) if cnt and cnt.get("c") is not None else 0
    db.execute("DELETE FROM booking_menu_items")
    db.execute("DELETE FROM payment_records")
    db.execute("DELETE FROM invoices")
    db.execute("DELETE FROM kitchen_tasks")
    db.execute("DELETE FROM kitchen_orders")
    db.execute("DELETE FROM bookings")
    return c_val


def purge_customers(cascade_bookings=False) -> int:
    """Delete all customers, loyalty records, follow-ups, and customer addresses."""
    if cascade_bookings:
        purge_bookings()
    cnt = db.fetchone("SELECT COUNT(*) AS c FROM customers")
    c_val = int(cnt["c"]) if cnt and cnt.get("c") is not None else 0
    db.execute("DELETE FROM customer_follow_ups")
    db.execute("DELETE FROM customer_loyalty_tiers")
    db.execute("DELETE FROM customer_addresses")
    db.execute("DELETE FROM customers")
    return c_val


def purge_expenses() -> int:
    """Delete all expenses."""
    cnt = db.fetchone("SELECT COUNT(*) AS c FROM expenses")
    c_val = int(cnt["c"]) if cnt and cnt.get("c") is not None else 0
    db.execute("DELETE FROM expenses")
    return c_val


def purge_menu_items() -> int:
    """Delete all menu items and package item linkages."""
    cnt = db.fetchone("SELECT COUNT(*) AS c FROM menu_items")
    c_val = int(cnt["c"]) if cnt and cnt.get("c") is not None else 0
    db.execute("DELETE FROM booking_menu_items")
    db.execute("DELETE FROM package_items")
    db.execute("DELETE FROM menu_items")
    return c_val


def purge_packages() -> int:
    """Delete all packages and package item linkages."""
    cnt = db.fetchone("SELECT COUNT(*) AS c FROM packages")
    c_val = int(cnt["c"]) if cnt and cnt.get("c") is not None else 0
    db.execute("DELETE FROM package_items")
    db.execute("DELETE FROM packages")
    return c_val


def purge_calendar_events() -> int:
    """Delete all manual calendar events."""
    cnt = db.fetchone("SELECT COUNT(*) AS c FROM calendar_events")
    c_val = int(cnt["c"]) if cnt and cnt.get("c") is not None else 0
    db.execute("DELETE FROM calendar_events")
    return c_val


def purge_logs() -> int:
    """Delete all notifications and audit logs."""
    cnt = db.fetchone("SELECT (SELECT COUNT(*) FROM notifications) + (SELECT COUNT(*) FROM audit_logs) AS c")
    c_val = int(cnt["c"]) if cnt and cnt.get("c") is not None else 0
    db.execute("DELETE FROM notifications")
    db.execute("DELETE FROM audit_logs")
    return c_val


def purge_selected_data(categories: list[str]) -> dict:
    """Purge specific categories selected by user."""
    results = {}
    if "bookings" in categories:
        results["bookings"] = purge_bookings()
    if "customers" in categories:
        results["customers"] = purge_customers(cascade_bookings=("bookings" in categories))
    if "expenses" in categories:
        results["expenses"] = purge_expenses()
    if "menu_items" in categories:
        results["menu_items"] = purge_menu_items()
    if "packages" in categories:
        results["packages"] = purge_packages()
    if "calendar_events" in categories:
        results["calendar_events"] = purge_calendar_events()
    if "logs" in categories:
        results["logs"] = purge_logs()

    # Emit app-wide refresh signals
    try:
        from utils.signals import app_events
        ev = app_events()
        ev.booking_saved.emit()
        ev.booking_updated.emit()
        ev.payment_recorded.emit()
        ev.kitchen_updated.emit()
        ev.customer_saved.emit()
        ev.menu_saved.emit()
        ev.expense_saved.emit()
        ev.data_changed.emit()
    except Exception:
        pass

    return results


def purge_all_data() -> dict:
    """Completely wipe all operational data and reset system to clean state."""
    all_cats = ["bookings", "customers", "expenses", "menu_items", "packages", "calendar_events", "logs"]
    return purge_selected_data(all_cats)


# ---------------------------------------------------------------------------
# Cash Flow Management (Ref Image 2)
# ---------------------------------------------------------------------------

def recalculate_cash_flow_balances():
    """Recalculate running balances for all cash flow transactions chronologically."""
    rows = db.fetchall("SELECT cft_id, cft_deposit, cft_withdrawal FROM cash_flow_transactions ORDER BY cft_date ASC, cft_id ASC") or []
    running = 0.0
    for r in rows:
        dep = float(r.get("cft_deposit") or 0.0)
        withd = float(r.get("cft_withdrawal") or 0.0)
        running = running + dep - withd
        db.execute("UPDATE cash_flow_transactions SET cft_balance = %s WHERE cft_id = %s", (running, r["cft_id"]))


def get_cash_flow_transactions(filter_date=None, search=None) -> list[dict]:
    """Fetch cash flow transactions with running balance and formatting."""
    query = """
        SELECT cft_id AS id, cft_date AS date, cft_check_no AS check_no,
               cft_particulars AS particulars, cft_deposit AS deposit,
               cft_withdrawal AS withdrawal, cft_balance AS balance,
               COALESCE(cft_actual_sales, 0.0) AS actual_sales,
               cft_notes AS notes
        FROM cash_flow_transactions
    """
    params = []
    conds = []
    if filter_date:
        conds.append("cft_date = %s")
        params.append(str(filter_date))
    if search:
        s = f"%{search.strip().lower()}%"
        conds.append("(LOWER(cft_particulars) LIKE %s OR LOWER(cft_check_no) LIKE %s OR LOWER(cft_notes) LIKE %s)")
        params.extend([s, s, s])
    if conds:
        query += " WHERE " + " AND ".join(conds)
    query += " ORDER BY cft_date ASC, cft_id ASC"
    
    rows = db.fetchall(query, tuple(params) if params else None) or []
    return rows


def get_cash_flow_transactions_page(offset: int = 0, limit: int = 50,
                                    filter_date=None, search=None) -> list[dict]:
    """Fetch one page of cash flow transactions (oldest first, matching the
    ledger display order) for incremental/lazy loading. Mirrors the row-shaping
    of get_cash_flow_transactions but with LIMIT/OFFSET so the UI only pulls the
    rows it's about to render. Running balances are pre-stored per row (cft_balance),
    so paging does not affect balance correctness."""
    query = """
        SELECT cft_id AS id, cft_date AS date, cft_check_no AS check_no,
               cft_particulars AS particulars, cft_deposit AS deposit,
               cft_withdrawal AS withdrawal, cft_balance AS balance,
               COALESCE(cft_actual_sales, 0.0) AS actual_sales,
               cft_notes AS notes
        FROM cash_flow_transactions
    """
    params = []
    conds = []
    if filter_date:
        conds.append("cft_date = %s")
        params.append(str(filter_date))
    if search:
        s = f"%{search.strip().lower()}%"
        conds.append("(LOWER(cft_particulars) LIKE %s OR LOWER(cft_check_no) LIKE %s OR LOWER(cft_notes) LIKE %s)")
        params.extend([s, s, s])
    if conds:
        query += " WHERE " + " AND ".join(conds)
    query += " ORDER BY cft_date ASC, cft_id ASC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    rows = db.fetchall(query, tuple(params)) or []
    return rows


def find_duplicate_cash_flow(t_date, particulars: str, deposit: float = 0.0,
                             withdrawal: float = 0.0, actual_sales: float = 0.0,
                             check_no: str = "") -> Optional[dict]:
    """Check if an identical cash flow transaction already exists in the database.
    Prevents duplicate entries during Excel/CSV batch imports.
    """
    p_date = _parse_date(t_date)
    chk = str(check_no or "").strip()
    part = str(particulars or "").strip()
    dep = round(float(deposit or 0.0), 2)
    withd = round(float(withdrawal or 0.0), 2)
    sales = round(float(actual_sales or 0.0), 2)

    # 1. If check / reference number is provided, check by check_no + date
    if chk:
        row = db.fetchone("""
            SELECT cft_id, cft_date, cft_check_no, cft_particulars, cft_deposit, cft_withdrawal, cft_actual_sales
            FROM cash_flow_transactions
            WHERE cft_check_no = %s
              AND cft_date = %s
            LIMIT 1
        """, (chk, p_date))
        if row:
            return row

    # 2. Match by date, particulars, and exact amounts (within 1 cent)
    row = db.fetchone("""
        SELECT cft_id, cft_date, cft_check_no, cft_particulars, cft_deposit, cft_withdrawal, cft_actual_sales
        FROM cash_flow_transactions
        WHERE cft_date = %s
          AND LOWER(TRIM(cft_particulars)) = LOWER(TRIM(%s))
          AND ABS(COALESCE(cft_deposit, 0) - %s) < 0.01
          AND ABS(COALESCE(cft_withdrawal, 0) - %s) < 0.01
          AND ABS(COALESCE(cft_actual_sales, 0) - %s) < 0.01
        LIMIT 1
    """, (p_date, part, dep, withd, sales))
    return row


def add_cash_flow_transaction(data: dict, check_duplicate: bool = False) -> bool:
    """Insert a new cash flow transaction and recompute running balance."""
    t_date = _parse_date(data.get("date", datetime.today().strftime("%Y-%m-%d")))
    check_no = str(data.get("check_no", "")).strip()
    particulars = str(data.get("particulars", "Cash on Hand")).strip()
    deposit = float(data.get("deposit") or 0.0)
    withdrawal = float(data.get("withdrawal") or 0.0)
    actual_sales = float(data.get("actual_sales") or 0.0)
    notes = str(data.get("notes", "")).strip()

    if check_duplicate:
        dup = find_duplicate_cash_flow(t_date, particulars, deposit, withdrawal, actual_sales, check_no)
        if dup:
            return False

    if db.get_engine_type() == "postgres":
        row = db.fetchone("""
            INSERT INTO cash_flow_transactions (cft_date, cft_check_no, cft_particulars, cft_deposit, cft_withdrawal, cft_balance, cft_actual_sales, cft_notes)
            VALUES (%s, %s, %s, %s, %s, 0.0, %s, %s)
            RETURNING cft_id
        """, (t_date, check_no, particulars, deposit, withdrawal, actual_sales, notes))
        new_id = row["cft_id"] if row else None
    else:
        db.execute("""
            INSERT INTO cash_flow_transactions (cft_date, cft_check_no, cft_particulars, cft_deposit, cft_withdrawal, cft_balance, cft_actual_sales, cft_notes)
            VALUES (%s, %s, %s, %s, %s, 0.0, %s, %s)
        """, (t_date, check_no, particulars, deposit, withdrawal, actual_sales, notes))
        last_row = db.fetchone("SELECT last_insert_rowid() AS id")
        new_id = last_row["id"] if last_row else None

    recalculate_cash_flow_balances()
    cft_type = "Deposit" if deposit > 0 else ("Withdrawal" if withdrawal > 0 else "Sales")
    write_audit_log(
        action="CREATE",
        table_name="cash_flow",
        record_id=new_id or 0,
        new_value={
            "description": particulars,
            "amount": deposit or withdrawal or actual_sales,
            "type": cft_type,
        }
    )
    return new_id if new_id is not None else True


def update_cash_flow_transaction(cft_id: int, data: dict) -> bool:
    """Update an existing cash flow transaction."""
    t_date = _parse_date(data.get("date", datetime.today().strftime("%Y-%m-%d")))
    check_no = str(data.get("check_no", "")).strip()
    particulars = str(data.get("particulars", "")).strip()
    deposit = float(data.get("deposit") or 0.0)
    withdrawal = float(data.get("withdrawal") or 0.0)
    actual_sales = float(data.get("actual_sales") or 0.0)
    notes = str(data.get("notes", "")).strip()

    db.execute("""
        UPDATE cash_flow_transactions
        SET cft_date = %s, cft_check_no = %s, cft_particulars = %s,
            cft_deposit = %s, cft_withdrawal = %s, cft_actual_sales = %s, cft_notes = %s
        WHERE cft_id = %s
    """, (t_date, check_no, particulars, deposit, withdrawal, actual_sales, notes, cft_id))
    recalculate_cash_flow_balances()
    write_audit_log(
        action="UPDATE",
        table_name="cash_flow",
        record_id=cft_id,
        new_value={
            "description": particulars,
            "amount": deposit or withdrawal or actual_sales,
        }
    )
    return True


def delete_cash_flow_transaction(cft_id: int) -> bool:
    """Delete a single cash flow transaction."""
    desc = ""
    try:
        row = db.fetchone("SELECT cft_particulars FROM cash_flow_transactions WHERE cft_id = %s", (cft_id,))
        if row:
            desc = row.get("cft_particulars", "")
    except Exception:
        pass
    db.execute("DELETE FROM cash_flow_transactions WHERE cft_id = %s", (cft_id,))
    recalculate_cash_flow_balances()
    write_audit_log(
        action="DELETE",
        table_name="cash_flow",
        record_id=cft_id,
        old_value={"description": desc or f"Transaction #{cft_id}"}
    )
    return True


def delete_cash_flow_transactions(cft_ids: list[int]) -> int:
    """Delete multiple cash flow transactions in a single atomic batch."""
    if not cft_ids:
        return 0
    clean_ids = [int(i) for i in cft_ids if i]
    if not clean_ids:
        return 0
    placeholders = ",".join(["%s"] * len(clean_ids))
    db.execute(f"DELETE FROM cash_flow_transactions WHERE cft_id IN ({placeholders})", tuple(clean_ids))
    recalculate_cash_flow_balances()
    return len(clean_ids)


def get_cash_flow_summary() -> dict:
    """Return total deposits, total withdrawals, current ending balance, and total actual sales."""
    row = db.fetchone("""
        SELECT COALESCE(SUM(cft_deposit), 0.0) AS total_deposits,
               COALESCE(SUM(cft_withdrawal), 0.0) AS total_withdrawals,
               COALESCE(SUM(cft_actual_sales), 0.0) AS total_actual_sales
        FROM cash_flow_transactions
    """)
    dep = float(row["total_deposits"] if row and row.get("total_deposits") is not None else 0.0)
    withd = float(row["total_withdrawals"] if row and row.get("total_withdrawals") is not None else 0.0)
    act_sales = float(row["total_actual_sales"] if row and row.get("total_actual_sales") is not None else 0.0)
    bal = dep - withd
    diff = bal - act_sales
    return {
        "total_deposits": dep,
        "total_withdrawals": withd,
        "current_balance": bal,
        "total_actual_sales": act_sales,
        "total_difference": diff,
    }


# ---------------------------------------------------------------------------
# Monthly Sales Targets & Sales Report Analytics (Ref Image 1)
# ---------------------------------------------------------------------------

def get_monthly_sales_targets(year: int) -> dict:
    """Return dictionary of {month_int: target_amount} for the given year."""
    rows = db.fetchall("SELECT mst_month, mst_target_amount FROM monthly_sales_targets WHERE mst_year = %s", (year,)) or []
    targets = {m: 85000.0 for m in range(1, 13)}
    for r in rows:
        m = int(r["mst_month"])
        targets[m] = float(r["mst_target_amount"] or 85000.0)
    return targets


def set_monthly_sales_target(year: int, month: int, amount: float):
    """Set or update target sales for a specific month/year."""
    db.execute("""
        INSERT INTO monthly_sales_targets (mst_year, mst_month, mst_target_amount, mst_updated_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT(mst_year, mst_month) DO UPDATE SET
            mst_target_amount = EXCLUDED.mst_target_amount,
            mst_updated_at = CURRENT_TIMESTAMP
    """, (year, month, amount))


def set_yearly_default_target(year: int, default_amount: float):
    """Set default monthly target for all 12 months in a year."""
    for m in range(1, 13):
        set_monthly_sales_target(year, m, default_amount)


def get_monthly_sales_evaluation_report(year: int) -> dict:
    """
    Generate the 12-month Sales Evaluation Report based on real system sales (Ref Image 1).
    Formula: Target Sales - Actual Sales = Remaining Amount
    """
    targets = get_monthly_sales_targets(year)
    actual_sales_by_month = {m: 0.0 for m in range(1, 13)}
    
    # Fetch all non-cancelled bookings
    all_bks = db.fetchall("""
        SELECT bk_event_date, bk_total_amount, bk_status
        FROM bookings
        WHERE bk_status != 'CANCELLED'
    """) or []

    for b in all_bks:
        d_val = b.get("bk_event_date")
        if not d_val:
            continue
        try:
            if isinstance(d_val, (datetime, date)):
                b_year = d_val.year
                b_month = d_val.month
            else:
                qd = _parse_date(str(d_val))
                if qd:
                    b_year = qd.year
                    b_month = qd.month
                else:
                    parts = str(d_val).split("-")
                    b_year = int(parts[0])
                    b_month = int(parts[1])

            if b_year == int(year) and 1 <= b_month <= 12:
                actual_sales_by_month[b_month] += float(b.get("bk_total_amount") or 0.0)
        except Exception as err:
            print(f"[reports] Error parsing booking event date '{d_val}': {err}")

    month_names = [
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
    ]

    months_data = []
    tot_target = 0.0
    tot_actual = 0.0

    for m in range(1, 13):
        t_amt = targets.get(m, 85000.0)
        a_amt = actual_sales_by_month.get(m, 0.0)
        rem = t_amt - a_amt
        tot_target += t_amt
        tot_actual += a_amt

        months_data.append({
            "month_num": m,
            "month_name": month_names[m - 1],
            "target_sales": t_amt,
            "actual_sales": a_amt,
            "remaining": rem,
            "is_shortfall": (a_amt < t_amt),
            "is_achieved": (a_amt >= t_amt),
        })

    tot_remaining = tot_target - tot_actual

    return {
        "year": year,
        "months": months_data,
        "total_target": tot_target,
        "total_actual": tot_actual,
        "total_remaining": tot_remaining,
        "overall_shortfall": (tot_actual < tot_target),
    }


# ---------------------------------------------------------------------------
# Down Payment Tracking & Manual Actions
# ---------------------------------------------------------------------------

def get_down_payments_summary() -> dict:
    """Summary of all payments, down payments: received, pending, and upcoming events."""
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    # 1. Total payments & down payments received across invoices, payment_records, and bookings
    r1 = db.fetchone("""
        SELECT COALESCE(SUM(inv_amount_paid), 0.0) AS total_inv_paid
        FROM invoices
    """)
    r1_alt = db.fetchone("""
        SELECT COALESCE(SUM(pr_amount), 0.0) AS total_pr_paid
        FROM payment_records
    """)
    r1_bk = db.fetchone("""
        SELECT COALESCE(SUM(bk_down_payment), 0.0) AS total_bk_dp
        FROM bookings
        WHERE bk_status != 'CANCELLED'
    """)
    inv_paid = float(r1["total_inv_paid"] if r1 and r1.get("total_inv_paid") is not None else 0.0)
    pr_paid = float(r1_alt["total_pr_paid"] if r1_alt and r1_alt.get("total_pr_paid") is not None else 0.0)
    bk_dp = float(r1_bk["total_bk_dp"] if r1_bk and r1_bk.get("total_bk_dp") is not None else 0.0)
    total_received = max(inv_paid, pr_paid, bk_dp)

    # 2. Pending balances & pending down payments
    r2 = db.fetchone("""
        SELECT COALESCE(SUM(
            CASE 
                WHEN inv_balance IS NOT NULL AND inv_balance > 0 THEN inv_balance
                WHEN (inv_total_amount - inv_amount_paid) > 0 THEN (inv_total_amount - inv_amount_paid)
                ELSE 0.0 
            END
        ), 0.0) AS pending_inv
        FROM invoices
        WHERE CAST(inv_status AS TEXT) != 'Paid' AND CAST(inv_status AS TEXT) NOT IN ('CANCELLED', 'Cancelled')
    """)
    r2_bk = db.fetchone("""
        SELECT COALESCE(SUM(
            CASE 
                WHEN (bk_total_amount - bk_down_payment) > 0 THEN (bk_total_amount - bk_down_payment)
                ELSE 0.0 
            END
        ), 0.0) AS pending_bk
        FROM bookings
        WHERE bk_status != 'CANCELLED' AND (bk_status = 'PENDING' OR bk_down_payment < bk_total_amount)
    """)
    inv_pending = float(r2["pending_inv"] if r2 and r2.get("pending_inv") is not None else 0.0)
    bk_pending = float(r2_bk["pending_bk"] if r2_bk and r2_bk.get("pending_bk") is not None else 0.0)
    pending_down = max(inv_pending, bk_pending)

    # 3. Upcoming events count & amount
    r3 = db.fetchone("""
        SELECT COALESCE(SUM(
            CASE 
                WHEN inv_balance IS NOT NULL AND inv_balance > 0 THEN inv_balance
                WHEN (inv_total_amount - inv_amount_paid) > 0 THEN (inv_total_amount - inv_amount_paid)
                ELSE 0.0 
            END
        ), 0.0) AS upcoming_amt
        FROM invoices
        WHERE inv_event_date >= %s AND CAST(inv_status AS TEXT) NOT IN ('CANCELLED', 'Cancelled')
    """, (today_str,))
    upcoming_down = float(r3["upcoming_amt"] if r3 and r3.get("upcoming_amt") is not None else 0.0)

    r4 = db.fetchone("""
        SELECT COUNT(*) AS cnt
        FROM invoices
        WHERE CAST(inv_status AS TEXT) NOT IN ('CANCELLED', 'Cancelled')
    """)
    r4_bk = db.fetchone("""
        SELECT COUNT(*) AS cnt
        FROM bookings
        WHERE bk_status != 'CANCELLED'
    """)
    cnt_inv = int(r4["cnt"] if r4 and r4.get("cnt") is not None else 0)
    cnt_bk = int(r4_bk["cnt"] if r4_bk and r4_bk.get("cnt") is not None else 0)
    upcoming_cnt = max(cnt_inv, cnt_bk)

    return {
        "total_received": total_received,
        "total_down_payments_received": total_received,
        "pending_down": pending_down,
        "pending_down_payments": pending_down,
        "upcoming_down": upcoming_down,
        "upcoming_events_count": upcoming_cnt,
    }


def get_upcoming_down_payments(future_only=True) -> list[dict]:
    """List of all bookings with down payments for upcoming events, grouped chronologically."""
    today_str = datetime.today().strftime("%Y-%m-%d")
    query = """
        SELECT bk_id AS id, bk_booking_ref AS ref, bk_customer_name AS customer,
               bk_event_date AS event_date, bk_occasion AS occasion,
               bk_total_amount AS total, bk_down_payment AS down_payment,
               (bk_total_amount - bk_down_payment) AS balance,
               bk_status AS status, bk_down_payment_status AS down_status
        FROM bookings
        WHERE bk_down_payment > 0 AND bk_status != 'CANCELLED'
    """
    params = []
    if future_only:
        query += " AND bk_event_date >= %s"
        params.append(today_str)
    query += " ORDER BY bk_event_date ASC, bk_id ASC"
    
    return db.fetchall(query, tuple(params) if params else None) or []


def confirm_booking_order(bk_id: int) -> bool:
    """Manually accept/confirm a pending order."""
    db.callproc_void("sp_confirm_booking", (bk_id,))
    try:
        from utils.signals import app_events
        app_events().booking_updated.emit()
    except Exception:
        pass
    return True


def verify_invoice_payment(inv_id: int, pr_id: int = None) -> bool:
    """Manually verify and accept a payment record/invoice."""
    db.callproc_void("sp_verify_payment", (inv_id, pr_id))
    try:
        from utils.signals import app_events
        app_events().payment_recorded.emit()
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# INVENTORY
# ---------------------------------------------------------------------------

def get_all_inventory() -> list[dict]:
    try:
        rows = db.fetchall("SELECT * FROM inventory ORDER BY inv_ingredient")
        return [
            {
                "id": r.get("inv_id") or r.get("id"),
                "ingredient": r.get("inv_ingredient") or r.get("ingredient"),
                "unit": r.get("inv_unit") or r.get("unit") or "pcs",
                "stock": float(r.get("inv_stock") or r.get("stock") or 0.0),
                "min_stock": float(r.get("inv_min_stock") or r.get("min_stock") or 0.0),
                "status": "Low Stock" if float(r.get("inv_stock") or r.get("stock") or 0.0) < float(r.get("inv_min_stock") or r.get("min_stock") or 0.0) else "OK"
            }
            for r in rows
        ]
    except Exception:
        return []


def add_inventory_item(data: dict) -> Optional[int]:
    try:
        row = db.fetchone("""
            INSERT INTO inventory (inv_ingredient, inv_unit, inv_stock, inv_min_stock)
            VALUES (%s, %s, %s, %s)
            RETURNING inv_id
        """, (data["ingredient"], data.get("unit", "pcs"), float(data.get("stock", 0.0)), float(data.get("min_stock", 0.0))))
        new_id = row.get("inv_id") if row else None
        if new_id:
            write_audit_log(
                action="CREATE",
                table_name="inventory",
                record_id=new_id,
                new_value={"ingredient": data["ingredient"], "unit": data.get("unit"), "stock": data.get("stock")}
            )
        return new_id
    except Exception:
        return None


def adjust_inventory_stock(item_id: int, delta: float) -> Optional[float]:
    try:
        row = db.fetchone("SELECT inv_ingredient, inv_stock, inv_unit FROM inventory WHERE inv_id = %s", (item_id,))
        if not row:
            return None
        ing = row.get("inv_ingredient", "")
        unit = row.get("inv_unit", "")
        new_stock = max(0.0, float(row.get("inv_stock") or 0.0) + float(delta))
        db.execute("UPDATE inventory SET inv_stock = %s WHERE inv_id = %s", (new_stock, item_id))
        write_audit_log(
            action="ADJUST_STOCK",
            table_name="inventory",
            record_id=item_id,
            new_value={"ingredient": ing, "unit": unit, "delta": delta, "stock": new_stock}
        )
        return new_stock
    except Exception:
        return None


def delete_inventory_item(item_id: int) -> bool:
    try:
        row = db.fetchone("SELECT inv_ingredient FROM inventory WHERE inv_id = %s", (item_id,))
        ing = row.get("inv_ingredient", "") if row else f"Item #{item_id}"
        db.execute("DELETE FROM inventory WHERE inv_id = %s", (item_id,))
        write_audit_log(
            action="DELETE",
            table_name="inventory",
            record_id=item_id,
            old_value={"ingredient": ing}
        )
        return True
    except Exception:
        return False

