# Event Sourcing & Mutation Journal Architecture Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Core Ledger, Offline Sync, Distributed State Management

---

## 1. Overview
In a multi-device catering environment with desktop cashier terminals, kitchen displays, and mobile waiter tablets, concurrent writes to booking states can produce race conditions. This specification formalizes an **Event Sourcing Mutation Journal** pattern.

Instead of performing in-place mutable updates directly on SQLite tables, state changes are captured as an append-only stream of immutable mutation events.

---

## 2. Event Schema & Types

```json
{
  "event_id": "evt_7f8a9b1c-3d2e-4f5a-8b9c-0d1e2f3a4b5c",
  "aggregate_id": "BK-20261021-0042",
  "aggregate_type": "BOOKING",
  "event_type": "BOOKING_DOWNPAYMENT_RECORDED",
  "payload": {
    "amount": 15000.00,
    "payment_method": "GCash",
    "reference_no": "GC-98234112",
    "received_by": "Cashier-01"
  },
  "sequence_no": 4,
  "client_timestamp": "2026-10-07T08:30:00+08:00",
  "server_received_at": "2026-10-07T08:30:02+08:00"
}
```

### Supported Event Types
1. `BOOKING_CREATED`
2. `BOOKING_DISH_SELECTION_UPDATED`
3. `BOOKING_ADDON_CHARGED`
4. `BOOKING_DOWNPAYMENT_RECORDED`
5. `BOOKING_FINAL_SETTLEMENT_RECORDED`
6. `BOOKING_RESCHEDULED`
7. `BOOKING_CANCELLED`

---

## 3. Projection Engine
A lightweight projection worker continuously consumes the mutation journal in sequence and materializes the canonical query-optimized read models in `bookings`, `invoices`, and `cash_flow_transactions`.\n