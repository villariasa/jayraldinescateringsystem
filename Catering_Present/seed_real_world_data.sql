-- =============================================================================
-- REAL-WORLD SAMPLE DATASET FOR JAYRALDINE'S CATERING SERVICES
-- Populates authentic Filipino catering customers, menu items, packages,
-- bookings, invoices, payment records, inventory, and expense tracking.
-- =============================================================================

BEGIN;

-- 1. TRUNCATE EXISTING TABLES CLEANLY
TRUNCATE TABLE payment_records, invoices, booking_menu_items, kitchen_tasks, kitchen_orders,
               customer_follow_ups, communication_logs, audit_logs, notifications,
               calendar_events, expenses, package_items, packages, menu_items,
               bookings, customers CASCADE;

-- Reset sequence values
ALTER SEQUENCE customers_cus_id_seq RESTART WITH 1;
ALTER SEQUENCE menu_items_mi_id_seq RESTART WITH 1;
ALTER SEQUENCE packages_pkg_id_seq RESTART WITH 1;
ALTER SEQUENCE bookings_bk_id_seq RESTART WITH 1;
ALTER SEQUENCE invoices_inv_id_seq RESTART WITH 1;
ALTER SEQUENCE payment_records_pr_id_seq RESTART WITH 1;
ALTER SEQUENCE expenses_exp_id_seq RESTART WITH 1;
ALTER SEQUENCE seq_booking_ref RESTART WITH 1;
ALTER SEQUENCE seq_invoice_ref RESTART WITH 1;
ALTER SEQUENCE seq_order_ref RESTART WITH 1;

-- 2. INSERT REAL-LIFE CUSTOMERS (CEBU & VISAYAS LOCATIONS)
INSERT INTO customers (cus_id, cus_name, cus_contact, cus_email, cus_address, cus_status, cus_loyalty_tier, cus_total_events) VALUES
(1, 'Medy Villarias', '09171234567', 'medy.villarias@gmail.com', 'Gorordo Ave, Lahug, Cebu City', 'Active', 'VIP', 5),
(2, 'Maria Clara Santos', '09209876543', 'mariaclara.santos@yahoo.com', 'Escario St, Capitol Site, Cebu City', 'Active', 'Gold', 3),
(3, 'Engr. Rodrigo Tan', '09183334444', 'rodrigo.tan@tanconstruction.ph', 'Banilad, Mandaue City', 'Active', 'VIP', 8),
(4, 'Dr. Vanessa Lim', '09275556666', 'vanessa.lim@chunghua.com.ph', 'Fuente Osmeña, Cebu City', 'Active', 'Silver', 2),
(5, 'Capt. Juanito Dela Cruz', '09194445555', 'juanito.delacruz@gmail.com', 'Pardo, Cebu City', 'Active', 'Gold', 4),
(6, 'Sofia Mendoza-Reyes', '09167778888', 'sofia.reyes@smprime.com', 'IT Park, Apas, Cebu City', 'Active', 'Silver', 2),
(7, 'Atty. Fernando Gomez', '09228889999', 'fgomez@gomezlaw.ph', 'SRP, Talisay City', 'Active', 'Bronze', 1),
(8, 'Chef Paolo Alonzo', '09151112222', 'paolo.alonzo@bistro.ph', 'Mactan Newtown, Lapu-Lapu City', 'Active', 'Bronze', 1),
(9, 'Bea Alonzo-Garcia', '09179990000', 'bea.garcia@outlook.com', 'Guadalupe, Cebu City', 'Active', 'Silver', 2),
(10, 'Davao Agri Corp', '09187776655', 'events@davaoagri.com', 'Mandaue Industrial Zone, Mandaue City', 'Active', 'Gold', 3);

SELECT setval('customers_cus_id_seq', 10);

