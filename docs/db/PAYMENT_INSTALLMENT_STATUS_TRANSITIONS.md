# Booking Payment Installment Status Transitions

## State Flow
- `Pending Deposit` -> `Partial Downpayment` -> `Fully Paid` -> `Refunded / Voided`.
- Transition requires authorized cashier role.
- Every status change triggers automated SMS receipt to client.
