-- =============================================================================
-- FIX: v_customer_ledger
-- Run this against your existing database to make sure the view matches the
-- current schema. Safe to re-run — CREATE OR REPLACE VIEW does not touch data.
--
-- Symptom this fixes: the Customers > Ledger dialog always shows
-- "No ledger entries found for this customer" even for customers with
-- bookings/invoices/payments. utils/repository.get_customer_ledger() selects
-- entry_type, recorded_date, event_date, reference, description, debit,
-- credit, entry_status from this view — if the live view predates this
-- definition (or was never created), that query errors out and
-- ui/customers_page.py silently swallows the exception, rendering an empty
-- ledger instead of surfacing the problem.
--
-- Usage:
--   psql -U postgres -d jayraldines_catering -f fix_customer_ledger_view.sql
-- =============================================================================

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