-- 3. INSERT AUTHENTIC MENU ITEMS
INSERT INTO menu_items (mi_id, mi_name, mi_description, mi_category, mi_package_tier, mi_price, mi_status) VALUES
(1,  'Lechon de Cebu (Whole Roast Pig)', 'Crispy skin, roasted with lemongrass, garlic, and native herbs.', 'Main Course', 'Premium', 8500.00, 'Available'),
(2,  'Beef Caldereta Special', 'Tender beef chunks stewed in rich tomato liver sauce with bell peppers.', 'Main Course', 'Standard', 280.00, 'Available'),
(3,  'Pork Humba Bisaya', 'Slow-cooked pork belly in soy-vinegar sauce with banana blossoms.', 'Main Course', 'Budget', 240.00, 'Available'),
(4,  'Chicken Inasal Bacolod', 'Grilled marinated chicken quarters brushed with annatto oil.', 'Main Course', 'Budget', 210.00, 'Available'),
(5,  'Kare-Kare with Homemade Bagoong', 'Rich peanut stew with ox tripe, vegetables, and savory shrimp paste.', 'Main Course', 'Standard', 260.00, 'Available'),
(6,  'Fish Fillet in Tartar Sauce', 'Crispy golden dory fillets served with creamy homemade tartar sauce.', 'Main Course', 'Standard', 220.00, 'Available'),
(7,  'Sweet & Sour Pork Ribs', 'Crispy pork ribs tossed in vibrant sweet and sour pineapple glaze.', 'Main Course', 'Standard', 250.00, 'Available'),
(8,  'Garlic Butter Shrimp', 'Fresh tiger prawns sauteed in rich garlic butter and herbs.', 'Main Course', 'Premium', 320.00, 'Available'),
(9,  'Beef Broccoli in Oyster Sauce', 'Tender sliced beef sirloin sauteed with fresh broccoli florets.', 'Main Course', 'Standard', 270.00, 'Available'),
(10, 'Pancit Canton Special', 'Stir-fried egg noodles with pork, chicken liver, and mixed vegetables.', 'Noodles', 'Budget', 160.00, 'Available'),
(11, 'Pancit Palabok Supreme', 'Rice noodles topped with shrimp sauce, crushed chicharon, and boiled eggs.', 'Noodles', 'Standard', 180.00, 'Available'),
(12, 'Creamy Carbonara with Bacon', 'Fettuccine in rich cream sauce topped with crispy bacon bits.', 'Noodles', 'Standard', 190.00, 'Available'),
(13, 'Baked Macaroni Cheese Delight', 'Elbow macaroni baked in rich meat sauce and topped with melted cheese.', 'Noodles', 'Standard', 200.00, 'Available'),
(14, 'Sinigang na Baboy sa Sampalok', 'Pork ribs in sour tamarind broth with kangkong, radish, and taro.', 'Soup', 'Standard', 180.00, 'Available'),
(15, 'Classic Chicken Tinola sa Gabi', 'Native chicken in ginger papaya soup with chili leaves.', 'Soup', 'Budget', 150.00, 'Available'),
(16, 'Cream of Mushroom Soup', 'Velvety mushroom soup served with garlic croutons.', 'Soup', 'Budget', 130.00, 'Available'),
(17, 'Special Pinakbet sa Bagoong', 'Sauteed squash, eggplant, okra, and ampalaya with crispy pork bagnet.', 'Vegetables', 'Budget', 140.00, 'Available'),
(18, 'Chopsuey Special with Seafood', 'Crispy stir-fried vegetables with shrimp, squid balls, and quail eggs.', 'Vegetables', 'Standard', 160.00, 'Available'),
(19, 'Biko sa Latik', 'Sticky sweet rice cake topped with caramelized coconut cream latik.', 'Dessert', 'Budget', 90.00, 'Available'),
(20, 'Buko Pandan Salad', 'Young coconut strips and pandan jelly cubes in sweetened cream.', 'Dessert', 'Budget', 110.00, 'Available'),
(21, 'Leche Flan Supreme', 'Rich and silky caramel custard cooked with fresh egg yolks.', 'Dessert', 'Standard', 120.00, 'Available'),
(22, 'Mango Float Deluxe', 'Chilled Graham crackers layered with fresh Cebu mangoes and cream.', 'Dessert', 'Standard', 130.00, 'Available'),
(23, 'Unli Steamed Jasmine Rice', 'Fragrant steamed white Jasmine rice.', 'Other', 'Budget', 50.00, 'Available'),
(24, 'Signature Iced Tea (Per Gallon)', 'House-blend citrus iced tea served chilled.', 'Drinks', 'Budget', 150.00, 'Available');

SELECT setval('menu_items_mi_id_seq', 24);

-- 4. INSERT CATERING PACKAGES
INSERT INTO packages (pkg_id, pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax) VALUES
(1, 'Budget Fiesta Package', 'Affordable complete catering package perfect for intimate birthdays and family gatherings.', 350.00, 30),
(2, 'Standard Celebration Package', 'Most popular catering option for debuts, baptismals, anniversaries, and reunions.', 550.00, 50),
(3, 'Grand Fiesta Package', 'Grand banquet package featuring Lechon de Cebu, full buffet setup, and table skirts.', 850.00, 80),
(4, 'VIP Executive Package', 'Top-tier luxury experience for corporate galas and high-end weddings with waiter service.', 1200.00, 100);

