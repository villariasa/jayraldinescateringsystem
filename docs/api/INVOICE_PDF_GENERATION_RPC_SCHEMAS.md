# Invoice PDF Generation RPC Endpoint Payload Schema

## Endpoint: `POST /api/reports/invoice-pdf`

### Request Payload:
```json
{
  "booking_id": 1420,
  "include_breakdown": true,
  "watermark": "OFFICIAL_RECEIPT",
  "paper_size": "80mm_thermal"
}
```
