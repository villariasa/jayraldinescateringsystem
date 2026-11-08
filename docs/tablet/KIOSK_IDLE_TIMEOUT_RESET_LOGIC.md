# Kiosk Guest Idle Timeout Reset Logic

## Session Lifecycle
- 60-second warning dialog appears before clearing in-progress orders.
- Tapping anywhere resets idle timer back to full duration.
- Clears temporary order draft to protect guest privacy if abandoned.
