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
CREATE TYPE menu_status       AS ENUM ('Available', 'Unavailable', 'Seasonal', 'Out of Stock');
CREATE TYPE kitchen_status    AS ENUM ('Queued', 'Preparing', 'In Progress', 'Ready', 'Delivered', 'Cancelled', 'Done');
CREATE TYPE payment_method    AS ENUM ('Cash', 'Bank Transfer', 'GCash', 'PayMaya');
CREATE TYPE menu_category     AS ENUM ('Main Course','Noodles','Soup','Vegetables','Dessert','Drinks','Bread','Other');
CREATE TYPE menu_package_tier AS ENUM ('Budget','Standard','Premium','Custom');
CREATE TYPE inventory_unit    AS ENUM ('kg','g','L','mL','pcs','packs','trays','boxes');

-- =============================================================================
-- TABLE: business_info
-- =============================================================================
CREATE TABLE business_info (
    id          SERIAL          PRIMARY KEY,
    name        VARCHAR(120)    NOT NULL DEFAULT 'Jayraldine''s Catering',
    contact     VARCHAR(30)     NOT NULL,
    email       VARCHAR(120),
    address     TEXT,
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
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
    status          customer_status NOT NULL DEFAULT 'Active',
    total_events    INT             NOT NULL DEFAULT 0 CHECK (total_events >= 0),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_customers_name_contact ON customers (name, contact);

INSERT INTO customers (name, contact, email, status, total_events) VALUES
  ('Maria Santos',   '+63 912 345 6789', 'maria@email.com',    'Active',  3),
  ('TechCorp Inc.',  '+63 917 000 1234', 'events@techcorp.ph', 'Active',  1),
  ('Cruz Family',    '+63 920 111 2222', 'cruz@gmail.com',     'Active',  2),
  ('Smith Wedding',  '+63 932 555 6666', 'smith@yahoo.com',    'Pending', 1);

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
    id              SERIAL          PRIMARY KEY,
    booking_ref     VARCHAR(12)     NOT NULL UNIQUE,
    customer_id     INT             REFERENCES customers(id) ON DELETE SET NULL,
    customer_name   VARCHAR(150)    NOT NULL,
    contact         VARCHAR(30),
    email           VARCHAR(120),
    address         TEXT,
    occasion        VARCHAR(120)    NOT NULL,
    venue           VARCHAR(200)    NOT NULL,
    event_date      DATE            NOT NULL,
    event_time      TIME            NOT NULL DEFAULT '18:00:00',
    pax             INT             NOT NULL CHECK (pax >= 1),
    special_notes   TEXT,
    menu_type       VARCHAR(10)     NOT NULL DEFAULT 'package' CHECK (menu_type IN ('package','custom')),
    package_id      INT             REFERENCES packages(id) ON DELETE SET NULL,
    custom_items    TEXT,
    total_amount    NUMERIC(12,2)   NOT NULL CHECK (total_amount >= 0),
    payment_mode    payment_method  NOT NULL DEFAULT 'Cash',
    amount_paid     NUMERIC(12,2)   NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    status          booking_status  NOT NULL DEFAULT 'PENDING',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
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
-- TABLE: inventory
-- =============================================================================
CREATE TABLE inventory (
    id          SERIAL          PRIMARY KEY,
    ingredient  VARCHAR(120)    NOT NULL UNIQUE,
    unit        inventory_unit  NOT NULL,
    stock       NUMERIC(10,2)   NOT NULL DEFAULT 0 CHECK (stock >= 0),
    min_stock   NUMERIC(10,2)   NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

INSERT INTO inventory (ingredient, unit, stock, min_stock) VALUES
  ('Chicken',     'kg', 8,  20),
  ('Rice',        'kg', 15, 30),
  ('Cooking Oil', 'L',  4,  10),
  ('Pork',        'kg', 25, 15),
  ('Flour',       'kg', 40, 10);

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

INSERT INTO notifications (type, title, message, color) VALUES
  ('warning', 'Payment Pending',    'Invoice #BKG-002 (Smith Wedding) requires a 50% downpayment of ₱60,000.',  '#F59E0B'),
  ('success', 'Booking Confirmed',  'TechCorp Inc. booking for Oct 24 has been confirmed. 150 pax.',             '#22C55E'),
  ('info',    'New Booking Request','Cruz Corporate submitted an event inquiry for Apr 30, 2026.',               '#3B82F6');

-- =============================================================================
-- SEQUENCES for reference number generation
-- =============================================================================
CREATE SEQUENCE IF NOT EXISTS seq_booking_ref START 5;
CREATE SEQUENCE IF NOT EXISTS seq_invoice_ref START 5;
CREATE SEQUENCE IF NOT EXISTS seq_order_ref   START 5;

-- =============================================================================
-- STORED PROCEDURE: sp_next_booking_ref
-- Generates next booking reference number
-- OUT p_ref TEXT
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_next_booking_ref(OUT p_ref TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    p_ref := 'BKG-' || LPAD(nextval('seq_booking_ref')::TEXT, 3, '0');
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_next_invoice_ref
-- OUT p_ref TEXT
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_next_invoice_ref(OUT p_ref TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    p_ref := 'INV-' || LPAD(nextval('seq_invoice_ref')::TEXT, 3, '0');
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_next_order_ref
-- OUT p_ref TEXT
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
-- Updates all editable fields of a booking
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
-- Updates only the status field of a booking
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_booking_status(
    IN p_booking_id  INT,
    IN p_new_status  TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE bookings
    SET status = p_new_status::booking_status, updated_at = NOW()
    WHERE id = p_booking_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_booking
-- Deletes a booking by id
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_booking(IN p_booking_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM bookings WHERE id = p_booking_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_create_invoice
-- Inserts a new invoice record
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
-- Updates all editable fields of an invoice
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_invoice(
    IN p_invoice_id   INT,
    IN p_customer_name TEXT,
    IN p_event_date   DATE,
    IN p_total_amount NUMERIC,
    IN p_amount_paid  NUMERIC,
    IN p_status       TEXT
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
-- Deletes an invoice by id
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_invoice(IN p_invoice_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM invoices WHERE id = p_invoice_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_menu_item
-- Inserts a new menu item
-- OUT p_item_id INT
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_menu_item(
    IN  p_name     TEXT,
    IN  p_category TEXT,
    IN  p_package  TEXT,
    IN  p_price    NUMERIC,
    IN  p_status   TEXT,
    OUT p_item_id  INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO menu_items (name, category, package_tier, price, status)
    VALUES (
        p_name,
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
-- Updates an existing menu item
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_menu_item(
    IN p_item_id   INT,
    IN p_name      TEXT,
    IN p_category  TEXT,
    IN p_package   TEXT,
    IN p_price     NUMERIC,
    IN p_status    TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE menu_items
    SET
        name         = p_name,
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
-- Deletes a menu item by id
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_menu_item(IN p_item_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM menu_items WHERE id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_customer
-- Inserts a new customer record
-- OUT p_customer_id INT
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_customer(
    IN  p_name         TEXT,
    IN  p_contact      TEXT,
    IN  p_email        TEXT,
    IN  p_status       TEXT,
    OUT p_customer_id  INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO customers (name, contact, email, status)
    VALUES (p_name, p_contact, p_email, p_status::customer_status)
    ON CONFLICT DO NOTHING
    RETURNING id INTO p_customer_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_customer
-- Updates an existing customer record
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_customer(
    IN p_customer_id INT,
    IN p_name        TEXT,
    IN p_contact     TEXT,
    IN p_email       TEXT,
    IN p_status      TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE customers
    SET
        name       = p_name,
        contact    = p_contact,
        email      = p_email,
        status     = p_status::customer_status,
        updated_at = NOW()
    WHERE id = p_customer_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_customer
-- Deletes a customer by id
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_customer(IN p_customer_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM customers WHERE id = p_customer_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_add_inventory_item
-- Inserts a new inventory item
-- OUT p_item_id INT
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_add_inventory_item(
    IN  p_ingredient TEXT,
    IN  p_unit       TEXT,
    IN  p_stock      NUMERIC,
    IN  p_min_stock  NUMERIC,
    OUT p_item_id    INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO inventory (ingredient, unit, stock, min_stock)
    VALUES (p_ingredient, p_unit::inventory_unit, p_stock, p_min_stock)
    RETURNING id INTO p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_update_inventory_item
-- Updates ingredient name, unit and min_stock for an inventory item
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_update_inventory_item(
    IN p_item_id    INT,
    IN p_ingredient TEXT,
    IN p_unit       TEXT,
    IN p_min_stock  NUMERIC
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE inventory
    SET
        ingredient = p_ingredient,
        unit       = p_unit::inventory_unit,
        min_stock  = p_min_stock,
        updated_at = NOW()
    WHERE id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_adjust_inventory_stock
-- Adjusts stock by a delta (positive = restock, negative = usage)
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
    WHERE id = p_item_id
    RETURNING stock INTO p_new_stock;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_delete_inventory_item
-- Deletes an inventory item by id
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_inventory_item(IN p_item_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM inventory WHERE id = p_item_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_create_kitchen_order
-- Inserts a new kitchen order
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
-- Updates the status of a kitchen order
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
-- Deletes a kitchen order by id
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_delete_kitchen_order(IN p_order_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM kitchen_orders WHERE id = p_order_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_dismiss_notification
-- Marks a single notification as read
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_dismiss_notification(IN p_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE notifications SET is_read = TRUE WHERE id = p_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_mark_all_notifications_read
-- Marks all unread notifications as read
-- =============================================================================
CREATE OR REPLACE PROCEDURE sp_mark_all_notifications_read()
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE notifications SET is_read = TRUE WHERE is_read = FALSE;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: sp_save_business_info
-- Updates the single business_info row
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
-- STORED PROCEDURE: sp_calculate_total_amount
-- Calculates total booking cost from pax and package
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
  AND b.status != 'CANCELLED'
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
    event_date,
    COUNT(*)    AS booking_count,
    SUM(pax)    AS total_pax
FROM bookings
WHERE status != 'CANCELLED'
GROUP BY event_date;

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