SELECT setval('packages_pkg_id_seq', 4);

-- Package Menu Linkages
INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_custom_price) VALUES
(1, 3, 240.00), (1, 4, 210.00), (1, 10, 160.00), (1, 19, 90.00), (1, 23, 50.00),
(2, 2, 280.00), (2, 5, 260.00), (2, 6, 220.00), (2, 11, 180.00), (2, 14, 180.00), (2, 21, 120.00), (2, 23, 50.00),
(3, 1, 8500.00), (3, 2, 280.00), (3, 5, 260.00), (3, 8, 320.00), (3, 12, 190.00), (3, 14, 180.00), (3, 18, 160.00), (3, 21, 120.00), (3, 22, 130.00), (3, 23, 50.00),
(4, 1, 8500.00), (4, 2, 280.00), (4, 8, 320.00), (4, 9, 270.00), (4, 12, 190.00), (4, 13, 200.00), (4, 14, 180.00), (4, 18, 160.00), (4, 21, 120.00), (4, 22, 130.00), (4, 23, 50.00), (4, 24, 150.00);

-- 5. INSERT REAL-WORLD BOOKINGS & ORDERS
INSERT INTO bookings (bk_id, bk_booking_ref, bk_customer_id, bk_customer_name, bk_contact, bk_email, bk_address, bk_occasion, bk_venue, bk_event_date, bk_event_time, bk_pax, bk_special_notes, bk_menu_type, bk_package_id, bk_total_amount, bk_payment_mode, bk_amount_paid, bk_status, bk_created_at) VALUES
(1, 'BKG-001', 1, 'Medy Villarias', '09171234567', 'medy.villarias@gmail.com', 'Gorordo Ave, Lahug, Cebu City', 'Wedding', 'Waterfront Hotel Grand Ballroom, Lahug', CURRENT_DATE - INTERVAL '15 days', '17:30:00', 150, 'Requires red carpet aisle setup and VIP head table arrangement.', 'package', 3, 127500.00, 'Bank Transfer', 127500.00, 'COMPLETED', NOW() - INTERVAL '30 days'),

(2, 'BKG-002', 2, 'Maria Clara Santos', '09209876543', 'mariaclara.santos@yahoo.com', 'Escario St, Capitol Site, Cebu City', 'Birthday', 'Chateau de Busay, Cebu City', CURRENT_DATE - INTERVAL '5 days', '18:00:00', 80, 'Golden 50th birthday celebration theme.', 'package', 2, 44000.00, 'GCash', 44000.00, 'COMPLETED', NOW() - INTERVAL '20 days'),

(3, 'BKG-003', 3, 'Engr. Rodrigo Tan', '09183334444', 'rodrigo.tan@tanconstruction.ph', 'Banilad, Mandaue City', 'Corporate', 'Marco Polo Plaza Ballroom, Nivel Hills', CURRENT_DATE + INTERVAL '2 days', '19:00:00', 200, 'Annual Corporate Contractors Gala. Needs official invoice upon completion.', 'package', 4, 240000.00, 'Bank Transfer', 120000.00, 'CONFIRMED', NOW() - INTERVAL '10 days'),

(4, 'BKG-004', 4, 'Dr. Vanessa Lim', '09275556666', 'vanessa.lim@chunghua.com.ph', 'Fuente Osmeña, Cebu City', 'Anniversary', 'Casino Español de Cebu, Juana Osmeña', CURRENT_DATE + INTERVAL '7 days', '18:30:00', 100, 'Silver Wedding Anniversary dinner.', 'package', 3, 85000.00, 'Bank Transfer', 42500.00, 'CONFIRMED', NOW() - INTERVAL '8 days'),

(5, 'BKG-005', 5, 'Capt. Juanito Dela Cruz', '09194445555', 'juanito.delacruz@gmail.com', 'Pardo, Cebu City', 'Debut', 'Montebello Villa Hotel Pavilion', CURRENT_DATE + INTERVAL '12 days', '16:00:00', 120, '18th Debut Party for daughter Princess Dela Cruz.', 'package', 2, 66000.00, 'Cash', 66000.00, 'CONFIRMED', NOW() - INTERVAL '6 days'),

(6, 'BKG-006', 6, 'Sofia Mendoza-Reyes', '09167778888', 'sofia.reyes@smprime.com', 'IT Park, Apas, Cebu City', 'Corporate', 'Cebu Trade Hall, SM City Cebu', CURRENT_DATE + INTERVAL '18 days', '11:30:00', 150, 'SM Prime Product Launch Luncheon.', 'package', 1, 52500.00, 'Bank Transfer', 26250.00, 'CONFIRMED', NOW() - INTERVAL '5 days'),

