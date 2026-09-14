# SMS Notification Queue & Transactional Dispatch

## 1. Message Dispatch Pipeline
- **Triggers**: Booking confirmation, payment down payment receipt, 3-day event countdown reminder, post-event thank you message.
- **Gateway Failover**: Attempts local GSM AT-command modem first, failing over to HTTPS cloud SMS webhook APIs if cellular signal is weak.
