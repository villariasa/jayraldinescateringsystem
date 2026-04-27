-- =============================================================================
-- Jayraldine's Catering Management System
-- PostgreSQL Database Schema + Stored Procedures
-- =============================================================================
-- Run this script once as a PostgreSQL superuser:
--   psql -U postgres -f jayraldines_catering.sql
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
CREATE TYPE booking_status    AS ENUM ('PENDING', 'CONFIRMED', 'CANCELLED');
CREATE TYPE invoice_status    AS ENUM ('Unpaid', 'Partial', 'Paid');
CREATE TYPE customer_status   AS ENUM ('Active', 'Pending', 'Inactive');
CREATE TYPE loyalty_tier      AS ENUM ('Bronze', 'Silver', 'Gold', 'VIP');
CREATE TYPE menu_status       AS ENUM ('Available', 'Unavailable', 'Seasonal', 'Out of Stock');
CREATE TYPE kitchen_status    AS ENUM ('Queued', 'Preparing', 'In Progress', 'Ready', 'Delivered', 'Cancelled', 'Done');
CREATE TYPE payment_method    AS ENUM ('Cash', 'Bank Transfer', 'GCash', 'PayMaya');
CREATE TYPE menu_category     AS ENUM ('Main Course','Noodles','Soup','Vegetables','Dessert','Drinks','Bread','Other');
CREATE TYPE menu_package_tier AS ENUM ('Budget','Standard','Premium','Custom');
CREATE TYPE inventory_unit    AS ENUM ('kg','g','L','mL','pcs','packs','trays','boxes');
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
    -- SMTP email config (Feature 2)
    smtp_host               VARCHAR(120),
    smtp_port               INT             DEFAULT 587,
    smtp_user               VARCHAR(120),
    smtp_pass               TEXT,
    -- SMS config (Feature 3)
    sms_api_key             TEXT,
    -- Booking policy (Feature 4)
    min_downpayment_pct     NUMERIC(5,2)    NOT NULL DEFAULT 30.00,
    allow_zero_downpayment  BOOLEAN         NOT NULL DEFAULT FALSE,
    -- Capacity policy (Feature 5)
    max_daily_pax           INT             NOT NULL DEFAULT 600,
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

INSERT INTO business_info (name, contact, email, address)
VALUES ('Jayraldine''s Catering', '+63 912 345 6789',
        'admin@jayraldines.com', '123 Rizal St., Manila, Metro Manila');

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

INSERT INTO customers (name, contact, email, status, loyalty_tier, total_events) VALUES
  ('Maria Santos',   '+63 912 345 6789', 'maria@email.com',    'Active',  'Silver', 3),
  ('TechCorp Inc.',  '+63 917 000 1234', 'events@techcorp.ph', 'Active',  'Bronze', 1),
  ('Cruz Family',    '+63 920 111 2222', 'cruz@gmail.com',     'Active',  'Silver', 2),
  ('Smith Wedding',  '+63 932 555 6666', 'smith@yahoo.com',    'Pending', 'Bronze', 1);

-- =============================================================================
-- TABLE: packages
-- =============================================================================
CREATE TABLE packages (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL UNIQUE,
    price_per_pax   NUMERIC(10,2)   NOT NULL CHECK (price_per_pax > 0),
    description     TEXT
);

INSERT INTO packages (name, price_per_pax, description) VALUES
  ('Standard Package', 1500.00, 'Buffet setup, 5 dishes, dessert'),
  ('Premium Package',  2500.00, 'Plated service, 8 dishes, dessert + drinks'),
  ('VIP Package',      3500.00, 'Full service, 12 dishes, open bar, décor');

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

INSERT INTO menu_items (name, category, package_tier, price, status) VALUES
  ('Lechon de Leche',  'Main Course', 'Premium',  8500.00, 'Available'),
  ('Kare-Kare',        'Main Course', 'Standard', 3500.00, 'Available'),
  ('Pancit Malabon',   'Noodles',     'Standard', 1800.00, 'Available'),
  ('Buko Pandan',      'Dessert',     'Standard',  950.00, 'Available'),
  ('Leche Flan',       'Dessert',     'Premium',  1200.00, 'Available'),
  ('Chicken Inasal',   'Main Course', 'Budget',   2200.00, 'Available'),
  ('Chopsuey',         'Vegetables',  'Budget',   1200.00, 'Available'),
  ('Puto Bumbong',     'Dessert',     'Budget',    600.00, 'Seasonal');

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

INSERT INTO bookings
  (booking_ref, customer_name, occasion, venue, event_date, pax,
   menu_type, total_amount, payment_mode, amount_paid, status)
