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
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()

-- =============================================================================
-- ENUMERATIONS
-- =============================================================================

CREATE TYPE booking_status   AS ENUM ('PENDING', 'CONFIRMED', 'CANCELLED');
CREATE TYPE invoice_status   AS ENUM ('Unpaid', 'Partial', 'Paid');
CREATE TYPE customer_status  AS ENUM ('Active', 'Pending', 'Inactive');
CREATE TYPE menu_status      AS ENUM ('Available', 'Unavailable', 'Seasonal', 'Out of Stock');
CREATE TYPE kitchen_status   AS ENUM ('Queued', 'Preparing', 'In Progress', 'Ready', 'Delivered', 'Cancelled', 'Done');
CREATE TYPE payment_method   AS ENUM ('Cash', 'Bank Transfer', 'GCash', 'PayMaya');
CREATE TYPE menu_category    AS ENUM ('Main Course','Noodles','Soup','Vegetables','Dessert','Drinks','Bread','Other');
CREATE TYPE menu_package_tier AS ENUM ('Budget','Standard','Premium','Custom');
CREATE TYPE inventory_unit   AS ENUM ('kg','g','L','mL','pcs','packs','trays','boxes');

-- =============================================================================
-- TABLE: business_info
-- Stores the single-owner business profile (Settings page)
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
-- Matches CustomersPage / AddCustomerDialog
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
-- The three hard-coded packages shown in BookingModal Step 2
-- =============================================================================
CREATE TABLE packages (
    id          SERIAL          PRIMARY KEY,
    name        VARCHAR(100)    NOT NULL UNIQUE,
    price_per_pax NUMERIC(10,2) NOT NULL CHECK (price_per_pax > 0),
    description TEXT
);

INSERT INTO packages (name, price_per_pax, description) VALUES
  ('Standard Package', 1500.00, 'Buffet setup, 5 dishes, dessert'),
  ('Premium Package',  2500.00, 'Plated service, 8 dishes, dessert + drinks'),
  ('VIP Package',      3500.00, 'Full service, 12 dishes, open bar, décor');

