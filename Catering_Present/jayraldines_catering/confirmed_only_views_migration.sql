\connect jayraldines_catering

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
    COUNT(*) AS total_bookings,
    COALESCE(SUM(b.bk_pax), 0)::INT AS total_pax,
    COALESCE((SELECT SUM(inv_total_amount) FROM invoices), 0)::FLOAT AS total_revenue,
    COALESCE((SELECT SUM(inv_total_amount - inv_amount_paid) FROM invoices WHERE inv_status != 'Paid'), 0)::FLOAT AS unpaid_amount,
    COALESCE((SELECT COUNT(*) FROM bookings WHERE bk_created_at::DATE = CURRENT_DATE AND bk_status IN ('CONFIRMED', 'COMPLETED')), 0)::INT AS today_bookings,
    COALESCE((SELECT COUNT(*) FROM bookings
              WHERE bk_created_at::DATE BETWEEN date_trunc('week', CURRENT_DATE)::DATE
                                            AND (date_trunc('week', CURRENT_DATE) + INTERVAL '6 days')::DATE
                AND bk_status IN ('CONFIRMED', 'COMPLETED')), 0)::INT AS week_bookings
FROM bookings b
WHERE b.bk_status IN ('CONFIRMED', 'COMPLETED');
