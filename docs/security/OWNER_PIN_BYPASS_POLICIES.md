# Owner PIN Elevation & Rate-Limiting Policy

## 1. Triggers
The `OwnerAuthDialog` modal is triggered when non-admin users attempt restricted actions:
- Deleting an existing confirmed booking.
- Overriding a fixed package price with a custom manual discount.
- Accessing database backup management or resetting settings.

## 2. Security Thresholds
- PIN is checked against salted cryptographic hash in `users` table.
- 3 consecutive failed attempts lock the dialog for 60 seconds with a logged security audit entry.
