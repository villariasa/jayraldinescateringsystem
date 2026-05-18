from utils.db import DB


db = DB()


# ─────────────────────────────────────────────
# BUSINESS INFO
# ─────────────────────────────────────────────

def get_business_info():
    rows = db.fetchall("""
        SELECT bi_id        AS id,
               bi_name      AS name,
               bi_address   AS address,
               bi_contact   AS contact,
               bi_email     AS email,
               bi_logo_path AS logo_path,
               bi_updated_at AS updated_at
        FROM business_info
        LIMIT 1
    """)
    return rows[0] if rows else None


def update_business_info(name, address, contact, email, logo_path=None):
    db.execute("""
        UPDATE business_info
        SET bi_name      = %s,
            bi_address   = %s,
            bi_contact   = %s,
            bi_email     = %s,
            bi_logo_path = COALESCE(%s, bi_logo_path),
            bi_updated_at = NOW()
    """, (name, address, contact, email, logo_path))


# ─────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────

def get_all_customers():
    return db.fetchall("""
        SELECT cus_id                  AS id,
               cus_name               AS name,
               cus_contact            AS contact,
               cus_email              AS email,
               cus_address            AS address,
               cus_occasion_preference AS occasion_preference,
               cus_notes              AS notes,
               cus_loyalty_tier       AS loyalty_tier,
               cus_status             AS status,
               cus_address_id         AS address_id,
               cus_created_at         AS created_at,
               cus_updated_at         AS updated_at,
               (SELECT COUNT(*) FROM bookings
                WHERE bk_customer_id = cus_id
                  AND bk_status IN ('CONFIRMED', 'COMPLETED')) AS booking_count
        FROM customers
        ORDER BY cus_name
    """)


def get_customer_by_id(customer_id):
    rows = db.fetchall("""
        SELECT cus_id                  AS id,
               cus_name               AS name,
               cus_contact            AS contact,
               cus_email              AS email,
               cus_address            AS address,
               cus_occasion_preference AS occasion_preference,
               cus_notes              AS notes,
               cus_loyalty_tier       AS loyalty_tier,
               cus_status             AS status,
               cus_address_id         AS address_id,
               cus_created_at         AS created_at,
               cus_updated_at         AS updated_at
        FROM customers
        WHERE cus_id = %s
    """, (customer_id,))
    return rows[0] if rows else None


def add_customer(name, contact, email='', address='', notes='', occasion_preference=None):
    return db.fetchone("""
        INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_notes, cus_occasion_preference)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING cus_id AS id
    """, (name, contact, email, address, notes, occasion_preference))


def update_customer(customer_id, name, contact, email='', address='', notes='', occasion_preference=None):
    db.execute("""
        UPDATE customers
        SET cus_name                = %s,
            cus_contact             = %s,
            cus_email               = %s,
            cus_address             = %s,
            cus_notes               = %s,
            cus_occasion_preference = %s,
            cus_updated_at          = NOW()
        WHERE cus_id = %s
    """, (name, contact, email, address, notes, occasion_preference, customer_id))


def delete_customer(customer_id):
    db.execute("DELETE FROM customers WHERE cus_id = %s", (customer_id,))


def get_all_customers_with_loyalty():
    return db.fetchall("""
        SELECT cus_id            AS id,
               cus_name         AS name,
               cus_contact      AS contact,
               cus_email        AS email,
               cus_address      AS address,
               cus_loyalty_tier AS loyalty_tier,
               cus_status       AS status,
               cus_notes        AS notes,
               (SELECT COUNT(*) FROM bookings
                WHERE bk_customer_id = cus_id
                  AND bk_status IN ('CONFIRMED', 'COMPLETED')) AS booking_count
        FROM customers
        ORDER BY cus_name
    """)


def recalculate_loyalty(customer_id):
    db.execute("""
        UPDATE customers
        SET cus_loyalty_tier = CASE
            WHEN (SELECT COUNT(*) FROM bookings
                  WHERE bk_customer_id = %s
                    AND bk_status IN ('CONFIRMED','COMPLETED')) >= 10 THEN 'GOLD'
            WHEN (SELECT COUNT(*) FROM bookings
                  WHERE bk_customer_id = %s
                    AND bk_status IN ('CONFIRMED','COMPLETED')) >= 5  THEN 'SILVER'
            WHEN (SELECT COUNT(*) FROM bookings
                  WHERE bk_customer_id = %s
                    AND bk_status IN ('CONFIRMED','COMPLETED')) >= 1  THEN 'BRONZE'
            ELSE 'NONE'
        END,
        cus_updated_at = NOW()
        WHERE cus_id = %s
    """, (customer_id, customer_id, customer_id, customer_id))


# ─────────────────────────────────────────────
# PACKAGES
# ─────────────────────────────────────────────

def get_all_packages():
    return db.fetchall("""
        SELECT pkg_id             AS id,
               pkg_name          AS name,
               pkg_description   AS description,
               pkg_base_price    AS base_price,
               pkg_per_head_price AS per_head_price,
               pkg_min_pax       AS min_pax,
               pkg_is_active     AS is_active,
               pkg_created_at    AS created_at,
               pkg_updated_at    AS updated_at
        FROM packages
        WHERE pkg_is_active = TRUE
        ORDER BY pkg_name
    """)


def get_package_by_id(package_id):
    rows = db.fetchall("""
        SELECT pkg_id             AS id,
               pkg_name          AS name,
               pkg_description   AS description,
               pkg_base_price    AS base_price,
               pkg_per_head_price AS per_head_price,
               pkg_min_pax       AS min_pax,
               pkg_is_active     AS is_active
        FROM packages
        WHERE pkg_id = %s
    """, (package_id,))
    return rows[0] if rows else None