(7, 'BKG-007', 7, 'Atty. Fernando Gomez', '09228889999', 'fgomez@gomezlaw.ph', 'SRP, Talisay City', 'Reunion', 'Villa Elizabeth Beach Resort', CURRENT_DATE + INTERVAL '25 days', '12:00:00', 60, 'Grand Gomez Family Reunion.', 'package', 1, 21000.00, 'GCash', 0.00, 'PENDING', NOW() - INTERVAL '2 days'),

(8, 'BKG-008', 8, 'Chef Paolo Alonzo', '09151112222', 'paolo.alonzo@bistro.ph', 'Mactan Newtown, Lapu-Lapu City', 'Graduation', 'Mactan Newtown Function Hall', CURRENT_DATE + INTERVAL '30 days', '17:00:00', 40, 'Culinary Arts Graduation Dinner.', 'package', 1, 14000.00, 'GCash', 14000.00, 'CONFIRMED', NOW() - INTERVAL '1 day');

SELECT setval('bookings_bk_id_seq', 8);

-- Booking Menu Items
INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id) VALUES
(1, 1), (1, 2), (1, 8), (1, 12), (1, 21),
(2, 2), (2, 5), (2, 11), (2, 21),
(3, 1), (3, 8), (3, 9), (3, 13),
(4, 1), (4, 2), (4, 5), (4, 18),
(5, 2), (5, 6), (5, 11), (5, 21);

-- 6. INVOICES & PAYMENT RECORDS
INSERT INTO invoices (inv_id, inv_invoice_ref, inv_booking_id, inv_customer_name, inv_event_date, inv_total_amount, inv_amount_paid, inv_status, inv_created_at) VALUES
(1, 'INV-001', 1, 'Medy Villarias', CURRENT_DATE - INTERVAL '15 days', 127500.00, 127500.00, 'Paid', NOW() - INTERVAL '30 days'),
(2, 'INV-002', 2, 'Maria Clara Santos', CURRENT_DATE - INTERVAL '5 days', 44000.00, 44000.00, 'Paid', NOW() - INTERVAL '20 days'),
(3, 'INV-003', 3, 'Engr. Rodrigo Tan', CURRENT_DATE + INTERVAL '2 days', 240000.00, 120000.00, 'Partial', NOW() - INTERVAL '10 days'),
(4, 'INV-004', 4, 'Dr. Vanessa Lim', CURRENT_DATE + INTERVAL '7 days', 85000.00, 42500.00, 'Partial', NOW() - INTERVAL '8 days'),
(5, 'INV-005', 5, 'Capt. Juanito Dela Cruz', CURRENT_DATE + INTERVAL '12 days', 66000.00, 66000.00, 'Paid', NOW() - INTERVAL '6 days'),
(6, 'INV-006', 6, 'Sofia Mendoza-Reyes', CURRENT_DATE + INTERVAL '18 days', 52500.00, 26250.00, 'Partial', NOW() - INTERVAL '5 days'),
(7, 'INV-007', 7, 'Atty. Fernando Gomez', CURRENT_DATE + INTERVAL '25 days', 21000.00, 0.00, 'Unpaid', NOW() - INTERVAL '2 days'),
(8, 'INV-008', 8, 'Chef Paolo Alonzo', CURRENT_DATE + INTERVAL '30 days', 14000.00, 14000.00, 'Paid', NOW() - INTERVAL '1 day');

SELECT setval('invoices_inv_id_seq', 8);

-- Payment Records
INSERT INTO payment_records (pr_id, pr_invoice_id, pr_amount, pr_payment_date, pr_method, pr_note) VALUES
(1, 1, 127500.00, CURRENT_DATE - INTERVAL '15 days', 'Bank Transfer', 'Full settlement for Villarias Wedding (Ref: BDO-9921)'),
(2, 2, 44000.00, CURRENT_DATE - INTERVAL '5 days', 'GCash', 'Full settlement for Santos Birthday (Ref: GC-88301)'),
(3, 3, 120000.00, CURRENT_DATE - INTERVAL '10 days', 'Bank Transfer', '50% Corporate reservation deposit (Ref: CHK-0044)'),
(4, 4, 42500.00, CURRENT_DATE - INTERVAL '8 days', 'Bank Transfer', '50% Anniversary deposit (Ref: MBT-33211)'),
(5, 5, 66000.00, CURRENT_DATE - INTERVAL '6 days', 'Cash', 'Full cash payment for Debut (Rec: CASH-0012)'),
(6, 6, 26250.00, CURRENT_DATE - INTERVAL '5 days', 'Bank Transfer', 'Corporate event deposit (Ref: BPI-77120)'),
(7, 8, 14000.00, CURRENT_DATE - INTERVAL '1 day', 'GCash', 'Full settlement for Graduation Dinner (Ref: GC-9940)');

