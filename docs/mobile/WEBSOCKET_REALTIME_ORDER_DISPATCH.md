# WebSocket Real-Time Order Dispatch Specification

## 1. Message Frame
```json
{
  "event": "NEW_ORDER_DISPATCHED",
  "booking_id": 1042,
  "venue": "Heritage Ballroom",
  "dishes": [{"id": 12, "name": "Beef Caldereta", "qty": 150}],
  "timestamp": "2026-09-20T22:45:00+08:00"
}
```
