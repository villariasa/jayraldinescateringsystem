# Customer Outbound Webhook Architecture

## 1. Webhook Events
Dispatches signed JSON webhooks upon critical booking milestones:

- `booking.created`: Sent when a client completes initial wizard booking.
- `payment.received`: Dispatched when down payment or final settlement is recorded.
- `event.reminded`: 72-hour automated countdown notification.
- **Signature Verification**: Payloads signed with `X-Jayraldines-Signature` HMAC-SHA256 headers.