def add_package(name, description, base_price, per_head_price, min_pax):
    return db.fetchone("""
        INSERT INTO packages (pkg_name, pkg_description, pkg_base_price, pkg_per_head_price, pkg_min_pax)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING pkg_id AS id
    """, (name, description, base_price, per_head_price, min_pax))


def update_package(package_id, name, description, base_price, per_head_price, min_pax):
    db.execute("""
        UPDATE packages
        SET pkg_name           = %s,
            pkg_description    = %s,
            pkg_base_price     = %s,
            pkg_per_head_price = %s,
            pkg_min_pax        = %s,
            pkg_updated_at     = NOW()
        WHERE pkg_id = %s
    """, (name, description, base_price, per_head_price, min_pax, package_id))


def deactivate_package(package_id):
    db.execute("""
        UPDATE packages SET pkg_is_active = FALSE, pkg_updated_at = NOW()
        WHERE pkg_id = %s
    """, (package_id,))


# ─────────────────────────────────────────────
# MENU ITEMS
# ─────────────────────────────────────────────

def get_all_menu_items():
    return db.fetchall("""
        SELECT mi_id          AS id,
               mi_name        AS name,
               mi_description AS description,
               mi_category    AS category,
               mi_price       AS price,
               mi_package_tier AS package_tier,
               mi_is_active   AS is_active,
               mi_created_at  AS created_at,
               mi_updated_at  AS updated_at
        FROM menu_items
        ORDER BY mi_category, mi_name
    """)


def get_menu_item_by_id(item_id):
    rows = db.fetchall("""
        SELECT mi_id          AS id,
               mi_name        AS name,
               mi_description AS description,
               mi_category    AS category,
               mi_price       AS price,
               mi_package_tier AS package_tier,
               mi_is_active   AS is_active
        FROM menu_items
        WHERE mi_id = %s
    """, (item_id,))
    return rows[0] if rows else None


def add_menu_item(name, description, category, price, package_tier=None):
    return db.fetchone("""
        INSERT INTO menu_items (mi_name, mi_description, mi_category, mi_price, mi_package_tier)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING mi_id AS id
    """, (name, description, category, price, package_tier))


def update_menu_item(item_id, name, description, category, price, package_tier=None, is_active=True):
    db.execute("""
        UPDATE menu_items
        SET mi_name        = %s,
            mi_description = %s,
            mi_category    = %s,
            mi_price       = %s,
            mi_package_tier = %s,
            mi_is_active   = %s,
            mi_updated_at  = NOW()
        WHERE mi_id = %s
    """, (name, description, category, price, package_tier, is_active, item_id))


def delete_menu_item(item_id):
    db.execute("DELETE FROM menu_items WHERE mi_id = %s", (item_id,))


def get_package_items(package_id):
    return db.fetchall("""
        SELECT pi.pi_id        AS id,
               pi.pi_item_id   AS item_id,
               mi.mi_name      AS name,
               mi.mi_category  AS category,
               mi.mi_price     AS price
        FROM package_items pi
        JOIN menu_items mi ON mi.mi_id = pi.pi_item_id
        WHERE pi.pi_package_id = %s
        ORDER BY mi.mi_category, mi.mi_name
    """, (package_id,))