VALUES
  ('BKG-001','TechCorp Inc.',  'Corporate Dinner',  'Makati CBD',     '2026-10-24', 150, 'package', 45000,  'Cash',          45000,  'CONFIRMED'),
  ('BKG-002','Smith Wedding',  'Wedding Reception', 'Tagaytay Venue', '2026-10-25', 300, 'package', 120000, 'Bank Transfer', 60000,  'PENDING'),
  ('BKG-003','Sarah''s 18th',  'Debut',             'Quezon City',    '2026-10-26', 100, 'package', 35000,  'GCash',         35000,  'CONFIRMED'),
  ('BKG-004','Local NGO Meet', 'Corporate Meeting', 'Manila Hotel',   '2026-10-28',  60, 'package', 18000,  'Cash',          0,      'CANCELLED');

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

INSERT INTO invoices (invoice_ref, customer_name, event_date, total_amount, amount_paid, status) VALUES
  ('INV-001','Maria Santos',  '2026-04-30',  45000.00,  22500.00, 'Partial'),
  ('INV-002','TechCorp Inc.', '2025-10-24', 120000.00, 120000.00, 'Paid'),
  ('INV-003','Cruz Family',   '2025-12-15',  85000.00,      0.00, 'Unpaid'),
  ('INV-004','Smith Wedding', '2026-06-12', 200000.00,  60000.00, 'Partial');

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

INSERT INTO kitchen_orders (order_ref, client_name, event_name, pax, items_desc, status) VALUES
  ('ORD-001','Maria Santos',  'Birthday Party',    80,  'Lechon, Kare-Kara, Buko Pandan',    'Queued'),
  ('ORD-002','TechCorp Inc.', 'Corporate Dinner',  150, 'Chicken Inasal, Pancit, Leche Flan', 'In Progress'),
  ('ORD-003','Cruz Family',   'Debut',             200, 'Lechon, Kare-Kare, Chopsuey',        'Ready'),
  ('ORD-004','Smith Wedding', 'Wedding Reception', 300, 'Full Package Premium',                'Queued');