SELECT setval('payment_records_pr_id_seq', 7);

-- 7. KITCHEN ORDERS
INSERT INTO kitchen_orders (ko_id, ko_order_ref, ko_booking_id, ko_client_name, ko_event_name, ko_pax, ko_items_desc, ko_status, ko_created_at) VALUES
(1, 'KO-001', 3, 'Engr. Rodrigo Tan', 'Tan Construction Annual Gala', 200, '2x Lechon de Cebu, Garlic Butter Shrimp, Beef Broccoli, Baked Macaroni, Leche Flan', 'In Progress', NOW() - INTERVAL '1 day'),
(2, 'KO-002', 4, 'Dr. Vanessa Lim', 'Silver Wedding Anniversary', 100, '1x Lechon de Cebu, Beef Caldereta, Kare-Kare, Chopsuey, Buko Pandan', 'Queued', NOW()),
(3, 'KO-003', 5, 'Capt. Juanito Dela Cruz', 'Princess 18th Debut', 120, 'Beef Caldereta, Fish Fillet, Pancit Palabok, Leche Flan', 'Preparing', NOW());

SELECT setval('kitchen_orders_ko_id_seq', 3);

-- Kitchen Tasks
INSERT INTO kitchen_tasks (kt_order_id, kt_task_label, kt_is_done, kt_sort_order) VALUES
(1, 'Roast 2 whole pigs (Lechon de Cebu)', FALSE, 1),
(1, 'Prep 25kg Fresh Tiger Prawns for Garlic Butter Shrimp', TRUE, 2),
(1, 'Slice beef sirloin and steam broccoli', TRUE, 3),
(1, 'Bake 10 pans of Macaroni Cheese', FALSE, 4),
(2, 'Inspect & season Lechon pig', FALSE, 1),
(2, 'Marinate beef sirloin for Caldereta', FALSE, 2),
(2, 'Prepare Buko Pandan cream mixture', TRUE, 3);

-- 8. EXPENSES (OPERATING & FOOD COSTS)
INSERT INTO expenses (exp_id, exp_category, exp_description, exp_amount, exp_expense_date) VALUES
(1, 'Food Cost', 'Procurement of 2 Whole Pigs for Lechon from Carcar Supplier', 14000.00, CURRENT_DATE - INTERVAL '12 days'),
(2, 'Food Cost', 'Fresh Seafood & Prawns from Carbon Market', 8500.00, CURRENT_DATE - INTERVAL '10 days'),
(3, 'Labor', 'Service Crew & Chef Wages for Villarias Wedding Banquet', 6500.00, CURRENT_DATE - INTERVAL '15 days'),
(4, 'Transport', 'Diesel & Transport Fuel for Catering Van (Lahug & Mactan trips)', 2800.00, CURRENT_DATE - INTERVAL '8 days'),
(5, 'Utilities', '50kg LPG Cooking Gas Refill (2 Tanks)', 3400.00, CURRENT_DATE - INTERVAL '6 days'),
(6, 'Equipment', 'Rental of Additional Chafing Dishes & Tiffany Chairs', 4200.00, CURRENT_DATE - INTERVAL '4 days'),
(7, 'Other', 'Laundry & Sanitation of Table Linens & Napkins', 1800.00, CURRENT_DATE - INTERVAL '2 days');

SELECT setval('expenses_exp_id_seq', 7);

-- 9. AUDIT LOGS
INSERT INTO audit_logs (al_actor, al_action, al_table_name, al_record_id, al_created_at) VALUES
('Owner', 'CREATE', 'bookings', 1, NOW() - INTERVAL '30 days'),
('Owner', 'APPROVE', 'bookings', 1, NOW() - INTERVAL '28 days'),
('System', 'CREATE', 'invoices', 1, NOW() - INTERVAL '28 days'),
('Owner', 'PAYMENT', 'payment_records', 1, NOW() - INTERVAL '15 days'),
('Owner', 'CREATE', 'bookings', 3, NOW() - INTERVAL '10 days'),
('Owner', 'APPROVE', 'bookings', 3, NOW() - INTERVAL '9 days');

COMMIT;
