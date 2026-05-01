\connect jayraldines_catering

CREATE OR REPLACE VIEW v_payment_methods AS
SELECT payment_mode::TEXT AS method, COUNT(*) AS total
FROM bookings
WHERE status IN ('CONFIRMED', 'COMPLETED')
GROUP BY payment_mode;

CREATE OR REPLACE VIEW v_top_menu_items AS
SELECT mi.name AS item, COUNT(*) AS order_count
FROM booking_menu_items bmi
JOIN menu_items mi ON mi.id = bmi.item_id
JOIN bookings b ON b.id = bmi.booking_id
WHERE b.status IN ('CONFIRMED', 'COMPLETED')
GROUP BY mi.name
ORDER BY order_count DESC
LIMIT 10;

CREATE OR REPLACE VIEW v_customer_order_frequency AS
SELECT name, booking_count FROM (
    SELECT customer_name AS name, COUNT(*) AS booking_count
    FROM bookings
    WHERE status IN ('CONFIRMED', 'COMPLETED')
    GROUP BY customer_name
    ORDER BY booking_count DESC LIMIT 5
) top5
UNION ALL
SELECT 'Others', COUNT(*) FROM (
    SELECT customer_name FROM (
        SELECT customer_name, RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
        FROM bookings
        WHERE status IN ('CONFIRMED', 'COMPLETED')
        GROUP BY customer_name
    ) ranked WHERE rnk > 5
) rest;

CREATE OR REPLACE VIEW v_report_kpis AS
SELECT
    COUNT(*) AS total_bookings,
    COALESCE(SUM(b.pax), 0)::INT AS total_pax,
    COALESCE((SELECT SUM(total_amount) FROM invoices), 0)::FLOAT AS total_revenue,
    COALESCE((SELECT SUM(total_amount - amount_paid) FROM invoices WHERE status != 'Paid'), 0)::FLOAT AS unpaid_amount,
    COALESCE((SELECT COUNT(*) FROM bookings WHERE created_at::DATE = CURRENT_DATE AND status IN ('CONFIRMED', 'COMPLETED')), 0)::INT AS today_bookings,
    COALESCE((SELECT COUNT(*) FROM bookings
              WHERE created_at::DATE BETWEEN date_trunc('week', CURRENT_DATE)::DATE
                                        AND (date_trunc('week', CURRENT_DATE) + INTERVAL '6 days')::DATE
                AND status IN ('CONFIRMED', 'COMPLETED')), 0)::INT AS week_bookings
FROM bookings b
WHERE b.status IN ('CONFIRMED', 'COMPLETED');
