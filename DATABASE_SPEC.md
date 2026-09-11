# PostgreSQL Database Schema Specification

## Core Relational Tables
1. `business_info`: Global business preferences and email SMTP parameters.
2. `users` & `user_permissions`: Role-Based Access Control (Admin, Manager, Staff).
3. `customers` & `customer_addresses`: Customer master ledger and multi-tier loyalty.
4. `menu_items` & `packages`: Catering packages with customizable dish item choices.
5. `bookings`, `booking_menu_items`, `booking_additional_charges`: Event bookings ledger.
6. `invoices` & `payment_records`: Double-entry financial billing records.
7. `device_sessions`: Real-time client terminal monitoring and heartbeats.
