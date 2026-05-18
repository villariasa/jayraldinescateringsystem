-- =============================================================================
-- Jayraldine's Catering Management System
-- PostgreSQL Database Schema + Stored Procedures  (CLEAN — no sample data)
-- =============================================================================
-- Run this script once as a PostgreSQL superuser:
--   psql -U postgres -f jayraldines_catering_clean.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DATABASE
-- -----------------------------------------------------------------------------
DROP DATABASE IF EXISTS jayraldines_catering;
CREATE DATABASE jayraldines_catering
    ENCODING    'UTF8'
    LC_COLLATE  'en_US.UTF-8'
    LC_CTYPE    'en_US.UTF-8'
    TEMPLATE    template0;

\connect jayraldines_catering

-- =============================================================================
-- EXTENSIONS
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ENUMERATIONS
-- =============================================================================
CREATE TYPE booking_status    AS ENUM ('PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED');
CREATE TYPE invoice_status    AS ENUM ('Unpaid', 'Partial', 'Paid');
CREATE TYPE customer_status   AS ENUM ('Active', 'Pending', 'Inactive');
CREATE TYPE loyalty_tier      AS ENUM ('Bronze', 'Silver', 'Gold', 'VIP');
CREATE TYPE menu_status       AS ENUM ('Available', 'Unavailable', 'Seasonal', 'Out of Stock');
CREATE TYPE kitchen_status    AS ENUM ('Queued', 'Preparing', 'In Progress', 'Ready', 'Delivered', 'Cancelled', 'Done');
CREATE TYPE payment_method    AS ENUM ('Cash', 'Bank Transfer', 'GCash', 'PayMaya');
CREATE TYPE menu_category     AS ENUM ('Main Course','Noodles','Soup','Vegetables','Dessert','Drinks','Bread','Other');
CREATE TYPE menu_package_tier AS ENUM ('Budget','Standard','Premium','Custom');
CREATE TYPE expense_category  AS ENUM ('Food Cost','Labor','Transport','Utilities','Equipment','Other');

