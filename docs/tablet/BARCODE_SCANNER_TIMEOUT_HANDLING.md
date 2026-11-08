# Barcode Scanner Timeout Handling

## Kiosk Check-In Flow
- Kiosk scanner listener resets after 15 seconds of inactivity.
- Audible chime prompts guest if partial barcode string is detected.
- Prevents scanner hardware buffer lockups during heavy guest queues.