-- =============================================================================
-- TABLE: menu_items
-- Matches MenuPage / menu_store.py
-- =============================================================================
CREATE TABLE menu_items (
    id          SERIAL              PRIMARY KEY,
    name        VARCHAR(120)        NOT NULL UNIQUE,
    category    menu_category       NOT NULL DEFAULT 'Other',
    package_tier menu_package_tier  NOT NULL DEFAULT 'Standard',
    price       NUMERIC(10,2)       NOT NULL CHECK (price >= 0),
    status      menu_status         NOT NULL DEFAULT 'Available',
    created_at  TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ         NOT NULL DEFAULT NOW()
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
-- Matches BookingPage / BookingModal (all 4 steps)
-- =============================================================================
CREATE TABLE bookings (
    id              SERIAL          PRIMARY KEY,
    booking_ref     VARCHAR(12)     NOT NULL UNIQUE,   -- e.g. BKG-001
    customer_id     INT             REFERENCES customers(id) ON DELETE SET NULL,
    customer_name   VARCHAR(150)    NOT NULL,           -- denormalised for display
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
    custom_items    TEXT,           -- comma-separated item names when menu_type='custom'
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
-- Junction: which custom menu items were selected for a booking
-- =============================================================================
CREATE TABLE booking_menu_items (
    booking_id  INT NOT NULL REFERENCES bookings(id)    ON DELETE CASCADE,
    item_id     INT NOT NULL REFERENCES menu_items(id)  ON DELETE CASCADE,
    PRIMARY KEY (booking_id, item_id)
);

-- =============================================================================
-- TABLE: invoices
-- Matches BillingPage / NewInvoiceDialog
-- =============================================================================
CREATE TABLE invoices (
    id              SERIAL          PRIMARY KEY,
    invoice_ref     VARCHAR(12)     NOT NULL UNIQUE,   -- e.g. INV-001
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
-- Matches KitchenPage kanban board
-- =============================================================================
CREATE TABLE kitchen_orders (
    id          SERIAL          PRIMARY KEY,
    order_ref   VARCHAR(12)     NOT NULL UNIQUE,   -- e.g. ORD-001
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
  ('ORD-001','Maria Santos',  'Birthday Party',    80,  'Lechon, Kare-Kare, Buko Pandan',   'Queued'),
  ('ORD-002','TechCorp Inc.', 'Corporate Dinner',  150, 'Chicken Inasal, Pancit, Leche Flan','In Progress'),
  ('ORD-003','Cruz Family',   'Debut',             200, 'Lechon, Kare-Kare, Chopsuey',       'Ready'),
  ('ORD-004','Smith Wedding', 'Wedding Reception', 300, 'Full Package Premium',               'Queued');

-- =============================================================================
-- TABLE: inventory
-- Matches InventoryPage
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
-- Persists the notifications shown in NotificationsPanel
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
-- SEQUENCE HELPERS (used by stored procedures to generate refs)
-- =============================================================================
CREATE SEQUENCE IF NOT EXISTS seq_booking_ref START 5;
CREATE SEQUENCE IF NOT EXISTS seq_invoice_ref START 5;
CREATE SEQUENCE IF NOT EXISTS seq_order_ref   START 5;

-- =============================================================================
-- FUNCTION: next_booking_ref()
-- =============================================================================
CREATE OR REPLACE FUNCTION next_booking_ref()
RETURNS TEXT LANGUAGE plpgsql AS $$
BEGIN
    RETURN 'BKG-' || LPAD(nextval('seq_booking_ref')::TEXT, 3, '0');
END;
$$;

CREATE OR REPLACE FUNCTION next_invoice_ref()
RETURNS TEXT LANGUAGE plpgsql AS $$
BEGIN
    RETURN 'INV-' || LPAD(nextval('seq_invoice_ref')::TEXT, 3, '0');
END;
$$;

CREATE OR REPLACE FUNCTION next_order_ref()
RETURNS TEXT LANGUAGE plpgsql AS $$
BEGIN
    RETURN 'ORD-' || LPAD(nextval('seq_order_ref')::TEXT, 3, '0');
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: create_booking
-- Called when BookingModal emits booking_saved signal
-- =============================================================================
CREATE OR REPLACE FUNCTION create_booking(
    p_customer_name  TEXT,
    p_contact        TEXT,
    p_email          TEXT,
    p_address        TEXT,
    p_occasion       TEXT,
    p_venue          TEXT,
    p_event_date     DATE,
    p_event_time     TIME,
    p_pax            INT,
    p_special_notes  TEXT,
    p_menu_type      TEXT,
    p_package_id     INT,
    p_custom_items   TEXT,
    p_total_amount   NUMERIC,
    p_payment_mode   TEXT,
    p_amount_paid    NUMERIC
)
RETURNS TABLE (booking_id INT, booking_ref TEXT)
LANGUAGE plpgsql AS $$
DECLARE
    v_ref       TEXT;
    v_bid       INT;
    v_cid       INT;
BEGIN
    v_ref := next_booking_ref();

    SELECT id INTO v_cid FROM customers WHERE name = p_customer_name LIMIT 1;

    INSERT INTO bookings (
        booking_ref, customer_id, customer_name, contact, email, address,
        occasion, venue, event_date, event_time, pax, special_notes,
        menu_type, package_id, custom_items,
        total_amount, payment_mode, amount_paid, status
    ) VALUES (
        v_ref, v_cid, p_customer_name, p_contact, p_email, p_address,
        p_occasion, p_venue, p_event_date, p_event_time, p_pax, p_special_notes,
        p_menu_type, p_package_id, p_custom_items,
        p_total_amount, p_payment_mode::payment_method, p_amount_paid, 'PENDING'
    )
    RETURNING id INTO v_bid;

    UPDATE customers SET total_events = total_events + 1, updated_at = NOW()
    WHERE id = v_cid;

    RETURN QUERY SELECT v_bid, v_ref;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: update_booking_status
-- Called when status badge is clicked in BookingPage
-- =============================================================================
CREATE OR REPLACE FUNCTION update_booking_status(
    p_booking_id  INT,
    p_new_status  TEXT
)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    UPDATE bookings
    SET status = p_new_status::booking_status, updated_at = NOW()
    WHERE id = p_booking_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: generate_invoice
-- Called from BillingPage "New Invoice"
-- =============================================================================
CREATE OR REPLACE FUNCTION generate_invoice(
    p_booking_id    INT,
    p_customer_name TEXT,
    p_event_date    DATE,
    p_total_amount  NUMERIC,
    p_amount_paid   NUMERIC,
    p_status        TEXT
)
RETURNS TABLE (invoice_id INT, invoice_ref TEXT)
LANGUAGE plpgsql AS $$
DECLARE
    v_ref TEXT;
    v_iid INT;
BEGIN
    v_ref := next_invoice_ref();

    INSERT INTO invoices (
        invoice_ref, booking_id, customer_name, event_date,
        total_amount, amount_paid, status
    ) VALUES (
        v_ref, p_booking_id, p_customer_name, p_event_date,
        p_total_amount, p_amount_paid, p_status::invoice_status
    )
    RETURNING id INTO v_iid;

    RETURN QUERY SELECT v_iid, v_ref;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: record_payment
-- Updates invoice paid amount and recalculates status
-- =============================================================================
CREATE OR REPLACE FUNCTION record_payment(
    p_invoice_id  INT,
    p_amount      NUMERIC
)
RETURNS invoice_status LANGUAGE plpgsql AS $$
DECLARE
    v_total   NUMERIC;
    v_paid    NUMERIC;
    v_status  invoice_status;
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

    RETURN v_status;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: calculate_total_amount
-- Matches BookingModal _update_cost logic
-- =============================================================================
CREATE OR REPLACE FUNCTION calculate_total_amount(
    p_pax        INT,
    p_package_id INT
)
RETURNS NUMERIC LANGUAGE plpgsql AS $$
DECLARE
    v_rate NUMERIC;
BEGIN
    SELECT price_per_pax INTO v_rate FROM packages WHERE id = p_package_id;
    RETURN p_pax * v_rate;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: update_kitchen_order_status
-- Called from KitchenPage advance/done buttons
-- =============================================================================
CREATE OR REPLACE FUNCTION update_kitchen_order_status(
    p_order_id   INT,
    p_new_status TEXT
)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    UPDATE kitchen_orders
    SET status = p_new_status::kitchen_status, updated_at = NOW()
    WHERE id = p_order_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: update_inventory
-- Called when inventory stock is adjusted
-- =============================================================================
CREATE OR REPLACE FUNCTION update_inventory(
    p_item_id   INT,
    p_delta     NUMERIC       -- positive = restock, negative = usage
)
RETURNS NUMERIC LANGUAGE plpgsql AS $$
DECLARE
    v_new_stock NUMERIC;
BEGIN
    UPDATE inventory
    SET stock = GREATEST(0, stock + p_delta), updated_at = NOW()
    WHERE id = p_item_id
    RETURNING stock INTO v_new_stock;

    RETURN v_new_stock;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: add_menu_item
-- Called from MenuPage "Add Item" dialog
-- =============================================================================
CREATE OR REPLACE FUNCTION add_menu_item(
    p_name     TEXT,
    p_category TEXT,
    p_package  TEXT,
    p_price    NUMERIC,
    p_status   TEXT
)
RETURNS INT LANGUAGE plpgsql AS $$
DECLARE
    v_id INT;
BEGIN
    INSERT INTO menu_items (name, category, package_tier, price, status)
    VALUES (
        p_name,
        p_category::menu_category,
        p_package::menu_package_tier,
        p_price,
        p_status::menu_status
    )
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$$;

-- =============================================================================
-- STORED PROCEDURE: dismiss_notification / mark_all_read
-- =============================================================================
CREATE OR REPLACE FUNCTION dismiss_notification(p_id INT)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    UPDATE notifications SET is_read = TRUE WHERE id = p_id;
END;
$$;

CREATE OR REPLACE FUNCTION mark_all_notifications_read()
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    UPDATE notifications SET is_read = TRUE WHERE is_read = FALSE;
END;
$$;

-- =============================================================================
-- VIEW: v_dashboard_kpis
-- Powers DashboardPage KPI cards
-- =============================================================================
CREATE OR REPLACE VIEW v_dashboard_kpis AS
SELECT
    (SELECT COUNT(*) FROM bookings WHERE event_date = CURRENT_DATE)                        AS todays_events,
    (SELECT COUNT(*) FROM bookings WHERE status = 'PENDING')                               AS pending_bookings,
    (SELECT COALESCE(SUM(total_amount),0) FROM bookings
     WHERE event_date BETWEEN date_trunc('week', CURRENT_DATE)
                          AND date_trunc('week', CURRENT_DATE) + INTERVAL '6 days')        AS weekly_revenue,
    (SELECT COALESCE(SUM(total_amount - amount_paid),0) FROM invoices WHERE status != 'Paid') AS unpaid_invoices,
    (SELECT COALESCE(SUM(pax),0) FROM bookings WHERE event_date = CURRENT_DATE)            AS todays_pax;

-- =============================================================================
-- VIEW: v_upcoming_events
-- Powers DashboardPage "Upcoming Events" + CalendarPage side panel
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
-- Powers DashboardPage "Inventory Alerts" - items below min_stock
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
-- Powers CalendarPage day cells: total pax per date
-- =============================================================================
CREATE OR REPLACE VIEW v_calendar_day_summary AS
SELECT
    event_date,
    COUNT(*)        AS booking_count,
    SUM(pax)        AS total_pax
FROM bookings
WHERE status != 'CANCELLED'
GROUP BY event_date;

-- =============================================================================
-- VIEW: v_reports_summary
-- Powers ReportsPage KPI + table
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
-- GRANT: single owner user (create separately, then grant)
-- psql -U postgres -c "CREATE USER catering_owner WITH PASSWORD 'change_me';"
-- =============================================================================
-- GRANT CONNECT ON DATABASE jayraldines_catering TO catering_owner;
-- GRANT USAGE  ON SCHEMA public TO catering_owner;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO catering_owner;
-- GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO catering_owner;
-- GRANT EXECUTE                        ON ALL FUNCTIONS IN SCHEMA public TO catering_owner;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