-- =============================================================================
-- TABLE: business_info
-- =============================================================================
CREATE TABLE business_info (
    bi_id                      SERIAL          PRIMARY KEY,
    bi_name                    VARCHAR(120)    NOT NULL DEFAULT 'Jayraldine''s Catering',
    bi_contact                 VARCHAR(30)     NOT NULL,
    bi_email                   VARCHAR(120),
    bi_address                 TEXT,
    bi_smtp_host               VARCHAR(120),
    bi_smtp_port               INT             DEFAULT 587,
    bi_smtp_user               VARCHAR(120),
    bi_smtp_pass               TEXT,
    bi_min_downpayment_pct     NUMERIC(5,2)    NOT NULL DEFAULT 30.00,
    bi_allow_zero_downpayment  BOOLEAN         NOT NULL DEFAULT FALSE,
    bi_max_daily_pax           INT             NOT NULL DEFAULT 600,
    bi_updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Required: exactly one row — update name/contact/address after setup
INSERT INTO business_info (bi_name, bi_contact, bi_email, bi_address)
VALUES ('Jayraldine''s Catering', '+63 912 345 6789', '', '');

-- =============================================================================
-- TABLE: customers
-- =============================================================================
CREATE TABLE customers (
    cus_id              SERIAL          PRIMARY KEY,
    cus_name            VARCHAR(150)    NOT NULL,
    cus_contact         VARCHAR(30)     NOT NULL,
    cus_email           VARCHAR(120),
    cus_address         TEXT,
    cus_status          customer_status NOT NULL DEFAULT 'Active',
    cus_loyalty_tier    loyalty_tier    NOT NULL DEFAULT 'Bronze',
    cus_total_events    INT             NOT NULL DEFAULT 0 CHECK (cus_total_events >= 0),
    cus_created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    cus_updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_customers_name_contact ON customers (cus_name, cus_contact);

-- =============================================================================
-- TABLE: packages
-- =============================================================================
CREATE TABLE packages (
    pkg_id              SERIAL          PRIMARY KEY,
    pkg_name            VARCHAR(100)    NOT NULL UNIQUE,
    pkg_price_per_pax   NUMERIC(10,2)   NOT NULL CHECK (pkg_price_per_pax > 0),
    pkg_min_pax         INT             NOT NULL DEFAULT 1 CHECK (pkg_min_pax >= 1),
    pkg_description     TEXT
);

-- =============================================================================
-- TABLE: menu_items
-- =============================================================================
CREATE TABLE menu_items (
    mi_id           SERIAL              PRIMARY KEY,
    mi_name         VARCHAR(120)        NOT NULL UNIQUE,
    mi_description  TEXT                NOT NULL DEFAULT '',
    mi_category     menu_category       NOT NULL DEFAULT 'Other',
    mi_package_tier menu_package_tier   NOT NULL DEFAULT 'Standard',
    mi_price        NUMERIC(10,2)       NOT NULL CHECK (mi_price >= 0),
    mi_status       menu_status         NOT NULL DEFAULT 'Available',
    mi_created_at   TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    mi_updated_at   TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: package_items
-- =============================================================================
CREATE TABLE package_items (
    pi_id              SERIAL          PRIMARY KEY,
    pi_package_id      INT             NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
    pi_menu_item_id    INT             NOT NULL REFERENCES menu_items(mi_id) ON DELETE CASCADE,
    pi_custom_price    NUMERIC(10,2)   NOT NULL CHECK (pi_custom_price >= 0),
    CONSTRAINT uq_package_menu_item UNIQUE (pi_package_id, pi_menu_item_id)
);

CREATE INDEX idx_package_items_pkg ON package_items (pi_package_id);

-- =============================================================================
-- TABLE: bookings
-- =============================================================================
CREATE TABLE bookings (
    bk_id                  SERIAL          PRIMARY KEY,
    bk_booking_ref         VARCHAR(12)     NOT NULL UNIQUE,
    bk_customer_id         INT             REFERENCES customers(cus_id) ON DELETE SET NULL,
    bk_customer_name       VARCHAR(150)    NOT NULL,
    bk_contact             VARCHAR(30),
    bk_email               VARCHAR(120),
    bk_address             TEXT,
    bk_occasion            VARCHAR(120)    NOT NULL,
    bk_venue               VARCHAR(200)    NOT NULL,
    bk_event_date          DATE            NOT NULL,
    bk_event_time          TIME            NOT NULL DEFAULT '18:00:00',
    bk_pax                 INT             NOT NULL CHECK (bk_pax >= 1),
    bk_special_notes       TEXT,
    bk_menu_type           VARCHAR(10)     NOT NULL DEFAULT 'package' CHECK (bk_menu_type IN ('package','custom')),
    bk_package_id          INT             REFERENCES packages(pkg_id) ON DELETE SET NULL,
    bk_custom_items        TEXT,
    bk_total_amount        NUMERIC(12,2)   NOT NULL CHECK (bk_total_amount >= 0),
    bk_payment_mode        payment_method  NOT NULL DEFAULT 'Cash',
    bk_amount_paid         NUMERIC(12,2)   NOT NULL DEFAULT 0 CHECK (bk_amount_paid >= 0),
    bk_status              booking_status  NOT NULL DEFAULT 'PENDING',
    bk_cancellation_reason TEXT,
    bk_created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    bk_updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_paid_lte_total CHECK (bk_amount_paid <= bk_total_amount)
);

CREATE INDEX idx_bookings_event_date ON bookings (bk_event_date);
CREATE INDEX idx_bookings_status     ON bookings (bk_status);
CREATE INDEX idx_bookings_customer   ON bookings (bk_customer_id);

-- =============================================================================
-- TABLE: booking_menu_items
-- =============================================================================
CREATE TABLE booking_menu_items (
    bmi_booking_id  INT NOT NULL REFERENCES bookings(bk_id)    ON DELETE CASCADE,
    bmi_item_id     INT NOT NULL REFERENCES menu_items(mi_id)  ON DELETE CASCADE,
    PRIMARY KEY (bmi_booking_id, bmi_item_id)
);

-- =============================================================================
-- TABLE: invoices
-- =============================================================================
CREATE TABLE invoices (
    inv_id              SERIAL          PRIMARY KEY,
    inv_invoice_ref     VARCHAR(12)     NOT NULL UNIQUE,
    inv_booking_id      INT             REFERENCES bookings(bk_id) ON DELETE SET NULL,
    inv_customer_name   VARCHAR(150)    NOT NULL,
    inv_event_date      DATE            NOT NULL,
    inv_total_amount    NUMERIC(12,2)   NOT NULL CHECK (inv_total_amount >= 0),
    inv_amount_paid     NUMERIC(12,2)   NOT NULL DEFAULT 0 CHECK (inv_amount_paid >= 0),
    inv_status          invoice_status  NOT NULL DEFAULT 'Unpaid',
    inv_created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    inv_updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_inv_paid_lte_total CHECK (inv_amount_paid <= inv_total_amount)
);

CREATE INDEX idx_invoices_status ON invoices (inv_status);

-- =============================================================================
-- TABLE: payment_records
-- =============================================================================
CREATE TABLE payment_records (
    pr_id              SERIAL          PRIMARY KEY,
    pr_invoice_id      INT             NOT NULL REFERENCES invoices(inv_id) ON DELETE CASCADE,
    pr_amount          NUMERIC(12,2)   NOT NULL CHECK (pr_amount > 0),
    pr_payment_date    DATE            NOT NULL DEFAULT CURRENT_DATE,
    pr_method          VARCHAR(50)     NOT NULL DEFAULT 'Cash',
    pr_note            TEXT,
    pr_created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payment_records_invoice ON payment_records (pr_invoice_id);

-- =============================================================================
-- TABLE: kitchen_orders
-- =============================================================================
CREATE TABLE kitchen_orders (
    ko_id          SERIAL          PRIMARY KEY,
    ko_order_ref   VARCHAR(12)     NOT NULL UNIQUE,
    ko_booking_id  INT             REFERENCES bookings(bk_id) ON DELETE SET NULL,
    ko_client_name VARCHAR(150)    NOT NULL,
    ko_event_name  VARCHAR(150)    NOT NULL,
    ko_pax         INT             NOT NULL CHECK (ko_pax >= 1),
    ko_items_desc  TEXT            NOT NULL,
    ko_status      kitchen_status  NOT NULL DEFAULT 'Queued',
    ko_created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ko_updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kitchen_orders_status ON kitchen_orders (ko_status);

-- =============================================================================
-- TABLE: kitchen_tasks
-- =============================================================================
CREATE TABLE kitchen_tasks (
    kt_id          SERIAL          PRIMARY KEY,
    kt_order_id    INT             NOT NULL REFERENCES kitchen_orders(ko_id) ON DELETE CASCADE,
    kt_task_label  VARCHAR(200)    NOT NULL,
    kt_is_done     BOOLEAN         NOT NULL DEFAULT FALSE,
    kt_sort_order  INT             NOT NULL DEFAULT 0,
    kt_updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kitchen_tasks_order ON kitchen_tasks (kt_order_id);

-- =============================================================================
-- TABLE: expenses
-- =============================================================================
CREATE TABLE expenses (
    exp_id              SERIAL              PRIMARY KEY,
    exp_category        expense_category    NOT NULL DEFAULT 'Other',
    exp_description     TEXT                NOT NULL,
    exp_amount          NUMERIC(12,2)       NOT NULL CHECK (exp_amount >= 0),
    exp_expense_date    DATE                NOT NULL DEFAULT CURRENT_DATE,
    exp_created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    exp_updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_expenses_date ON expenses (exp_expense_date);

-- =============================================================================
-- TABLE: customer_follow_ups
-- =============================================================================
CREATE TABLE customer_follow_ups (
    cfu_id              SERIAL          PRIMARY KEY,
    cfu_customer_id     INT             NOT NULL REFERENCES customers(cus_id) ON DELETE CASCADE,
    cfu_follow_up_date  DATE            NOT NULL,
    cfu_note            TEXT            NOT NULL DEFAULT '',
    cfu_is_done         BOOLEAN         NOT NULL DEFAULT FALSE,
    cfu_created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    cfu_updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_follow_ups_customer ON customer_follow_ups (cfu_customer_id);
CREATE INDEX idx_follow_ups_date     ON customer_follow_ups (cfu_follow_up_date);

-- =============================================================================
-- TABLE: communication_logs
-- =============================================================================
CREATE TABLE communication_logs (
    cl_id          SERIAL          PRIMARY KEY,
    cl_log_type    VARCHAR(30)     NOT NULL CHECK (cl_log_type IN ('receipt','booking_confirm','follow_up')),
    cl_method      VARCHAR(10)     NOT NULL CHECK (cl_method IN ('email','sms','print')),
    cl_recipient   VARCHAR(150)    NOT NULL,
    cl_booking_id  INT             REFERENCES bookings(bk_id)  ON DELETE SET NULL,
    cl_invoice_id  INT             REFERENCES invoices(inv_id) ON DELETE SET NULL,
    cl_status      VARCHAR(20)     NOT NULL DEFAULT 'sent' CHECK (cl_status IN ('sent','failed')),
    cl_note        TEXT,
    cl_created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: audit_logs
-- =============================================================================
CREATE TABLE audit_logs (
    al_id          SERIAL          PRIMARY KEY,
    al_actor       VARCHAR(100)    NOT NULL DEFAULT 'system',
    al_action      VARCHAR(60)     NOT NULL,
    al_table_name  VARCHAR(60)     NOT NULL,
    al_record_id   INT,
    al_old_value   JSONB,
    al_new_value   JSONB,
    al_created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_table   ON audit_logs (al_table_name);
CREATE INDEX idx_audit_logs_created ON audit_logs (al_created_at DESC);

-- =============================================================================
-- TABLE: notifications
-- =============================================================================
CREATE TABLE notifications (
    notif_id          SERIAL          PRIMARY KEY,
    notif_type        VARCHAR(20)     NOT NULL DEFAULT 'info'
                                      CHECK (notif_type IN ('info','success','warning','error')),
    notif_title       VARCHAR(120)    NOT NULL,
    notif_message     TEXT            NOT NULL,
    notif_color       VARCHAR(10)     NOT NULL DEFAULT '#3B82F6',
    notif_is_read     BOOLEAN         NOT NULL DEFAULT FALSE,
    notif_created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: calendar_events
-- =============================================================================
CREATE TABLE calendar_events (
    ce_id          SERIAL          PRIMARY KEY,
    ce_event_date  DATE            NOT NULL,
    ce_name        VARCHAR(200)    NOT NULL,
    ce_pax         INT             NOT NULL DEFAULT 0,
    ce_event_time  VARCHAR(20)     NOT NULL DEFAULT '06:00 PM',
    ce_location    VARCHAR(200)    NOT NULL DEFAULT 'TBD',
    ce_created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_calendar_events_date ON calendar_events (ce_event_date);

-- =============================================================================
-- TABLE: occasions
-- =============================================================================
CREATE TABLE occasions (
    occ_id          SERIAL          PRIMARY KEY,
    occ_name        VARCHAR(120)    NOT NULL UNIQUE,
    occ_created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

INSERT INTO occasions (occ_name) VALUES
    ('Wedding'),
    ('Birthday'),
    ('Anniversary'),
    ('Debut'),
    ('Graduation'),
    ('Christening / Baptism'),
    ('Corporate Event'),
    ('Family Reunion'),
    ('Holiday Party'),
    ('Other');

-- =============================================================================
-- SEQUENCES for reference number generation
-- =============================================================================
CREATE SEQUENCE IF NOT EXISTS seq_booking_ref START 1;
CREATE SEQUENCE IF NOT EXISTS seq_invoice_ref START 1;
CREATE SEQUENCE IF NOT EXISTS seq_order_ref   START 1;

-- =============================================================================
-- STORED PROCEDURE: sp_next_booking_ref
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_next_booking_ref(OUT p_ref TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    p_ref := 'BKG-' || LPAD(nextval('seq_booking_ref')::TEXT, 3, '0');
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_next_invoice_ref
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_next_invoice_ref(OUT p_ref TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    p_ref := 'INV-' || LPAD(nextval('seq_invoice_ref')::TEXT, 3, '0');
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_next_order_ref
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_next_order_ref(OUT p_ref TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    p_ref := 'ORD-' || LPAD(nextval('seq_order_ref')::TEXT, 3, '0');
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_create_booking
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_create_booking(
    IN  p_customer_name  TEXT,
    IN  p_contact        TEXT,
    IN  p_email          TEXT,
    IN  p_address        TEXT,
    IN  p_occasion       TEXT,
    IN  p_venue          TEXT,
    IN  p_event_date     DATE,
    IN  p_event_time     TIME,
    IN  p_pax            INT,
    IN  p_special_notes  TEXT,
    IN  p_menu_type      TEXT,
    IN  p_package_id     INT,
    IN  p_custom_items   TEXT,
    IN  p_total_amount   NUMERIC,
    IN  p_payment_mode   TEXT,
    IN  p_amount_paid    NUMERIC,
    OUT p_booking_id     INT,
    OUT p_booking_ref    TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_cid INT;
BEGIN
    CALL sp_next_booking_ref(p_booking_ref);

    SELECT cus_id INTO v_cid FROM customers WHERE cus_name = p_customer_name LIMIT 1;

    INSERT INTO bookings (
        bk_booking_ref, bk_customer_id, bk_customer_name, bk_contact, bk_email, bk_address,
        bk_occasion, bk_venue, bk_event_date, bk_event_time, bk_pax, bk_special_notes,
        bk_menu_type, bk_package_id, bk_custom_items,
        bk_total_amount, bk_payment_mode, bk_amount_paid, bk_status
    ) VALUES (
        p_booking_ref, v_cid, p_customer_name, p_contact, p_email, p_address,
        p_occasion, p_venue, p_event_date, p_event_time, p_pax, p_special_notes,
        p_menu_type, p_package_id, p_custom_items,
        p_total_amount, p_payment_mode::payment_method, p_amount_paid, 'PENDING'
    )
    RETURNING bk_id INTO p_booking_id;

    IF v_cid IS NOT NULL THEN
        UPDATE customers
        SET cus_total_events = cus_total_events + 1, cus_updated_at = NOW()
        WHERE cus_id = v_cid;
        CALL sp_recalculate_loyalty(v_cid);
    END IF;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_booking
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_booking(
    IN p_booking_id    INT,
    IN p_customer_name TEXT,
    IN p_contact       TEXT,
    IN p_email         TEXT,
    IN p_address       TEXT,
    IN p_occasion      TEXT,
    IN p_venue         TEXT,
    IN p_event_date    DATE,
    IN p_event_time    TIME,
    IN p_pax           INT,
    IN p_special_notes TEXT,
    IN p_menu_type     TEXT,
    IN p_package_id    INT,
    IN p_custom_items  TEXT,
    IN p_total_amount  NUMERIC,
    IN p_payment_mode  TEXT,
    IN p_amount_paid   NUMERIC
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE bookings
    SET
        bk_customer_name = p_customer_name,
        bk_contact       = p_contact,
        bk_email         = p_email,
        bk_address       = p_address,
        bk_occasion      = p_occasion,
        bk_venue         = p_venue,
        bk_event_date    = p_event_date,
        bk_event_time    = p_event_time,
        bk_pax           = p_pax,
        bk_special_notes = p_special_notes,
        bk_menu_type     = p_menu_type,
        bk_package_id    = p_package_id,
        bk_custom_items  = p_custom_items,
        bk_total_amount  = p_total_amount,
        bk_payment_mode  = p_payment_mode::payment_method,
        bk_amount_paid   = p_amount_paid,
        bk_updated_at    = NOW()
    WHERE bk_id = p_booking_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_booking_status
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_booking_status(
    IN  p_booking_id            INT,
    IN  p_new_status            TEXT,
    IN  p_cancellation_reason   TEXT DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
    v_current       booking_status;
    v_customer_id   INT;
BEGIN
    SELECT bk_status
    INTO v_current
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
    SET bk_status              = p_new_status::booking_status,
        bk_cancellation_reason = CASE WHEN p_new_status = 'CANCELLED'
                                      THEN p_cancellation_reason
                                      ELSE bk_cancellation_reason END,
        bk_updated_at          = NOW()
    WHERE bk_id = p_booking_id;

    IF p_new_status = 'CONFIRMED' THEN
        SELECT bk_customer_id INTO v_customer_id FROM bookings WHERE bk_id = p_booking_id;

        IF v_customer_id IS NOT NULL THEN
            UPDATE customers
            SET cus_total_events = (
                SELECT COUNT(*) FROM bookings
                WHERE bk_customer_id = v_customer_id
                  AND bk_status IN ('CONFIRMED', 'COMPLETED')
            ), cus_updated_at = NOW()
            WHERE cus_id = v_customer_id;

            CALL sp_recalculate_loyalty(v_customer_id);
        END IF;
    END IF;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_complete_booking
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_complete_booking(IN p_booking_id INT)
LANGUAGE plpgsql AS $$
DECLARE
    v_current booking_status;
BEGIN
    SELECT bk_status INTO v_current FROM bookings WHERE bk_id = p_booking_id;

    IF v_current != 'CONFIRMED' THEN
        RAISE EXCEPTION 'Only CONFIRMED bookings can be marked as COMPLETED. Current status: %', v_current;
    END IF;

    UPDATE bookings
    SET bk_status     = 'COMPLETED'::booking_status,
        bk_updated_at = NOW()
    WHERE bk_id = p_booking_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_booking
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_booking(IN p_booking_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM bookings WHERE bk_id = p_booking_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_check_date_capacity
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_check_date_capacity(
    IN  p_event_date    DATE,
    IN  p_exclude_id    INT,
    OUT p_booked_pax    INT,
    OUT p_max_pax       INT,
    OUT p_is_over       BOOLEAN
)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT COALESCE(SUM(bk_pax), 0)
    INTO p_booked_pax
    FROM bookings
    WHERE bk_event_date = p_event_date
      AND bk_status != 'CANCELLED'
      AND bk_id != COALESCE(p_exclude_id, 0);

    SELECT bi_max_daily_pax INTO p_max_pax FROM business_info WHERE bi_id = 1;
    p_max_pax := COALESCE(p_max_pax, 600);
    p_is_over := p_booked_pax >= p_max_pax;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_create_invoice
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_create_invoice(
    IN  p_booking_id    INT,
    IN  p_customer_name TEXT,
    IN  p_event_date    DATE,
    IN  p_total_amount  NUMERIC,
    OUT p_invoice_id    INT,
    OUT p_invoice_ref   TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    CALL sp_next_invoice_ref(p_invoice_ref);

    INSERT INTO invoices (
        inv_invoice_ref, inv_booking_id, inv_customer_name, inv_event_date,
        inv_total_amount, inv_amount_paid, inv_status
    ) VALUES (
        p_invoice_ref, p_booking_id, p_customer_name, p_event_date,
        p_total_amount, 0, 'Unpaid'::invoice_status
    )
    RETURNING inv_id INTO p_invoice_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_auto_create_invoice
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_auto_create_invoice(
    IN  p_booking_id INT,
    OUT p_invoice_id INT,
    OUT p_invoice_ref TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_customer_name TEXT;
    v_event_date    DATE;
    v_total_amount  NUMERIC;
    v_existing_id   INT;
BEGIN
    SELECT bk_customer_name, bk_event_date, bk_total_amount
    INTO v_customer_name, v_event_date, v_total_amount
    FROM bookings WHERE bk_id = p_booking_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Booking not found: %', p_booking_id;
    END IF;

    SELECT inv_id INTO v_existing_id FROM invoices WHERE inv_booking_id = p_booking_id LIMIT 1;
    IF v_existing_id IS NOT NULL THEN
        SELECT inv_id, inv_invoice_ref INTO p_invoice_id, p_invoice_ref
        FROM invoices WHERE inv_id = v_existing_id;
        RETURN;
    END IF;

    CALL sp_create_invoice(p_booking_id, v_customer_name, v_event_date, v_total_amount,
                           p_invoice_id, p_invoice_ref);
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_pay_invoice
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_pay_invoice(
    IN  p_booking_id     INT,
    IN  p_payment_amount NUMERIC,
    IN  p_payment_date   DATE,
    IN  p_method         TEXT,
    IN  p_note           TEXT,
    OUT p_invoice_id           INT,
    OUT p_invoice_ref          TEXT,
    OUT p_new_invoice_status   TEXT,
    OUT p_new_booking_status   TEXT,
    OUT p_new_paid             NUMERIC,
    OUT p_remaining            NUMERIC
)
LANGUAGE plpgsql AS $$
DECLARE
    v_total          NUMERIC;
    v_inv_paid       NUMERIC;
    v_min_pct        NUMERIC;
    v_allow_zero     BOOLEAN;
    v_required_down  NUMERIC;
    v_bk_status      booking_status;
    v_new_inv_status invoice_status;
    v_record_id      INT;
BEGIN
    SELECT i.inv_id, i.inv_invoice_ref, i.inv_total_amount, i.inv_amount_paid, b.bk_status
    INTO p_invoice_id, p_invoice_ref, v_total, v_inv_paid, v_bk_status
    FROM invoices i
    JOIN bookings b ON b.bk_id = i.inv_booking_id
    WHERE i.inv_booking_id = p_booking_id
    FOR UPDATE OF i;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No invoice found for booking %', p_booking_id;
    END IF;

    IF v_bk_status = 'CANCELLED' THEN
        RAISE EXCEPTION 'Cannot record payment: booking is cancelled.';
    END IF;

    SELECT bi_min_downpayment_pct, bi_allow_zero_downpayment
    INTO v_min_pct, v_allow_zero
    FROM business_info WHERE bi_id = 1;
    v_min_pct    := COALESCE(v_min_pct, 30);
    v_allow_zero := COALESCE(v_allow_zero, FALSE);
    v_required_down := ROUND(v_total * v_min_pct / 100, 2);

    IF p_payment_amount <= 0 THEN
        RAISE EXCEPTION 'Payment amount must be greater than zero.';
    END IF;

    IF (v_inv_paid + p_payment_amount) > v_total THEN
        RAISE EXCEPTION 'Payment of ₱% exceeds remaining balance of ₱%.',
            p_payment_amount, (v_total - v_inv_paid);
    END IF;

    IF v_inv_paid = 0 AND NOT v_allow_zero AND p_payment_amount < v_required_down THEN
        RAISE EXCEPTION 'Downpayment insufficient. Required: ₱% (% %%). Entered: ₱%.',
            v_required_down, v_min_pct, p_payment_amount;
    END IF;

    INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_method, pr_note)
    VALUES (p_invoice_id, p_payment_amount, p_payment_date, p_method, p_note)
    RETURNING pr_id INTO v_record_id;

    p_new_paid  := v_inv_paid + p_payment_amount;
    p_remaining := v_total - p_new_paid;

    v_new_inv_status := CASE
        WHEN p_new_paid = 0       THEN 'Unpaid'::invoice_status
        WHEN p_new_paid < v_total THEN 'Partial'::invoice_status
        ELSE                           'Paid'::invoice_status
    END;

    UPDATE invoices
    SET inv_amount_paid = p_new_paid, inv_status = v_new_inv_status, inv_updated_at = NOW()
    WHERE inv_id = p_invoice_id;

    UPDATE bookings
    SET bk_amount_paid = p_new_paid,
        bk_status = CASE
            WHEN bk_status = 'CANCELLED' THEN bk_status
            WHEN p_new_paid >= v_total THEN 'CONFIRMED'::booking_status
            WHEN p_new_paid >= v_required_down OR v_allow_zero THEN 'CONFIRMED'::booking_status
            ELSE 'PENDING'::booking_status
        END,
        bk_updated_at = NOW()
    WHERE bk_id = p_booking_id
    RETURNING bk_status::TEXT INTO p_new_booking_status;

    p_new_invoice_status := v_new_inv_status::TEXT;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_invoice
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_invoice(
    IN p_invoice_id    INT,
    IN p_customer_name TEXT,
    IN p_event_date    DATE,
    IN p_total_amount  NUMERIC,
    IN p_amount_paid   NUMERIC,
    IN p_status        TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE invoices
    SET
        inv_customer_name = p_customer_name,
        inv_event_date    = p_event_date,
        inv_total_amount  = p_total_amount,
        inv_amount_paid   = p_amount_paid,
        inv_status        = p_status::invoice_status,
        inv_updated_at    = NOW()
    WHERE inv_id = p_invoice_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_record_payment
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_record_payment(
    IN  p_invoice_id  INT,
    IN  p_amount      NUMERIC,
    OUT p_new_status  TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_total  NUMERIC;
    v_paid   NUMERIC;
    v_status invoice_status;
BEGIN
    SELECT inv_total_amount, inv_amount_paid INTO v_total, v_paid
    FROM invoices WHERE inv_id = p_invoice_id FOR UPDATE;

    v_paid := v_paid + p_amount;
    IF v_paid > v_total THEN
        RAISE EXCEPTION 'Payment exceeds total amount';
    END IF;

    v_status := CASE
        WHEN v_paid = 0       THEN 'Unpaid'::invoice_status
        WHEN v_paid < v_total THEN 'Partial'::invoice_status
        ELSE                       'Paid'::invoice_status
    END;

    UPDATE invoices
    SET inv_amount_paid = v_paid, inv_status = v_status, inv_updated_at = NOW()
    WHERE inv_id = p_invoice_id;

    p_new_status := v_status::TEXT;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_invoice
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_invoice(IN p_invoice_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM invoices WHERE inv_id = p_invoice_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_payment_record
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_payment_record(
    IN  p_invoice_id    INT,
    IN  p_amount        NUMERIC,
    IN  p_payment_date  DATE,
    IN  p_method        TEXT,
    IN  p_note          TEXT,
    OUT p_record_id     INT,
    OUT p_new_status    TEXT,
    OUT p_new_paid      NUMERIC
)
LANGUAGE plpgsql AS $$
DECLARE
    v_total  NUMERIC;
    v_paid   NUMERIC;
    v_status invoice_status;
BEGIN
    SELECT inv_total_amount, inv_amount_paid INTO v_total, v_paid
    FROM invoices WHERE inv_id = p_invoice_id FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invoice not found: %', p_invoice_id;
    END IF;

    IF v_paid + p_amount > v_total THEN
        RAISE EXCEPTION 'Payment of % exceeds remaining balance of %.', p_amount, (v_total - v_paid);
    END IF;

    INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_method, pr_note)
    VALUES (p_invoice_id, p_amount, p_payment_date, p_method, p_note)
    RETURNING pr_id INTO p_record_id;

    p_new_paid := v_paid + p_amount;

    v_status := CASE
        WHEN p_new_paid = 0       THEN 'Unpaid'::invoice_status
        WHEN p_new_paid < v_total THEN 'Partial'::invoice_status
        ELSE                           'Paid'::invoice_status
    END;

    UPDATE invoices
    SET inv_amount_paid = p_new_paid, inv_status = v_status, inv_updated_at = NOW()
    WHERE inv_id = p_invoice_id;

    p_new_status := v_status::TEXT;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_get_payment_records
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_get_payment_records(
    IN  p_invoice_id INT,
    OUT p_cursor     REFCURSOR
)
LANGUAGE plpgsql AS $$
BEGIN
    OPEN p_cursor FOR
        SELECT pr_id, pr_amount, pr_payment_date, pr_method, pr_note, pr_created_at
        FROM payment_records
        WHERE pr_invoice_id = p_invoice_id
        ORDER BY pr_payment_date DESC, pr_created_at DESC;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_menu_item
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_menu_item(
    IN  p_name        TEXT,
    IN  p_description TEXT,
    IN  p_category    TEXT,
    IN  p_package     TEXT,
    IN  p_price       NUMERIC,
    IN  p_status      TEXT,
    OUT p_item_id     INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO menu_items (mi_name, mi_description, mi_category, mi_package_tier, mi_price, mi_status)
    VALUES (
        p_name, p_description,
        p_category::menu_category,
        p_package::menu_package_tier,
        p_price,
        p_status::menu_status
    )
    RETURNING mi_id INTO p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_menu_item
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_menu_item(
    IN p_item_id      INT,
    IN p_name         TEXT,
    IN p_description  TEXT,
    IN p_category     TEXT,
    IN p_package      TEXT,
    IN p_price        NUMERIC,
    IN p_status       TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE menu_items
    SET
        mi_name         = p_name,
        mi_description  = p_description,
        mi_category     = p_category::menu_category,
        mi_package_tier = p_package::menu_package_tier,
        mi_price        = p_price,
        mi_status       = p_status::menu_status,
        mi_updated_at   = NOW()
    WHERE mi_id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_menu_item
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_menu_item(IN p_item_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM menu_items WHERE mi_id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_customer
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_customer(
    IN  p_name         TEXT,
    IN  p_contact      TEXT,
    IN  p_email        TEXT,
    IN  p_address      TEXT,
    IN  p_status       TEXT,
    OUT p_customer_id  INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status)
    VALUES (p_name, p_contact, p_email, p_address, p_status::customer_status)
    ON CONFLICT DO NOTHING
    RETURNING cus_id INTO p_customer_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_customer
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_customer(
    IN p_customer_id INT,
    IN p_name        TEXT,
    IN p_contact     TEXT,
    IN p_email       TEXT,
    IN p_address     TEXT,
    IN p_status      TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE customers
    SET
        cus_name       = p_name,
        cus_contact    = p_contact,
        cus_email      = p_email,
        cus_address    = p_address,
        cus_status     = p_status::customer_status,
        cus_updated_at = NOW()
    WHERE cus_id = p_customer_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_customer
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_customer(IN p_customer_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM customers WHERE cus_id = p_customer_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_recalculate_loyalty
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_recalculate_loyalty(IN p_customer_id INT)
LANGUAGE plpgsql AS $$
DECLARE
    v_events INT;
    v_tier   loyalty_tier;
BEGIN
    SELECT cus_total_events INTO v_events FROM customers WHERE cus_id = p_customer_id;

    v_tier := CASE
        WHEN v_events >= 10 THEN 'VIP'::loyalty_tier
        WHEN v_events >= 6  THEN 'Gold'::loyalty_tier
        WHEN v_events >= 3  THEN 'Silver'::loyalty_tier
        ELSE                     'Bronze'::loyalty_tier
    END;

    UPDATE customers
    SET cus_loyalty_tier = v_tier, cus_updated_at = NOW()
    WHERE cus_id = p_customer_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_follow_up
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_follow_up(
    IN  p_customer_id   INT,
    IN  p_date          DATE,
    IN  p_note          TEXT,
    OUT p_follow_up_id  INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO customer_follow_ups (cfu_customer_id, cfu_follow_up_date, cfu_note)
    VALUES (p_customer_id, p_date, p_note)
    RETURNING cfu_id INTO p_follow_up_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_complete_follow_up
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_complete_follow_up(IN p_follow_up_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE customer_follow_ups
    SET cfu_is_done = TRUE, cfu_updated_at = NOW()
    WHERE cfu_id = p_follow_up_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_follow_up
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_follow_up(IN p_follow_up_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM customer_follow_ups WHERE cfu_id = p_follow_up_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_create_kitchen_order
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_create_kitchen_order(
    IN  p_booking_id  INT,
    IN  p_client_name TEXT,
    IN  p_event_name  TEXT,
    IN  p_pax         INT,
    IN  p_items_desc  TEXT,
    OUT p_order_id    INT,
    OUT p_order_ref   TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    CALL sp_next_order_ref(p_order_ref);

    INSERT INTO kitchen_orders (ko_order_ref, ko_booking_id, ko_client_name, ko_event_name, ko_pax, ko_items_desc, ko_status)
    VALUES (p_order_ref, p_booking_id, p_client_name, p_event_name, p_pax, p_items_desc, 'Queued')
    RETURNING ko_id INTO p_order_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_kitchen_order_status
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_kitchen_order_status(
    IN p_order_id   INT,
    IN p_new_status TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE kitchen_orders
    SET ko_status = p_new_status::kitchen_status, ko_updated_at = NOW()
    WHERE ko_id = p_order_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_kitchen_order
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_kitchen_order(IN p_order_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM kitchen_orders WHERE ko_id = p_order_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_kitchen_task
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_kitchen_task(
    IN  p_order_id    INT,
    IN  p_task_label  TEXT,
    IN  p_sort_order  INT,
    OUT p_task_id     INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO kitchen_tasks (kt_order_id, kt_task_label, kt_sort_order)
    VALUES (p_order_id, p_task_label, p_sort_order)
    RETURNING kt_id INTO p_task_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_toggle_kitchen_task
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_toggle_kitchen_task(
    IN  p_task_id   INT,
    OUT p_new_state BOOLEAN
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE kitchen_tasks
    SET kt_is_done = NOT kt_is_done, kt_updated_at = NOW()
    WHERE kt_id = p_task_id
    RETURNING kt_is_done INTO p_new_state;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_kitchen_task
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_kitchen_task(IN p_task_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM kitchen_tasks WHERE kt_id = p_task_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_expense
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_expense(
    IN  p_category     TEXT,
    IN  p_description  TEXT,
    IN  p_amount       NUMERIC,
    IN  p_date         DATE,
    OUT p_expense_id   INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO expenses (exp_category, exp_description, exp_amount, exp_expense_date)
    VALUES (p_category::expense_category, p_description, p_amount, p_date)
    RETURNING exp_id INTO p_expense_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_expense
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_expense(
    IN p_expense_id   INT,
    IN p_category     TEXT,
    IN p_description  TEXT,
    IN p_amount       NUMERIC,
    IN p_date         DATE
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE expenses
    SET exp_category     = p_category::expense_category,
        exp_description  = p_description,
        exp_amount       = p_amount,
        exp_expense_date = p_date,
        exp_updated_at   = NOW()
    WHERE exp_id = p_expense_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_expense
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_expense(IN p_expense_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM expenses WHERE exp_id = p_expense_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_dismiss_notification
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_dismiss_notification(IN p_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE notifications SET notif_is_read = TRUE WHERE notif_id = p_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_mark_all_notifications_read
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_mark_all_notifications_read()
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE notifications SET notif_is_read = TRUE WHERE notif_is_read = FALSE;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_push_notification
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_push_notification(
    IN  p_type    TEXT,
    IN  p_title   TEXT,
    IN  p_message TEXT,
    IN  p_color   TEXT,
    OUT p_id      INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO notifications (notif_type, notif_title, notif_message, notif_color, notif_is_read)
    VALUES (p_type, p_title, p_message, p_color, FALSE)
    RETURNING notif_id INTO p_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_save_business_info
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_save_business_info(
    IN p_name    TEXT,
    IN p_contact TEXT,
    IN p_email   TEXT,
    IN p_address TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE business_info
    SET bi_name = p_name, bi_contact = p_contact, bi_email = p_email,
        bi_address = p_address, bi_updated_at = NOW()
    WHERE bi_id = 1;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_save_smtp_config
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_save_smtp_config(
    IN p_smtp_host TEXT,
    IN p_smtp_port INT,
    IN p_smtp_user TEXT,
    IN p_smtp_pass TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE business_info
    SET bi_smtp_host  = p_smtp_host,
        bi_smtp_port  = p_smtp_port,
        bi_smtp_user  = p_smtp_user,
        bi_smtp_pass  = p_smtp_pass,
        bi_updated_at = NOW()
    WHERE bi_id = 1;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_save_booking_policy
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_save_booking_policy(
    IN p_min_downpayment_pct    NUMERIC,
    IN p_allow_zero_downpayment BOOLEAN
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE business_info
    SET bi_min_downpayment_pct    = p_min_downpayment_pct,
        bi_allow_zero_downpayment = p_allow_zero_downpayment,
        bi_updated_at             = NOW()
    WHERE bi_id = 1;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_save_capacity_policy
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_save_capacity_policy(IN p_max_daily_pax INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE business_info
    SET bi_max_daily_pax = p_max_daily_pax, bi_updated_at = NOW()
    WHERE bi_id = 1;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_log_communication
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_log_communication(
    IN  p_log_type   TEXT,
    IN  p_method     TEXT,
    IN  p_recipient  TEXT,
    IN  p_booking_id INT,
    IN  p_invoice_id INT,
    IN  p_status     TEXT,
    IN  p_note       TEXT,
    OUT p_log_id     INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO communication_logs (cl_log_type, cl_method, cl_recipient, cl_booking_id, cl_invoice_id, cl_status, cl_note)
    VALUES (p_log_type, p_method, p_recipient, p_booking_id, p_invoice_id, p_status, p_note)
    RETURNING cl_id INTO p_log_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_write_audit_log
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_write_audit_log(
    IN  p_actor       TEXT,
    IN  p_action      TEXT,
    IN  p_table_name  TEXT,
    IN  p_record_id   INT,
    IN  p_old_value   JSONB,
    IN  p_new_value   JSONB,
    OUT p_log_id      INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO audit_logs (al_actor, al_action, al_table_name, al_record_id, al_old_value, al_new_value)
    VALUES (p_actor, p_action, p_table_name, p_record_id, p_old_value, p_new_value)
    RETURNING al_id INTO p_log_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_calculate_total_amount
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_calculate_total_amount(
    IN  p_pax        INT,
    IN  p_package_id INT,
    OUT p_total      NUMERIC
)
LANGUAGE plpgsql AS $$
DECLARE
    v_rate NUMERIC;
BEGIN
    SELECT pkg_price_per_pax INTO v_rate FROM packages WHERE pkg_id = p_package_id;
    p_total := p_pax * COALESCE(v_rate, 0);
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_save_calendar_event
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_save_calendar_event(
    IN  p_event_date DATE,
    IN  p_name       TEXT,
    IN  p_pax        INT,
    IN  p_event_time VARCHAR(20),
    IN  p_location   TEXT,
    OUT p_id         INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO calendar_events (ce_event_date, ce_name, ce_pax, ce_event_time, ce_location)
    VALUES (p_event_date, p_name, p_pax, p_event_time, p_location)
    RETURNING ce_id INTO p_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_calendar_event
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_calendar_event(IN p_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM calendar_events WHERE ce_id = p_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_calendar_events_for_date
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_calendar_events_for_date(IN p_event_date DATE)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM calendar_events WHERE ce_event_date = p_event_date;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_get_event_alert_candidates
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_get_event_alert_candidates(
    INOUT p_cursor REFCURSOR
)
LANGUAGE plpgsql AS $$
BEGIN
    OPEN p_cursor FOR
    SELECT
        b.bk_id          AS booking_id,
        b.bk_booking_ref::TEXT,
        b.bk_customer_name,
        b.bk_event_date,
        b.bk_event_time,
        w.window_label
    FROM bookings b
    CROSS JOIN (
        VALUES ('1_day'), ('30_min'), ('1_min')
    ) AS w(window_label)
    WHERE b.bk_status = 'CONFIRMED'
      AND (
          (w.window_label = '1_day' AND
           (b.bk_event_date + b.bk_event_time) BETWEEN NOW() + INTERVAL '23 hours'
                                               AND NOW() + INTERVAL '25 hours')
          OR
          (w.window_label = '30_min' AND
           (b.bk_event_date + b.bk_event_time) BETWEEN NOW() + INTERVAL '28 minutes'
                                               AND NOW() + INTERVAL '32 minutes')
          OR
          (w.window_label = '1_min' AND
           (b.bk_event_date + b.bk_event_time) BETWEEN NOW()
                                               AND NOW() + INTERVAL '5 minutes')
      )
      AND NOT EXISTS (
          SELECT 1 FROM notifications n
          WHERE n.notif_title LIKE '%' || b.bk_booking_ref || '%'
            AND n.notif_title LIKE CASE w.window_label
                               WHEN '1_day'  THEN '%Tomorrow%'
                               WHEN '30_min' THEN '%30 Minutes%'
                               ELSE '%Starting Now%'
                             END
            AND n.notif_created_at >= NOW() - INTERVAL '2 hours'
      );
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_package
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_package(
    IN  p_name          TEXT,
    IN  p_price_per_pax NUMERIC,
    IN  p_min_pax       INT,
    IN  p_description   TEXT,
    OUT p_package_id    INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO packages (pkg_name, pkg_price_per_pax, pkg_min_pax, pkg_description)
    VALUES (p_name, p_price_per_pax, COALESCE(p_min_pax, 1), p_description)
    RETURNING pkg_id INTO p_package_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_package
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_package(
    IN p_package_id     INT,
    IN p_name           TEXT,
    IN p_price_per_pax  NUMERIC,
    IN p_min_pax        INT,
    IN p_description    TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM packages WHERE pkg_id = p_package_id) THEN
        RAISE EXCEPTION 'Package not found: %', p_package_id;
    END IF;
    UPDATE packages
    SET pkg_name          = p_name,
        pkg_price_per_pax = p_price_per_pax,
        pkg_min_pax       = COALESCE(p_min_pax, 1),
        pkg_description   = p_description
    WHERE pkg_id = p_package_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_package
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_package(IN p_package_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM bookings WHERE bk_package_id = p_package_id) THEN
        RAISE EXCEPTION 'Cannot delete package: it is linked to existing bookings.';
    END IF;
    DELETE FROM packages WHERE pkg_id = p_package_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_set_package_items
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_set_package_items(
    IN p_package_id     INT,
    IN p_menu_item_ids  INT[],
    IN p_custom_prices  NUMERIC[]
)
LANGUAGE plpgsql AS $$
DECLARE
    i INT;
BEGIN
    DELETE FROM package_items WHERE pi_package_id = p_package_id;
    IF p_menu_item_ids IS NOT NULL THEN
        FOR i IN 1 .. array_length(p_menu_item_ids, 1) LOOP
            INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price)
            VALUES (p_package_id, p_menu_item_ids[i], p_custom_prices[i]);
        END LOOP;
    END IF;
END;
$$;

-- =============================================================================
-- VIEWS
-- =============================================================================
CREATE OR REPLACE VIEW v_dashboard_kpis AS
SELECT
    (SELECT COUNT(*) FROM bookings WHERE bk_event_date = CURRENT_DATE)                                AS todays_events,
    (SELECT COUNT(*) FROM bookings WHERE bk_status = 'PENDING')                                       AS pending_bookings,
    (SELECT COALESCE(SUM(bk_total_amount),0) FROM bookings
     WHERE bk_event_date BETWEEN date_trunc('week', CURRENT_DATE)
                             AND date_trunc('week', CURRENT_DATE) + INTERVAL '6 days')                AS weekly_revenue,
    (SELECT COALESCE(SUM(inv_total_amount - inv_amount_paid),0) FROM invoices WHERE inv_status != 'Paid') AS unpaid_invoices,
    (SELECT COALESCE(SUM(bk_pax),0) FROM bookings WHERE bk_event_date = CURRENT_DATE)                 AS todays_pax;

CREATE OR REPLACE VIEW v_upcoming_events AS
SELECT
    b.bk_id, b.bk_booking_ref, b.bk_customer_name, b.bk_occasion,
    b.bk_venue, b.bk_event_date, b.bk_event_time, b.bk_pax, b.bk_status
FROM bookings b
WHERE b.bk_event_date >= CURRENT_DATE AND b.bk_status = 'CONFIRMED'
ORDER BY b.bk_event_date, b.bk_event_time;

CREATE OR REPLACE VIEW v_calendar_day_summary AS
SELECT
    b.bk_event_date,
    COUNT(*)                               AS booking_count,
    SUM(b.bk_pax)                          AS total_pax,
    bi.bi_max_daily_pax,
    CASE
        WHEN SUM(b.bk_pax) >= bi.bi_max_daily_pax            THEN 'Full'
        WHEN SUM(b.bk_pax) >= bi.bi_max_daily_pax * 0.67     THEN 'Near Full'
        ELSE                                                  'Available'
    END AS capacity_status
FROM bookings b
CROSS JOIN (SELECT bi_max_daily_pax FROM business_info LIMIT 1) bi
WHERE b.bk_status != 'CANCELLED'
GROUP BY b.bk_event_date, bi.bi_max_daily_pax;

CREATE OR REPLACE VIEW v_reports_summary AS
SELECT
    b.bk_booking_ref, b.bk_event_date, b.bk_customer_name,
    COALESCE(p.pkg_name, 'Custom') AS package_name,
    b.bk_pax, b.bk_total_amount, b.bk_status
FROM bookings b
LEFT JOIN packages p ON p.pkg_id = b.bk_package_id
ORDER BY b.bk_event_date DESC;

CREATE OR REPLACE VIEW v_monthly_income AS
SELECT
    TO_CHAR(inv_event_date, 'Mon')              AS month_label,
    EXTRACT(MONTH FROM inv_event_date)::INT     AS month_num,
    COALESCE(SUM(inv_total_amount), 0)::FLOAT  AS total_revenue,
    COALESCE(SUM(inv_amount_paid), 0)::FLOAT   AS total_paid
FROM invoices
WHERE EXTRACT(YEAR FROM inv_event_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY month_label, month_num
ORDER BY month_num;

CREATE OR REPLACE VIEW v_payment_methods AS
SELECT bk_payment_mode::TEXT AS method, COUNT(*) AS total
FROM bookings
WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
GROUP BY bk_payment_mode;

CREATE OR REPLACE VIEW v_top_menu_items AS
SELECT mi.mi_name AS item, COUNT(*) AS order_count
FROM booking_menu_items bmi
JOIN menu_items mi ON mi.mi_id = bmi.bmi_item_id
JOIN bookings b ON b.bk_id = bmi.bmi_booking_id
WHERE b.bk_status IN ('CONFIRMED', 'COMPLETED')
GROUP BY mi.mi_name
ORDER BY order_count DESC
LIMIT 10;

CREATE OR REPLACE VIEW v_customer_order_frequency AS
SELECT name, booking_count FROM (
    SELECT bk_customer_name AS name, COUNT(*) AS booking_count
    FROM bookings
    WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
    GROUP BY bk_customer_name
    ORDER BY booking_count DESC LIMIT 5
) top5
UNION ALL
SELECT 'Others', COUNT(*) FROM (
    SELECT bk_customer_name FROM (
        SELECT bk_customer_name, RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
        FROM bookings
        WHERE bk_status IN ('CONFIRMED', 'COMPLETED')
        GROUP BY bk_customer_name
    ) ranked WHERE rnk > 5
) rest;

CREATE OR REPLACE VIEW v_report_kpis AS
SELECT
    COUNT(*)                                                                                                      AS total_bookings,
    COALESCE(SUM(b.bk_pax), 0)::INT                                                                              AS total_pax,
    COALESCE((SELECT SUM(inv_total_amount) FROM invoices), 0)::FLOAT                                             AS total_revenue,
    COALESCE((SELECT SUM(inv_total_amount - inv_amount_paid) FROM invoices WHERE inv_status != 'Paid'), 0)::FLOAT AS unpaid_amount,
    COALESCE((SELECT COUNT(*) FROM bookings WHERE bk_created_at::DATE = CURRENT_DATE AND bk_status IN ('CONFIRMED', 'COMPLETED')), 0)::INT AS today_bookings,
    COALESCE((SELECT COUNT(*) FROM bookings
              WHERE bk_created_at::DATE BETWEEN date_trunc('week', CURRENT_DATE)::DATE
                                           AND (date_trunc('week', CURRENT_DATE) + INTERVAL '6 days')::DATE
                AND bk_status IN ('CONFIRMED', 'COMPLETED')), 0)::INT AS week_bookings
FROM bookings b
WHERE b.bk_status IN ('CONFIRMED', 'COMPLETED');

CREATE OR REPLACE VIEW v_recent_activity AS
SELECT title, description, color, created_at
FROM (
    SELECT title, description, color, created_at
    FROM (
        SELECT
            CASE bk_status
                WHEN 'CONFIRMED' THEN 'Booking Confirmed'
                WHEN 'CANCELLED' THEN 'Booking Cancelled'
                ELSE 'New Booking Request'
            END AS title,
            bk_customer_name || ' - ' || bk_occasion || ' (' || bk_pax || ' pax)' AS description,
            CASE bk_status
                WHEN 'CONFIRMED' THEN '#22C55E'
                WHEN 'CANCELLED' THEN '#EF4444'
                ELSE '#3B82F6'
            END AS color,
            bk_created_at AS created_at
        FROM bookings
        UNION ALL
        SELECT
            CASE inv_status
                WHEN 'Paid'    THEN 'Payment Received'
                WHEN 'Partial' THEN 'Partial Payment'
                ELSE 'Invoice Unpaid'
            END AS title,
            inv_customer_name || ' - Invoice ' || inv_invoice_ref AS description,
            CASE inv_status
                WHEN 'Paid'    THEN '#22C55E'
                WHEN 'Partial' THEN '#F59E0B'
                ELSE '#EF4444'
            END AS color,
            inv_created_at AS created_at
        FROM invoices
    ) combined
    ORDER BY created_at DESC
    LIMIT 10
) final_result;

CREATE OR REPLACE VIEW v_menu_alerts AS
SELECT
    mi.mi_name AS item,
    CASE mi.mi_status
        WHEN 'Seasonal'     THEN 'Seasonal / Limited'
        WHEN 'Out of Stock' THEN 'Out of stock'
        ELSE 'Unavailable'
    END AS issue,
    CASE mi.mi_status
        WHEN 'Seasonal' THEN 'warning'
        ELSE 'danger'
    END AS badge_type
FROM menu_items mi
WHERE mi.mi_status IN ('Seasonal', 'Out of Stock', 'Unavailable')
ORDER BY badge_type DESC, item
LIMIT 10;

CREATE OR REPLACE VIEW v_profit_summary AS
SELECT
    COALESCE(m.month_num, e.month_num)                                          AS month_num,
    COALESCE(m.month_label, TO_CHAR(TO_DATE(e.month_num::TEXT, 'MM'), 'Mon')) AS month_label,
    COALESCE(m.revenue, 0)::FLOAT                                               AS revenue,
    COALESCE(e.total_expense, 0)::FLOAT                                         AS total_expense,
    (COALESCE(m.revenue, 0) - COALESCE(e.total_expense, 0))::FLOAT             AS net_profit
FROM (
    SELECT EXTRACT(MONTH FROM inv_event_date)::INT AS month_num,
           TO_CHAR(inv_event_date, 'Mon') AS month_label,
           SUM(inv_total_amount) AS revenue
    FROM invoices
    WHERE EXTRACT(YEAR FROM inv_event_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY month_num, month_label
) m
FULL OUTER JOIN (
    SELECT EXTRACT(MONTH FROM exp_expense_date)::INT AS month_num,
           SUM(exp_amount) AS total_expense
    FROM expenses
    WHERE EXTRACT(YEAR FROM exp_expense_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY month_num
) e ON m.month_num = e.month_num
ORDER BY COALESCE(m.month_num, e.month_num);

CREATE OR REPLACE VIEW v_audit_log_recent AS
SELECT
    al_id, al_actor, al_action, al_table_name, al_record_id,
    al_old_value, al_new_value, al_created_at,
    al_actor || ' — ' || al_action || ' on ' || al_table_name
        || COALESCE(' #' || al_record_id::TEXT, '') AS description
FROM audit_logs
ORDER BY al_created_at DESC
LIMIT 50;

CREATE OR REPLACE VIEW v_customer_ledger AS
SELECT
    c.cus_id AS customer_id, c.cus_name AS customer_name,
    'Booking' AS entry_type,
    b.bk_created_at::DATE AS recorded_date,
    b.bk_event_date, b.bk_booking_ref AS reference,
    b.bk_occasion AS description,
    0 AS debit, 0 AS credit,
    b.bk_status::TEXT AS entry_status, b.bk_id AS source_id
FROM customers c
JOIN bookings b ON b.bk_customer_id = c.cus_id

UNION ALL

SELECT
    c.cus_id, c.cus_name, 'Invoice',
    i.inv_created_at::DATE, i.inv_event_date, i.inv_invoice_ref,
    'Invoice issued', i.inv_total_amount, 0,
    i.inv_status::TEXT, i.inv_id
FROM customers c
JOIN bookings b ON b.bk_customer_id = c.cus_id
JOIN invoices i ON i.inv_booking_id = b.bk_id

UNION ALL

SELECT
    c.cus_id, c.cus_name, 'Payment',
    pr.pr_payment_date, i.inv_event_date,
    CONCAT('PMT-', pr.pr_id::TEXT),
    COALESCE(pr.pr_note, pr.pr_method),
    0, pr.pr_amount, 'Paid', pr.pr_id
FROM customers c
JOIN bookings b ON b.bk_customer_id = c.cus_id
JOIN invoices i ON i.inv_booking_id = b.bk_id
JOIN payment_records pr ON pr.pr_invoice_id = i.inv_id

ORDER BY recorded_date DESC, entry_type;

-- =============================================================================
-- GRANT (uncomment after creating the app user)
-- psql -U postgres -c "CREATE USER catering_owner WITH PASSWORD 'change_me';"
-- =============================================================================
-- GRANT CONNECT ON DATABASE jayraldines_catering TO catering_owner;
-- GRANT USAGE  ON SCHEMA public TO catering_owner;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO catering_owner;
-- GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO catering_owner;
-- GRANT EXECUTE                        ON ALL ROUTINES  IN SCHEMA public TO catering_owner;

-- =============================================================================
-- CEBU ADDRESS SYSTEM
-- =============================================================================

CREATE TABLE IF NOT EXISTS address_regions (
    ar_id   SERIAL PRIMARY KEY,
    ar_name VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_provinces (
    ap_id        SERIAL PRIMARY KEY,
    ap_region_id INT NOT NULL REFERENCES address_regions(ar_id) ON DELETE CASCADE,
    ap_name      VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_cities (
    ac_id          SERIAL PRIMARY KEY,
    ac_province_id INT NOT NULL REFERENCES address_provinces(ap_id) ON DELETE CASCADE,
    ac_name        VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_barangays (
    ab_id      SERIAL PRIMARY KEY,
    ab_city_id INT NOT NULL REFERENCES address_cities(ac_id) ON DELETE CASCADE,
    ab_name    VARCHAR(120) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_address_barangays_name ON address_barangays (LOWER(ab_name));
CREATE INDEX IF NOT EXISTS idx_address_cities_name    ON address_cities    (LOWER(ac_name));

CREATE TABLE IF NOT EXISTS addresses (
    addr_id          SERIAL PRIMARY KEY,
    addr_street      VARCHAR(255)    NOT NULL,
    addr_barangay_id INT REFERENCES address_barangays(ab_id),
    addr_city_id     INT REFERENCES address_cities(ac_id),
    addr_province_id INT REFERENCES address_provinces(ap_id),
    addr_zip_code    VARCHAR(10),
    addr_created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS cus_address_id INT REFERENCES addresses(addr_id);

INSERT INTO address_regions (ar_name) VALUES ('Region VII - Central Visayas')
    ON CONFLICT DO NOTHING;

INSERT INTO address_provinces (ap_region_id, ap_name)
SELECT r.ar_id, 'Cebu'
FROM address_regions r WHERE r.ar_name = 'Region VII - Central Visayas'
ON CONFLICT DO NOTHING;

DO $$
DECLARE v_prov_id INT;
BEGIN
    SELECT ap_id INTO v_prov_id FROM address_provinces WHERE ap_name = 'Cebu' LIMIT 1;
    INSERT INTO address_cities (ac_province_id, ac_name) VALUES
        (v_prov_id,'Cebu City'),(v_prov_id,'Lapu-Lapu City'),(v_prov_id,'Mandaue City'),
        (v_prov_id,'Carcar City'),(v_prov_id,'Danao City'),(v_prov_id,'Naga City'),
        (v_prov_id,'Talisay City'),(v_prov_id,'Toledo City'),(v_prov_id,'Alcantara'),
        (v_prov_id,'Alcoy'),(v_prov_id,'Alegria'),(v_prov_id,'Aloguinsan'),
        (v_prov_id,'Argao'),(v_prov_id,'Asturias'),(v_prov_id,'Badian'),
        (v_prov_id,'Balamban'),(v_prov_id,'Bantayan'),(v_prov_id,'Barili'),
        (v_prov_id,'Binaliw'),(v_prov_id,'Bogo City'),(v_prov_id,'Boljoon'),(v_prov_id,'Borbon'),
        (v_prov_id,'Carmen'),(v_prov_id,'Catmon'),(v_prov_id,'Compostela'),
        (v_prov_id,'Consolacion'),(v_prov_id,'Cordova'),(v_prov_id,'Daanbantayan'),
        (v_prov_id,'Dalaguete'),(v_prov_id,'Dumanjug'),(v_prov_id,'Ginatilan'),
        (v_prov_id,'Liloan'),(v_prov_id,'Madridejos'),(v_prov_id,'Malabuyoc'),
        (v_prov_id,'Medellin'),(v_prov_id,'Minglanilla'),(v_prov_id,'Moalboal'),
        (v_prov_id,'Oslob'),(v_prov_id,'Pilar'),(v_prov_id,'Pinamungajan'),
        (v_prov_id,'Poro'),(v_prov_id,'Ronda'),(v_prov_id,'Samboan'),
        (v_prov_id,'San Fernando'),(v_prov_id,'San Francisco'),(v_prov_id,'San Remigio'),
        (v_prov_id,'Santa Fe'),(v_prov_id,'Santander'),(v_prov_id,'Sibonga'),
        (v_prov_id,'Sogod'),(v_prov_id,'Tabogon'),(v_prov_id,'Tabuelan'),
        (v_prov_id,'Tuburan'),(v_prov_id,'Tudela')
    ON CONFLICT DO NOTHING;
END$$;

DO $$
DECLARE v_city_id INT;
BEGIN
SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Cebu City' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Adlaon'),(v_city_id,'Agsungot'),(v_city_id,'Apas'),(v_city_id,'Bacayan'),
(v_city_id,'Banilad'),(v_city_id,'Basak Pardo'),(v_city_id,'Basak San Nicolas'),
(v_city_id,'Binaliw'),(v_city_id,'Bonbon'),(v_city_id,'Budla-an'),(v_city_id,'Buhisan'),
(v_city_id,'Bulacao'),(v_city_id,'Buot-Taup Pardo'),(v_city_id,'Busay'),
(v_city_id,'Calamba'),(v_city_id,'Cambinocot'),(v_city_id,'Capitol Site'),
(v_city_id,'Carreta'),(v_city_id,'Central'),(v_city_id,'Cogon Pardo'),
(v_city_id,'Cogon Ramos'),(v_city_id,'Day-as'),(v_city_id,'Duljo-Fatima'),
(v_city_id,'Ermita'),(v_city_id,'Forecast'),(v_city_id,'Guadalupe'),(v_city_id,'Guba'),
(v_city_id,'Hippodromo'),(v_city_id,'Inayawan'),(v_city_id,'Kalubihan'),
(v_city_id,'Kalunasan'),(v_city_id,'Kamagayan'),(v_city_id,'Kasambagan'),
(v_city_id,'Kinasang-an Pardo'),(v_city_id,'Labangon'),(v_city_id,'Lahug'),
(v_city_id,'Lorega San Miguel'),(v_city_id,'Lusaran'),(v_city_id,'Luz'),
(v_city_id,'Mabini'),(v_city_id,'Mabolo'),(v_city_id,'Malubog'),
(v_city_id,'Mambaling'),(v_city_id,'Pahina Central'),(v_city_id,'Pahina San Nicolas'),
(v_city_id,'Pamutan'),(v_city_id,'Pardo'),(v_city_id,'Pari-an'),(v_city_id,'Paril'),
(v_city_id,'Pasil'),(v_city_id,'Pit-os'),(v_city_id,'Poblacion Pardo'),
(v_city_id,'Pulangbato'),(v_city_id,'Pung-ol-Sibugay'),(v_city_id,'Punta Princesa'),
(v_city_id,'Quiot Pardo'),(v_city_id,'Sambag I'),(v_city_id,'Sambag II'),
(v_city_id,'San Antonio'),(v_city_id,'San Jose'),(v_city_id,'San Nicolas Central'),
(v_city_id,'San Nicolas Proper'),(v_city_id,'San Roque'),(v_city_id,'Santa Cruz'),
(v_city_id,'Santo Nino'),(v_city_id,'Sapangdaku'),(v_city_id,'Sawang Calero'),
(v_city_id,'Sinsin'),(v_city_id,'Sirao'),(v_city_id,'Suba-basbas'),
(v_city_id,'Sudlon I'),(v_city_id,'Sudlon II'),(v_city_id,'T. Padilla'),
(v_city_id,'Tabunan'),(v_city_id,'Tagbao'),(v_city_id,'Talamban'),(v_city_id,'Taptap'),
(v_city_id,'Tejero'),(v_city_id,'Tinago'),(v_city_id,'Tisa'),(v_city_id,'To-og'),
(v_city_id,'Toong'),(v_city_id,'Tugbongan'),(v_city_id,'Umapad'),(v_city_id,'Zapatera')
ON CONFLICT DO NOTHING;

SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Lapu-Lapu City' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Agus'),(v_city_id,'Babag'),(v_city_id,'Bankal'),(v_city_id,'Baring'),
(v_city_id,'Basak'),(v_city_id,'Buaya'),(v_city_id,'Calawisan'),(v_city_id,'Canjulao'),
(v_city_id,'Caubian'),(v_city_id,'Caw-oy'),(v_city_id,'Cawhagan'),(v_city_id,'Gun-ob'),
(v_city_id,'Ibo'),(v_city_id,'Looc'),(v_city_id,'Mactan'),(v_city_id,'Maribago'),
(v_city_id,'Marigondon'),(v_city_id,'Pajac'),(v_city_id,'Pajo'),(v_city_id,'Pangan-an'),
(v_city_id,'Poblacion'),(v_city_id,'Portcat'),(v_city_id,'Punta Engano'),
(v_city_id,'Pusok'),(v_city_id,'Sabang'),(v_city_id,'Santa Rosa'),
(v_city_id,'Subabasbas'),(v_city_id,'Talima'),(v_city_id,'Tingo'),(v_city_id,'Tungasan')
ON CONFLICT DO NOTHING;

SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Mandaue City' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Alang-alang'),(v_city_id,'Bakilid'),(v_city_id,'Banilad'),
(v_city_id,'Basak'),(v_city_id,'Cambaro'),(v_city_id,'Canduman'),
(v_city_id,'Casili'),(v_city_id,'Casuntingan'),(v_city_id,'Centro'),
(v_city_id,'Cubacub'),(v_city_id,'Guizo'),(v_city_id,'Ibabao-Estancia'),
(v_city_id,'Jagobiao'),(v_city_id,'Labogon'),(v_city_id,'Looc'),
(v_city_id,'Maguikay'),(v_city_id,'Mantuyong'),(v_city_id,'Novaliches'),
(v_city_id,'Opao'),(v_city_id,'Pagsabungan'),(v_city_id,'Pakna-an'),
(v_city_id,'Putlod'),(v_city_id,'Subangdaku'),(v_city_id,'Tabok'),
(v_city_id,'Tawason'),(v_city_id,'Tingub'),(v_city_id,'Tipolo'),(v_city_id,'Umapad')
ON CONFLICT DO NOTHING;

SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Talisay City' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Biasong'),(v_city_id,'Bulacao'),(v_city_id,'Cansojong'),
(v_city_id,'Dumlog'),(v_city_id,'Jaclupan'),(v_city_id,'Lagtang'),
(v_city_id,'Lawaan I'),(v_city_id,'Lawaan II'),(v_city_id,'Lawaan III'),
(v_city_id,'Linao'),(v_city_id,'Maghaway'),(v_city_id,'Manipis'),
(v_city_id,'Mohon'),(v_city_id,'Pooc'),(v_city_id,'Poblacion'),
(v_city_id,'San Isidro'),(v_city_id,'San Roque'),(v_city_id,'Tabunok'),
(v_city_id,'Tangke'),(v_city_id,'Tapul')
ON CONFLICT DO NOTHING;

SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Consolacion' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Bagacay'),(v_city_id,'Butong'),(v_city_id,'Cansaga'),
(v_city_id,'Casili'),(v_city_id,'Danglag'),(v_city_id,'Garing'),
(v_city_id,'Jugan'),(v_city_id,'Lamac'),(v_city_id,'Lanipga'),
(v_city_id,'Nangka'),(v_city_id,'Panas'),(v_city_id,'Panoypoy'),
(v_city_id,'Pitogo'),(v_city_id,'Poblacion Occidental'),(v_city_id,'Poblacion Oriental'),
(v_city_id,'Pulpog'),(v_city_id,'Sacsac'),(v_city_id,'Tayud'),
(v_city_id,'Tilhaong'),(v_city_id,'Tolotolo'),(v_city_id,'Tugbongan')
ON CONFLICT DO NOTHING;

SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Liloan' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Cabadiangan'),(v_city_id,'Calero'),(v_city_id,'Catarman'),
(v_city_id,'Cotcot'),(v_city_id,'Jubay'),(v_city_id,'Lataban'),
(v_city_id,'Mulao'),(v_city_id,'Poblacion'),(v_city_id,'San Roque'),
(v_city_id,'San Vicente'),(v_city_id,'Santa Cruz'),(v_city_id,'Santander'),
(v_city_id,'Science Park'),(v_city_id,'Tabla'),(v_city_id,'Tayud'),(v_city_id,'Yati')
ON CONFLICT DO NOTHING;

SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Minglanilla' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Cadulawan'),(v_city_id,'Calajunan'),(v_city_id,'Canlaon'),
(v_city_id,'Cogon'),(v_city_id,'Cuanos'),(v_city_id,'Guindaruhan'),
(v_city_id,'Linao'),(v_city_id,'Manduang'),(v_city_id,'Pakigne'),
(v_city_id,'Poblacion Ward I'),(v_city_id,'Poblacion Ward II'),
(v_city_id,'Poblacion Ward III'),(v_city_id,'Poblacion Ward IV'),
(v_city_id,'Tubod'),(v_city_id,'Tulay'),(v_city_id,'Tunghaan'),
(v_city_id,'Tungkop'),(v_city_id,'Vito')
ON CONFLICT DO NOTHING;

SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Cordova' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Alegria'),(v_city_id,'Bangbang'),(v_city_id,'Buagsong'),
(v_city_id,'Catarman'),(v_city_id,'Cogon'),(v_city_id,'Dapitan'),
(v_city_id,'Day-as'),(v_city_id,'Gabi'),(v_city_id,'Gilutongan'),
(v_city_id,'Ibabao'),(v_city_id,'Pilipog'),(v_city_id,'Poblacion'),(v_city_id,'San Miguel')
ON CONFLICT DO NOTHING;

SELECT ac_id INTO v_city_id FROM address_cities WHERE ac_name='Compostela' LIMIT 1;
INSERT INTO address_barangays(ab_city_id,ab_name) VALUES
(v_city_id,'Bagalnga'),(v_city_id,'Basak'),(v_city_id,'Bulukon'),
(v_city_id,'Cabadiangan'),(v_city_id,'Cambayog'),(v_city_id,'Canamucan'),
(v_city_id,'Cogon'),(v_city_id,'Dapdap'),(v_city_id,'Estipona'),
(v_city_id,'Lupa'),(v_city_id,'Magay'),(v_city_id,'Mulao'),
(v_city_id,'Ngall'),(v_city_id,'Nug-as'),(v_city_id,'Oldlungsod'),
(v_city_id,'Poblacion'),(v_city_id,'Tamiao'),(v_city_id,'Tubigan')
ON CONFLICT DO NOTHING;

END$$;

CREATE OR REPLACE FUNCTION fn_search_cebu_address(p_query TEXT, p_limit INT DEFAULT 10)
RETURNS TABLE(
    barangay_id INT, barangay TEXT, city_id INT, city TEXT,
    province_id INT, province TEXT, display_text TEXT
)
LANGUAGE plpgsql AS $$
DECLARE v_q TEXT;
BEGIN
    v_q := '%' || LOWER(TRIM(p_query)) || '%';
    RETURN QUERY
    SELECT b.ab_id, b.ab_name::TEXT, c.ac_id, c.ac_name::TEXT, pr.ap_id, pr.ap_name::TEXT,
           (b.ab_name || ', ' || c.ac_name || ', ' || pr.ap_name)::TEXT
    FROM address_barangays b
    JOIN address_cities    c  ON c.ac_id  = b.ab_city_id
    JOIN address_provinces pr ON pr.ap_id = c.ac_province_id
    WHERE LOWER(b.ab_name) LIKE v_q OR LOWER(c.ac_name) LIKE v_q
    ORDER BY CASE WHEN LOWER(b.ab_name) LIKE LOWER(TRIM(p_query)) || '%' THEN 0 ELSE 1 END, b.ab_name
    LIMIT p_limit;
END;
$$;

CREATE OR REPLACE PROCEDURE sp_save_address(
    IN  p_street TEXT, IN p_barangay_id INT, IN p_city_id INT,
    IN  p_province_id INT, IN p_zip_code TEXT, OUT p_address_id INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO addresses(addr_street, addr_barangay_id, addr_city_id, addr_province_id, addr_zip_code)
    VALUES(p_street, p_barangay_id, p_city_id, p_province_id, NULLIF(p_zip_code,''))
    RETURNING addr_id INTO p_address_id;
END;
$$;

-- =============================================================================
-- DEFAULT SEED DATA (required for app to function on first install)
-- =============================================================================

INSERT INTO business_info (bi_name, bi_contact, bi_email, bi_address)
VALUES ('Jayraldine''s Catering', '+63 900 000 0000', 'info@jayraldines.com', 'Cebu City, Cebu')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- SAMPLE DATA: menu_items (10 realistic Filipino catering dishes)
-- =============================================================================
-- Columns: mi_name, mi_description, mi_category, mi_package_tier, mi_price, mi_status
-- mi_price = individual a la carte price per serving (reference price for custom orders)
-- =============================================================================

INSERT INTO menu_items (mi_name, mi_description, mi_category, mi_package_tier, mi_price, mi_status) VALUES
(
    'Lechon de Cebu',
    'Whole roasted suckling pig seasoned with native herbs and spices, slow-roasted over charcoal until the skin is perfectly crisp. A centerpiece dish for any Cebuano celebration.',
    'Main Course',
    'Premium',
    350.00,
    'Available'
),
(
    'Chicken Inasal',
    'Bisaya-style grilled chicken marinated in lemongrass, calamansi, and annatto oil, then flame-grilled to juicy perfection. Served with garlic rice and sukang Iloco dipping sauce.',
    'Main Course',
    'Budget',
    180.00,
    'Available'
),
(
    'Kare-Kare',
    'Slow-braised ox tail and tripe in a rich, thick peanut-based sauce with banana blossom, eggplant, and pechay. Served with homemade bagoong alamang on the side.',
    'Main Course',
    'Standard',
    220.00,
    'Available'
),
(
    'Pancit Canton',
    'Stir-fried egg noodles tossed with tender slices of chicken, pork, shrimp, cabbage, carrots, and green beans in a savory oyster-soy sauce. A classic Filipino celebration noodle dish.',
    'Noodles',
    'Budget',
    120.00,
    'Available'
),
(
    'Sinigang na Baboy',
    'A comforting sour pork soup made with sampaloc (tamarind) broth, pork belly, radish, eggplant, string beans, and kangkong. Bold, tangy, and deeply satisfying.',
    'Soup',
    'Standard',
    160.00,
    'Available'
),
(
    'Pinakbet',
    'Traditional Ilocano vegetable medley — ampalaya, okra, eggplant, squash, and sitaw — sautéed with pork belly and shrimp paste (bagoong). Earthy, savory, and homestyle.',
    'Vegetables',
    'Budget',
    110.00,
    'Available'
),
(
    'Biko',
    'Sticky rice cake cooked in coconut milk and brown sugar, topped with latik (caramelized coconut cream curds). A beloved Filipino kakanin served at every special occasion.',
    'Dessert',
    'Standard',
    80.00,
    'Available'
),
(
    'Beef Caldereta',
    'Tender chunks of beef braised in a rich tomato-liver sauce with potatoes, carrots, bell peppers, olives, and cheese. A fiesta-worthy dish with deep, bold flavors.',
    'Main Course',
    'Standard',
    240.00,
    'Available'
),
(
    'Pancit Palabok',
    'Rice noodles blanketed in a smoky shrimp-based golden sauce, topped with smoked tinapa flakes, boiled eggs, chicharron, green onions, and calamansi.',
    'Noodles',
    'Standard',
    140.00,
    'Available'
),
(
    'Buko Pandan',
    'A creamy, refreshing dessert salad made with young coconut strips, pandan-flavored gelatin, and sweetened cream. A crowd-pleasing Filipino classic, served chilled.',
    'Dessert',
    'Budget',
    70.00,
    'Available'
);

-- =============================================================================
-- SAMPLE DATA: packages (5 tiers from budget to premium)
-- =============================================================================
-- pkg_price_per_pax = total package charge per guest (inclusive of all included items)
-- =============================================================================

INSERT INTO packages (pkg_name, pkg_price_per_pax, pkg_min_pax, pkg_description) VALUES
(
    'Tipid Package',
    350.00,
    50,
    'Our most affordable catering option — perfect for intimate gatherings and small birthday parties. Includes 2 main dishes, 1 noodle dish, 1 dessert, and steamed rice. Simple, hearty, and budget-friendly.'
),
(
    'Handaan Package',
    550.00,
    80,
    'Our most popular package for debuts, christenings, and family celebrations. Includes 3 main dishes, 1 noodle dish, 1 soup, 1 vegetable dish, 1 dessert, and steamed rice. A complete Filipino spread for your special day.'
),
(
    'Kasalan Package',
    800.00,
    100,
    'Designed for weddings and grand receptions. Includes 4 main dishes, 1 noodle dish, 1 soup, 1 vegetable dish, 2 desserts, and unlimited rice. Comes with free table skirting and basic table centerpiece setup.'
),
(
    'Premium Fiesta Package',
    1200.00,
    150,
    'Our top-tier experience for corporate events and premium celebrations. Includes Lechon de Cebu as centerpiece, 4 additional main dishes, 2 noodle dishes, 1 soup, 1 vegetable dish, 2 desserts, and unlimited rice. Includes full venue set-up coordination.'
),
(
    'Custom Package',
    1.00,
    20,
    'Fully customizable menu tailored to your event needs and preferences. Price is quoted separately based on your chosen dishes and guest count. Ideal for clients with specific dietary requirements or themed events. Contact us to build your dream menu.'
);

-- =============================================================================
-- SAMPLE DATA: package_items
-- Link each package to its included menu items with pi_custom_price per pax
-- Menu item IDs: 1=Lechon, 2=Chicken Inasal, 3=Kare-Kare, 4=Pancit Canton,
--                5=Sinigang na Baboy, 6=Pinakbet, 7=Biko, 8=Beef Caldereta,
--                9=Pancit Palabok, 10=Buko Pandan
-- =============================================================================

-- Package 1: Tipid Package (₱350/pax)
-- Includes: Chicken Inasal, Beef Caldereta, Pancit Canton, Buko Pandan + rice
INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price) VALUES
(1, 2,  70.00),   -- Chicken Inasal
(1, 8,  80.00),   -- Beef Caldereta
(1, 4,  50.00),   -- Pancit Canton
(1, 10, 40.00);   -- Buko Pandan

-- Package 2: Handaan Package (₱550/pax)
-- Includes: Chicken Inasal, Kare-Kare, Beef Caldereta, Pancit Canton,
--           Sinigang na Baboy, Pinakbet, Biko
INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price) VALUES
(2, 2,  70.00),   -- Chicken Inasal
(2, 3,  80.00),   -- Kare-Kare
(2, 8,  80.00),   -- Beef Caldereta
(2, 4,  50.00),   -- Pancit Canton
(2, 5,  60.00),   -- Sinigang na Baboy
(2, 6,  40.00),   -- Pinakbet
(2, 7,  40.00);   -- Biko

-- Package 3: Kasalan Package (₱800/pax)
-- Includes: Chicken Inasal, Kare-Kare, Beef Caldereta, Sinigang na Baboy,
--           Pancit Canton, Pancit Palabok, Pinakbet, Biko, Buko Pandan
INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price) VALUES
(3, 2,  70.00),   -- Chicken Inasal
(3, 3,  80.00),   -- Kare-Kare
(3, 8,  90.00),   -- Beef Caldereta
(3, 5,  65.00),   -- Sinigang na Baboy
(3, 4,  55.00),   -- Pancit Canton
(3, 9,  60.00),   -- Pancit Palabok
(3, 6,  45.00),   -- Pinakbet
(3, 7,  45.00),   -- Biko
(3, 10, 45.00);   -- Buko Pandan

-- Package 4: Premium Fiesta Package (₱1,200/pax)
-- Includes: All 10 menu items — full spread with Lechon as centerpiece
INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price) VALUES
(4, 1,  200.00),  -- Lechon de Cebu
(4, 2,  80.00),   -- Chicken Inasal
(4, 3,  90.00),   -- Kare-Kare
(4, 8,  100.00),  -- Beef Caldereta
(4, 5,  70.00),   -- Sinigang na Baboy
(4, 4,  60.00),   -- Pancit Canton
(4, 9,  65.00),   -- Pancit Palabok
(4, 6,  50.00),   -- Pinakbet
(4, 7,  50.00),   -- Biko
(4, 10, 50.00);   -- Buko Pandan

-- Package 5: Custom Package — no fixed items, quoted per client request
-- (No package_items rows — items are added dynamically per booking)

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
