# Real-Time Order Dispatch Pipeline & Billing Triggers

## 1. Transaction Flow
Upon completion of the 6-step booking wizard, the system executes an automated transaction pipeline:

1. **Local Record Generation**: Generates booking, invoice, customer, and booking menu item records in SQLite.
2. **Immediate Server Dispatch**: Asynchronously dispatches a sync payload to `/api/sync/lan-sync`.
3. **Database Insertion**: PostgreSQL inserts the booking, generates the official invoice (`INV-XXXX`), records initial payments, and updates customer loyalty statistics.
4. **Receipt Generation**: Pre-renders digital PDF receipts and broadcasts confirmation toasts to the operator.