-- =============================================================================
-- TABLE: kitchen_tasks  (Feature 6 — per-dish checklist)
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
-- TABLE: inventory
-- =============================================================================
CREATE TABLE inventory (
    id           SERIAL          PRIMARY KEY,
    ingredient   VARCHAR(120)    NOT NULL UNIQUE,
    unit         inventory_unit  NOT NULL,
    stock        NUMERIC(10,2)   NOT NULL DEFAULT 0 CHECK (stock >= 0),
    min_stock    NUMERIC(10,2)   NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    expiry_date  DATE,
    updated_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

INSERT INTO inventory (ingredient, unit, stock, min_stock) VALUES
  ('Chicken',     'kg', 8,  20),
  ('Rice',        'kg', 15, 30),
  ('Cooking Oil', 'L',  4,  10),
  ('Pork',        'kg', 25, 15),
  ('Flour',       'kg', 40, 10);

-- =============================================================================
-- TABLE: expenses  (Feature 8 — profit/expense tracking)
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
-- TABLE: customer_follow_ups  (Feature 9 — loyalty / follow-up reminders)
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
-- TABLE: communication_logs  (Feature 2 & 3 — receipt/confirmation sends)
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
-- TABLE: audit_logs  (Feature 10 — audit trail)
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

INSERT INTO notifications (type, title, message, color, is_read) VALUES
  ('warning', 'Payment Pending',    'Invoice #BKG-002 (Smith Wedding) requires a 50% downpayment of ₱60,000.',  '#F59E0B', TRUE),
  ('success', 'Booking Confirmed',  'TechCorp Inc. booking for Oct 24 has been confirmed. 150 pax.',             '#22C55E', TRUE),
  ('info',    'New Booking Request','Cruz Corporate submitted an event inquiry for Apr 30, 2026.',               '#3B82F6', TRUE);

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
CREATE SEQUENCE IF NOT EXISTS seq_booking_ref START 5;
CREATE SEQUENCE IF NOT EXISTS seq_invoice_ref START 5;
CREATE SEQUENCE IF NOT EXISTS seq_order_ref   START 5;

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
-- Inserts a new booking and increments customer event count
-- OUT p_booking_id INT, OUT p_booking_ref TEXT
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
-- Transitions a PENDING booking to CONFIRMED or CANCELLED.
-- Feature 4: enforces minimum downpayment before confirming.
-- Feature 7: stores cancellation_reason when cancelling.
-- OUT p_booking_id INT, OUT p_new_status TEXT, OUT p_cancellation_reason TEXT
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
BEGIN
    SELECT status, amount_paid, total_amount
    INTO v_current, v_amount_paid, v_total
    FROM bookings WHERE id = p_booking_id;

    IF v_current IN ('CONFIRMED', 'CANCELLED') THEN
        RAISE EXCEPTION 'Booking status is locked. Cannot change from % to %.',
            v_current, p_new_status;
    END IF;

    IF v_current != 'PENDING' THEN
        RAISE EXCEPTION 'Only PENDING bookings can be transitioned.';
    END IF;

    IF p_new_status = 'CONFIRMED' THEN
        SELECT min_downpayment_pct, allow_zero_downpayment
        INTO v_min_pct, v_allow_zero
        FROM business_info WHERE id = 1;

        v_min_pct   := COALESCE(v_min_pct, 30);
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
-- Feature 5: returns pax booked on a date vs max capacity.
-- Pass p_exclude_id = 0 when creating; pass booking id when editing.
-- OUT p_booked_pax INT, OUT p_max_pax INT, OUT p_is_over BOOLEAN
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
-- OUT p_invoice_id INT, OUT p_invoice_ref TEXT
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_create_invoice(
    IN  p_booking_id    INT,
    IN  p_customer_name TEXT,
    IN  p_event_date    DATE,
    IN  p_total_amount  NUMERIC,
    IN  p_amount_paid   NUMERIC,
    IN  p_status        TEXT,
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
        p_total_amount, p_amount_paid, p_status::invoice_status
    )
    RETURNING id INTO p_invoice_id;
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
-- Adds a payment amount to an invoice and recalculates its status
-- OUT p_new_status TEXT
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
-- STORED PROCEDURE: sp_add_menu_item
-- OUT p_item_id INT
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
        p_name,
        p_description,
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
-- OUT p_customer_id INT
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
-- Feature 9: updates a customer's loyalty_tier based on total_events
-- Bronze: 1-2, Silver: 3-5, Gold: 6-9, VIP: 10+
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
-- Feature 9: insert a customer follow-up reminder
-- OUT p_follow_up_id INT
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
-- STORED PROCEDURE: sp_add_inventory_item
-- OUT p_item_id INT
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_inventory_item(
    IN  p_ingredient   TEXT,
    IN  p_unit         TEXT,
    IN  p_stock        NUMERIC,
    IN  p_min_stock    NUMERIC,
    IN  p_expiry_date  DATE,
    OUT p_item_id      INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO inventory (ingredient, unit, stock, min_stock, expiry_date)
    VALUES (p_ingredient, p_unit::inventory_unit, p_stock, p_min_stock, p_expiry_date)
    RETURNING id INTO p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_inventory_item
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_inventory_item(
    IN p_item_id      INT,
    IN p_ingredient   TEXT,
    IN p_unit         TEXT,
    IN p_min_stock    NUMERIC,
    IN p_expiry_date  DATE
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE inventory
    SET
        ingredient  = p_ingredient,
        unit        = p_unit::inventory_unit,
        min_stock   = p_min_stock,
        expiry_date = p_expiry_date,
        updated_at  = NOW()
    WHERE id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_adjust_inventory_stock
-- OUT p_new_stock NUMERIC
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_adjust_inventory_stock(
    IN  p_item_id   INT,
    IN  p_delta     NUMERIC,
    OUT p_new_stock NUMERIC
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE inventory
    SET stock = GREATEST(0, stock + p_delta), updated_at = NOW()
    WHERE id = p_item_id;

    SELECT stock INTO p_new_stock FROM inventory WHERE id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_inventory_item
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_inventory_item(IN p_item_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM inventory WHERE id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_create_kitchen_order
-- OUT p_order_id INT, OUT p_order_ref TEXT
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
-- Feature 6: insert a per-dish task for a kitchen order
-- OUT p_task_id INT
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
-- OUT p_new_state BOOLEAN
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
-- Feature 8: insert a new expense record
-- OUT p_expense_id INT
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
-- OUT p_id INT
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
-- Feature 2: updates SMTP email settings
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
-- STORED PROCEDURE: sp_save_sms_config
-- Feature 3: updates SMS API key
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_save_sms_config(IN p_sms_api_key TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE business_info
    SET sms_api_key = p_sms_api_key, updated_at = NOW()
    WHERE id = 1;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_save_booking_policy
-- Feature 4: updates downpayment enforcement settings
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
-- Feature 5: updates max daily pax
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
-- Feature 2 & 3: records receipt or booking confirmation send
-- OUT p_log_id INT
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
-- Feature 10: inserts one audit log entry
-- OUT p_log_id INT
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
-- OUT p_total NUMERIC
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
-- OUT p_id INT
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
-- Returns bookings near their event time for notification scheduling
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
-- VIEW: v_dashboard_kpis
-- =============================================================================
CREATE OR REPLACE VIEW v_dashboard_kpis AS
SELECT
    (SELECT COUNT(*) FROM bookings WHERE event_date = CURRENT_DATE)                         AS todays_events,
    (SELECT COUNT(*) FROM bookings WHERE status = 'PENDING')                                AS pending_bookings,
    (SELECT COALESCE(SUM(total_amount),0) FROM bookings
     WHERE event_date BETWEEN date_trunc('week', CURRENT_DATE)
                          AND date_trunc('week', CURRENT_DATE) + INTERVAL '6 days')         AS weekly_revenue,
    (SELECT COALESCE(SUM(total_amount - amount_paid),0) FROM invoices WHERE status != 'Paid') AS unpaid_invoices,
    (SELECT COALESCE(SUM(pax),0) FROM bookings WHERE event_date = CURRENT_DATE)             AS todays_pax;

-- =============================================================================
-- VIEW: v_upcoming_events
-- =============================================================================
CREATE OR REPLACE VIEW v_upcoming_events AS
SELECT
    b.id,
    b.booking_ref,
    b.customer_name,
    b.occasion,
    b.venue,
    b.event_date,
    b.event_time,
    b.pax,
    b.status
FROM bookings b
WHERE b.event_date >= CURRENT_DATE
  AND b.status = 'CONFIRMED'
ORDER BY b.event_date, b.event_time;

-- =============================================================================
-- VIEW: v_inventory_alerts
-- =============================================================================
CREATE OR REPLACE VIEW v_inventory_alerts AS
SELECT
    id,
    ingredient,
    unit,
    stock,
    min_stock,
    ROUND((stock / NULLIF(min_stock,0)) * 100, 1) AS stock_pct
FROM inventory
WHERE stock < min_stock
ORDER BY stock_pct;

-- =============================================================================
-- VIEW: v_calendar_day_summary
-- =============================================================================
CREATE OR REPLACE VIEW v_calendar_day_summary AS
SELECT
    b.event_date,
    COUNT(*)                            AS booking_count,
    SUM(b.pax)                         AS total_pax,
    bi.max_daily_pax,
    CASE
        WHEN SUM(b.pax) >= bi.max_daily_pax            THEN 'Full'
        WHEN SUM(b.pax) >= bi.max_daily_pax * 0.67     THEN 'Near Full'
        ELSE                                                 'Available'
    END                                AS capacity_status
FROM bookings b
CROSS JOIN (SELECT max_daily_pax FROM business_info LIMIT 1) bi
WHERE b.status != 'CANCELLED'
GROUP BY b.event_date, bi.max_daily_pax;

-- =============================================================================
-- VIEW: v_reports_summary
-- =============================================================================
CREATE OR REPLACE VIEW v_reports_summary AS
SELECT
    b.booking_ref,
    b.event_date,
    b.customer_name,
    COALESCE(p.name, 'Custom') AS package_name,
    b.pax,
    b.total_amount,
    b.status
FROM bookings b
LEFT JOIN packages p ON p.id = b.package_id
ORDER BY b.event_date DESC;

-- =============================================================================
-- VIEW: v_monthly_income
-- =============================================================================
CREATE OR REPLACE VIEW v_monthly_income AS
SELECT
    TO_CHAR(event_date, 'Mon') AS month_label,
    EXTRACT(MONTH FROM event_date)::INT AS month_num,
    COALESCE(SUM(total_amount), 0)::FLOAT AS total_revenue,
    COALESCE(SUM(amount_paid), 0)::FLOAT AS total_paid
FROM invoices
WHERE EXTRACT(YEAR FROM event_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY month_label, month_num
ORDER BY month_num;

-- =============================================================================
-- VIEW: v_payment_methods
-- =============================================================================
CREATE OR REPLACE VIEW v_payment_methods AS
SELECT
    payment_mode::TEXT AS method,
    COUNT(*) AS total
FROM bookings
GROUP BY payment_mode;

-- =============================================================================
-- VIEW: v_top_menu_items
-- =============================================================================
CREATE OR REPLACE VIEW v_top_menu_items AS
SELECT
    mi.name AS item,
    COUNT(*) AS order_count
FROM booking_menu_items bmi
JOIN menu_items mi ON mi.id = bmi.item_id
GROUP BY mi.name
ORDER BY order_count DESC
LIMIT 10;

-- =============================================================================
-- VIEW: v_customer_order_frequency
-- =============================================================================
CREATE OR REPLACE VIEW v_customer_order_frequency AS
SELECT name, booking_count FROM (
    SELECT customer_name AS name, COUNT(*) AS booking_count
    FROM bookings
    GROUP BY customer_name
    ORDER BY booking_count DESC
    LIMIT 5
) top5
UNION ALL
SELECT 'Others', COUNT(*) FROM (
    SELECT customer_name FROM (
        SELECT customer_name, RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
        FROM bookings GROUP BY customer_name
    ) ranked WHERE rnk > 5
) rest;

-- =============================================================================
-- VIEW: v_report_kpis
-- =============================================================================
CREATE OR REPLACE VIEW v_report_kpis AS
SELECT
    COUNT(*)                                                                    AS total_bookings,
    COALESCE(SUM(b.pax), 0)::INT                                               AS total_pax,
    COALESCE((SELECT SUM(total_amount) FROM invoices), 0)::FLOAT               AS total_revenue,
    COALESCE((SELECT SUM(total_amount - amount_paid) FROM invoices WHERE status != 'Paid'), 0)::FLOAT AS unpaid_amount,
    COALESCE((SELECT COUNT(*) FROM bookings WHERE DATE(event_date) = CURRENT_DATE), 0)::INT AS today_bookings,
    COALESCE((SELECT COUNT(*) FROM bookings
              WHERE event_date BETWEEN date_trunc('week', CURRENT_DATE)
                                   AND date_trunc('week', CURRENT_DATE) + INTERVAL '6 days'), 0)::INT AS week_bookings
FROM bookings b;

-- =============================================================================
-- VIEW: v_recent_activity
-- =============================================================================
CREATE OR REPLACE VIEW v_recent_activity AS
SELECT
    title,
    description,
    color,
    created_at
FROM (
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

-- =============================================================================
-- VIEW: v_menu_alerts
-- =============================================================================
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
UNION ALL
SELECT
    mi.name AS item,
    'Ingredient near low stock' AS issue,
    'danger' AS badge_type
FROM inventory inv
JOIN menu_items mi ON LOWER(mi.name) LIKE '%' || LOWER(inv.ingredient) || '%'
WHERE inv.stock < inv.min_stock
ORDER BY badge_type DESC, item
LIMIT 10;

-- =============================================================================
-- VIEW: v_profit_summary
-- Feature 8: monthly revenue vs expenses vs net profit (current year)
-- =============================================================================
CREATE OR REPLACE VIEW v_profit_summary AS
SELECT
    COALESCE(m.month_num, e.month_num)                                  AS month_num,
    COALESCE(m.month_label, TO_CHAR(TO_DATE(e.month_num::TEXT, 'MM'), 'Mon')) AS month_label,
    COALESCE(m.revenue, 0)::FLOAT                                       AS revenue,
    COALESCE(e.total_expense, 0)::FLOAT                                 AS total_expense,
    (COALESCE(m.revenue, 0) - COALESCE(e.total_expense, 0))::FLOAT     AS net_profit
FROM (
    SELECT
        EXTRACT(MONTH FROM event_date)::INT AS month_num,
        TO_CHAR(event_date, 'Mon')          AS month_label,
        SUM(total_amount)                   AS revenue
    FROM invoices
    WHERE EXTRACT(YEAR FROM event_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY month_num, month_label
) m
FULL OUTER JOIN (
    SELECT
        EXTRACT(MONTH FROM expense_date)::INT AS month_num,
        SUM(amount)                           AS total_expense
    FROM expenses
    WHERE EXTRACT(YEAR FROM expense_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY month_num
) e ON m.month_num = e.month_num
ORDER BY COALESCE(m.month_num, e.month_num);

-- =============================================================================
-- VIEW: v_audit_log_recent
-- Feature 10: last 50 audit entries with human-readable description
-- =============================================================================
CREATE OR REPLACE VIEW v_audit_log_recent AS
SELECT
    id,
    actor,
    action,
    table_name,
    record_id,
    old_value,
    new_value,
    created_at,
    actor || ' — ' || action || ' on ' || table_name
        || COALESCE(' #' || record_id::TEXT, '') AS description
FROM audit_logs
ORDER BY created_at DESC
LIMIT 50;

-- =============================================================================
-- GRANT (uncomment after creating the user)
-- psql -U postgres -c "CREATE USER catering_owner WITH PASSWORD 'change_me';"
-- =============================================================================
-- GRANT CONNECT ON DATABASE jayraldines_catering TO catering_owner;
-- GRANT USAGE  ON SCHEMA public TO catering_owner;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO catering_owner;
-- GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO catering_owner;
-- GRANT EXECUTE                        ON ALL ROUTINES  IN SCHEMA public TO catering_owner;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