def add_package_item(package_id, item_id):
    db.execute("""
        INSERT INTO package_items (pi_package_id, pi_item_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (package_id, item_id))


def remove_package_item(pi_id):
    db.execute("DELETE FROM package_items WHERE pi_id = %s", (pi_id,))


# ─────────────────────────────────────────────
# BOOKINGS
# ─────────────────────────────────────────────

def get_all_bookings():
    return db.fetchall("""
        SELECT bk_id            AS id,
               bk_booking_ref  AS booking_ref,
               bk_customer_id  AS customer_id,
               bk_customer_name AS customer_name,
               bk_contact      AS contact,
               bk_email        AS email,
               bk_address      AS address,
               bk_occasion     AS occasion,
               bk_venue        AS venue,
               bk_event_date   AS event_date,
               bk_event_time   AS event_time,
               bk_pax          AS pax,
               bk_special_notes AS special_notes,
               bk_menu_type    AS menu_type,
               bk_package_id   AS package_id,
               bk_total_amount AS total_amount,
               bk_payment_mode AS payment_mode,
               bk_amount_paid  AS amount_paid,
               bk_balance      AS balance,
               bk_status       AS status,
               bk_payment_status AS payment_status,
               bk_created_at   AS created_at,
               bk_updated_at   AS updated_at
        FROM bookings
        ORDER BY bk_event_date DESC, bk_created_at DESC
    """)


def get_booking_by_id(booking_id):
    rows = db.fetchall("""
        SELECT bk_id            AS id,
               bk_booking_ref  AS booking_ref,
               bk_customer_id  AS customer_id,
               bk_customer_name AS customer_name,
               bk_contact      AS contact,
               bk_email        AS email,
               bk_address      AS address,
               bk_occasion     AS occasion,
               bk_venue        AS venue,
               bk_event_date   AS event_date,
               bk_event_time   AS event_time,
               bk_pax          AS pax,
               bk_special_notes AS special_notes,
               bk_menu_type    AS menu_type,
               bk_package_id   AS package_id,
               bk_total_amount AS total_amount,
               bk_payment_mode AS payment_mode,
               bk_amount_paid  AS amount_paid,
               bk_balance      AS balance,
               bk_status       AS status,
               bk_payment_status AS payment_status,
               bk_created_at   AS created_at,
               bk_updated_at   AS updated_at
        FROM bookings
        WHERE bk_id = %s
    """, (booking_id,))
    return rows[0] if rows else None


def get_booking_detail(booking_id):
    return get_booking_by_id(booking_id)


def save_booking(customer_name, contact, email, address, occasion, venue,
                 event_date, event_time, pax, special_notes, menu_type,
                 package_id, total_amount, payment_mode, amount_paid,
                 customer_id=None):
    return db.fetchone("""
        INSERT INTO bookings (
            bk_customer_id, bk_customer_name, bk_contact, bk_email, bk_address,
            bk_occasion, bk_venue, bk_event_date, bk_event_time, bk_pax,
            bk_special_notes, bk_menu_type, bk_package_id, bk_total_amount,
            bk_payment_mode, bk_amount_paid
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING bk_id AS id, bk_booking_ref AS booking_ref
    """, (customer_id, customer_name, contact, email, address, occasion, venue,
          event_date, event_time, pax, special_notes, menu_type, package_id,
          total_amount, payment_mode, amount_paid))


def update_booking(booking_id, customer_name, contact, email, address, occasion, venue,
                   event_date, event_time, pax, special_notes, menu_type,
                   package_id, total_amount, payment_mode, amount_paid, customer_id=None):
    db.execute("""
        UPDATE bookings
        SET bk_customer_id   = %s,
            bk_customer_name = %s,
            bk_contact       = %s,
            bk_email         = %s,
            bk_address       = %s,
            bk_occasion      = %s,
            bk_venue         = %s,
            bk_event_date    = %s,
            bk_event_time    = %s,
            bk_pax           = %s,
            bk_special_notes = %s,
            bk_menu_type     = %s,
            bk_package_id    = %s,
            bk_total_amount  = %s,
            bk_payment_mode  = %s,
            bk_amount_paid   = %s,
            bk_updated_at    = NOW()
        WHERE bk_id = %s
    """, (customer_id, customer_name, contact, email, address, occasion, venue,
          event_date, event_time, pax, special_notes, menu_type, package_id,
          total_amount, payment_mode, amount_paid, booking_id))


def update_booking_status(booking_id, new_status, cancellation_reason=None):
    db.callproc_void('sp_update_booking_status', (booking_id, new_status, cancellation_reason))


def get_upcoming_bookings(days=7):
    return db.fetchall("""
        SELECT bk_id            AS id,
               bk_booking_ref  AS booking_ref,
               bk_customer_name AS customer_name,
               bk_occasion     AS occasion,
               bk_event_date   AS event_date,
               bk_event_time   AS event_time,
               bk_pax          AS pax,
               bk_venue        AS venue,
               bk_status       AS status
        FROM bookings
        WHERE bk_event_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '%s days'
          AND bk_status IN ('PENDING', 'CONFIRMED')
        ORDER BY bk_event_date, bk_event_time
    """, (days,))


def get_bookings_by_date_range(date_from, date_to):
    return db.fetchall("""
        SELECT bk_id            AS id,
               bk_booking_ref  AS booking_ref,
               bk_customer_name AS customer_name,
               bk_occasion     AS occasion,
               bk_event_date   AS event_date,
               bk_pax          AS pax,
               bk_total_amount AS total_amount,
               bk_amount_paid  AS amount_paid,
               bk_balance      AS balance,
               bk_status       AS status
        FROM bookings
        WHERE bk_event_date BETWEEN %s AND %s
        ORDER BY bk_event_date
    """, (date_from, date_to))


def get_booking_menu_items(booking_id):
    return db.fetchall("""
        SELECT bmi.bmi_id        AS id,
               bmi.bmi_item_id   AS item_id,
               mi.mi_name        AS name,
               mi.mi_category    AS category,
               bmi.bmi_quantity  AS quantity,
               bmi.bmi_unit_price AS unit_price,
               bmi.bmi_subtotal  AS subtotal
        FROM booking_menu_items bmi
        JOIN menu_items mi ON mi.mi_id = bmi.bmi_item_id
        WHERE bmi.bmi_booking_id = %s
        ORDER BY mi.mi_category, mi.mi_name
    """, (booking_id,))


def save_booking_menu_items(booking_id, items):
    db.execute("DELETE FROM booking_menu_items WHERE bmi_booking_id = %s", (booking_id,))
    for item in items:
        db.execute("""
            INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_quantity, bmi_unit_price, bmi_subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """, (booking_id, item['item_id'], item.get('quantity', 1),
              item.get('unit_price', 0), item.get('subtotal', 0)))


def get_customer_event_dates(customer_id):
    return db.fetchall("""
        SELECT bk_event_date AS event_date,
               bk_booking_ref AS booking_ref,
               bk_status      AS status
        FROM bookings
        WHERE bk_customer_id = %s
          AND bk_status IN ('PENDING', 'CONFIRMED')
        ORDER BY bk_event_date
    """, (customer_id,))


def auto_create_invoice(booking_id):
    db.callproc_void('sp_auto_create_invoice', (booking_id,))


# ─────────────────────────────────────────────
# INVOICES
# ─────────────────────────────────────────────

def get_all_invoices():
    return db.fetchall("""
        SELECT inv.inv_id          AS id,
               inv.inv_invoice_ref AS invoice_ref,
               inv.inv_booking_id  AS booking_id,
               b.bk_customer_name  AS customer_name,
               b.bk_event_date     AS event_date,
               inv.inv_total_amount AS total_amount,
               inv.inv_amount_paid  AS amount_paid,
               inv.inv_balance      AS balance,
               inv.inv_status       AS status,
               inv.inv_due_date     AS due_date,
               inv.inv_notes        AS notes,
               inv.inv_created_at   AS created_at,
               inv.inv_updated_at   AS updated_at
        FROM invoices inv
        JOIN bookings b ON b.bk_id = inv.inv_booking_id
        ORDER BY inv.inv_created_at DESC
    """)


def get_invoice_by_id(invoice_id):
    rows = db.fetchall("""
        SELECT inv.inv_id          AS id,
               inv.inv_invoice_ref AS invoice_ref,
               inv.inv_booking_id  AS booking_id,
               b.bk_customer_name  AS customer_name,
               b.bk_customer_id    AS customer_id,
               b.bk_event_date     AS event_date,
               b.bk_occasion       AS occasion,
               b.bk_pax            AS pax,
               inv.inv_total_amount AS total_amount,
               inv.inv_amount_paid  AS amount_paid,
               inv.inv_balance      AS balance,
               inv.inv_status       AS status,
               inv.inv_due_date     AS due_date,
               inv.inv_notes        AS notes,
               inv.inv_created_at   AS created_at
        FROM invoices inv
        JOIN bookings b ON b.bk_id = inv.inv_booking_id
        WHERE inv.inv_id = %s
    """, (invoice_id,))
    return rows[0] if rows else None


def get_invoices_by_booking(booking_id):
    return db.fetchall("""
        SELECT inv_id          AS id,
               inv_invoice_ref AS invoice_ref,
               inv_total_amount AS total_amount,
               inv_amount_paid  AS amount_paid,
               inv_balance      AS balance,
               inv_status       AS status,
               inv_due_date     AS due_date,
               inv_created_at   AS created_at
        FROM invoices
        WHERE inv_booking_id = %s
        ORDER BY inv_created_at DESC
    """, (booking_id,))


def create_invoice(booking_id, total_amount, due_date=None, notes=''):
    return db.fetchone("""
        INSERT INTO invoices (inv_booking_id, inv_total_amount, inv_due_date, inv_notes)
        VALUES (%s, %s, %s, %s)
        RETURNING inv_id AS id, inv_invoice_ref AS invoice_ref
    """, (booking_id, total_amount, due_date, notes))


def update_invoice_status(invoice_id, status):
    db.execute("""
        UPDATE invoices
        SET inv_status = %s, inv_updated_at = NOW()
        WHERE inv_id = %s
    """, (status, invoice_id))


# ─────────────────────────────────────────────
# PAYMENT RECORDS
# ─────────────────────────────────────────────

def get_payment_records(invoice_id):
    return db.fetchall("""
        SELECT pr_id           AS id,
               pr_invoice_id   AS invoice_id,
               pr_amount       AS amount,
               pr_payment_date AS payment_date,
               pr_method       AS method,
               pr_reference_no AS reference_no,
               pr_notes        AS notes,
               pr_created_at   AS created_at
        FROM payment_records
        WHERE pr_invoice_id = %s
        ORDER BY pr_payment_date DESC
    """, (invoice_id,))


def add_payment_record(invoice_id, amount, method, payment_date=None, reference_no='', notes=''):
    row = db.fetchone("""
        INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_method, pr_payment_date, pr_reference_no, pr_notes)
        VALUES (%s, %s, %s, COALESCE(%s, CURRENT_DATE), %s, %s)
        RETURNING pr_id AS id
    """, (invoice_id, amount, method, payment_date, reference_no, notes))

    db.execute("""
        UPDATE invoices
        SET inv_amount_paid = inv_amount_paid + %s,
            inv_status = CASE
                WHEN inv_amount_paid + %s >= inv_total_amount THEN 'Paid'
                WHEN inv_amount_paid + %s > 0 THEN 'Partial'
                ELSE inv_status
            END,
            inv_updated_at = NOW()
        WHERE inv_id = %s
    """, (amount, amount, amount, invoice_id))
    return row


def get_all_payment_records():
    return db.fetchall("""
        SELECT pr.pr_id           AS id,
               pr.pr_invoice_id   AS invoice_id,
               inv.inv_invoice_ref AS invoice_ref,
               b.bk_customer_name  AS customer_name,
               pr.pr_amount        AS amount,
               pr.pr_payment_date  AS payment_date,
               pr.pr_method        AS method,
               pr.pr_reference_no  AS reference_no,
               pr.pr_notes         AS notes,
               pr.pr_created_at    AS created_at
        FROM payment_records pr
        JOIN invoices inv ON inv.inv_id = pr.pr_invoice_id
        JOIN bookings b ON b.bk_id = inv.inv_booking_id
        ORDER BY pr.pr_payment_date DESC
    """)


# ─────────────────────────────────────────────
# KITCHEN ORDERS
# ─────────────────────────────────────────────

def get_all_kitchen_orders():
    return db.fetchall("""
        SELECT ko.ko_id          AS id,
               ko.ko_order_ref   AS order_ref,
               ko.ko_booking_id  AS booking_id,
               ko.ko_client_name AS client_name,
               ko.ko_event_name  AS event_name,
               ko.ko_pax         AS pax,
               ko.ko_items_desc  AS items_desc,
               ko.ko_status      AS status,
               ko.ko_created_at  AS created_at,
               ko.ko_updated_at  AS updated_at,
               COALESCE(
                   (SELECT json_agg(json_build_object(
                       'id',         kt.kt_id,
                       'task_label', kt.kt_task_label,
                       'is_done',    kt.kt_is_done,
                       'sort_order', kt.kt_sort_order
                   ) ORDER BY kt.kt_sort_order)
                    FROM kitchen_tasks kt WHERE kt.kt_order_id = ko.ko_id),
                   '[]'::json
               ) AS tasks
        FROM kitchen_orders ko
        ORDER BY ko.ko_created_at DESC
    """)


def get_kitchen_order_by_id(order_id):
    rows = db.fetchall("""
        SELECT ko_id          AS id,
               ko_order_ref   AS order_ref,
               ko_booking_id  AS booking_id,
               ko_client_name AS client_name,
               ko_event_name  AS event_name,
               ko_pax         AS pax,
               ko_items_desc  AS items_desc,
               ko_status      AS status,
               ko_created_at  AS created_at,
               ko_updated_at  AS updated_at
        FROM kitchen_orders
        WHERE ko_id = %s
    """, (order_id,))
    return rows[0] if rows else None


def create_kitchen_order(booking_id, client_name, event_name, pax, items_desc):
    return db.fetchone("""
        INSERT INTO kitchen_orders (ko_booking_id, ko_client_name, ko_event_name, ko_pax, ko_items_desc)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING ko_id AS id, ko_order_ref AS order_ref
    """, (booking_id, client_name, event_name, pax, items_desc))


def update_kitchen_order_status(order_id, status):
    db.execute("""
        UPDATE kitchen_orders
        SET ko_status = %s, ko_updated_at = NOW()
        WHERE ko_id = %s
    """, (status, order_id))


def get_kitchen_tasks(order_id):
    return db.fetchall("""
        SELECT kt_id         AS id,
               kt_order_id   AS order_id,
               kt_task_label AS task_label,
               kt_is_done    AS is_done,
               kt_sort_order AS sort_order,
               kt_updated_at AS updated_at
        FROM kitchen_tasks
        WHERE kt_order_id = %s
        ORDER BY kt_sort_order
    """, (order_id,))


def add_kitchen_task(order_id, task_label, sort_order=0):
    return db.fetchone("""
        INSERT INTO kitchen_tasks (kt_order_id, kt_task_label, kt_sort_order)
        VALUES (%s, %s, %s)
        RETURNING kt_id AS id
    """, (order_id, task_label, sort_order))


def toggle_kitchen_task(task_id, is_done):
    db.execute("""
        UPDATE kitchen_tasks
        SET kt_is_done = %s, kt_updated_at = NOW()
        WHERE kt_id = %s
    """, (is_done, task_id))


def delete_kitchen_task(task_id):
    db.execute("DELETE FROM kitchen_tasks WHERE kt_id = %s", (task_id,))


# ─────────────────────────────────────────────
# EXPENSES
# ─────────────────────────────────────────────

def get_all_expenses():
    return db.fetchall("""
        SELECT exp_id          AS id,
               exp_category    AS category,
               exp_description AS description,
               exp_amount      AS amount,
               exp_expense_date AS expense_date,
               exp_created_at  AS created_at,
               exp_updated_at  AS updated_at
        FROM expenses
        ORDER BY exp_expense_date DESC
    """)


def add_expense(category, description, amount, expense_date=None):
    return db.fetchone("""
        INSERT INTO expenses (exp_category, exp_description, exp_amount, exp_expense_date)
        VALUES (%s, %s, %s, COALESCE(%s, CURRENT_DATE))
        RETURNING exp_id AS id
    """, (category, description, amount, expense_date))


def update_expense(expense_id, category, description, amount, expense_date):
    db.execute("""
        UPDATE expenses
        SET exp_category    = %s,
            exp_description = %s,
            exp_amount      = %s,
            exp_expense_date = %s,
            exp_updated_at  = NOW()
        WHERE exp_id = %s
    """, (category, description, amount, expense_date, expense_id))


def delete_expense(expense_id):
    db.execute("DELETE FROM expenses WHERE exp_id = %s", (expense_id,))


# ─────────────────────────────────────────────
# CUSTOMER FOLLOW-UPS
# ─────────────────────────────────────────────

def get_follow_ups(customer_id=None):
    if customer_id:
        return db.fetchall("""
            SELECT cfu_id            AS id,
                   cfu_customer_id   AS customer_id,
                   cfu_follow_up_date AS follow_up_date,
                   cfu_note          AS note,
                   cfu_is_done       AS is_done,
                   cfu_created_at    AS created_at,
                   cfu_updated_at    AS updated_at
            FROM customer_follow_ups
            WHERE cfu_customer_id = %s
            ORDER BY cfu_follow_up_date DESC
        """, (customer_id,))
    return db.fetchall("""
        SELECT cfu.cfu_id            AS id,
               cfu.cfu_customer_id   AS customer_id,
               c.cus_name            AS customer_name,
               cfu.cfu_follow_up_date AS follow_up_date,
               cfu.cfu_note          AS note,
               cfu.cfu_is_done       AS is_done,
               cfu.cfu_created_at    AS created_at
        FROM customer_follow_ups cfu
        JOIN customers c ON c.cus_id = cfu.cfu_customer_id
        ORDER BY cfu.cfu_follow_up_date DESC
    """)


def add_follow_up(customer_id, follow_up_date, note):
    return db.fetchone("""
        INSERT INTO customer_follow_ups (cfu_customer_id, cfu_follow_up_date, cfu_note)
        VALUES (%s, %s, %s)
        RETURNING cfu_id AS id
    """, (customer_id, follow_up_date, note))


def toggle_follow_up(follow_up_id, is_done):
    db.execute("""
        UPDATE customer_follow_ups
        SET cfu_is_done = %s, cfu_updated_at = NOW()
        WHERE cfu_id = %s
    """, (is_done, follow_up_id))


def delete_follow_up(follow_up_id):
    db.execute("DELETE FROM customer_follow_ups WHERE cfu_id = %s", (follow_up_id,))


# ─────────────────────────────────────────────
# COMMUNICATION LOGS
# ─────────────────────────────────────────────

def add_communication_log(log_type, method, recipient, status, note='', booking_id=None, invoice_id=None):
    db.execute("""
        INSERT INTO communication_logs (cl_log_type, cl_method, cl_recipient, cl_booking_id, cl_invoice_id, cl_status, cl_note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (log_type, method, recipient, booking_id, invoice_id, status, note))


def get_communication_logs(booking_id=None):
    if booking_id:
        return db.fetchall("""
            SELECT cl_id         AS id,
                   cl_log_type   AS log_type,
                   cl_method     AS method,
                   cl_recipient  AS recipient,
                   cl_booking_id AS booking_id,
                   cl_invoice_id AS invoice_id,
                   cl_status     AS status,
                   cl_note       AS note,
                   cl_created_at AS created_at
            FROM communication_logs
            WHERE cl_booking_id = %s
            ORDER BY cl_created_at DESC
        """, (booking_id,))
    return db.fetchall("""
        SELECT cl_id         AS id,
               cl_log_type   AS log_type,
               cl_method     AS method,
               cl_recipient  AS recipient,
               cl_booking_id AS booking_id,
               cl_invoice_id AS invoice_id,
               cl_status     AS status,
               cl_note       AS note,
               cl_created_at AS created_at
        FROM communication_logs
        ORDER BY cl_created_at DESC
    """)


# ─────────────────────────────────────────────
# AUDIT LOGS
# ─────────────────────────────────────────────

def add_audit_log(actor, action, table_name, record_id, old_value=None, new_value=None):
    db.execute("""
        INSERT INTO audit_logs (al_actor, al_action, al_table_name, al_record_id, al_old_value, al_new_value)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (actor, action, table_name, record_id, old_value, new_value))


def get_audit_logs(table_name=None, record_id=None):
    if table_name and record_id:
        return db.fetchall("""
            SELECT al_id         AS id,
                   al_actor      AS actor,
                   al_action     AS action,
                   al_table_name AS table_name,
                   al_record_id  AS record_id,
                   al_old_value  AS old_value,
                   al_new_value  AS new_value,
                   al_created_at AS created_at
            FROM audit_logs
            WHERE al_table_name = %s AND al_record_id = %s
            ORDER BY al_created_at DESC
        """, (table_name, record_id))
    return db.fetchall("""
        SELECT al_id         AS id,
               al_actor      AS actor,
               al_action     AS action,
               al_table_name AS table_name,
               al_record_id  AS record_id,
               al_old_value  AS old_value,
               al_new_value  AS new_value,
               al_created_at AS created_at
        FROM audit_logs
        ORDER BY al_created_at DESC
        LIMIT 500
    """)


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

def get_all_notifications(unread_only=False):
    if unread_only:
        return db.fetchall("""
            SELECT notif_id         AS id,
                   notif_type       AS type,
                   notif_title      AS title,
                   notif_message    AS message,
                   notif_color      AS color,
                   notif_is_read    AS is_read,
                   notif_created_at AS created_at
            FROM notifications
            WHERE notif_is_read = FALSE
            ORDER BY notif_created_at DESC
        """)
    return db.fetchall("""
        SELECT notif_id         AS id,
               notif_type       AS type,
               notif_title      AS title,
               notif_message    AS message,
               notif_color      AS color,
               notif_is_read    AS is_read,
               notif_created_at AS created_at
        FROM notifications
        ORDER BY notif_created_at DESC
        LIMIT 100
    """)


def push_notification(notif_type, title, message, color='#3B82F6'):
    db.execute("""
        INSERT INTO notifications (notif_type, notif_title, notif_message, notif_color)
        VALUES (%s, %s, %s, %s)
    """, (notif_type, title, message, color))


def mark_notification_read(notif_id):
    db.execute("UPDATE notifications SET notif_is_read = TRUE WHERE notif_id = %s", (notif_id,))


def mark_all_notifications_read():
    db.execute("UPDATE notifications SET notif_is_read = TRUE WHERE notif_is_read = FALSE")


def get_unread_notification_count():
    row = db.fetchone("SELECT COUNT(*) AS cnt FROM notifications WHERE notif_is_read = FALSE")
    return row['cnt'] if row else 0


def get_event_alert_candidates():
    return db.fetchall("""
        SELECT bk_id            AS id,
               bk_booking_ref  AS booking_ref,
               bk_customer_name AS customer_name,
               bk_event_date   AS event_date,
               bk_event_time   AS event_time,
               bk_occasion     AS occasion,
               bk_pax          AS pax,
               bk_status       AS status,
               (bk_event_date - CURRENT_DATE) AS days_until_event
        FROM bookings
        WHERE bk_status IN ('CONFIRMED', 'PENDING')
          AND bk_event_date >= CURRENT_DATE
          AND bk_event_date <= CURRENT_DATE + INTERVAL '7 days'
        ORDER BY bk_event_date
    """)


# ─────────────────────────────────────────────
# CALENDAR EVENTS
# ─────────────────────────────────────────────

def get_all_calendar_events():
    return db.fetchall("""
        SELECT ce_id         AS id,
               ce_event_date AS event_date,
               ce_name       AS name,
               ce_pax        AS pax,
               ce_event_time AS event_time,
               ce_location   AS location,
               ce_created_at AS created_at
        FROM calendar_events
        ORDER BY ce_event_date, ce_event_time
    """)


def get_calendar_events_for_month(year, month):
    return db.fetchall("""
        SELECT ce_id         AS id,
               ce_event_date AS event_date,
               ce_name       AS name,
               ce_pax        AS pax,
               ce_event_time AS event_time,
               ce_location   AS location
        FROM calendar_events
        WHERE EXTRACT(YEAR FROM ce_event_date) = %s
          AND EXTRACT(MONTH FROM ce_event_date) = %s
        ORDER BY ce_event_date, ce_event_time
    """, (year, month))


def add_calendar_event(event_date, name, pax=0, event_time=None, location=''):
    return db.fetchone("""
        INSERT INTO calendar_events (ce_event_date, ce_name, ce_pax, ce_event_time, ce_location)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING ce_id AS id
    """, (event_date, name, pax, event_time, location))


def delete_calendar_event(event_id):
    db.execute("DELETE FROM calendar_events WHERE ce_id = %s", (event_id,))


# ─────────────────────────────────────────────
# OCCASIONS
# ─────────────────────────────────────────────

def get_all_occasions():
    return db.fetchall("""
        SELECT occ_id         AS id,
               occ_name       AS name,
               occ_created_at AS created_at
        FROM occasions
        ORDER BY occ_name
    """)


def add_occasion(name):
    return db.fetchone("""
        INSERT INTO occasions (occ_name)
        VALUES (%s)
        ON CONFLICT (occ_name) DO NOTHING
        RETURNING occ_id AS id
    """, (name,))


def delete_occasion(occasion_id):
    db.execute("DELETE FROM occasions WHERE occ_id = %s", (occasion_id,))


# ─────────────────────────────────────────────
# ADDRESSES
# ─────────────────────────────────────────────

def get_address_regions():
    return db.fetchall("SELECT ar_id AS id, ar_name AS name FROM address_regions ORDER BY ar_name")


def get_address_provinces(region_id=None):
    if region_id:
        return db.fetchall(
            "SELECT ap_id AS id, ap_region_id AS region_id, ap_name AS name FROM address_provinces WHERE ap_region_id = %s ORDER BY ap_name",
            (region_id,)
        )
    return db.fetchall("SELECT ap_id AS id, ap_region_id AS region_id, ap_name AS name FROM address_provinces ORDER BY ap_name")


def get_address_cities(province_id=None):
    if province_id:
        return db.fetchall(
            "SELECT ac_id AS id, ac_province_id AS province_id, ac_name AS name FROM address_cities WHERE ac_province_id = %s ORDER BY ac_name",
            (province_id,)
        )
    return db.fetchall("SELECT ac_id AS id, ac_province_id AS province_id, ac_name AS name FROM address_cities ORDER BY ac_name")


def get_address_barangays(city_id=None):
    if city_id:
        return db.fetchall(
            "SELECT ab_id AS id, ab_city_id AS city_id, ab_name AS name FROM address_barangays WHERE ab_city_id = %s ORDER BY ab_name",
            (city_id,)
        )
    return db.fetchall("SELECT ab_id AS id, ab_city_id AS city_id, ab_name AS name FROM address_barangays ORDER BY ab_name")


def save_address(region_id, province_id, city_id, barangay_id, street=''):
    return db.fetchone("""
        INSERT INTO addresses (addr_region_id, addr_province_id, addr_city_id, addr_barangay_id, addr_street)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING addr_id AS id
    """, (region_id, province_id, city_id, barangay_id, street))


def get_address_by_id(address_id):
    rows = db.fetchall("""
        SELECT a.addr_id          AS id,
               a.addr_region_id   AS region_id,
               r.ar_name          AS region,
               a.addr_province_id AS province_id,
               p.ap_name          AS province,
               a.addr_city_id     AS city_id,
               c.ac_name          AS city,
               a.addr_barangay_id AS barangay_id,
               b.ab_name          AS barangay,
               a.addr_street      AS street
        FROM addresses a
        LEFT JOIN address_regions r   ON r.ar_id = a.addr_region_id
        LEFT JOIN address_provinces p ON p.ap_id = a.addr_province_id
        LEFT JOIN address_cities c    ON c.ac_id = a.addr_city_id
        LEFT JOIN address_barangays b ON b.ab_id = a.addr_barangay_id
        WHERE a.addr_id = %s
    """, (address_id,))
    return rows[0] if rows else None


def link_customer_address(customer_id, address_id):
    db.execute("""
        UPDATE customers SET cus_address_id = %s, cus_updated_at = NOW()
        WHERE cus_id = %s
    """, (address_id, customer_id))


# ─────────────────────────────────────────────
# DASHBOARD KPIs
# ─────────────────────────────────────────────

def get_dashboard_kpis():
    row = db.fetchone("""
        SELECT
            COUNT(*) FILTER (WHERE bk_status IN ('CONFIRMED','COMPLETED')) AS total_bookings,
            COUNT(*) FILTER (WHERE bk_status = 'CONFIRMED')                AS confirmed,
            COUNT(*) FILTER (WHERE bk_status = 'PENDING')                  AS pending,
            COUNT(*) FILTER (WHERE bk_status = 'CANCELLED')                AS cancelled,
            COALESCE(SUM(CASE WHEN bk_status IN ('CONFIRMED','COMPLETED') THEN bk_total_amount ELSE 0 END), 0) AS total_revenue,
            COUNT(*) FILTER (WHERE bk_status IN ('CONFIRMED','PENDING')
                             AND bk_event_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days') AS upcoming
        FROM bookings
    """)
    return row or {
        'total_bookings': 0, 'confirmed': 0, 'pending': 0,
        'cancelled': 0, 'total_revenue': 0.0, 'upcoming': 0
    }


def get_recent_activity(limit=10):
    return db.fetchall("""
        SELECT title, description, color, created_at
        FROM v_recent_activity
        LIMIT %s
    """, (limit,))


def get_upcoming_events_dashboard(days=7):
    return db.fetchall("""
        SELECT bk_id            AS id,
               bk_booking_ref  AS booking_ref,
               bk_customer_name AS customer_name,
               bk_event_date   AS event_date,
               bk_event_time   AS event_time,
               bk_occasion     AS occasion,
               bk_pax          AS pax,
               bk_venue        AS venue,
               bk_status       AS status
        FROM bookings
        WHERE bk_event_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '%s days'
          AND bk_status IN ('PENDING','CONFIRMED')
        ORDER BY bk_event_date, bk_event_time
    """, (days,))


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────

def get_report_kpis():
    return db.fetchone("SELECT * FROM v_report_kpis")


def get_monthly_income(year=None):
    if year:
        return db.fetchall("""
            SELECT TO_CHAR(inv_created_at, 'Mon') AS month,
                   EXTRACT(MONTH FROM inv_created_at)::INT AS month_num,
                   SUM(inv_total_amount) AS income
            FROM invoices
            WHERE EXTRACT(YEAR FROM inv_created_at) = %s
            GROUP BY TO_CHAR(inv_created_at, 'Mon'), EXTRACT(MONTH FROM inv_created_at)
            ORDER BY month_num
        """, (year,))
    return db.fetchall("""
        SELECT TO_CHAR(inv_created_at, 'Mon YYYY') AS month,
               TO_CHAR(inv_created_at, 'YYYY-MM')  AS month_key,
               SUM(inv_total_amount) AS income
        FROM invoices
        GROUP BY TO_CHAR(inv_created_at, 'Mon YYYY'), TO_CHAR(inv_created_at, 'YYYY-MM')
        ORDER BY month_key DESC
        LIMIT 12
    """)


def get_payment_methods():
    return db.fetchall("SELECT method, total FROM v_payment_methods ORDER BY total DESC")


def get_top_menu_items():
    return db.fetchall("SELECT item, order_count FROM v_top_menu_items")


def get_customer_order_frequency():
    return db.fetchall("SELECT name, booking_count FROM v_customer_order_frequency")


def get_top_locations(limit=5):
    return db.fetchall("""
        SELECT bk_venue AS venue, COUNT(*) AS event_count
        FROM bookings
        WHERE bk_status IN ('CONFIRMED','COMPLETED')
          AND bk_venue IS NOT NULL AND bk_venue != ''
        GROUP BY bk_venue
        ORDER BY event_count DESC
        LIMIT %s
    """, (limit,))


def get_top_occasions(limit=5):
    return db.fetchall("""
        SELECT bk_occasion AS occasion, COUNT(*) AS event_count
        FROM bookings
        WHERE bk_status IN ('CONFIRMED','COMPLETED')
          AND bk_occasion IS NOT NULL AND bk_occasion != ''
        GROUP BY bk_occasion
        ORDER BY event_count DESC
        LIMIT %s
    """, (limit,))


def get_profit_summary(date_from=None, date_to=None):
    if date_from and date_to:
        return db.fetchone("""
            SELECT
                COALESCE(SUM(inv_total_amount), 0) AS total_revenue,
                COALESCE((SELECT SUM(exp_amount) FROM expenses
                          WHERE exp_expense_date BETWEEN %s AND %s), 0) AS total_expenses,
                COALESCE(SUM(inv_total_amount), 0) -
                COALESCE((SELECT SUM(exp_amount) FROM expenses
                          WHERE exp_expense_date BETWEEN %s AND %s), 0) AS net_profit
            FROM invoices
            WHERE inv_created_at::DATE BETWEEN %s AND %s
              AND inv_status IN ('Paid','Partial')
        """, (date_from, date_to, date_from, date_to, date_from, date_to))
    return db.fetchone("""
        SELECT
            COALESCE(SUM(inv_total_amount), 0) AS total_revenue,
            COALESCE((SELECT SUM(exp_amount) FROM expenses), 0) AS total_expenses,
            COALESCE(SUM(inv_total_amount), 0) -
            COALESCE((SELECT SUM(exp_amount) FROM expenses), 0) AS net_profit
        FROM invoices
        WHERE inv_status IN ('Paid','Partial')
    """)


def get_bookings_report(date_from=None, date_to=None, status=None):
    conditions = []
    params = []

    if date_from:
        conditions.append("bk_event_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("bk_event_date <= %s")
        params.append(date_to)
    if status:
        conditions.append("bk_status = %s")
        params.append(status)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    return db.fetchall(f"""
        SELECT bk_id            AS id,
               bk_booking_ref  AS booking_ref,
               bk_customer_name AS customer_name,
               bk_occasion     AS occasion,
               bk_event_date   AS event_date,
               bk_pax          AS pax,
               bk_total_amount AS total_amount,
               bk_amount_paid  AS amount_paid,
               bk_balance      AS balance,
               bk_status       AS status
        FROM bookings
        {where}
        ORDER BY bk_event_date DESC
    """, params if params else None)


def get_sms_config():
    row = db.fetchone("SELECT bi_name AS name, bi_contact AS contact FROM business_info LIMIT 1")
    return row


def get_policy():
    row = db.fetchone("""
        SELECT bi_name AS name FROM business_info LIMIT 1
    """)
    return row


def get_customer_ledger(customer_id):
    return db.fetchall("""
        SELECT b.bk_id            AS booking_id,
               b.bk_booking_ref  AS booking_ref,
               b.bk_event_date   AS event_date,
               b.bk_occasion     AS occasion,
               inv.inv_invoice_ref AS invoice_ref,
               inv.inv_total_amount AS total_amount,
               inv.inv_amount_paid  AS amount_paid,
               inv.inv_balance      AS balance,
               inv.inv_status       AS status
        FROM bookings b
        LEFT JOIN invoices inv ON inv.inv_booking_id = b.bk_id
        WHERE b.bk_customer_id = %s
        ORDER BY b.bk_event_date DESC
    """, (customer_id,))
