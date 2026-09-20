# REST Synchronization API v3 Contract

## 1. Endpoints
- `GET /api/health`: Returns server status, current timestamp, and active database mode.
- `GET /api/packages`: Returns current menu packages and dish catalogs.
- `POST /api/bookings/create`: Accepts new catering reservation payloads from tablets.
- `GET /api/devices`: Returns connected tablet terminals and heartbeat timestamps.
- `POST /api/sync/batch`: Atomic transactional batch mutations.
