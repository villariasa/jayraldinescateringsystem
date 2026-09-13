# Relational Database Data Dictionary

## 1. Core Tables
- `users`: Staff credentials, roles (Admin, Cashier, Kitchen, Owner), active status.
- `bookings`: Event date, venue, guest count, status, payment status, package id.
- `customers`: Client full name, phone number, email address, corporate company.
- `menu_packages`: Package title, per-head price, category inclusion allowances.
- `inventory_items`: Item name, unit, unit cost, quantity on hand, minimum par.
- `audit_logs`: Timestamp, user id, action, details, cryptographic hash.
