# SQLite to PostgreSQL Data Reconciliation & Checksum Verification

## 1. Verification Protocol
Executes automated checksum validation following data migrations:

- **Row Count Matching**: Confirms identical row counts across `bookings`, `invoices`, `customers`, and `menu_items`.
- **Financial Balance Reconciliation**: Computes sum of `inv_total_amount` across source and target databases with zero discrepancy tolerance.
- **Foreign Key Integrity**: Validates all child records resolve to valid parent IDs.
