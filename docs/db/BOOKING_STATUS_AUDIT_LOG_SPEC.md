# Booking Status Audit Trail Logging Spec

## Database Triggers
- Every update to `bookings.status` writes to `booking_status_audit` table.
- Captures previous status, new status, timestamp, and user id.
- Prevents unauthorized cancellations or unconfirmed booking overrides.
