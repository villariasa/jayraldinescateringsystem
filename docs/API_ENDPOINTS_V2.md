# REST API v2 Endpoints & Schema Contracts Specification

## 1. Endpoints Overview
- `GET /api/v2/health`: Service health and database ping status.
- `GET /api/v2/packages`: List of all active catering packages and dishes.
- `POST /api/v2/bookings`: Create or update a banquet booking.
- `POST /api/v2/sync/batch`: Atomic batch mutation ingestion for offline kiosks.
- `GET /api/v2/inventory/low-stock`: List of ingredients requiring replenishment.
