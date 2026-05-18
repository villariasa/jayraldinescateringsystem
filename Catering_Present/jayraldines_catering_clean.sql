-- ============================================================
-- Jayraldines Catering System — Clean Schema (Prefixed Columns)
-- ============================================================

-- ENUMs
DO $$ BEGIN
    CREATE TYPE booking_status AS ENUM ('PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE invoice_status AS ENUM ('Unpaid', 'Partial', 'Paid');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE customer_status AS ENUM ('Active', 'Inactive');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE loyalty_tier AS ENUM ('Bronze', 'Silver', 'Gold', 'Platinum');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE kitchen_order_status AS ENUM ('Pending', 'In Progress', 'Done');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notification_type AS ENUM ('booking', 'invoice', 'kitchen', 'alert', 'system');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE payment_mode_type AS ENUM ('Cash', 'GCash', 'Bank Transfer', 'Check', 'Other');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Sequences
CREATE SEQUENCE IF NOT EXISTS seq_booking_ref START 1;
CREATE SEQUENCE IF NOT EXISTS seq_invoice_ref START 1;
CREATE SEQUENCE IF NOT EXISTS seq_order_ref START 1;

-- ============================================================
-- TABLE: business_info
-- ============================================================
CREATE TABLE IF NOT EXISTS business_info (
    bi_id           SERIAL PRIMARY KEY,
    bi_name         VARCHAR(255) NOT NULL DEFAULT '',
    bi_address      TEXT NOT NULL DEFAULT '',
    bi_contact      VARCHAR(50) NOT NULL DEFAULT '',
    bi_email        VARCHAR(255) NOT NULL DEFAULT '',
    bi_logo_path    TEXT NOT NULL DEFAULT '',
    bi_updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE: address_regions
-- ============================================================
CREATE TABLE IF NOT EXISTS address_regions (
    ar_id   SERIAL PRIMARY KEY,
    ar_name VARCHAR(255) NOT NULL
);

-- ============================================================
-- TABLE: address_provinces
-- ============================================================
CREATE TABLE IF NOT EXISTS address_provinces (
    ap_id        SERIAL PRIMARY KEY,
    ap_region_id INT NOT NULL REFERENCES address_regions(ar_id) ON DELETE CASCADE,
    ap_name      VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ap_region_id ON address_provinces(ap_region_id);

-- ============================================================
-- TABLE: address_cities
-- ============================================================
CREATE TABLE IF NOT EXISTS address_cities (
    ac_id          SERIAL PRIMARY KEY,
    ac_province_id INT NOT NULL REFERENCES address_provinces(ap_id) ON DELETE CASCADE,
    ac_name        VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ac_province_id ON address_cities(ac_province_id);

-- ============================================================
-- TABLE: address_barangays
-- ============================================================
CREATE TABLE IF NOT EXISTS address_barangays (
    ab_id      SERIAL PRIMARY KEY,
    ab_city_id INT NOT NULL REFERENCES address_cities(ac_id) ON DELETE CASCADE,
    ab_name    VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ab_city_id ON address_barangays(ab_city_id);

-- ============================================================
-- TABLE: addresses
-- ============================================================
CREATE TABLE IF NOT EXISTS addresses (
    addr_id          SERIAL PRIMARY KEY,
    addr_region_id   INT REFERENCES address_regions(ar_id) ON DELETE SET NULL,
    addr_province_id INT REFERENCES address_provinces(ap_id) ON DELETE SET NULL,
    addr_city_id     INT REFERENCES address_cities(ac_id) ON DELETE SET NULL,
    addr_barangay_id INT REFERENCES address_barangays(ab_id) ON DELETE SET NULL,
    addr_street      TEXT NOT NULL DEFAULT '',
    addr_created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_addr_region_id   ON addresses(addr_region_id);
CREATE INDEX IF NOT EXISTS idx_addr_province_id ON addresses(addr_province_id);
CREATE INDEX IF NOT EXISTS idx_addr_city_id     ON addresses(addr_city_id);
CREATE INDEX IF NOT EXISTS idx_addr_barangay_id ON addresses(addr_barangay_id);

-- ============================================================
-- TABLE: occasions
-- ============================================================
CREATE TABLE IF NOT EXISTS occasions (
    occ_id         SERIAL PRIMARY KEY,
    occ_name       VARCHAR(100) NOT NULL UNIQUE,
    occ_created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE: customers
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    cus_id                  SERIAL PRIMARY KEY,
    cus_name                VARCHAR(255) NOT NULL,
    cus_contact             VARCHAR(50)  NOT NULL DEFAULT '',
    cus_email               VARCHAR(255) NOT NULL DEFAULT '',
    cus_address             TEXT         NOT NULL DEFAULT '',
    cus_occasion_preference VARCHAR(100)          DEFAULT NULL,
    cus_notes               TEXT                  DEFAULT NULL,
    cus_loyalty_tier        loyalty_tier NOT NULL DEFAULT 'Bronze',
    cus_status              customer_status NOT NULL DEFAULT 'Active',
    cus_address_id          INT                   DEFAULT NULL REFERENCES addresses(addr_id) ON DELETE SET NULL,
    cus_created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    cus_updated_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cus_status      ON customers(cus_status);
CREATE INDEX IF NOT EXISTS idx_cus_loyalty_tier ON customers(cus_loyalty_tier);
CREATE INDEX IF NOT EXISTS idx_cus_address_id  ON customers(cus_address_id);

-- ============================================================
-- TABLE: packages
-- ============================================================
CREATE TABLE IF NOT EXISTS packages (
    pkg_id            SERIAL PRIMARY KEY,
    pkg_name          VARCHAR(100) NOT NULL UNIQUE,
    pkg_description   TEXT                  DEFAULT NULL,
    pkg_base_price    NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    pkg_per_head_price NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    pkg_min_pax       INT          NOT NULL DEFAULT 1,
    pkg_is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    pkg_created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    pkg_updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE: menu_items
-- ============================================================
CREATE TABLE IF NOT EXISTS menu_items (
    mi_id           SERIAL PRIMARY KEY,
    mi_name         VARCHAR(255)  NOT NULL,
    mi_description  TEXT                   DEFAULT NULL,
    mi_category     VARCHAR(100)  NOT NULL DEFAULT 'Uncategorized',
    mi_price        NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    mi_package_tier VARCHAR(50)            DEFAULT NULL,
    mi_is_active    BOOLEAN       NOT NULL DEFAULT TRUE,
    mi_created_at   TIMESTAMP     NOT NULL DEFAULT NOW(),
    mi_updated_at   TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mi_category    ON menu_items(mi_category);
CREATE INDEX IF NOT EXISTS idx_mi_is_active   ON menu_items(mi_is_active);

-- ============================================================
-- TABLE: package_items
-- ============================================================
CREATE TABLE IF NOT EXISTS package_items (
    pi_id         SERIAL PRIMARY KEY,
    pi_package_id INT NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
    pi_item_id    INT NOT NULL REFERENCES menu_items(mi_id) ON DELETE CASCADE,
    UNIQUE (pi_package_id, pi_item_id)
);

CREATE INDEX IF NOT EXISTS idx_pi_package_id ON package_items(pi_package_id);
CREATE INDEX IF NOT EXISTS idx_pi_item_id    ON package_items(pi_item_id);

-- ============================================================
-- TABLE: bookings
-- ============================================================
CREATE TABLE IF NOT EXISTS bookings (
    bk_id             SERIAL PRIMARY KEY,
    bk_booking_ref    VARCHAR(50)    NOT NULL UNIQUE DEFAULT ('BK-' || LPAD(nextval('seq_booking_ref')::TEXT, 6, '0')),
    bk_customer_id    INT                     DEFAULT NULL REFERENCES customers(cus_id) ON DELETE SET NULL,
    bk_customer_name  VARCHAR(255)   NOT NULL,
    bk_contact        VARCHAR(50)    NOT NULL DEFAULT '',
    bk_email          VARCHAR(255)   NOT NULL DEFAULT '',
    bk_address        TEXT           NOT NULL DEFAULT '',
    bk_occasion       VARCHAR(100)            DEFAULT NULL,
    bk_venue          TEXT                    DEFAULT NULL,
    bk_event_date     DATE           NOT NULL,
    bk_event_time     TIME                    DEFAULT NULL,
    bk_pax            INT            NOT NULL DEFAULT 1,
    bk_special_notes  TEXT                    DEFAULT NULL,
    bk_menu_type      VARCHAR(50)             DEFAULT NULL,
    bk_package_id     INT                     DEFAULT NULL REFERENCES packages(pkg_id) ON DELETE SET NULL,
    bk_total_amount   NUMERIC(12,2)  NOT NULL DEFAULT 0.00,
    bk_payment_mode   payment_mode_type       DEFAULT NULL,
    bk_amount_paid    NUMERIC(12,2)  NOT NULL DEFAULT 0.00,
    bk_balance        NUMERIC(12,2)  GENERATED ALWAYS AS (bk_total_amount - bk_amount_paid) STORED,
    bk_status         booking_status NOT NULL DEFAULT 'PENDING',
    bk_payment_status VARCHAR(50)             DEFAULT 'Unpaid',
    bk_created_at     TIMESTAMP      NOT NULL DEFAULT NOW(),
    bk_updated_at     TIMESTAMP      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bk_customer_id ON bookings(bk_customer_id);
CREATE INDEX IF NOT EXISTS idx_bk_event_date  ON bookings(bk_event_date);
CREATE INDEX IF NOT EXISTS idx_bk_status      ON bookings(bk_status);
CREATE INDEX IF NOT EXISTS idx_bk_package_id  ON bookings(bk_package_id);

-- ============================================================
-- TABLE: booking_menu_items
-- ============================================================
CREATE TABLE IF NOT EXISTS booking_menu_items (
    bmi_id         SERIAL PRIMARY KEY,
    bmi_booking_id INT           NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    bmi_item_id    INT           NOT NULL REFERENCES menu_items(mi_id) ON DELETE CASCADE,
    bmi_quantity   INT           NOT NULL DEFAULT 1,
    bmi_unit_price NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    bmi_subtotal   NUMERIC(12,2) GENERATED ALWAYS AS (bmi_quantity * bmi_unit_price) STORED
);

CREATE INDEX IF NOT EXISTS idx_bmi_booking_id ON booking_menu_items(bmi_booking_id);
CREATE INDEX IF NOT EXISTS idx_bmi_item_id    ON booking_menu_items(bmi_item_id);

-- ============================================================
-- TABLE: invoices
-- ============================================================
CREATE TABLE IF NOT EXISTS invoices (
    inv_id          SERIAL PRIMARY KEY,
    inv_invoice_ref VARCHAR(50)    NOT NULL UNIQUE DEFAULT ('INV-' || LPAD(nextval('seq_invoice_ref')::TEXT, 6, '0')),
    inv_booking_id  INT            NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    inv_total_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    inv_amount_paid  NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    inv_balance      NUMERIC(12,2) GENERATED ALWAYS AS (inv_total_amount - inv_amount_paid) STORED,
    inv_status      invoice_status NOT NULL DEFAULT 'Unpaid',
    inv_due_date    DATE                    DEFAULT NULL,
    inv_notes       TEXT                    DEFAULT NULL,
    inv_created_at  TIMESTAMP      NOT NULL DEFAULT NOW(),
    inv_updated_at  TIMESTAMP      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inv_booking_id ON invoices(inv_booking_id);
CREATE INDEX IF NOT EXISTS idx_inv_status     ON invoices(inv_status);

-- ============================================================
-- TABLE: payment_records
-- ============================================================
CREATE TABLE IF NOT EXISTS payment_records (
    pr_id           SERIAL PRIMARY KEY,
    pr_invoice_id   INT           NOT NULL REFERENCES invoices(inv_id) ON DELETE CASCADE,
    pr_amount       NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    pr_payment_date DATE          NOT NULL DEFAULT CURRENT_DATE,
    pr_method       VARCHAR(50)   NOT NULL DEFAULT 'Cash',
    pr_reference_no VARCHAR(100)           DEFAULT NULL,
    pr_notes        TEXT                   DEFAULT NULL,
    pr_created_at   TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pr_invoice_id   ON payment_records(pr_invoice_id);
CREATE INDEX IF NOT EXISTS idx_pr_payment_date ON payment_records(pr_payment_date);

-- ============================================================
-- TABLE: kitchen_orders
-- ============================================================
CREATE TABLE IF NOT EXISTS kitchen_orders (
    ko_id         SERIAL PRIMARY KEY,
    ko_order_ref  VARCHAR(50)          NOT NULL UNIQUE DEFAULT ('KO-' || LPAD(nextval('seq_order_ref')::TEXT, 6, '0')),
    ko_booking_id INT                           DEFAULT NULL REFERENCES bookings(bk_id) ON DELETE SET NULL,
    ko_client_name VARCHAR(255)         NOT NULL DEFAULT '',
    ko_event_name  VARCHAR(255)         NOT NULL DEFAULT '',
    ko_pax         INT                  NOT NULL DEFAULT 1,
    ko_items_desc  TEXT                          DEFAULT NULL,
    ko_status      kitchen_order_status NOT NULL DEFAULT 'Pending',
    ko_created_at  TIMESTAMP            NOT NULL DEFAULT NOW(),
    ko_updated_at  TIMESTAMP            NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ko_booking_id ON kitchen_orders(ko_booking_id);
CREATE INDEX IF NOT EXISTS idx_ko_status     ON kitchen_orders(ko_status);

-- ============================================================
-- TABLE: kitchen_tasks
-- ============================================================
CREATE TABLE IF NOT EXISTS kitchen_tasks (
    kt_id         SERIAL PRIMARY KEY,
    kt_order_id   INT       NOT NULL REFERENCES kitchen_orders(ko_id) ON DELETE CASCADE,
    kt_task_label TEXT      NOT NULL,
    kt_is_done    BOOLEAN   NOT NULL DEFAULT FALSE,
    kt_sort_order INT       NOT NULL DEFAULT 0,
    kt_updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kt_order_id ON kitchen_tasks(kt_order_id);

-- ============================================================
-- TABLE: expenses
-- ============================================================
CREATE TABLE IF NOT EXISTS expenses (
    exp_id           SERIAL PRIMARY KEY,
    exp_category     VARCHAR(100)  NOT NULL DEFAULT 'General',
    exp_description  TEXT                   DEFAULT NULL,
    exp_amount       NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    exp_expense_date DATE          NOT NULL DEFAULT CURRENT_DATE,
    exp_created_at   TIMESTAMP     NOT NULL DEFAULT NOW(),
    exp_updated_at   TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exp_expense_date ON expenses(exp_expense_date);
CREATE INDEX IF NOT EXISTS idx_exp_category     ON expenses(exp_category);

-- ============================================================
-- TABLE: customer_follow_ups
-- ============================================================
CREATE TABLE IF NOT EXISTS customer_follow_ups (
    cfu_id            SERIAL PRIMARY KEY,
    cfu_customer_id   INT       NOT NULL REFERENCES customers(cus_id) ON DELETE CASCADE,
    cfu_follow_up_date DATE     NOT NULL,
    cfu_note          TEXT               DEFAULT NULL,
    cfu_is_done       BOOLEAN   NOT NULL DEFAULT FALSE,
    cfu_created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    cfu_updated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cfu_customer_id   ON customer_follow_ups(cfu_customer_id);
CREATE INDEX IF NOT EXISTS idx_cfu_follow_up_date ON customer_follow_ups(cfu_follow_up_date);
CREATE INDEX IF NOT EXISTS idx_cfu_is_done       ON customer_follow_ups(cfu_is_done);

-- ============================================================
-- TABLE: communication_logs
-- ============================================================
CREATE TABLE IF NOT EXISTS communication_logs (
    cl_id         SERIAL PRIMARY KEY,
    cl_log_type   VARCHAR(50)  NOT NULL DEFAULT 'email',
    cl_method     VARCHAR(50)  NOT NULL DEFAULT 'email',
    cl_recipient  VARCHAR(255) NOT NULL DEFAULT '',
    cl_booking_id INT                   DEFAULT NULL REFERENCES bookings(bk_id) ON DELETE SET NULL,
    cl_invoice_id INT                   DEFAULT NULL REFERENCES invoices(inv_id) ON DELETE SET NULL,
    cl_status     VARCHAR(50)  NOT NULL DEFAULT 'sent',
    cl_note       TEXT                  DEFAULT NULL,
    cl_created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cl_booking_id ON communication_logs(cl_booking_id);
CREATE INDEX IF NOT EXISTS idx_cl_invoice_id ON communication_logs(cl_invoice_id);

-- ============================================================
-- TABLE: audit_logs
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    al_id         SERIAL PRIMARY KEY,
    al_actor      VARCHAR(255) NOT NULL DEFAULT 'system',
    al_action     VARCHAR(100) NOT NULL,
    al_table_name VARCHAR(100) NOT NULL,
    al_record_id  INT                   DEFAULT NULL,
    al_old_value  JSONB                 DEFAULT NULL,
    al_new_value  JSONB                 DEFAULT NULL,
    al_created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_al_table_name ON audit_logs(al_table_name);
CREATE INDEX IF NOT EXISTS idx_al_record_id  ON audit_logs(al_record_id);
CREATE INDEX IF NOT EXISTS idx_al_created_at ON audit_logs(al_created_at);

-- ============================================================
-- TABLE: notifications
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    notif_id         SERIAL PRIMARY KEY,
    notif_type       notification_type NOT NULL DEFAULT 'system',
    notif_title      VARCHAR(255)      NOT NULL DEFAULT '',
    notif_message    TEXT              NOT NULL DEFAULT '',
    notif_color      VARCHAR(20)       NOT NULL DEFAULT '#3B82F6',
    notif_is_read    BOOLEAN           NOT NULL DEFAULT FALSE,
    notif_created_at TIMESTAMP         NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_is_read    ON notifications(notif_is_read);
CREATE INDEX IF NOT EXISTS idx_notif_created_at ON notifications(notif_created_at DESC);

-- ============================================================
-- TABLE: calendar_events
-- ============================================================
CREATE TABLE IF NOT EXISTS calendar_events (
    ce_id         SERIAL PRIMARY KEY,
    ce_event_date DATE         NOT NULL,
    ce_name       VARCHAR(255) NOT NULL,
    ce_pax        INT                   DEFAULT NULL,
    ce_event_time TIME                  DEFAULT NULL,
    ce_location   TEXT                  DEFAULT NULL,
    ce_created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ce_event_date ON calendar_events(ce_event_date);

-- ============================================================
-- VIEWS
-- ============================================================

CREATE OR REPLACE VIEW v_monthly_income AS
SELECT
    TO_CHAR(DATE_TRUNC('month', inv_created_at), 'Mon YYYY') AS month,
    DATE_TRUNC('month', inv_created_at)                       AS month_date,
    COALESCE(SUM(inv_total_amount), 0)::FLOAT                 AS revenue,
    COALESCE(SUM(inv_amount_paid), 0)::FLOAT                  AS collected,
    COALESCE(SUM(inv_balance), 0)::FLOAT                      AS outstanding
FROM invoices
GROUP BY DATE_TRUNC('month', inv_created_at)
ORDER BY month_date;

CREATE OR REPLACE VIEW v_payment_methods AS
SELECT
    bk_payment_mode::TEXT AS method,
    COUNT(*)              AS total
FROM bookings
WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
  AND bk_payment_mode IS NOT NULL
GROUP BY bk_payment_mode;

CREATE OR REPLACE VIEW v_top_menu_items AS
SELECT
    mi.mi_name AS item,
    COUNT(*)   AS order_count
FROM booking_menu_items bmi
JOIN menu_items mi ON mi.mi_id = bmi.bmi_item_id
JOIN bookings b    ON b.bk_id  = bmi.bmi_booking_id
WHERE b.bk_status IN ('CONFIRMED', 'COMPLETED')
GROUP BY mi.mi_name
ORDER BY order_count DESC
LIMIT 10;

CREATE OR REPLACE VIEW v_customer_order_frequency AS
SELECT name, booking_count FROM (
    SELECT
        bk_customer_name        AS name,
        COUNT(*)                AS booking_count,
        RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
    FROM bookings
    WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
    GROUP BY bk_customer_name
) ranked
WHERE rnk <= 5
UNION ALL
SELECT 'Others', COUNT(*) FROM (
    SELECT bk_customer_name FROM (
        SELECT
            bk_customer_name,
            RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
        FROM bookings
        WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
        GROUP BY bk_customer_name
    ) r WHERE rnk > 5
) rest;

CREATE OR REPLACE VIEW v_report_kpis AS
SELECT
    COUNT(*)                                                                AS total_bookings,
    COALESCE(SUM(b.bk_pax), 0)::INT                                        AS total_pax,
    COALESCE((SELECT SUM(inv_total_amount) FROM invoices), 0)::FLOAT       AS total_revenue,
    COALESCE((SELECT SUM(inv_balance) FROM invoices WHERE inv_status != 'Paid'), 0)::FLOAT AS unpaid_amount,
    COALESCE((SELECT COUNT(*) FROM bookings
              WHERE bk_created_at::DATE = CURRENT_DATE
                AND bk_status IN ('CONFIRMED', 'COMPLETED')), 0)::INT      AS today_bookings,
    COALESCE((SELECT COUNT(*) FROM bookings
              WHERE bk_created_at::DATE BETWEEN DATE_TRUNC('week', CURRENT_DATE)::DATE
                                            AND (DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '6 days')::DATE
                AND bk_status IN ('CONFIRMED', 'COMPLETED')), 0)::INT      AS week_bookings
FROM bookings b
WHERE b.bk_status IN ('CONFIRMED', 'COMPLETED');

CREATE OR REPLACE VIEW v_recent_activity AS
SELECT title, description, color, created_at
FROM (
    SELECT
        CASE bk_status
            WHEN 'CONFIRMED' THEN 'Booking Confirmed'
            WHEN 'CANCELLED' THEN 'Booking Cancelled'
            ELSE 'New Booking Request'
        END                                                          AS title,
        bk_customer_name || ' - ' || COALESCE(bk_occasion, 'Event') ||
            ' (' || bk_pax || ' pax)'                               AS description,
        CASE bk_status
            WHEN 'CONFIRMED' THEN '#22C55E'
            WHEN 'CANCELLED' THEN '#EF4444'
            ELSE '#3B82F6'
        END                                                          AS color,
        bk_created_at                                               AS created_at
    FROM bookings
    UNION ALL
    SELECT
        CASE inv_status
            WHEN 'Paid'    THEN 'Payment Received'
            WHEN 'Partial' THEN 'Partial Payment'
            ELSE 'Invoice Unpaid'
        END                                                          AS title,
        COALESCE(b.bk_customer_name, '') || ' - Invoice ' || i.inv_invoice_ref AS description,
        CASE inv_status
            WHEN 'Paid'    THEN '#22C55E'
            WHEN 'Partial' THEN '#F59E0B'
            ELSE '#EF4444'
        END                                                          AS color,
        i.inv_created_at                                            AS created_at
    FROM invoices i
    LEFT JOIN bookings b ON b.bk_id = i.inv_booking_id
) combined
ORDER BY created_at DESC
LIMIT 10;

CREATE OR REPLACE VIEW v_customer_ledger AS
SELECT
    c.cus_id                                                         AS customer_id,
    c.cus_name                                                       AS customer_name,
    COUNT(DISTINCT b.bk_id)                                          AS total_bookings,
    COALESCE(SUM(DISTINCT i.inv_total_amount), 0)                    AS total_invoiced,
    COALESCE(SUM(DISTINCT i.inv_amount_paid), 0)                     AS total_paid,
    COALESCE(SUM(DISTINCT i.inv_balance), 0)                         AS outstanding_balance
FROM customers c
LEFT JOIN bookings b ON b.bk_customer_id = c.cus_id
LEFT JOIN invoices i ON i.inv_booking_id = b.bk_id
GROUP BY c.cus_id, c.cus_name;

-- ============================================================
-- STORED PROCEDURES
-- ============================================================

-- sp_recalculate_loyalty
CREATE OR REPLACE FUNCTION sp_recalculate_loyalty(p_customer_id INT)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    v_count INT;
    v_tier  loyalty_tier;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM bookings
    WHERE bk_customer_id = p_customer_id
      AND bk_status IN ('CONFIRMED', 'COMPLETED');

    IF    v_count >= 20 THEN v_tier := 'Platinum';
    ELSIF v_count >= 10 THEN v_tier := 'Gold';
    ELSIF v_count >= 5  THEN v_tier := 'Silver';
    ELSE                     v_tier := 'Bronze';
    END IF;

    UPDATE customers
    SET cus_loyalty_tier = v_tier,
        cus_updated_at   = NOW()
    WHERE cus_id = p_customer_id;
END;
$$;

-- sp_update_booking_status
CREATE OR REPLACE PROCEDURE sp_update_booking_status(
    IN p_booking_id          INT,
    IN p_new_status          TEXT,
    IN p_cancellation_reason TEXT DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
    v_current    booking_status;
    v_customer_id INT;
BEGIN
    SELECT bk_status, bk_customer_id
    INTO v_current, v_customer_id
    FROM bookings WHERE bk_id = p_booking_id;

    IF v_current = 'CANCELLED' THEN
        RAISE EXCEPTION 'Cancelled bookings cannot be changed.';
    END IF;

    IF v_current = 'COMPLETED' THEN
        RAISE EXCEPTION 'Completed bookings cannot be changed.';
    END IF;

    IF v_current NOT IN ('PENDING', 'CONFIRMED') THEN
        RAISE EXCEPTION 'Only PENDING or CONFIRMED bookings can be transitioned.';
    END IF;

    IF p_new_status = 'COMPLETED' AND v_current != 'CONFIRMED' THEN
        RAISE EXCEPTION 'Only CONFIRMED bookings can be marked as COMPLETED.';
    END IF;

    UPDATE bookings
    SET bk_status             = p_new_status::booking_status,
        bk_cancellation_reason = CASE WHEN p_new_status = 'CANCELLED'
                                       THEN p_cancellation_reason
                                       ELSE NULL END,
        bk_updated_at          = NOW()
    WHERE bk_id = p_booking_id;

    IF p_new_status = 'CONFIRMED' AND v_customer_id IS NOT NULL THEN
        PERFORM sp_recalculate_loyalty(v_customer_id);
    END IF;
END;
$$;

-- sp_add_booking
CREATE OR REPLACE PROCEDURE sp_add_booking(
    IN p_customer_id    INT,
    IN p_customer_name  TEXT,
    IN p_contact        TEXT,
    IN p_email          TEXT,
    IN p_address        TEXT,
    IN p_occasion       TEXT,
    IN p_venue          TEXT,
    IN p_event_date     DATE,
    IN p_event_time     TIME,
    IN p_pax            INT,
    IN p_special_notes  TEXT,
    IN p_menu_type      TEXT,
    IN p_package_id     INT,
    IN p_total_amount   NUMERIC,
    IN p_payment_mode   TEXT,
    OUT p_booking_id    INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO bookings (
        bk_customer_id, bk_customer_name, bk_contact, bk_email, bk_address,
        bk_occasion, bk_venue, bk_event_date, bk_event_time, bk_pax,
        bk_special_notes, bk_menu_type, bk_package_id, bk_total_amount,
        bk_payment_mode, bk_status
    ) VALUES (
        NULLIF(p_customer_id, 0), p_customer_name, p_contact, p_email, p_address,
        NULLIF(p_occasion, ''), NULLIF(p_venue, ''), p_event_date, p_event_time, p_pax,
        NULLIF(p_special_notes, ''), NULLIF(p_menu_type, ''),
        NULLIF(p_package_id, 0), p_total_amount,
        NULLIF(p_payment_mode, '')::payment_mode_type, 'PENDING'
    )
    RETURNING bk_id INTO p_booking_id;
END;
$$;

-- sp_add_customer
CREATE OR REPLACE PROCEDURE sp_add_customer(
    IN p_name               TEXT,
    IN p_contact            TEXT,
    IN p_email              TEXT,
    IN p_address            TEXT,
    IN p_occasion_preference TEXT,
    IN p_notes              TEXT,
    OUT p_customer_id       INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO customers (
        cus_name, cus_contact, cus_email, cus_address,
        cus_occasion_preference, cus_notes
    ) VALUES (
        p_name, p_contact, p_email, p_address,
        NULLIF(p_occasion_preference, ''), NULLIF(p_notes, '')
    )
    RETURNING cus_id INTO p_customer_id;
END;
$$;

-- sp_update_customer
CREATE OR REPLACE PROCEDURE sp_update_customer(
    IN p_customer_id        INT,
    IN p_name               TEXT,
    IN p_contact            TEXT,
    IN p_email              TEXT,
    IN p_address            TEXT,
    IN p_occasion_preference TEXT,
    IN p_notes              TEXT,
    IN p_status             TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE customers
    SET cus_name                = p_name,
        cus_contact             = p_contact,
        cus_email               = p_email,
        cus_address             = p_address,
        cus_occasion_preference = NULLIF(p_occasion_preference, ''),
        cus_notes               = NULLIF(p_notes, ''),
        cus_status              = p_status::customer_status,
        cus_updated_at          = NOW()
    WHERE cus_id = p_customer_id;
END;
$$;

-- sp_create_invoice
CREATE OR REPLACE PROCEDURE sp_create_invoice(
    IN  p_booking_id    INT,
    IN  p_total_amount  NUMERIC,
    IN  p_due_date      DATE,
    IN  p_notes         TEXT,
    OUT p_invoice_id    INT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_existing INT;
BEGIN
    SELECT inv_id INTO v_existing
    FROM invoices WHERE inv_booking_id = p_booking_id
    LIMIT 1;

    IF v_existing IS NOT NULL THEN
        RAISE EXCEPTION 'An invoice already exists for this booking.';
    END IF;

    INSERT INTO invoices (inv_booking_id, inv_total_amount, inv_due_date, inv_notes)
    VALUES (p_booking_id, p_total_amount, p_due_date, NULLIF(p_notes, ''))
    RETURNING inv_id INTO p_invoice_id;
END;
$$;

-- sp_record_payment
CREATE OR REPLACE PROCEDURE sp_record_payment(
    IN  p_invoice_id    INT,
    IN  p_amount        NUMERIC,
    IN  p_payment_date  DATE,
    IN  p_method        TEXT,
    IN  p_reference_no  TEXT,
    IN  p_notes         TEXT,
    OUT p_payment_id    INT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_balance    NUMERIC;
    v_new_status invoice_status;
    v_new_paid   NUMERIC;
BEGIN
    SELECT inv_balance, inv_amount_paid
    INTO v_balance, v_new_paid
    FROM invoices WHERE inv_id = p_invoice_id;

    IF p_amount > v_balance THEN
        RAISE EXCEPTION 'Payment amount (%) exceeds outstanding balance (%).', p_amount, v_balance;
    END IF;

    INSERT INTO payment_records (
        pr_invoice_id, pr_amount, pr_payment_date, pr_method, pr_reference_no, pr_notes
    ) VALUES (
        p_invoice_id, p_amount, p_payment_date,
        p_method, NULLIF(p_reference_no, ''), NULLIF(p_notes, '')
    )
    RETURNING pr_id INTO p_payment_id;

    v_new_paid := v_new_paid + p_amount;

    IF (v_new_paid) >= (SELECT inv_total_amount FROM invoices WHERE inv_id = p_invoice_id) THEN
        v_new_status := 'Paid';
    ELSIF v_new_paid > 0 THEN
        v_new_status := 'Partial';
    ELSE
        v_new_status := 'Unpaid';
    END IF;

    UPDATE invoices
    SET inv_amount_paid = v_new_paid,
        inv_status      = v_new_status,
        inv_updated_at  = NOW()
    WHERE inv_id = p_invoice_id;

    UPDATE bookings
    SET bk_amount_paid    = v_new_paid,
        bk_payment_status = v_new_status::TEXT,
        bk_updated_at     = NOW()
    WHERE bk_id = (SELECT inv_booking_id FROM invoices WHERE inv_id = p_invoice_id);
END;
$$;

-- sp_create_kitchen_order
CREATE OR REPLACE PROCEDURE sp_create_kitchen_order(
    IN  p_booking_id    INT,
    IN  p_client_name   TEXT,
    IN  p_event_name    TEXT,
    IN  p_pax           INT,
    IN  p_items_desc    TEXT,
    OUT p_order_id      INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO kitchen_orders (
        ko_booking_id, ko_client_name, ko_event_name, ko_pax, ko_items_desc
    ) VALUES (
        NULLIF(p_booking_id, 0), p_client_name, p_event_name, p_pax, NULLIF(p_items_desc, '')
    )
    RETURNING ko_id INTO p_order_id;
END;
$$;

-- sp_update_kitchen_order_status
CREATE OR REPLACE PROCEDURE sp_update_kitchen_order_status(
    IN p_order_id INT,
    IN p_status   TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE kitchen_orders
    SET ko_status     = p_status::kitchen_order_status,
        ko_updated_at = NOW()
    WHERE ko_id = p_order_id;
END;
$$;

-- sp_get_event_alert_candidates
CREATE OR REPLACE FUNCTION sp_get_event_alert_candidates()
RETURNS TABLE (
    booking_id    INT,
    customer_name TEXT,
    event_date    DATE,
    event_time    TIME,
    occasion      TEXT,
    contact       TEXT,
    email         TEXT,
    window_label  TEXT
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        b.bk_id,
        b.bk_customer_name,
        b.bk_event_date,
        b.bk_event_time,
        b.bk_occasion,
        b.bk_contact,
        b.bk_email,
        CASE
            WHEN b.bk_event_date = CURRENT_DATE + 1  THEN '1_day'
            WHEN b.bk_event_date = CURRENT_DATE + 7  THEN '7_days'
            WHEN b.bk_event_date = CURRENT_DATE + 30 THEN '30_days'
        END AS window_label
    FROM bookings b
    WHERE b.bk_status = 'CONFIRMED'
      AND b.bk_event_date IN (
          CURRENT_DATE + 1,
          CURRENT_DATE + 7,
          CURRENT_DATE + 30
      );
END;
$$;

-- sp_push_notification
CREATE OR REPLACE PROCEDURE sp_push_notification(
    IN p_type    TEXT,
    IN p_title   TEXT,
    IN p_message TEXT,
    IN p_color   TEXT DEFAULT '#3B82F6'
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO notifications (notif_type, notif_title, notif_message, notif_color)
    VALUES (p_type::notification_type, p_title, p_message, p_color);
END;
$$;

-- sp_add_menu_item
CREATE OR REPLACE PROCEDURE sp_add_menu_item(
    IN  p_name         TEXT,
    IN  p_description  TEXT,
    IN  p_category     TEXT,
    IN  p_price        NUMERIC,
    IN  p_package_tier TEXT,
    OUT p_item_id      INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO menu_items (mi_name, mi_description, mi_category, mi_price, mi_package_tier)
    VALUES (p_name, NULLIF(p_description,''), p_category, p_price, NULLIF(p_package_tier,''))
    RETURNING mi_id INTO p_item_id;
END;
$$;

-- sp_update_menu_item
CREATE OR REPLACE PROCEDURE sp_update_menu_item(
    IN p_item_id      INT,
    IN p_name         TEXT,
    IN p_description  TEXT,
    IN p_category     TEXT,
    IN p_price        NUMERIC,
    IN p_package_tier TEXT,
    IN p_is_active    BOOLEAN
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE menu_items
    SET mi_name         = p_name,
        mi_description  = NULLIF(p_description,''),
        mi_category     = p_category,
        mi_price        = p_price,
        mi_package_tier = NULLIF(p_package_tier,''),
        mi_is_active    = p_is_active,
        mi_updated_at   = NOW()
    WHERE mi_id = p_item_id;
END;
$$;

-- sp_add_package
CREATE OR REPLACE PROCEDURE sp_add_package(
    IN  p_name            TEXT,
    IN  p_description     TEXT,
    IN  p_base_price      NUMERIC,
    IN  p_per_head_price  NUMERIC,
    IN  p_min_pax         INT,
    OUT p_package_id      INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO packages (pkg_name, pkg_description, pkg_base_price, pkg_per_head_price, pkg_min_pax)
    VALUES (p_name, NULLIF(p_description,''), p_base_price, p_per_head_price, p_min_pax)
    RETURNING pkg_id INTO p_package_id;
END;
$$;

-- sp_update_business_info
CREATE OR REPLACE PROCEDURE sp_update_business_info(
    IN p_name       TEXT,
    IN p_address    TEXT,
    IN p_contact    TEXT,
    IN p_email      TEXT,
    IN p_logo_path  TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM business_info LIMIT 1) THEN
        UPDATE business_info
        SET bi_name       = p_name,
            bi_address    = p_address,
            bi_contact    = p_contact,
            bi_email      = p_email,
            bi_logo_path  = COALESCE(NULLIF(p_logo_path,''), bi_logo_path),
            bi_updated_at = NOW();
    ELSE
        INSERT INTO business_info (bi_name, bi_address, bi_contact, bi_email, bi_logo_path)
        VALUES (p_name, p_address, p_contact, p_email, p_logo_path);
    END IF;
END;
$$;

-- sp_add_occasion
CREATE OR REPLACE PROCEDURE sp_add_occasion(
    IN  p_name       TEXT,
    OUT p_occasion_id INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO occasions (occ_name)
    VALUES (p_name)
    RETURNING occ_id INTO p_occasion_id;
END;
$$;

-- sp_delete_occasion
CREATE OR REPLACE PROCEDURE sp_delete_occasion(IN p_occasion_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM occasions WHERE occ_id = p_occasion_id;
END;
$$;

-- sp_add_expense
CREATE OR REPLACE PROCEDURE sp_add_expense(
    IN  p_category     TEXT,
    IN  p_description  TEXT,
    IN  p_amount       NUMERIC,
    IN  p_expense_date DATE,
    OUT p_expense_id   INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO expenses (exp_category, exp_description, exp_amount, exp_expense_date)
    VALUES (p_category, NULLIF(p_description,''), p_amount, p_expense_date)
    RETURNING exp_id INTO p_expense_id;
END;
$$;

-- sp_auto_create_invoice
CREATE OR REPLACE PROCEDURE sp_auto_create_invoice(IN p_booking_id INT)
LANGUAGE plpgsql AS $$
DECLARE
    v_total     NUMERIC;
    v_due       DATE;
    v_existing  INT;
BEGIN
    SELECT inv_id INTO v_existing
    FROM invoices WHERE inv_booking_id = p_booking_id LIMIT 1;

    IF v_existing IS NOT NULL THEN RETURN; END IF;

    SELECT bk_total_amount, bk_event_date
    INTO v_total, v_due
    FROM bookings WHERE bk_id = p_booking_id;

    INSERT INTO invoices (inv_booking_id, inv_total_amount, inv_due_date)
    VALUES (p_booking_id, v_total, v_due);
END;
$$;

-- Default business_info seed row
INSERT INTO business_info (bi_name, bi_address, bi_contact, bi_email)
VALUES ('Jayraldine''s Catering Services', '', '', '')
ON CONFLICT DO NOTHING;
