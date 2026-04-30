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
    id                      SERIAL          PRIMARY KEY,
    name                    VARCHAR(120)    NOT NULL DEFAULT 'Jayraldine''s Catering',
    contact                 VARCHAR(30)     NOT NULL,
    email                   VARCHAR(120),
    address                 TEXT,
    smtp_host               VARCHAR(120),
    smtp_port               INT             DEFAULT 587,
    smtp_user               VARCHAR(120),
    smtp_pass               TEXT,
    min_downpayment_pct     NUMERIC(5,2)    NOT NULL DEFAULT 30.00,
    allow_zero_downpayment  BOOLEAN         NOT NULL DEFAULT FALSE,
    max_daily_pax           INT             NOT NULL DEFAULT 600,
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Required: exactly one row — update name/contact/address after setup
INSERT INTO business_info (name, contact, email, address)
VALUES ('Jayraldine''s Catering', '+63 912 345 6789', '', '');

-- =============================================================================
-- TABLE: customers
-- =============================================================================
CREATE TABLE customers (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(150)    NOT NULL,
    contact         VARCHAR(30)     NOT NULL,
    email           VARCHAR(120),
    address         TEXT,
    status          customer_status NOT NULL DEFAULT 'Active',
    loyalty_tier    loyalty_tier    NOT NULL DEFAULT 'Bronze',
    total_events    INT             NOT NULL DEFAULT 0 CHECK (total_events >= 0),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_customers_name_contact ON customers (name, contact);

-- =============================================================================
-- TABLE: packages
-- =============================================================================
CREATE TABLE packages (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL UNIQUE,
    price_per_pax   NUMERIC(10,2)   NOT NULL CHECK (price_per_pax > 0),
    min_pax         INT             NOT NULL DEFAULT 1 CHECK (min_pax >= 1),
    description     TEXT
);

-- =============================================================================
-- TABLE: menu_items
-- =============================================================================
CREATE TABLE menu_items (
    id           SERIAL              PRIMARY KEY,
    name         VARCHAR(120)        NOT NULL UNIQUE,
    description  TEXT                NOT NULL DEFAULT '',
    category     menu_category       NOT NULL DEFAULT 'Other',
    package_tier menu_package_tier   NOT NULL DEFAULT 'Standard',
    price        NUMERIC(10,2)       NOT NULL CHECK (price >= 0),
    status       menu_status         NOT NULL DEFAULT 'Available',
    created_at   TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: package_items
-- =============================================================================
CREATE TABLE package_items (
    id              SERIAL          PRIMARY KEY,
    package_id      INT             NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    menu_item_id    INT             NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    custom_price    NUMERIC(10,2)   NOT NULL CHECK (custom_price >= 0),
    CONSTRAINT uq_package_menu_item UNIQUE (package_id, menu_item_id)
);

CREATE INDEX idx_package_items_pkg ON package_items (package_id);

-- =============================================================================
-- TABLE: bookings
-- =============================================================================
CREATE TABLE bookings (
    id                  SERIAL          PRIMARY KEY,
    booking_ref         VARCHAR(12)     NOT NULL UNIQUE,
    customer_id         INT             REFERENCES customers(id) ON DELETE SET NULL,
    customer_name       VARCHAR(150)    NOT NULL,
    contact             VARCHAR(30),
    email               VARCHAR(120),
    address             TEXT,
    occasion            VARCHAR(120)    NOT NULL,
    venue               VARCHAR(200)    NOT NULL,
    event_date          DATE            NOT NULL,
    event_time          TIME            NOT NULL DEFAULT '18:00:00',
    pax                 INT             NOT NULL CHECK (pax >= 1),
    special_notes       TEXT,
    menu_type           VARCHAR(10)     NOT NULL DEFAULT 'package' CHECK (menu_type IN ('package','custom')),
    package_id          INT             REFERENCES packages(id) ON DELETE SET NULL,
    custom_items        TEXT,
    total_amount        NUMERIC(12,2)   NOT NULL CHECK (total_amount >= 0),
    payment_mode        payment_method  NOT NULL DEFAULT 'Cash',
    amount_paid         NUMERIC(12,2)   NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    status              booking_status  NOT NULL DEFAULT 'PENDING',
    cancellation_reason TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_paid_lte_total CHECK (amount_paid <= total_amount)
);

CREATE INDEX idx_bookings_event_date ON bookings (event_date);
CREATE INDEX idx_bookings_status     ON bookings (status);
CREATE INDEX idx_bookings_customer   ON bookings (customer_id);

-- =============================================================================
-- TABLE: booking_menu_items
-- =============================================================================
CREATE TABLE booking_menu_items (
    booking_id  INT NOT NULL REFERENCES bookings(id)    ON DELETE CASCADE,
    item_id     INT NOT NULL REFERENCES menu_items(id)  ON DELETE CASCADE,
    PRIMARY KEY (booking_id, item_id)
);

-- =============================================================================
-- TABLE: invoices
-- =============================================================================
CREATE TABLE invoices (
    id              SERIAL          PRIMARY KEY,
    invoice_ref     VARCHAR(12)     NOT NULL UNIQUE,
    booking_id      INT             REFERENCES bookings(id) ON DELETE SET NULL,
    customer_name   VARCHAR(150)    NOT NULL,
    event_date      DATE            NOT NULL,
    total_amount    NUMERIC(12,2)   NOT NULL CHECK (total_amount >= 0),
    amount_paid     NUMERIC(12,2)   NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    status          invoice_status  NOT NULL DEFAULT 'Unpaid',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_inv_paid_lte_total CHECK (amount_paid <= total_amount)
);

CREATE INDEX idx_invoices_status ON invoices (status);

-- =============================================================================
-- TABLE: payment_records
-- =============================================================================
CREATE TABLE payment_records (
    id              SERIAL          PRIMARY KEY,
    invoice_id      INT             NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    amount          NUMERIC(12,2)   NOT NULL CHECK (amount > 0),
    payment_date    DATE            NOT NULL DEFAULT CURRENT_DATE,
    method          VARCHAR(50)     NOT NULL DEFAULT 'Cash',
    note            TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payment_records_invoice ON payment_records (invoice_id);

-- =============================================================================
-- TABLE: kitchen_orders
-- =============================================================================
CREATE TABLE kitchen_orders (
    id          SERIAL          PRIMARY KEY,
    order_ref   VARCHAR(12)     NOT NULL UNIQUE,
    booking_id  INT             REFERENCES bookings(id) ON DELETE SET NULL,
    client_name VARCHAR(150)    NOT NULL,
    event_name  VARCHAR(150)    NOT NULL,
    pax         INT             NOT NULL CHECK (pax >= 1),
    items_desc  TEXT            NOT NULL,
    status      kitchen_status  NOT NULL DEFAULT 'Queued',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kitchen_orders_status ON kitchen_orders (status);

-- =============================================================================
-- TABLE: kitchen_tasks
-- =============================================================================
CREATE TABLE kitchen_tasks (
    id          SERIAL          PRIMARY KEY,
    order_id    INT             NOT NULL REFERENCES kitchen_orders(id) ON DELETE CASCADE,
    task_label  VARCHAR(200)    NOT NULL,
    is_done     BOOLEAN         NOT NULL DEFAULT FALSE,
    sort_order  INT             NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kitchen_tasks_order ON kitchen_tasks (order_id);

-- =============================================================================
-- TABLE: expenses
-- =============================================================================
CREATE TABLE expenses (
    id              SERIAL              PRIMARY KEY,
    category        expense_category    NOT NULL DEFAULT 'Other',
    description     TEXT                NOT NULL,
    amount          NUMERIC(12,2)       NOT NULL CHECK (amount >= 0),
    expense_date    DATE                NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_expenses_date ON expenses (expense_date);

-- =============================================================================
-- TABLE: customer_follow_ups
-- =============================================================================
CREATE TABLE customer_follow_ups (
    id              SERIAL          PRIMARY KEY,
    customer_id     INT             NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    follow_up_date  DATE            NOT NULL,
    note            TEXT            NOT NULL DEFAULT '',
    is_done         BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_follow_ups_customer ON customer_follow_ups (customer_id);
CREATE INDEX idx_follow_ups_date     ON customer_follow_ups (follow_up_date);

-- =============================================================================
-- TABLE: communication_logs
-- =============================================================================
CREATE TABLE communication_logs (
    id          SERIAL          PRIMARY KEY,
    log_type    VARCHAR(30)     NOT NULL CHECK (log_type IN ('receipt','booking_confirm','follow_up')),
    method      VARCHAR(10)     NOT NULL CHECK (method IN ('email','sms','print')),
    recipient   VARCHAR(150)    NOT NULL,
    booking_id  INT             REFERENCES bookings(id)  ON DELETE SET NULL,
    invoice_id  INT             REFERENCES invoices(id)  ON DELETE SET NULL,
    status      VARCHAR(20)     NOT NULL DEFAULT 'sent' CHECK (status IN ('sent','failed')),
    note        TEXT,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: audit_logs
-- =============================================================================
CREATE TABLE audit_logs (
    id          SERIAL          PRIMARY KEY,
    actor       VARCHAR(100)    NOT NULL DEFAULT 'system',
    action      VARCHAR(60)     NOT NULL,
    table_name  VARCHAR(60)     NOT NULL,
    record_id   INT,
    old_value   JSONB,
    new_value   JSONB,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_table   ON audit_logs (table_name);
CREATE INDEX idx_audit_logs_created ON audit_logs (created_at DESC);

-- =============================================================================
-- TABLE: notifications
-- =============================================================================
CREATE TABLE notifications (
    id          SERIAL          PRIMARY KEY,
    type        VARCHAR(20)     NOT NULL DEFAULT 'info'
                                CHECK (type IN ('info','success','warning','error')),
    title       VARCHAR(120)    NOT NULL,
    message     TEXT            NOT NULL,
    color       VARCHAR(10)     NOT NULL DEFAULT '#3B82F6',
    is_read     BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: calendar_events
-- =============================================================================
CREATE TABLE calendar_events (
    id          SERIAL          PRIMARY KEY,
    event_date  DATE            NOT NULL,
    name        VARCHAR(200)    NOT NULL,
    pax         INT             NOT NULL DEFAULT 0,
    event_time  VARCHAR(20)     NOT NULL DEFAULT '06:00 PM',
    location    VARCHAR(200)    NOT NULL DEFAULT 'TBD',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_calendar_events_date ON calendar_events (event_date);

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

    SELECT id INTO v_cid FROM customers WHERE name = p_customer_name LIMIT 1;

    INSERT INTO bookings (
        booking_ref, customer_id, customer_name, contact, email, address,
        occasion, venue, event_date, event_time, pax, special_notes,
        menu_type, package_id, custom_items,
        total_amount, payment_mode, amount_paid, status
    ) VALUES (
        p_booking_ref, v_cid, p_customer_name, p_contact, p_email, p_address,
        p_occasion, p_venue, p_event_date, p_event_time, p_pax, p_special_notes,
        p_menu_type, p_package_id, p_custom_items,
        p_total_amount, p_payment_mode::payment_method, p_amount_paid, 'PENDING'
    )
    RETURNING id INTO p_booking_id;

    IF v_cid IS NOT NULL THEN
        UPDATE customers
        SET total_events = total_events + 1, updated_at = NOW()
        WHERE id = v_cid;
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
        customer_name = p_customer_name,
        contact       = p_contact,
        email         = p_email,
        address       = p_address,
        occasion      = p_occasion,
        venue         = p_venue,
        event_date    = p_event_date,
        event_time    = p_event_time,
        pax           = p_pax,
        special_notes = p_special_notes,
        menu_type     = p_menu_type,
        package_id    = p_package_id,
        custom_items  = p_custom_items,
        total_amount  = p_total_amount,
        payment_mode  = p_payment_mode::payment_method,
        amount_paid   = p_amount_paid,
        updated_at    = NOW()
    WHERE id = p_booking_id;
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
    v_amount_paid   NUMERIC;
    v_total         NUMERIC;
    v_min_pct       NUMERIC;
    v_allow_zero    BOOLEAN;
    v_customer_id   INT;
BEGIN
    SELECT status, amount_paid, total_amount
    INTO v_current, v_amount_paid, v_total
    FROM bookings WHERE id = p_booking_id;

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

    IF p_new_status = 'CONFIRMED' THEN
        SELECT min_downpayment_pct, allow_zero_downpayment
        INTO v_min_pct, v_allow_zero
        FROM business_info WHERE id = 1;

        v_min_pct    := COALESCE(v_min_pct, 30);
        v_allow_zero := COALESCE(v_allow_zero, FALSE);

        IF NOT v_allow_zero AND v_amount_paid < (v_total * v_min_pct / 100) THEN
            RAISE EXCEPTION 'Downpayment insufficient. Required: % pct. Paid: %.',
                ROUND(v_total * v_min_pct / 100, 2), v_amount_paid;
        END IF;
    END IF;

    UPDATE bookings
    SET status              = p_new_status::booking_status,
        cancellation_reason = CASE WHEN p_new_status = 'CANCELLED'
                                   THEN p_cancellation_reason
                                   ELSE cancellation_reason END,
        updated_at          = NOW()
    WHERE id = p_booking_id;

    IF p_new_status = 'CONFIRMED' THEN
        SELECT customer_id INTO v_customer_id FROM bookings WHERE id = p_booking_id;

        IF v_customer_id IS NOT NULL THEN
            UPDATE customers
            SET total_events = (
                SELECT COUNT(*) FROM bookings
                WHERE customer_id = v_customer_id
                  AND status IN ('CONFIRMED', 'COMPLETED')
            ), updated_at = NOW()
            WHERE id = v_customer_id;

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
    SELECT status INTO v_current FROM bookings WHERE id = p_booking_id;

    IF v_current != 'CONFIRMED' THEN
        RAISE EXCEPTION 'Only CONFIRMED bookings can be marked as COMPLETED. Current status: %', v_current;
    END IF;

    UPDATE bookings
    SET status     = 'COMPLETED'::booking_status,
        updated_at = NOW()
    WHERE id = p_booking_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_booking
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_booking(IN p_booking_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM bookings WHERE id = p_booking_id;
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
    SELECT COALESCE(SUM(pax), 0)
    INTO p_booked_pax
    FROM bookings
    WHERE event_date = p_event_date
      AND status != 'CANCELLED'
      AND id != COALESCE(p_exclude_id, 0);

    SELECT max_daily_pax INTO p_max_pax FROM business_info WHERE id = 1;
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
        invoice_ref, booking_id, customer_name, event_date,
        total_amount, amount_paid, status
    ) VALUES (
        p_invoice_ref, p_booking_id, p_customer_name, p_event_date,
        p_total_amount, 0, 'Unpaid'::invoice_status
    )
    RETURNING id INTO p_invoice_id;
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
    SELECT customer_name, event_date, total_amount
    INTO v_customer_name, v_event_date, v_total_amount
    FROM bookings WHERE id = p_booking_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Booking not found: %', p_booking_id;
    END IF;

    SELECT id INTO v_existing_id FROM invoices WHERE booking_id = p_booking_id LIMIT 1;
    IF v_existing_id IS NOT NULL THEN
        SELECT id, invoice_ref INTO p_invoice_id, p_invoice_ref
        FROM invoices WHERE id = v_existing_id;
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
    SELECT i.id, i.invoice_ref, i.total_amount, i.amount_paid, b.status
    INTO p_invoice_id, p_invoice_ref, v_total, v_inv_paid, v_bk_status
    FROM invoices i
    JOIN bookings b ON b.id = i.booking_id
    WHERE i.booking_id = p_booking_id
    FOR UPDATE OF i;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No invoice found for booking %', p_booking_id;
    END IF;

    IF v_bk_status = 'CANCELLED' THEN
        RAISE EXCEPTION 'Cannot record payment: booking is cancelled.';
    END IF;

    SELECT min_downpayment_pct, allow_zero_downpayment
    INTO v_min_pct, v_allow_zero
    FROM business_info WHERE id = 1;
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

    INSERT INTO payment_records (invoice_id, amount, payment_date, method, note)
    VALUES (p_invoice_id, p_payment_amount, p_payment_date, p_method, p_note)
    RETURNING id INTO v_record_id;

    p_new_paid  := v_inv_paid + p_payment_amount;
    p_remaining := v_total - p_new_paid;

    v_new_inv_status := CASE
        WHEN p_new_paid = 0       THEN 'Unpaid'::invoice_status
        WHEN p_new_paid < v_total THEN 'Partial'::invoice_status
        ELSE                           'Paid'::invoice_status
    END;

    UPDATE invoices
    SET amount_paid = p_new_paid, status = v_new_inv_status, updated_at = NOW()
    WHERE id = p_invoice_id;

    UPDATE bookings
    SET amount_paid = p_new_paid,
        status = CASE
            WHEN status = 'CANCELLED' THEN status
            WHEN p_new_paid >= v_total THEN 'CONFIRMED'::booking_status
            WHEN p_new_paid >= v_required_down OR v_allow_zero THEN 'CONFIRMED'::booking_status
            ELSE 'PENDING'::booking_status
        END,
        updated_at = NOW()
    WHERE id = p_booking_id
    RETURNING status::TEXT INTO p_new_booking_status;

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
        customer_name = p_customer_name,
        event_date    = p_event_date,
        total_amount  = p_total_amount,
        amount_paid   = p_amount_paid,
        status        = p_status::invoice_status,
        updated_at    = NOW()
    WHERE id = p_invoice_id;
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
    SELECT total_amount, amount_paid INTO v_total, v_paid
    FROM invoices WHERE id = p_invoice_id FOR UPDATE;

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
    SET amount_paid = v_paid, status = v_status, updated_at = NOW()
    WHERE id = p_invoice_id;

    p_new_status := v_status::TEXT;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_invoice
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_invoice(IN p_invoice_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM invoices WHERE id = p_invoice_id;
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
    SELECT total_amount, amount_paid INTO v_total, v_paid
    FROM invoices WHERE id = p_invoice_id FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invoice not found: %', p_invoice_id;
    END IF;

    IF v_paid + p_amount > v_total THEN
        RAISE EXCEPTION 'Payment of % exceeds remaining balance of %.', p_amount, (v_total - v_paid);
    END IF;

    INSERT INTO payment_records (invoice_id, amount, payment_date, method, note)
    VALUES (p_invoice_id, p_amount, p_payment_date, p_method, p_note)
    RETURNING id INTO p_record_id;

    p_new_paid := v_paid + p_amount;

    v_status := CASE
        WHEN p_new_paid = 0       THEN 'Unpaid'::invoice_status
        WHEN p_new_paid < v_total THEN 'Partial'::invoice_status
        ELSE                           'Paid'::invoice_status
    END;

    UPDATE invoices
    SET amount_paid = p_new_paid, status = v_status, updated_at = NOW()
    WHERE id = p_invoice_id;

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
        SELECT id, amount, payment_date, method, note, created_at
        FROM payment_records
        WHERE invoice_id = p_invoice_id
        ORDER BY payment_date DESC, created_at DESC;
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
    INSERT INTO menu_items (name, description, category, package_tier, price, status)
    VALUES (
        p_name, p_description,
        p_category::menu_category,
        p_package::menu_package_tier,
        p_price,
        p_status::menu_status
    )
    RETURNING id INTO p_item_id;
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
        name         = p_name,
        description  = p_description,
        category     = p_category::menu_category,
        package_tier = p_package::menu_package_tier,
        price        = p_price,
        status       = p_status::menu_status,
        updated_at   = NOW()
    WHERE id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_menu_item
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_menu_item(IN p_item_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM menu_items WHERE id = p_item_id;
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
    INSERT INTO customers (name, contact, email, address, status)
    VALUES (p_name, p_contact, p_email, p_address, p_status::customer_status)
    ON CONFLICT DO NOTHING
    RETURNING id INTO p_customer_id;
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
        name       = p_name,
        contact    = p_contact,
        email      = p_email,
        address    = p_address,
        status     = p_status::customer_status,
        updated_at = NOW()
    WHERE id = p_customer_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_customer
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_customer(IN p_customer_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM customers WHERE id = p_customer_id;
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
    SELECT total_events INTO v_events FROM customers WHERE id = p_customer_id;

    v_tier := CASE
        WHEN v_events >= 10 THEN 'VIP'::loyalty_tier
        WHEN v_events >= 6  THEN 'Gold'::loyalty_tier
        WHEN v_events >= 3  THEN 'Silver'::loyalty_tier
        ELSE                     'Bronze'::loyalty_tier
    END;

    UPDATE customers
    SET loyalty_tier = v_tier, updated_at = NOW()
    WHERE id = p_customer_id;
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
    INSERT INTO customer_follow_ups (customer_id, follow_up_date, note)
    VALUES (p_customer_id, p_date, p_note)
    RETURNING id INTO p_follow_up_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_complete_follow_up
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_complete_follow_up(IN p_follow_up_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE customer_follow_ups
    SET is_done = TRUE, updated_at = NOW()
    WHERE id = p_follow_up_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_follow_up
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_follow_up(IN p_follow_up_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM customer_follow_ups WHERE id = p_follow_up_id;
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

    INSERT INTO kitchen_orders (order_ref, booking_id, client_name, event_name, pax, items_desc, status)
    VALUES (p_order_ref, p_booking_id, p_client_name, p_event_name, p_pax, p_items_desc, 'Queued')
    RETURNING id INTO p_order_id;
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
    SET status = p_new_status::kitchen_status, updated_at = NOW()
    WHERE id = p_order_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_kitchen_order
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_kitchen_order(IN p_order_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM kitchen_orders WHERE id = p_order_id;
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
    INSERT INTO kitchen_tasks (order_id, task_label, sort_order)
    VALUES (p_order_id, p_task_label, p_sort_order)
    RETURNING id INTO p_task_id;
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
    SET is_done = NOT is_done, updated_at = NOW()
    WHERE id = p_task_id
    RETURNING is_done INTO p_new_state;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_kitchen_task
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_kitchen_task(IN p_task_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM kitchen_tasks WHERE id = p_task_id;
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
    INSERT INTO expenses (category, description, amount, expense_date)
    VALUES (p_category::expense_category, p_description, p_amount, p_date)
    RETURNING id INTO p_expense_id;
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
    SET category     = p_category::expense_category,
        description  = p_description,
        amount       = p_amount,
        expense_date = p_date,
        updated_at   = NOW()
    WHERE id = p_expense_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_expense
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_expense(IN p_expense_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM expenses WHERE id = p_expense_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_dismiss_notification
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_dismiss_notification(IN p_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE notifications SET is_read = TRUE WHERE id = p_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_mark_all_notifications_read
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_mark_all_notifications_read()
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE notifications SET is_read = TRUE WHERE is_read = FALSE;
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
    INSERT INTO notifications (type, title, message, color, is_read)
    VALUES (p_type, p_title, p_message, p_color, FALSE)
    RETURNING id INTO p_id;
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
    SET name = p_name, contact = p_contact, email = p_email,
        address = p_address, updated_at = NOW()
    WHERE id = 1;
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
    SET smtp_host  = p_smtp_host,
        smtp_port  = p_smtp_port,
        smtp_user  = p_smtp_user,
        smtp_pass  = p_smtp_pass,
        updated_at = NOW()
    WHERE id = 1;
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
    SET min_downpayment_pct    = p_min_downpayment_pct,
        allow_zero_downpayment = p_allow_zero_downpayment,
        updated_at             = NOW()
    WHERE id = 1;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_save_capacity_policy
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_save_capacity_policy(IN p_max_daily_pax INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE business_info
    SET max_daily_pax = p_max_daily_pax, updated_at = NOW()
    WHERE id = 1;
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
    INSERT INTO communication_logs (log_type, method, recipient, booking_id, invoice_id, status, note)
    VALUES (p_log_type, p_method, p_recipient, p_booking_id, p_invoice_id, p_status, p_note)
    RETURNING id INTO p_log_id;
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
    INSERT INTO audit_logs (actor, action, table_name, record_id, old_value, new_value)
    VALUES (p_actor, p_action, p_table_name, p_record_id, p_old_value, p_new_value)
    RETURNING id INTO p_log_id;
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
    SELECT price_per_pax INTO v_rate FROM packages WHERE id = p_package_id;
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
    INSERT INTO calendar_events (event_date, name, pax, event_time, location)
    VALUES (p_event_date, p_name, p_pax, p_event_time, p_location)
    RETURNING id INTO p_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_calendar_event
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_calendar_event(IN p_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM calendar_events WHERE id = p_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_calendar_events_for_date
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_calendar_events_for_date(IN p_event_date DATE)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM calendar_events WHERE event_date = p_event_date;
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
        b.id          AS booking_id,
        b.booking_ref::TEXT,
        b.customer_name,
        b.event_date,
        b.event_time,
        w.window_label
    FROM bookings b
    CROSS JOIN (
        VALUES ('1_day'), ('30_min'), ('1_min')
    ) AS w(window_label)
    WHERE b.status = 'CONFIRMED'
      AND (
          (w.window_label = '1_day' AND
           (b.event_date + b.event_time) BETWEEN NOW() + INTERVAL '23 hours'
                                              AND NOW() + INTERVAL '25 hours')
          OR
          (w.window_label = '30_min' AND
           (b.event_date + b.event_time) BETWEEN NOW() + INTERVAL '28 minutes'
                                              AND NOW() + INTERVAL '32 minutes')
          OR
          (w.window_label = '1_min' AND
           (b.event_date + b.event_time) BETWEEN NOW()
                                              AND NOW() + INTERVAL '5 minutes')
      )
      AND NOT EXISTS (
          SELECT 1 FROM notifications n
          WHERE n.title LIKE '%' || b.booking_ref || '%'
            AND n.title LIKE CASE w.window_label
                               WHEN '1_day'  THEN '%Tomorrow%'
                               WHEN '30_min' THEN '%30 Minutes%'
                               ELSE '%Starting Now%'
                             END
            AND n.created_at >= NOW() - INTERVAL '2 hours'
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
    INSERT INTO packages (name, price_per_pax, min_pax, description)
    VALUES (p_name, p_price_per_pax, COALESCE(p_min_pax, 1), p_description)
    RETURNING id INTO p_package_id;
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
    IF NOT EXISTS (SELECT 1 FROM packages WHERE id = p_package_id) THEN
        RAISE EXCEPTION 'Package not found: %', p_package_id;
    END IF;
    UPDATE packages
    SET name          = p_name,
        price_per_pax = p_price_per_pax,
        min_pax       = COALESCE(p_min_pax, 1),
        description   = p_description
    WHERE id = p_package_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_package
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_package(IN p_package_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM bookings WHERE package_id = p_package_id) THEN
        RAISE EXCEPTION 'Cannot delete package: it is linked to existing bookings.';
    END IF;
    DELETE FROM packages WHERE id = p_package_id;
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
    DELETE FROM package_items WHERE package_id = p_package_id;
    IF p_menu_item_ids IS NOT NULL THEN
        FOR i IN 1 .. array_length(p_menu_item_ids, 1) LOOP
            INSERT INTO package_items (package_id, menu_item_id, custom_price)
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
    (SELECT COUNT(*) FROM bookings WHERE event_date = CURRENT_DATE)                          AS todays_events,
    (SELECT COUNT(*) FROM bookings WHERE status = 'PENDING')                                 AS pending_bookings,
    (SELECT COALESCE(SUM(total_amount),0) FROM bookings
     WHERE event_date BETWEEN date_trunc('week', CURRENT_DATE)
                          AND date_trunc('week', CURRENT_DATE) + INTERVAL '6 days')         AS weekly_revenue,
    (SELECT COALESCE(SUM(total_amount - amount_paid),0) FROM invoices WHERE status != 'Paid') AS unpaid_invoices,
    (SELECT COALESCE(SUM(pax),0) FROM bookings WHERE event_date = CURRENT_DATE)             AS todays_pax;

CREATE OR REPLACE VIEW v_upcoming_events AS
SELECT
    b.id, b.booking_ref, b.customer_name, b.occasion,
    b.venue, b.event_date, b.event_time, b.pax, b.status
FROM bookings b
WHERE b.event_date >= CURRENT_DATE AND b.status = 'CONFIRMED'
ORDER BY b.event_date, b.event_time;

CREATE OR REPLACE VIEW v_calendar_day_summary AS
SELECT
    b.event_date,
    COUNT(*)                            AS booking_count,
    SUM(b.pax)                          AS total_pax,
    bi.max_daily_pax,
    CASE
        WHEN SUM(b.pax) >= bi.max_daily_pax            THEN 'Full'
        WHEN SUM(b.pax) >= bi.max_daily_pax * 0.67     THEN 'Near Full'
        ELSE                                           'Available'
    END AS capacity_status
FROM bookings b
CROSS JOIN (SELECT max_daily_pax FROM business_info LIMIT 1) bi
WHERE b.status != 'CANCELLED'
GROUP BY b.event_date, bi.max_daily_pax;

CREATE OR REPLACE VIEW v_reports_summary AS
SELECT
    b.booking_ref, b.event_date, b.customer_name,
    COALESCE(p.name, 'Custom') AS package_name,
    b.pax, b.total_amount, b.status
FROM bookings b
LEFT JOIN packages p ON p.id = b.package_id
ORDER BY b.event_date DESC;

CREATE OR REPLACE VIEW v_monthly_income AS
SELECT
    TO_CHAR(event_date, 'Mon')              AS month_label,
    EXTRACT(MONTH FROM event_date)::INT     AS month_num,
    COALESCE(SUM(total_amount), 0)::FLOAT  AS total_revenue,
    COALESCE(SUM(amount_paid), 0)::FLOAT   AS total_paid
FROM invoices
WHERE EXTRACT(YEAR FROM event_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY month_label, month_num
ORDER BY month_num;

CREATE OR REPLACE VIEW v_payment_methods AS
SELECT payment_mode::TEXT AS method, COUNT(*) AS total
FROM bookings
GROUP BY payment_mode;

CREATE OR REPLACE VIEW v_top_menu_items AS
SELECT mi.name AS item, COUNT(*) AS order_count
FROM booking_menu_items bmi
JOIN menu_items mi ON mi.id = bmi.item_id
GROUP BY mi.name
ORDER BY order_count DESC
LIMIT 10;

CREATE OR REPLACE VIEW v_customer_order_frequency AS
SELECT name, booking_count FROM (
    SELECT customer_name AS name, COUNT(*) AS booking_count
    FROM bookings GROUP BY customer_name
    ORDER BY booking_count DESC LIMIT 5
) top5
UNION ALL
SELECT 'Others', COUNT(*) FROM (
    SELECT customer_name FROM (
        SELECT customer_name, RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
        FROM bookings GROUP BY customer_name
    ) ranked WHERE rnk > 5
) rest;

CREATE OR REPLACE VIEW v_report_kpis AS
SELECT
    COUNT(*)                                                                        AS total_bookings,
    COALESCE(SUM(b.pax), 0)::INT                                                   AS total_pax,
    COALESCE((SELECT SUM(total_amount) FROM invoices), 0)::FLOAT                   AS total_revenue,
    COALESCE((SELECT SUM(total_amount - amount_paid) FROM invoices WHERE status != 'Paid'), 0)::FLOAT AS unpaid_amount,
    COALESCE((SELECT COUNT(*) FROM bookings WHERE DATE(event_date) = CURRENT_DATE), 0)::INT AS today_bookings,
    COALESCE((SELECT COUNT(*) FROM bookings
              WHERE event_date BETWEEN date_trunc('week', CURRENT_DATE)
                                   AND date_trunc('week', CURRENT_DATE) + INTERVAL '6 days'), 0)::INT AS week_bookings
FROM bookings b;

CREATE OR REPLACE VIEW v_recent_activity AS
SELECT title, description, color, created_at FROM (
    SELECT
        CASE status
            WHEN 'CONFIRMED' THEN 'Booking Confirmed'
            WHEN 'CANCELLED' THEN 'Booking Cancelled'
            ELSE 'New Booking Request'
        END AS title,
        customer_name || ' — ' || occasion || ' (' || pax || ' pax)' AS description,
        CASE status
            WHEN 'CONFIRMED' THEN '#22C55E'
            WHEN 'CANCELLED' THEN '#EF4444'
            ELSE '#3B82F6'
        END AS color,
        created_at
    FROM bookings
    UNION ALL
    SELECT
        CASE status
            WHEN 'Paid'    THEN 'Payment Received'
            WHEN 'Partial' THEN 'Partial Payment'
            ELSE 'Invoice Unpaid'
        END AS title,
        customer_name || ' — Invoice ' || invoice_ref AS description,
        CASE status
            WHEN 'Paid'    THEN '#22C55E'
            WHEN 'Partial' THEN '#F59E0B'
            ELSE '#EF4444'
        END AS color,
        created_at
    FROM invoices
) combined
ORDER BY created_at DESC
LIMIT 10;

CREATE OR REPLACE VIEW v_menu_alerts AS
SELECT
    mi.name AS item,
    CASE mi.status
        WHEN 'Seasonal'     THEN 'Seasonal / Limited'
        WHEN 'Out of Stock' THEN 'Out of stock'
        ELSE 'Unavailable'
    END AS issue,
    CASE mi.status
        WHEN 'Seasonal' THEN 'warning'
        ELSE 'danger'
    END AS badge_type
FROM menu_items mi
WHERE mi.status IN ('Seasonal', 'Out of Stock', 'Unavailable')
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
    SELECT EXTRACT(MONTH FROM event_date)::INT AS month_num,
           TO_CHAR(event_date, 'Mon') AS month_label,
           SUM(total_amount) AS revenue
    FROM invoices
    WHERE EXTRACT(YEAR FROM event_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY month_num, month_label
) m
FULL OUTER JOIN (
    SELECT EXTRACT(MONTH FROM expense_date)::INT AS month_num,
           SUM(amount) AS total_expense
    FROM expenses
    WHERE EXTRACT(YEAR FROM expense_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY month_num
) e ON m.month_num = e.month_num
ORDER BY COALESCE(m.month_num, e.month_num);

CREATE OR REPLACE VIEW v_audit_log_recent AS
SELECT
    id, actor, action, table_name, record_id,
    old_value, new_value, created_at,
    actor || ' — ' || action || ' on ' || table_name
        || COALESCE(' #' || record_id::TEXT, '') AS description
FROM audit_logs
ORDER BY created_at DESC
LIMIT 50;

CREATE OR REPLACE VIEW v_customer_ledger AS
SELECT
    c.id AS customer_id, c.name AS customer_name,
    'Booking' AS entry_type,
    b.created_at::DATE AS recorded_date,
    b.event_date, b.booking_ref AS reference,
    b.occasion AS description,
    0 AS debit, 0 AS credit,
    b.status::TEXT AS entry_status, b.id AS source_id
FROM customers c
JOIN bookings b ON b.customer_id = c.id

UNION ALL

SELECT
    c.id, c.name, 'Invoice',
    i.created_at::DATE, i.event_date, i.invoice_ref,
    'Invoice issued', i.total_amount, 0,
    i.status::TEXT, i.id
FROM customers c
JOIN bookings b ON b.customer_id = c.id
JOIN invoices i ON i.booking_id = b.id

UNION ALL

SELECT
    c.id, c.name, 'Payment',
    pr.payment_date, i.event_date,
    CONCAT('PMT-', pr.id::TEXT),
    COALESCE(pr.note, pr.method),
    0, pr.amount, 'Paid', pr.id
FROM customers c
JOIN bookings b ON b.customer_id = c.id
JOIN invoices i ON i.booking_id = b.id
JOIN payment_records pr ON pr.invoice_id = i.id

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
    id   SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_provinces (
    id        SERIAL PRIMARY KEY,
    region_id INT NOT NULL REFERENCES address_regions(id) ON DELETE CASCADE,
    name      VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_cities (
    id          SERIAL PRIMARY KEY,
    province_id INT NOT NULL REFERENCES address_provinces(id) ON DELETE CASCADE,
    name        VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_barangays (
    id      SERIAL PRIMARY KEY,
    city_id INT NOT NULL REFERENCES address_cities(id) ON DELETE CASCADE,
    name    VARCHAR(120) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_address_barangays_name ON address_barangays (LOWER(name));
CREATE INDEX IF NOT EXISTS idx_address_cities_name    ON address_cities    (LOWER(name));

CREATE TABLE IF NOT EXISTS addresses (
    id          SERIAL PRIMARY KEY,
    street      VARCHAR(255),
    barangay_id INT REFERENCES address_barangays(id),
    city_id     INT REFERENCES address_cities(id),
    province_id INT REFERENCES address_provinces(id),
    zip_code    VARCHAR(10),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS address_id INT REFERENCES addresses(id);

INSERT INTO address_regions (name) VALUES ('Region VII - Central Visayas')
    ON CONFLICT DO NOTHING;

INSERT INTO address_provinces (region_id, name)
SELECT r.id, 'Cebu'
FROM address_regions r WHERE r.name = 'Region VII - Central Visayas'
ON CONFLICT DO NOTHING;

DO $$
DECLARE v_prov_id INT;
BEGIN
    SELECT id INTO v_prov_id FROM address_provinces WHERE name = 'Cebu' LIMIT 1;
    INSERT INTO address_cities (province_id, name) VALUES
        (v_prov_id,'Cebu City'),(v_prov_id,'Lapu-Lapu City'),(v_prov_id,'Mandaue City'),
        (v_prov_id,'Carcar City'),(v_prov_id,'Danao City'),(v_prov_id,'Naga City'),
        (v_prov_id,'Talisay City'),(v_prov_id,'Toledo City'),(v_prov_id,'Alcantara'),
        (v_prov_id,'Alcoy'),(v_prov_id,'Alegria'),(v_prov_id,'Aloguinsan'),
        (v_prov_id,'Argao'),(v_prov_id,'Asturias'),(v_prov_id,'Badian'),
        (v_prov_id,'Balamban'),(v_prov_id,'Bantayan'),(v_prov_id,'Barili'),
        (v_prov_id,'Bogo City'),(v_prov_id,'Boljoon'),(v_prov_id,'Borbon'),
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
SELECT id INTO v_city_id FROM address_cities WHERE name='Cebu City' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
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

SELECT id INTO v_city_id FROM address_cities WHERE name='Lapu-Lapu City' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
(v_city_id,'Agus'),(v_city_id,'Babag'),(v_city_id,'Bankal'),(v_city_id,'Baring'),
(v_city_id,'Basak'),(v_city_id,'Buaya'),(v_city_id,'Calawisan'),(v_city_id,'Canjulao'),
(v_city_id,'Caubian'),(v_city_id,'Caw-oy'),(v_city_id,'Cawhagan'),(v_city_id,'Gun-ob'),
(v_city_id,'Ibo'),(v_city_id,'Looc'),(v_city_id,'Mactan'),(v_city_id,'Maribago'),
(v_city_id,'Marigondon'),(v_city_id,'Pajac'),(v_city_id,'Pajo'),(v_city_id,'Pangan-an'),
(v_city_id,'Poblacion'),(v_city_id,'Portcat'),(v_city_id,'Punta Engano'),
(v_city_id,'Pusok'),(v_city_id,'Sabang'),(v_city_id,'Santa Rosa'),
(v_city_id,'Subabasbas'),(v_city_id,'Talima'),(v_city_id,'Tingo'),(v_city_id,'Tungasan')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name='Mandaue City' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
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

SELECT id INTO v_city_id FROM address_cities WHERE name='Talisay City' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
(v_city_id,'Biasong'),(v_city_id,'Bulacao'),(v_city_id,'Cansojong'),
(v_city_id,'Dumlog'),(v_city_id,'Jaclupan'),(v_city_id,'Lagtang'),
(v_city_id,'Lawaan I'),(v_city_id,'Lawaan II'),(v_city_id,'Lawaan III'),
(v_city_id,'Linao'),(v_city_id,'Maghaway'),(v_city_id,'Manipis'),
(v_city_id,'Mohon'),(v_city_id,'Pooc'),(v_city_id,'Poblacion'),
(v_city_id,'San Isidro'),(v_city_id,'San Roque'),(v_city_id,'Tabunok'),
(v_city_id,'Tangke'),(v_city_id,'Tapul')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name='Consolacion' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
(v_city_id,'Bagacay'),(v_city_id,'Butong'),(v_city_id,'Cansaga'),
(v_city_id,'Casili'),(v_city_id,'Danglag'),(v_city_id,'Garing'),
(v_city_id,'Jugan'),(v_city_id,'Lamac'),(v_city_id,'Lanipga'),
(v_city_id,'Nangka'),(v_city_id,'Panas'),(v_city_id,'Panoypoy'),
(v_city_id,'Pitogo'),(v_city_id,'Poblacion Occidental'),(v_city_id,'Poblacion Oriental'),
(v_city_id,'Pulpog'),(v_city_id,'Sacsac'),(v_city_id,'Tayud'),
(v_city_id,'Tilhaong'),(v_city_id,'Tolotolo'),(v_city_id,'Tugbongan')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name='Liloan' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
(v_city_id,'Cabadiangan'),(v_city_id,'Calero'),(v_city_id,'Catarman'),
(v_city_id,'Cotcot'),(v_city_id,'Jubay'),(v_city_id,'Lataban'),
(v_city_id,'Mulao'),(v_city_id,'Poblacion'),(v_city_id,'San Roque'),
(v_city_id,'San Vicente'),(v_city_id,'Santa Cruz'),(v_city_id,'Santander'),
(v_city_id,'Science Park'),(v_city_id,'Tabla'),(v_city_id,'Tayud'),(v_city_id,'Yati')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name='Minglanilla' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
(v_city_id,'Cadulawan'),(v_city_id,'Calajunan'),(v_city_id,'Canlaon'),
(v_city_id,'Cogon'),(v_city_id,'Cuanos'),(v_city_id,'Guindaruhan'),
(v_city_id,'Linao'),(v_city_id,'Manduang'),(v_city_id,'Pakigne'),
(v_city_id,'Poblacion Ward I'),(v_city_id,'Poblacion Ward II'),
(v_city_id,'Poblacion Ward III'),(v_city_id,'Poblacion Ward IV'),
(v_city_id,'Tubod'),(v_city_id,'Tulay'),(v_city_id,'Tunghaan'),
(v_city_id,'Tungkop'),(v_city_id,'Vito')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name='Cordova' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
(v_city_id,'Alegria'),(v_city_id,'Bangbang'),(v_city_id,'Buagsong'),
(v_city_id,'Catarman'),(v_city_id,'Cogon'),(v_city_id,'Dapitan'),
(v_city_id,'Day-as'),(v_city_id,'Gabi'),(v_city_id,'Gilutongan'),
(v_city_id,'Ibabao'),(v_city_id,'Pilipog'),(v_city_id,'Poblacion'),(v_city_id,'San Miguel')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name='Compostela' LIMIT 1;
INSERT INTO address_barangays(city_id,name) VALUES
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
    SELECT b.id, b.name, c.id, c.name, pr.id, pr.name,
           (b.name || ', ' || c.name || ', ' || pr.name)
    FROM address_barangays b
    JOIN address_cities    c  ON c.id  = b.city_id
    JOIN address_provinces pr ON pr.id = c.province_id
    WHERE LOWER(b.name) LIKE v_q OR LOWER(c.name) LIKE v_q
    ORDER BY CASE WHEN LOWER(b.name) LIKE LOWER(TRIM(p_query)) || '%' THEN 0 ELSE 1 END, b.name
    LIMIT p_limit;
END;
$$;

CREATE OR REPLACE PROCEDURE sp_save_address(
    IN  p_street TEXT, IN p_barangay_id INT, IN p_city_id INT,
    IN  p_province_id INT, IN p_zip_code TEXT, OUT p_address_id INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO addresses(street, barangay_id, city_id, province_id, zip_code)
    VALUES(p_street, p_barangay_id, p_city_id, p_province_id, NULLIF(p_zip_code,''))
    RETURNING id INTO p_address_id;
END;
$$;

-- =============================================================================
-- DEFAULT SEED DATA (required for app to function on first install)
-- =============================================================================

INSERT INTO business_info (name, contact, email, address)
VALUES ('Jayraldine''s Catering', '+63 900 000 0000', 'info@jayraldines.com', 'Cebu City, Cebu')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
